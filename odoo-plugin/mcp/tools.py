"""Tool definitions and dispatch for the Odoo MCP server.

Deliberately small: eleven tools. Every MCP tool schema is injected into the
context window of every session where this server is enabled, so a sprawling
surface is a permanent tax on unrelated work. Servers in the wild range from 3
to 138 tools; this one stays near the low end and pushes breadth into
parameters instead of new tool names.

Every state-changing path goes through guards.check_write_allowed. No tool here
offers SQL, shell, filesystem or module-installation access.
"""

from __future__ import annotations

import json
import re
from typing import Any

import guards
import profiles as profiles_mod
from guards import GuardError
from odoo_client import DatabaseMissing, OdooClient, OdooError
from profiles import NoProfile, ProfileError, discover
from session_state import ApprovalError, SessionState, audit

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
        "name": "odoo_session",
        "description": "Switch THIS session's Odoo connection or its read/write mode, within "
                       "the limits the developer set in each profile. action=list shows every "
                       "profile (tier, ceiling, approval) and which is active and why; "
                       "use <profile> switches the connection; mode raises or lowers "
                       "read | write | write+unlink up to the profile's ceiling; reset returns to "
                       "the resolved profile. Raising a local profile needs nothing; a staging "
                       "profile needs the developer's explicit yes passed verbatim as "
                       "approved_by_user (ask first - never assume it); a production profile "
                       "needs the developer's own terminal grant. Other sessions are unaffected.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "use", "mode", "reset"]},
                "profile": {"type": "string", "description": "Profile name for action=use."},
                "mode": {"type": "string", "enum": ["read", "write", "write+unlink"]},
                "ttl_minutes": {
                    "type": "integer",
                    "description": "How long an elevation lasts (staging default 60, max 480; "
                                   "production default 30, max 120; local: whole session).",
                },
                "models": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Optional: restrict writes in this elevation to these models.",
                },
                "reason": {"type": "string", "description": "Why - recorded in the audit log."},
                "approved_by_user": {
                    "type": "string",
                    "description": "The developer's answer, verbatim, when the profile needs chat "
                                   "approval. Only fill this from an explicit reply to a question "
                                   "that named the profile and the mode.",
                },
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
                       "read-only require the session to be in write mode (odoo_session).",
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
        "description": "Create one or more records. Requires the session to be in write "
                       "mode (see odoo_session). Returns the new ids.",
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
        "description": "Delete records permanently. Requires the session mode "
                       "write+unlink (see odoo_session). Prefer archiving "
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


SETUP_HELP = """No Odoo connection is configured for this project.

LOCAL instance: connect without asking - from the project directory run
  python "<odoo-plugin>/scripts/mcp/local_profile.py" provision
then call odoo_status again (no restart).

STAGING / PRODUCTION: the developer defines profiles in ~/.odoo-mcp/servers.json
(url, username, api_key as "${ENV_VAR}", tier, ceiling, projects), or pins one
checkout with <project>/.odoo-mcp.json. A remote profile is never a global default.

API keys: Preferences > Account Security > Developer API Keys. For Odoo.sh staging
create the key in PRODUCTION so it survives staging rebuilds. Details: the odoo
plugin's mcp skill and /mcp-setup."""


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------


