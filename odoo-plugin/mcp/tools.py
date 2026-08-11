"""Tool definitions and dispatch for the Odoo MCP server.

Deliberately small: ten tools. Every MCP tool schema is injected into the
context window of every session where this server is enabled, so a sprawling
surface is a permanent tax on unrelated work. Servers in the wild range from 3
to 138 tools; this one stays near the low end and pushes breadth into
parameters instead of new tool names.

Every state-changing path goes through guards.check_write_allowed. No tool here
offers SQL, shell, filesystem or module-installation access.
"""

from __future__ import annotations

import json
from typing import Any

import guards
from guards import GuardError
from odoo_client import OdooClient, OdooError
from profiles import ProfileError, discover

DEFAULT_LIMIT = 50
MAX_LIMIT = 500
MAX_STR = 800          # per string value before truncation
MAX_CHARS = 60000      # per tool result


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

_DOMAIN = {
    "type": "array",
    "description": "Odoo domain, e.g. [[\"state\",\"=\",\"draft\"],[\"amount\",\">\",100]]. "
                   "Empty list matches all records the user may read.",
}
_FIELDS = {
    "type": "array",
    "items": {"type": "string"},
    "description": "Field names to return. Always pass this - omitting it returns every "
                   "field and wastes context.",
}
_CONTEXT = {
    "type": "object",
    "description": "Odoo context overrides, e.g. {\"allowed_company_ids\":[1,2]}, "
                   "{\"lang\":\"fr_FR\"}, {\"active_test\":false} to include archived records.",
}

TOOLS = [
    {
        "name": "odoo_status",
        "description": "Show which Odoo instance is connected: profile, URL, database, "
                       "server version, which API is in use (JSON-2 or XML-RPC), the "
                       "authenticated user, company context and read/write mode. "
                       "Call this first, and whenever a call fails unexpectedly. "
                       "If nothing is configured it explains exactly how to set it up.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "suggest_config": {
                    "type": "boolean",
                    "description": "Also scan the project directory for Odoo config hints "
                                   "and propose a starter profile.",
                }
            },
        },
    },
    {
        "name": "odoo_list_models",
        "description": "List Odoo models, optionally filtered. Use to discover the "
                       "technical model name behind a business concept.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Substring matched against model name and description, "
                                   "e.g. 'sale', 'account.move', 'partner'.",
                },
                "transient": {
                    "type": "boolean",
                    "description": "Include transient (wizard) models. Default false.",
                },
                "limit": {"type": "integer", "description": "Default 50, max 500."},
            },
        },
    },
    {
        "name": "odoo_inspect_model",
        "description": "Describe one model's fields: type, label, required, readonly, "
                       "stored, relation target, selection values. Also reports the "
                       "connected user's create/read/write/unlink rights on it. "
                       "Use before searching or writing an unfamiliar model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "e.g. res.partner"},
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Restrict to these field names. Omit for all fields.",
                },
                "field_pattern": {
                    "type": "string",
                    "description": "Substring filter over field names/labels, e.g. 'date'.",
                },
            },
            "required": ["model"],
        },
    },
    {
        "name": "odoo_search",
        "description": "Search and read records (search_read). The main read tool. "
                       "Runs under the connected user's access rights and record rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": _DOMAIN,
                "fields": _FIELDS,
                "limit": {"type": "integer", "description": "Default 50, max 500."},
                "offset": {"type": "integer"},
                "order": {"type": "string", "description": "e.g. 'date desc, id desc'"},
                "context": _CONTEXT,
            },
            "required": ["model"],
        },
    },
    {
        "name": "odoo_count",
        "description": "Count matching records without fetching them (search_count). "
                       "Use before a broad search to check the result size.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": _DOMAIN,
                "context": _CONTEXT,
            },
            "required": ["model"],
        },
    },
    {
        "name": "odoo_read_group",
        "description": "Aggregate records grouped by one or more fields (read_group): "
                       "sums, counts, averages. Use for analytics instead of pulling "
                       "many rows and totalling them yourself.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "domain": _DOMAIN,
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Aggregates, e.g. [\"amount_total:sum\",\"id:count\"].",
                },
                "groupby": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Group keys, e.g. [\"partner_id\"] or [\"date:month\"].",
                },
                "limit": {"type": "integer"},
                "orderby": {"type": "string"},
                "lazy": {
                    "type": "boolean",
                    "description": "Default true (groups by the first key only). Set false "
                                   "to group by every key at once.",
                },
                "context": _CONTEXT,
            },
            "required": ["model", "groupby"],
        },
    },
    {
        "name": "odoo_call",
        "description": "Call a public model method not covered by the other tools "
                       "(e.g. default_get, name_search, get_views, onchange, or a business "
                       "method). Private methods (leading underscore) and code-execution / "
                       "module-install methods are refused. Methods that are not known to be "
                       "read-only require the profile to be in write mode.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "method": {"type": "string"},
                "ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Record ids the method acts on, if it is a record method.",
                },
                "kwargs": {
                    "type": "object",
                    "description": "Keyword arguments for the method.",
                },
                "context": _CONTEXT,
            },
            "required": ["model", "method"],
        },
    },
    {
        "name": "odoo_create",
        "description": "Create one or more records. Requires the profile to be in write "
                       "mode. Returns the new ids.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "values": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of field->value objects, one per record.",
                },
                "context": _CONTEXT,
            },
            "required": ["model", "values"],
        },
    },
    {
        "name": "odoo_write",
        "description": "Update existing records. Requires write mode. Always confirm the "
                       "target ids with odoo_search first - a wrong domain can update far "
                       "more rows than intended.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "integer"}},
                "values": {"type": "object", "description": "Field -> new value."},
                "context": _CONTEXT,
            },
            "required": ["model", "ids", "values"],
        },
    },
    {
        "name": "odoo_unlink",
        "description": "Delete records permanently. Requires write mode AND "
                       "\"allow_unlink\": true in the profile. Prefer archiving "
                       "(odoo_write active=false), which is reversible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string"},
                "ids": {"type": "array", "items": {"type": "integer"}},
                "context": _CONTEXT,
            },
            "required": ["model", "ids"],
        },
    },
]


