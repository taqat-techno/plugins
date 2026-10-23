"""Tool definitions and dispatch for the Odoo MCP server.

Deliberately small: eleven tools. Every MCP tool schema is injected into the
context window of every session where this server is enabled, so a sprawling
surface is a permanent tax on unrelated work. Servers in the wild range from 3
to 138 tools; this one stays near the low end and pushes breadth into
parameters instead of new tool names.

Routing: every tool takes an optional `instance` - a name in this folder's
project ("prod") or "project/instance" - and otherwise goes to the project's
default. Every result starts with a tag naming where it went, so staging and
production can be compared call by call with no switching state in between.

Every state-changing path goes through guards.check_write_allowed, and every
guard runs before a connection is opened. No tool here offers raw database,
process, filesystem or module-installation access.
"""

from __future__ import annotations

import json
import re
from typing import Any

import config
import guards
from config import BrokenInstance, ConfigError
from guards import GuardError
from odoo_client import DatabaseMissing, OdooError
from session import SETUP_HELP, ApprovalError, _hhmm, audit

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
_INSTANCE = {
    "type": "string",
    "description": "Which instance: a name in this project (e.g. \"prod\") or "
                   "\"project/instance\". Omit for the project's default.",
}
_WRITE_NOTE = ("Needs access write on the instance; a prod instance also needs "
               "odoo_session unlock.")