class Session:
    """Resolved catalog + in-memory session state (active profile, mode, expiry)."""

    def __init__(self):
        self.state = SessionState()
        self._catalog = None
        self._base = None
        self._client = None
        self._error = None

    def load(self, force=False):
        """Return (effective profile or NoProfile, error)."""
        if force:
            self._catalog = self._base = self._client = self._error = None
        if self._catalog is None and self._error is None:
            try:
                wanted = self.state.override or profiles_mod.wanted_from_env()
                cat = profiles_mod.load_catalog(wanted)
                self._catalog = cat
                self._base = cat.profiles[cat.chosen] if cat.chosen else NoProfile(
                    searched=cat.searched, problem=cat.problem)
            except ProfileError as exc:
                self._error = str(exc)
        if self._error:
            return None, self._error
        if self._base is not None and self._base.configured:
            return self.state.effective(self._base), None
        return self._base, None

    @property
    def catalog(self):
        self.load()
        return self._catalog

    def base_profile(self):
        prof, err = self.load()
        if err:
            raise OdooError("configuration problem:\n%s" % err)
        if prof is None or not prof.configured:
            raise OdooError(SETUP_HELP)
        return self._base

    def client(self):
        prof, err = self.load()
        if err:
            raise OdooError("configuration problem:\n%s" % err)
        if prof is None or not prof.configured:
            raise OdooError(SETUP_HELP)
        if self._client is None:
            self._client = OdooClient(self._base)
        return self._client

    def secrets(self):
        prof = self._base
        return prof.secrets() if prof is not None else ()

    # ---- database follow ---------------------------------------------------

    def follow_database(self, exc: DatabaseMissing) -> str:
        """The configured database vanished (staging rebuild / restore renamed it).

        Non-production: discover the database now behind this URL, record it in the
        learned-state file (never in the developer's file) and return a notice.
        Production: report the candidate and change nothing."""
        base = self.base_profile()
        client = self.client()
        found = client.list_databases()
        old = base.db
        if found is not None and old in found:
            raise exc  # the database exists; this was something else
        new = _pick_database(old, found or [], base.db_pattern)
        if new is None and found is None and client.flavor == "json2":
            new = ""  # listing disabled, but JSON-2 lets the host select the database
        if new is None:
            raise OdooError(
                "%s\nThe server lists %s. Could not pick the new database unambiguously - set "
                "\"db_pattern\" (a regex) on profile %r, or update \"db\"."
                % (exc, ", ".join(found) if found else "no databases (listing disabled)", base.name)
            )
        if base.kind == "local":
            raise OdooError(
                "%s\nThis is a local profile: re-run local_profile.py provision to connect to %r."
                % (exc, new or "the host-selected database")
            )
        if base.tier == "production":
            audit({"action": "db-changed-not-followed", "profile": base.name,
                   "from": old, "candidate": new})
            raise OdooError(
                "%s\nThe server now serves %r. Production profiles are not re-pointed "
                "automatically - the developer updates \"db\" for %r."
                % (exc, new or "(host-selected)", base.name)
            )
        entry = profiles_mod.remember_db(base, new)
        audit({"action": "db-followed", "profile": base.name, "tier": base.tier,
               "from": old, "to": new or "(host-selected)"})
        self.load(force=True)
        return (
            "NOTE: the database for profile %r changed: %r -> %r. Updated automatically "
            "(recorded %s in %s; the developer's servers file is unchanged)."
            % (base.name, old, new or "(host-selected)", entry["learned_at"],
               profiles_mod.state_dir() / "learned.json")
        )


def _pick_database(old: str, found: list, pattern: str):
    cands = [d for d in found if d != old]
    if pattern:
        cands = [d for d in cands if re.search(pattern, d)]
    if len(cands) == 1:
        return cands[0]
    stem = re.sub(r"[-_]?\d+$", "", old or "")
    if stem:
        same = [d for d in cands if d.startswith(stem)]
        if len(same) == 1:
            return same[0]
    return None


KEY_AFTER_REBUILD_HINT = (
    "\nThe database was renamed, and the API key was rejected: a key created inside a "
    "staging build is deleted with that build. Fix once: create the MCP user and its API "
    "key in PRODUCTION - every staging build is a copy of production, so the key then "
    "survives every rebuild. Put the new key in the developer's servers file (or the env "
    "variable it references)."
)


def _write_audit(prof, op, model, count):
    if getattr(prof, "tier", "local") != "local":
        audit({"action": "write", "op": op, "model": model, "count": count,
               "profile": prof.name, "tier": prof.tier, "mode": prof.mode})


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
        cat = sess.catalog
        if cat is not None and cat.warnings:
            out["warnings"] = list(cat.warnings)
        disc = discover()
        if disc.get("conf_files") or disc.get("compose_files"):
            out["local_candidate"] = disc
        elif args.get("suggest_config"):
            out["discovered"] = disc
        return _dump(out)

    cat = sess.catalog
    out["profile"] = prof.describe()
    out["selected_because"] = cat.reason
    if sess.state.describe():
        out["session"] = sess.state.describe()
    others = sorted(n for n in cat.profiles if n != prof.name)
    if others:
        out["other_profiles"] = others
    try:
        out["connection"] = sess.client().whoami()
        out["connected"] = True
    except DatabaseMissing as exc:
        try:
            out["notice"] = sess.follow_database(exc)
            prof, _ = sess.load()
            out["profile"] = prof.describe()
            out["connection"] = sess.client().whoami()
            out["connected"] = True
        except OdooError as exc2:
            out["connected"] = False
            out["error"] = str(exc2)
    except OdooError as exc:
        out["connected"] = False
        out["error"] = str(exc)
    warnings = list(cat.warnings)
    warnings += _hygiene_warnings(cat)
    if warnings:
        out["warnings"] = warnings
    if sess.state.notices:
        out["notices"] = sess.state.notices[:]
        sess.state.notices.clear()
    if args.get("suggest_config"):
        out["discovered"] = discover()
    return _dump(out, sess.secrets())