# --------------------------------------------------------------------------
# Output shaping
# --------------------------------------------------------------------------


def _shrink(node: Any) -> Any:
    """Truncate oversized strings. Odoo rows carry HTML bodies and base64 blobs
    that would otherwise dominate the context window."""
    if isinstance(node, str):
        if len(node) > MAX_STR:
            return node[:MAX_STR] + ("... [truncated %d chars]" % (len(node) - MAX_STR))
        return node
    if isinstance(node, dict):
        return {k: _shrink(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_shrink(v) for v in node]
    return node


def _dump(payload: Any, secrets=()) -> str:
    payload = guards.redact(_shrink(payload), secrets)
    text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + (
            "\n... [output truncated at %d chars. Narrow `fields`, lower `limit`, "
            "or use odoo_read_group to aggregate.]" % MAX_CHARS
        )
    return text


SETUP_HELP = """No Odoo connection is configured yet, so this MCP server has nothing to talk to.

Create ONE of these (the first match wins):

  1. <project>/.odoo-mcp.json      - per project. Add it to .gitignore.
  2. ~/.odoo-mcp/profiles.json     - one file for all your projects.

Minimal example:

{
  "profiles": {
    "local": {
      "url": "http://localhost:8069",
      "db": "<database name>",
      "username": "<odoo login>",
      "api_key": "${ODOO_MCP_API_KEY}",
      "mode": "read"
    }
  },
  "default": "local"
}

Getting the API key: in Odoo, open the user menu > Preferences > Account Security >
Developer API Keys > New API Key. Use a DEDICATED least-privilege Odoo user, never
an administrator - this server executes as that user and inherits exactly its
access rights and record rules.

Keep the secret out of the file by writing "${ODOO_MCP_API_KEY}" and exporting that
environment variable, or paste the key directly if the file is git-ignored.

Alternatively set ODOO_URL, ODOO_DB, ODOO_USERNAME and ODOO_API_KEY in the
environment.

Run the /odoo-mcp command for a guided walkthrough."""


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------


class Session:
    """Caches the resolved profile and client for the life of the process."""

    def __init__(self):
        self._profile = None
        self._client = None
        self._error = None

    def load(self, force=False):
        if force:
            self._profile = self._client = self._error = None
        if self._profile is None and self._error is None:
            try:
                import profiles as profiles_mod

                self._profile = profiles_mod.resolve()
            except ProfileError as exc:
                self._error = str(exc)
        return self._profile, self._error

    def client(self):
        prof, err = self.load()
        if err:
            raise OdooError("configuration problem:\n%s" % err)
        if prof is None or not prof.configured:
            raise OdooError(SETUP_HELP)
        if self._client is None:
            self._client = OdooClient(prof)
        return self._client

    def secrets(self):
        prof = self._profile
        return prof.secrets() if prof is not None else ()


def _status(sess: Session, args: dict) -> str:
    prof, err = sess.load(force=True)
    out: dict = {}

    if err:
        out["configuration_error"] = err
        out["help"] = SETUP_HELP
        return _dump(out)

    if prof is None or not prof.configured:
        searched = getattr(prof, "searched", [])
        problem = getattr(prof, "problem", "")
        out["connected"] = False
        if problem:
            out["problem"] = problem
        out["searched"] = searched
        out["help"] = SETUP_HELP
        if args.get("suggest_config"):
            out["discovered"] = discover()
        return _dump(out)

    out["profile"] = prof.describe()
    try:
        out["connection"] = sess.client().whoami()
        out["connected"] = True
    except OdooError as exc:
        out["connected"] = False
        out["error"] = str(exc)
    if args.get("suggest_config"):
        out["discovered"] = discover()
    return _dump(out, sess.secrets())


def _list_models(sess: Session, args: dict) -> str:
    c = sess.client()
    limit = guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT)
    domain: list = []
    pattern = (args.get("pattern") or "").strip()
    if pattern:
        domain = ["|", ["model", "ilike", pattern], ["name", "ilike", pattern]]
    if not args.get("transient"):
        domain = domain + [["transient", "=", False]]
    rows = c.search_read(
        "ir.model", domain, fields=["model", "name", "transient"], limit=limit, order="model"
    )
    return _dump({"count": len(rows), "models": rows}, sess.secrets())