TOOLS = [
    {
        "name": "odoo_status",
        "description": "Show this folder's Odoo connections: its project, every instance "
                       "(tier, access, database, unlock state) and the default. Then connect "
                       "to one (the default, or `instance`) and report the Odoo version, the "
                       "API in use (JSON-2 or XML-RPC), the authenticated user and companies. "
                       "Call this first, and whenever a call fails unexpectedly. If nothing "
                       "is configured it explains exactly how to set it up.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
                "suggest_config": {
                    "type": "boolean",
                    "description": "Also scan the project folder for Odoo config hints.",
                },
            },
        },
    },
    {
        "name": "odoo_session",
        "description": "Production write unlock for THIS session. action=list shows this "
                       "project's instances with tier, access and unlock state; unlock lets a "
                       "prod instance write, up to its access, for `minutes` (default 30, max "
                       "120) and needs the developer's explicit yes passed verbatim as "
                       "approved_by_user - ask first, never assume it; lock ends it (every "
                       "unlock when no instance is named). Local and stage instances need no "
                       "unlock: their access in profiles.json decides. Other sessions are "
                       "unaffected.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "unlock", "lock"]},
                "instance": _INSTANCE,
                "approved_by_user": {
                    "type": "string",
                    "description": "The developer's answer, verbatim, to a question that "
                                   "named the instance and its url. Never reuse an earlier yes.",
                },
                "minutes": {"type": "integer", "description": "Unlock length (default 30, max 120)."},
            },
            "required": ["action"],
        },
    },
    {
        "name": "odoo_list_models",
        "description": "List Odoo models, optionally filtered. Use to discover the "
                       "technical model name behind a business concept.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
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
                "instance": _INSTANCE,
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
                "instance": _INSTANCE,
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
                "instance": _INSTANCE,
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
                "instance": _INSTANCE,
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
                       "module-install methods are refused. A method not known to be "
                       "read-only is a write: " + _WRITE_NOTE,
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
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
        "description": "Create one or more records. " + _WRITE_NOTE + " Returns the new ids.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
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
        "description": "Update existing records. " + _WRITE_NOTE + " Always confirm the "
                       "target ids with odoo_search first - a wrong domain can update far "
                       "more rows than intended.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
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
        "description": "Delete records permanently. Needs access full on the instance; a "
                       "prod instance also needs odoo_session unlock. Prefer archiving "
                       "(odoo_write active=false), which is reversible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instance": _INSTANCE,
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


KEY_AFTER_REBUILD_HINT = (
    "\nIf this staging was rebuilt, an API key created inside the old build died with it. "
    "Fix once: create the MCP user and its API key in PRODUCTION - every staging build is a "
    "copy of production, so the key then survives every rebuild - and update the key with "
    "odoo_mcp.py add."
)

_AUTH_RE = re.compile(r"401|no usable uid|Access Denied|authentication failed")
_MODE_LABEL = {"read": "read", "write": "write", "write+unlink": "full"}


# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------


def _instance(sess, args: dict):
    """The effective instance for this call. Resolved without any network access,
    so a refusal never waits on a connection."""
    inst = sess.effective(sess.resolve(args.get("instance")))
    sess.current = (inst, None)
    return inst


def _client(sess, inst):
    c = sess.client(inst)
    sess.current = (inst, c)
    return c


def _secrets(sess) -> tuple:
    cur = getattr(sess, "current", None)
    return cur[0].secrets() if cur else ()


def _tag(sess, inst, client=None) -> str:
    """[project/instance · database · mode], plus the unlock and legacy markers."""
    db = getattr(getattr(client, "p", None), "db", "") if client is not None else ""
    if not db:
        db = inst.db or ("auto" if inst.db_auto and client is None else "host-selected")
    tag = "[%s · %s · %s" % (inst.qualified, db, _MODE_LABEL.get(inst.mode, inst.mode))
    if inst.tier == "prod":
        until = sess.unlocked_until(inst)
        if until:
            tag += " · unlocked until %s" % _hhmm(until)
    if inst.legacy:
        tag += " · legacy"
    return tag + "]"


def _not_followed(inst, client, exc) -> str:
    try:
        found = client.list_databases() if client is not None else None
    except Exception:
        found = None
    return (
        "%s\ndatabase %r no longer exists on %s; it serves: %s. Not followed - update \"db\" "
        "with odoo_mcp.py add %s %s --db <name>%s."
        % (exc, inst.db, inst.url, ", ".join(found) if found else "(listing disabled)",
           inst.project, inst.name,
           " (a staging instance can use --db auto)" if inst.tier != "prod" else "")
    )


def _retrying(sess, fn):
    """Run fn() once more after the two failures a fresh client can fix:
    a "db": "auto" database that moved, and a rejected login. A fixed database
    that moved is reported and never followed."""
    try:
        return fn()
    except DatabaseMissing as exc:
        cur = getattr(sess, "current", None)
        if cur is None:
            raise
        inst, client = cur
        if inst.db_auto:
            sess.drop_client(inst)
            return fn()
        raise OdooError(_not_followed(inst, client, exc))
    except OdooError as exc:
        cur = getattr(sess, "current", None)
        if cur is None or not _AUTH_RE.search(str(exc)):
            raise
        inst = cur[0]
        sess.drop_client(inst)
        try:
            return fn()
        except OdooError as exc2:
            msg = str(exc2)
            if inst.tier == "stage" and _AUTH_RE.search(msg):
                msg += KEY_AFTER_REBUILD_HINT
            raise OdooError(msg)


def _write_audit(inst, op, model, count):
    if inst.tier != "local":
        audit({"action": "write", "op": op, "model": model, "count": count,
               "instance": inst.qualified, "tier": inst.tier, "mode": inst.mode})


# --------------------------------------------------------------------------
# Status and session
# --------------------------------------------------------------------------


def _row(sess, i) -> dict:
    if isinstance(i, BrokenInstance):
        return {"instance": i.qualified, "error": i.error}
    d = sess.effective(i).describe()
    until = sess.unlocked_until(i) if i.tier == "prod" else 0.0
    d["unlocked_until"] = _hhmm(until) if until else None
    return d


def _local_candidate(out: dict, folder) -> None:
    disc = config.discover(folder)
    if disc.get("conf_files") or disc.get("compose_files"):
        out["local_candidate"] = disc


def _status(sess, args: dict) -> str:
    out: dict = {"folder": str(sess.folder), "file": str(sess.loader.path)}
    try:
        cfg = sess.config()
    except ConfigError as exc:
        out["connected"] = False
        if sess.loader.path.exists():
            out["configuration_error"] = str(exc)
        out["help"] = SETUP_HELP
        _local_candidate(out, sess.folder)
        return _dump(out)

    project = cfg.match(sess.folders)
    out["version"] = cfg.version
    out["project"] = project.name if project else None
    if project is not None:
        out["default"] = project.default_name()
        out["instances"] = [_row(sess, i) for i in project.instances.values()]
    else:
        out["projects"] = {p.name: list(p.paths) for p in cfg.projects.values()}
        _local_candidate(out, sess.folder)

    def connect():
        inst = _instance(sess, args)
        c = _client(sess, inst)
        return inst, c, c.whoami()

    try:
        inst, client, who = _retrying(sess, connect)
        out["target"] = inst.qualified
        out["tag"] = _tag(sess, inst, client)
        out["connected"] = True
        out["connection"] = who
    except (ConfigError, GuardError, OdooError) as exc:
        cur = getattr(sess, "current", None)
        if cur is not None:
            out["target"] = cur[0].qualified
            out["tag"] = _tag(sess, cur[0], cur[1])
        out["connected"] = False
        out["error"] = str(exc)
    if args.get("suggest_config"):
        out["discovered"] = config.discover(sess.folder)
    warnings = sess.warnings()
    if warnings:
        out["warnings"] = warnings
    if sess.notices:
        out["notices"] = sess.notices[:]
        sess.notices.clear()
    return _dump(out, _secrets(sess))


def _session(sess, args: dict) -> str:
    action = (args.get("action") or "list").strip().lower()
    if action == "list":
        cfg = sess.config()
        project = cfg.match(sess.folders)
        out = {
            "project": project.name if project else None,
            "default": project.default_name() if project else None,
            "instances": [_row(sess, i) for i in project.instances.values()] if project else [],
            "projects": sorted(cfg.projects),
        }
        if sess.warnings():
            out["warnings"] = sess.warnings()
        return _dump(out)
    if action == "unlock":
        return _dump(sess.unlock(args.get("instance"), args.get("approved_by_user"),
                                 args.get("minutes")))
    if action == "lock":
        return _dump(sess.lock(args.get("instance")))
    raise GuardError("action must be one of list, unlock, lock")


# --------------------------------------------------------------------------
# Data tools
# --------------------------------------------------------------------------


def _list_models(sess, args: dict) -> str:
    inst = _instance(sess, args)
    limit = guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT)
    domain: list = []
    pattern = (args.get("pattern") or "").strip()
    if pattern:
        domain = ["|", ["model", "ilike", pattern], ["name", "ilike", pattern]]
    if not args.get("transient"):
        domain = domain + [["transient", "=", False]]
    c = _client(sess, inst)
    rows = c.search_read(
        "ir.model", domain, fields=["model", "name", "transient"], limit=limit, order="model"
    )
    return _dump({"count": len(rows), "models": rows}, inst.secrets())