def _hygiene_warnings(cat) -> list:
    """Keep ~/.odoo-mcp tidy: flag the patterns that turn it into a mess."""
    out = []
    try:
        sfile = profiles_mod.user_file()
        if sfile.is_file():
            raw = json.loads(sfile.read_text(encoding="utf-8"))
            for name, p in (raw.get("profiles") or {}).items():
                if isinstance(p, dict) and p.get("api_key") and "${" not in str(p.get("api_key")):
                    out.append("profile %r stores its API key literally in %s - prefer "
                               "\"${SOME_ENV_VAR}\"." % (name, sfile.name))
        known = {"servers.json", "profiles.json", "local", "state", "grants", "audit.log"}
        home = profiles_mod.home()
        if home.is_dir():
            stray = sorted(x.name for x in home.iterdir() if x.name not in known
                           and not x.name.endswith((".bak", ".tmp")))
            if stray:
                out.append("non-config files in %s: %s - project data belongs in the project "
                           "(e.g. .claude/docs), not the connection store." % (home, ", ".join(stray)))
    except Exception:
        pass
    for prof in cat.profiles.values():
        if prof.tier == "production" and prof.ceiling != "read":
            out.append("production profile %r allows %s (ceiling). Confirm that is intended."
                       % (prof.name, prof.ceiling))
    return out


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
    if method not in guards.READ_ONLY_METHODS:
        _write_audit(prof, method, model, len(ids))
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
    _write_audit(prof, "create", model, len(values))
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
    _write_audit(prof, "write", model, len(ids))
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
    _write_audit(prof, "unlink", model, len(ids))
    return _dump({"model": model, "deleted_ids": ids, "result": ok}, sess.secrets())


def _session(sess: Session, args: dict) -> str:
    action = (args.get("action") or "list").strip().lower()
    if action == "reset":
        sess.state.reset()
        sess.load(force=True)
        prof, _ = sess.load()
        return _dump({"reset": True, "active": getattr(prof, "name", None),
                      "mode": getattr(prof, "mode", None)}, sess.secrets())

    cat = sess.catalog
    if cat is None:
        raise ProfileError(sess._error or "configuration could not be loaded")

    if action == "list":
        active = cat.chosen
        rows = []
        for name in sorted(cat.profiles):
            p = cat.profiles[name]
            view = sess.state.effective(p) if name == active else p
            d = view.describe()
            rows.append({k: d[k] for k in ("profile", "kind", "tier", "url", "database", "mode",
                                           "ceiling", "approval_to_raise", "source") if k in d})
        return _dump({"active": active, "selected_because": cat.reason,
                      "session": sess.state.describe() or None,
                      "profiles": rows, "warnings": cat.warnings or None}, sess.secrets())

    if action == "use":
        name = (args.get("profile") or "").strip()
        if name not in cat.profiles:
            raise ApprovalError("unknown profile %r. Available: %s"
                                % (name, ", ".join(sorted(cat.profiles)) or "(none)"))
        out = sess.state.use(cat.profiles[name], args.get("approved_by_user"))
        sess.load(force=True)
        prof, _ = sess.load()
        out["profile"] = prof.describe()
        return _dump(out, sess.secrets())

    if action == "mode":
        target = (args.get("mode") or "").strip().lower()
        base = sess.base_profile()
        models = args.get("models") or []
        if not isinstance(models, list):
            raise GuardError("models must be a list of model names")
        out = sess.state.set_mode(base, target, args.get("ttl_minutes"), models,
                                  args.get("reason") or "", args.get("approved_by_user"))
        return _dump(out, sess.secrets())

    raise GuardError("action must be one of list, use, mode, reset")


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


def _with_notices(sess: Session, text: str) -> str:
    if sess.state.notices:
        notes = "\n".join("NOTE: %s" % n for n in sess.state.notices)
        sess.state.notices.clear()
        return notes + "\n\n" + text
    return text


def dispatch(sess: Session, name: str, args: dict):
    """Return (text, is_error). Never raises."""
    handler = HANDLERS.get(name)
    if handler is None:
        return ("Unknown tool %r. Available: %s" % (name, ", ".join(sorted(HANDLERS))), True)
    try:
        return _with_notices(sess, handler(sess, args or {})), False
    except DatabaseMissing as exc:
        try:
            notice = sess.follow_database(exc)
        except (GuardError, ProfileError, ApprovalError, OdooError) as exc2:
            return ("Odoo error: %s" % guards.redact(str(exc2), sess.secrets()), True)
        try:
            return notice + "\n\n" + handler(sess, args or {}), False
        except OdooError as exc2:
            msg = str(exc2)
            if re.search(r"401|no usable uid|Access Denied|authentication failed", msg):
                msg += KEY_AFTER_REBUILD_HINT
            return (notice + "\n\nOdoo error: %s" % guards.redact(msg, sess.secrets()), True)
    except (GuardError, ProfileError, ApprovalError) as exc:
        return ("Refused: %s" % guards.redact(str(exc), sess.secrets()), True)
    except OdooError as exc:
        return ("Odoo error: %s" % guards.redact(str(exc), sess.secrets()), True)
    except Exception as exc:  # never kill the server on a bad tool call
        return (
            "Unexpected %s: %s" % (type(exc).__name__, guards.redact(str(exc), sess.secrets())),
            True,
        )