def _inspect_model(sess: Session, args: dict) -> str:
    c = sess.client()
    model = guards.check_model_name(args.get("model"))

    meta = c.fields_get(
        model,
        attributes=[
            "string", "type", "required", "readonly", "store", "relation",
            "selection", "help", "digits", "related",
        ],
    )
    if not isinstance(meta, dict):
        raise OdooError("unexpected fields_get response for %s" % model)

    wanted = args.get("fields") or []
    pattern = (args.get("field_pattern") or "").strip().lower()
    fields = {}
    for fname, spec in meta.items():
        if wanted and fname not in wanted:
            continue
        if pattern:
            hay = "%s %s" % (fname.lower(), str(spec.get("string", "")).lower())
            if pattern not in hay:
                continue
        entry = {k: v for k, v in spec.items() if v not in (None, False, "", [])}
        help_text = str(entry.get("help", ""))
        if len(help_text) > 200:
            entry["help"] = help_text[:200] + "..."
        fields[fname] = entry

    access = {}
    for op in ("read", "write", "create", "unlink"):
        try:
            access[op] = c.call(
                model, "check_access_rights",
                kwargs={"operation": op, "raise_exception": False},
            )
        except OdooError:
            access[op] = "unknown"

    return _dump(
        {
            "model": model,
            "field_count": len(fields),
            "your_access": access,
            "fields": fields,
        },
        sess.secrets(),
    )


def _search(sess: Session, args: dict) -> str:
    c = sess.client()
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    limit = guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT)
    fields = args.get("fields") or None

    rows = c.search_read(
        model, domain, fields=fields, limit=limit,
        offset=int(args.get("offset") or 0), order=args.get("order"), context=ctx,
    )
    rows = rows if isinstance(rows, list) else []
    out = {"model": model, "returned": len(rows), "records": rows}
    if len(rows) == limit:
        total = c.search_count(model, domain, context=ctx)
        out["total_matching"] = total
        if isinstance(total, int) and total > limit:
            out["note"] = (
                "Showing %d of %d. Raise `limit` (max %d), page with `offset`, "
                "or aggregate with odoo_read_group." % (limit, total, MAX_LIMIT)
            )
    if not fields:
        out["hint"] = "No `fields` given, so every field was returned. Pass `fields` to save context."
    return _dump(out, sess.secrets())