def _inspect_model(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    c = _client(sess, inst)

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
        inst.secrets(),
    )


def _search(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    limit = guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT)
    fields = args.get("fields") or None
    c = _client(sess, inst)

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
    return _dump(out, inst.secrets())


def _count(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    c = _client(sess, inst)
    return _dump({"model": model, "count": c.search_count(model, domain, context=ctx)},
                 inst.secrets())


def _read_group(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    domain = guards.check_domain(args.get("domain"))
    ctx = guards.check_context(args.get("context"))
    groupby = args.get("groupby") or []
    if not isinstance(groupby, list) or not groupby:
        raise GuardError("groupby must be a non-empty list, e.g. [\"partner_id\"]")
    c = _client(sess, inst)
    rows = c.read_group(
        model, domain, args.get("fields") or [], groupby,
        limit=guards.clamp_limit(args.get("limit"), DEFAULT_LIMIT, MAX_LIMIT),
        orderby=args.get("orderby"),
        lazy=args.get("lazy", True) is not False,
        context=ctx,
    )
    return _dump({"model": model, "groups": rows}, inst.secrets())


def _fields_resolver(c):
    """fields_of(model) for guards.check_nested_values, cached per tool call."""
    cache: dict = {}

    def fields_of(model):
        if model not in cache:
            guards.check_model_name(model)
            cache[model] = c.fields_get(model, attributes=["type", "relation"])
        return cache[model]

    return fields_of


def _call(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    method = guards.check_method_name(args.get("method"))
    guards.check_call_allowed(inst, model, method)
    ids = guards.check_ids(args.get("ids"))
    kwargs = args.get("kwargs") or {}
    if not isinstance(kwargs, dict):
        raise GuardError("kwargs must be an object")
    kwargs = dict(kwargs)
    # A context can arrive twice: as the top-level `context` argument and as
    # kwargs["context"]. Merge both and check the merged dict, otherwise a denied
    # key (tracking_disable, ...) slips through kwargs unchecked.
    kw_ctx = kwargs.pop("context", None)
    if kw_ctx is not None and not isinstance(kw_ctx, dict):
        raise GuardError("kwargs.context must be an object/dict")
    merged = dict(kw_ctx or {})
    top = args.get("context")
    if top is not None and not isinstance(top, dict):
        raise GuardError("context must be an object/dict")
    merged.update(top or {})
    ctx = guards.check_context(merged)
    c = _client(sess, inst)
    if method not in guards.READ_ONLY_METHODS:
        # vals / vals_list / default (or any dict argument of a business method)
        # can carry x2many commands that reach other models.
        op = "create" if guards.CALL_METHOD_OPS.get(method) == "create" else "write"
        fields_of = _fields_resolver(c)
        for value in kwargs.values():
            guards.check_nested_values(inst, model, value, op, fields_of)
    result = c.call(model, method, ids=ids, kwargs=kwargs, context=ctx)
    if method not in guards.READ_ONLY_METHODS:
        _write_audit(inst, method, model, len(ids))
    return _dump({"model": model, "method": method, "result": result}, inst.secrets())


def _create(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(inst, model, "create")
    ctx = guards.check_context(args.get("context"))
    values = args.get("values")
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list) or not values or not all(isinstance(v, dict) for v in values):
        raise GuardError("values must be a non-empty list of objects")
    c = _client(sess, inst)
    guards.check_nested_values(inst, model, values, "create", _fields_resolver(c))
    ids = c.create(model, values, context=ctx)
    _write_audit(inst, "create", model, len(values))
    return _dump({"model": model, "created_ids": ids, "count": len(values)}, inst.secrets())


def _write(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(inst, model, "write")
    ctx = guards.check_context(args.get("context"))
    ids = guards.check_ids(args.get("ids"))
    if not ids:
        raise GuardError("ids must contain at least one record id")
    values = args.get("values")
    if not isinstance(values, dict) or not values:
        raise GuardError("values must be a non-empty object of field -> value")
    c = _client(sess, inst)
    guards.check_nested_values(inst, model, values, "write", _fields_resolver(c))
    ok = c.write(model, ids, values, context=ctx)
    _write_audit(inst, "write", model, len(ids))
    return _dump(
        {"model": model, "updated_ids": ids, "count": len(ids), "result": ok}, inst.secrets()
    )


def _unlink(sess, args: dict) -> str:
    inst = _instance(sess, args)
    model = guards.check_model_name(args.get("model"))
    guards.check_write_allowed(inst, model, "unlink")
    ctx = guards.check_context(args.get("context"))
    ids = guards.check_ids(args.get("ids"))
    if not ids:
        raise GuardError("ids must contain at least one record id")
    c = _client(sess, inst)
    ok = c.unlink(model, ids, context=ctx)
    _write_audit(inst, "unlink", model, len(ids))
    return _dump({"model": model, "deleted_ids": ids, "result": ok}, inst.secrets())


HANDLERS = {
    "odoo_status": _status,
    "odoo_session": _session,
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

# These answer with one JSON document that already carries the target, warnings
# and notices, so callers can parse it; every other result is framed by _frame.
_JSON_TOOLS = ("odoo_status", "odoo_session")


def _frame(sess, body: str) -> str:
    lines = []
    cur = getattr(sess, "current", None)
    if cur is not None:
        lines.append(_tag(sess, cur[0], cur[1]))
    lines += ["WARNING: %s" % w for w in sess.warnings()]
    lines += ["NOTE: %s" % n for n in sess.notices]
    sess.notices.clear()
    lines.append(body)
    return "\n".join(lines)


def dispatch(sess, name: str, args: dict):
    """Return (text, is_error). Never raises."""
    handler = HANDLERS.get(name)
    if handler is None:
        return ("Unknown tool %r. Available: %s" % (name, ", ".join(sorted(HANDLERS))), True)
    args = args or {}
    sess.current = None
    try:
        body, is_error = _retrying(sess, lambda: handler(sess, args)), False
    except (GuardError, ConfigError, ApprovalError) as exc:
        body, is_error = "Refused: %s" % guards.redact(str(exc), _secrets(sess)), True
    except OdooError as exc:
        body, is_error = "Odoo error: %s" % guards.redact(str(exc), _secrets(sess)), True
    except Exception as exc:  # never kill the server on a bad tool call
        body, is_error = ("Unexpected %s: %s"
                          % (type(exc).__name__, guards.redact(str(exc), _secrets(sess)))), True
    if name in _JSON_TOOLS and not is_error:
        return body, False
    return _frame(sess, body), is_error