def _count(sess: Session, args: dict) -> str:
    c = sess.client()
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    return _dump({"model": model, "count": c.search_count(model, domain, context=ctx)},
                 sess.secrets())


def _read_group(sess: Session, args: dict) -> str:
    c = sess.client()
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    groupby = args.get("groupby") or []
    if not isinstance(groupby, list) or not groupby:
        raise GuardError("groupby must be a non-empty list, e.g. [\"partner_id\"]")
    rows = c.read_group(
        model, domain, args.get("fields") or [], groupby,
        limit=guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT),
        orderby=args.get("orderby"),
        lazy=args.get("lazy", True) is not False,
        context=ctx,
    )
    return _dump({"model": model, "groups": rows}, sess.secrets())


def _call(sess: Session, args: dict) -> str:
    c = sess.client()
    prof, _ = sess.load()
    model = guards.check_model_name(args.get("model"))
    method = guards.check_method_name(args.get("method"))
    guards.check_call_allowed(prof, model, method)
    ctx = guards.check_context(args.get("context"))
    ids = guards.check_ids(args.get("ids"))
    kwargs = args.get("kwargs") or {}
    if not isinstance(kwargs, dict):
        raise GuardError("kwargs must be an object")
    result = c.call(model, method, ids=ids, kwargs=kwargs, context=ctx)
    return _dump({"model": model, "method": method, "result": result}, sess.secrets())


def _create(sess: Session, args: dict) -> str:
    c = sess.client()
    prof, _ = sess.load()
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(prof, model, "create")
    ctx = guards.check_context(args.get("context"))
    values = args.get("values")
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list) or not values or not all(isinstance(v, dict) for v in values):
        raise GuardError("values must be a non-empty list of objects")
    ids = c.create(model, values, context=ctx)
    return _dump({"model": model, "created_ids": ids, "count": len(values)}, sess.secrets())


def _write(sess: Session, args: dict) -> str:
    c = sess.client()
    prof, _ = sess.load()
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(prof, model, "write")
    ctx = guards.check_context(args.get("context"))
    ids = guards.check_ids(args.get("ids"))
    if not ids:
        raise GuardError("ids must contain at least one record id")
    values = args.get("values")
    if not isinstance(values, dict) or not values:
        raise GuardError("values must be a non-empty object of field -> value")
    ok = c.write(model, ids, values, context=ctx)
    return _dump(
        {"model": model, "updated_ids": ids, "count": len(ids), "result": ok}, sess.secrets()
    )


def _unlink(sess: Session, args: dict) -> str:
    c = sess.client()
    prof, _ = sess.load()
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(prof, model, "unlink")
    ctx = guards.check_context(args.get("context"))
    ids = guards.check_ids(args.get("ids"))
    if not ids:
        raise GuardError("ids must contain at least one record id")
    ok = c.unlink(model, ids, context=ctx)
    return _dump({"model": model, "deleted_ids": ids, "result": ok}, sess.secrets())


HANDLERS = {
    "odoo_status": _status,
    "odoo_list_models": _list_models,
    "odoo_inspect_model": _inspect_model,
    "odoo_search": _search,
    "odoo_count": _count,
    "odoo_read_group": _read_group,
    "odoo_call": _call,
    "odoo_create": _create,
    "odoo_write": _write,
    "odoo_unlink": _unlink,
}


def dispatch(sess: Session, name: str, args: dict):
    """Return (text, is_error). Never raises."""
    handler = HANDLERS.get(name)
    if handler is None:
        return ("Unknown tool %r. Available: %s" % (name, ", ".join(sorted(HANDLERS))), True)
    try:
        return (handler(sess, args or {}), False)
    except (GuardError, ProfileError) as exc:
        return ("Refused: %s" % guards.redact(str(exc), sess.secrets()), True)
    except OdooError as exc:
        return ("Odoo error: %s" % guards.redact(str(exc), sess.secrets()), True)
    except Exception as exc:  # never kill the server on a bad tool call
        return (
            "Unexpected %s: %s" % (type(exc).__name__, guards.redact(str(exc), sess.secrets())),
            True,
        )
