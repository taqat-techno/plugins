"""Safety guards for the Odoo MCP server.

Single owner of every access decision. Tools ask this module for permission;
they never re-implement a rule locally.

Design stance (from the connection research):
  * The MCP server must act as the authenticated Odoo user, never as a
    superuser bridge. We never send admin credentials, never use sudo, never
    open a SQL or shell path.
  * Odoo already enforces ir.model.access, ir.rule and field groups on every
    execute_kw / JSON-2 call. These guards are a SECOND layer that stops
    categories of damage Odoo would happily allow a privileged user to do.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# --------------------------------------------------------------------------
# Model policy
# --------------------------------------------------------------------------

# Writing to these can escalate privilege, execute code, exfiltrate data or
# rewrite the schema. Refused for create/write/unlink regardless of profile
# mode, unless the model appears in the profile's `allow_write_models`.
HARD_DENY_WRITE_MODELS = frozenset({
    # arbitrary Python / scheduled code execution
    "ir.actions.server",
    "ir.cron",
    "base.automation",
    # module lifecycle (install/upgrade runs arbitrary module code)
    "ir.module.module",
    # schema and ACL definition
    "ir.model",
    "ir.model.fields",
    "ir.model.access",
    "ir.model.data",
    "ir.rule",
    # privilege escalation
    "res.users",
    "res.groups",
    # secrets / infrastructure
    "ir.config_parameter",
    "ir.mail_server",
    # view + QWeb arch can embed executable expressions
    "ir.ui.view",
    # _inherits ir.ui.view: a website.page write/create sets the view's arch
    "website.page",
    # wizards that reach the models above on the server side
    "base.module.upgrade",
    "base.module.uninstall",
    "res.config.settings",  # set_values writes ir.config_parameter / groups
    "change.password.wizard",
    "change.password.user",
    "change.password.own",
    "res.users.apikeys",
    "res.users.apikeys.description",
})

# Never callable through odoo_call, on any model. These either execute code,
# change the installed code base, or bypass the ORM.
DENY_METHODS = frozenset({
    "button_immediate_install",
    "button_immediate_upgrade",
    "button_immediate_uninstall",
    "button_install",
    "button_upgrade",
    "button_uninstall",
    "install_from_urls",
    "execute",
    "execute_kw",
    "run",  # ir.cron.run and friends
    "_register_hook",
    "init",
    "load",  # ORM data import
})

# Methods odoo_call will run without the write gate. Anything not listed is
# treated as potentially state-changing and requires write mode.
READ_ONLY_METHODS = frozenset({
    "search",
    "search_read",
    "search_count",
    "read",
    "read_group",
    "formatted_read_group",
    "fields_get",
    "get_views",
    "default_get",
    "name_search",
    "onchange",
    "exists",
    "check_access_rights",
    "has_access",
    "get_metadata",
    "read_progress_bar",
    "export_data",
})

_PRIVATE = re.compile(r"^_")

# Context keys that silently suppress tracking/logging or change import
# semantics. Refused so an agent cannot quietly bypass the audit trail.
DENY_CONTEXT_KEYS = frozenset({
    "tracking_disable",
    "mail_notrack",
    "mail_create_nolog",
    "mail_create_nosubscribe",
    "mail_auto_subscribe_no_notify",
    "install_mode",
    "module_install",
    "import_file",
    "no_reset_password",
})


class GuardError(Exception):
    """Raised when a guard refuses an operation. Message is user-facing."""


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_model_name(model: Any) -> str:
    if not isinstance(model, str) or not model.strip():
        raise GuardError("model must be a non-empty string")
    model = model.strip()
    if not re.fullmatch(r"[a-z0-9_.]+", model):
        raise GuardError(
            "invalid model name %r (expected lowercase dotted form, e.g. res.partner)" % model
        )
    return model


def check_method_name(method: Any) -> str:
    if not isinstance(method, str) or not method.strip():
        raise GuardError("method must be a non-empty string")
    method = method.strip()
    if _PRIVATE.match(method):
        raise GuardError(
            "refusing to call private method %r. Odoo blocks these server-side too; "
            "private methods are not part of the external API." % method
        )
    if method in DENY_METHODS:
        raise GuardError(
            "method %r is blocked by the MCP server: it installs/upgrades code, "
            "executes arbitrary Python, or bypasses the ORM." % method
        )
    return method


_RANK = {"read": 0, "write": 1, "write+unlink": 2}
_ACCESS_FOR = {"write": "write", "write+unlink": "full"}
_MODE_OF = {"read": "read", "write": "write", "full": "write+unlink"}


def _raise_hint(inst: Any, needed: str) -> str:
    """How `needed` (a mode) could be reached, within what the developer allows.

    `access` in profiles.json is the limit. Widening it needs the developer's yes;
    a prod instance additionally needs this session's unlock."""
    access = getattr(inst, "access", "read")
    if _RANK.get(needed, 9) > _RANK.get(_MODE_OF.get(access, "read"), 0):
        return (
            "%s allows only access %r (profiles.json). Widening it needs the developer's yes: "
            "odoo_mcp.py add %s %s --access %s --approved-by \"<their answer>\"."
            % (inst.qualified, access, getattr(inst, "project", "<project>"),
               getattr(inst, "name", "<instance>"), _ACCESS_FOR.get(needed, "write"))
        )
    if getattr(inst, "tier", "") == "prod":
        return (
            "Production writes need an unlock: ask the developer (name the instance and url), "
            "then odoo_session action=unlock instance=%s approved_by_user=\"<their answer>\"."
            % inst.qualified
        )
    return "Its access in profiles.json is %r." % access


def check_write_allowed(inst: Any, model: str, op: str) -> None:
    """Gate every state-changing operation. `op` is create|write|unlink.

    `inst` is the EFFECTIVE instance: its `mode` is what this session may do now -
    its access, except a prod instance, which is read-only until unlocked."""
    mode = getattr(inst, "mode", "read")
    tier = getattr(inst, "tier", "prod")
    if _RANK.get(mode, 0) < _RANK["write"]:
        raise GuardError(
            "instance %s (%s) is read-only in this session (mode=%s), so %s on %s was refused.\n%s"
            % (inst.qualified, tier, mode, op, model, _raise_hint(inst, "write"))
        )

    if model in HARD_DENY_WRITE_MODELS and model not in inst.allow_write_models:
        raise GuardError(
            "writing to %s is blocked: this model can escalate privilege, execute "
            "code, or alter schema/secrets.\n"
            "If you genuinely need it, the developer adds it to \"allow_write_models\" on the "
            "instance in profiles.json." % model
        )

    if op == "unlink" and _RANK.get(mode, 0) < _RANK["write+unlink"]:
        raise GuardError(
            "delete (unlink) needs mode write+unlink (access 'full'); instance %s is at %s.\n%s "
            "Consider archiving (active=False) instead - it is reversible."
            % (inst.qualified, mode, _raise_hint(inst, "write+unlink"))
        )


# ORM methods reachable through odoo_call that are the same operation as a
# dedicated tool. They get that tool's gate exactly (e.g. unlink needs
# write+unlink), so odoo_call is never a way around odoo_unlink / odoo_write.
CALL_METHOD_OPS = {
    "create": "create",
    "copy": "create",
    "write": "write",
    "unlink": "unlink",
}


def check_call_allowed(profile: Any, model: str, method: str) -> None:
    """odoo_call gate: read-only methods pass; anything else is a write.

    A non-read method gets the same decision as the dedicated write tools, via
    check_write_allowed: write mode, the HARD_DENY_WRITE_MODELS list (so
    `res.users.write` or `ir.config_parameter.set_param` cannot slip through),
    the session write scope, and - for unlink - the write+unlink mode."""
    model = check_model_name(model)
    if method in READ_ONLY_METHODS:
        return
    mode = getattr(profile, "mode", "read")
    if _RANK.get(mode, 0) < _RANK["write"]:
        raise GuardError(
            "%s.%s is not on the read-only method list, so it may change state.\n"
            "Instance %s (%s) is read-only in this session. %s Or use odoo_search / "
            "odoo_read_group for reads."
            % (model, method, profile.qualified, getattr(profile, "tier", "prod"),
               _raise_hint(profile, "write"))
        )
    op = CALL_METHOD_OPS.get(method, "%s()" % method)
    check_write_allowed(profile, model, op)


# --------------------------------------------------------------------------
# Nested x2many commands inside create/write values
# --------------------------------------------------------------------------
#
# A write on an ordinary model can still reach other models through x2many
# command tuples (odoo.fields.Command): res.partner {"user_ids": [[1, uid,
# {"groups_id": [[4, gid]]}]]} updates res.users, and {"child_ids": [[2, id]]}
# deletes records. The gates below apply HARD_DENY_WRITE_MODELS and the
# write+unlink rule to every command, at every nesting level, by resolving the
# field's comodel from fields_get metadata. A command on a field whose comodel
# cannot be resolved is refused - fail closed.

X2MANY_TYPES = frozenset({"one2many", "many2many"})

CMD_CREATE, CMD_UPDATE, CMD_DELETE, CMD_UNLINK, CMD_LINK, CMD_CLEAR, CMD_SET = range(7)

# Commands that can delete comodel records. DELETE always does. On a one2many,
# UNLINK / CLEAR / SET also delete when the inverse many2one is
# ondelete="cascade" (Odoo's One2many write path unlinks instead of nulling) -
# only relevant when the parent record already exists (op == "write").
_O2M_MAY_DELETE = frozenset({CMD_UNLINK, CMD_CLEAR, CMD_SET})

MAX_NESTING = 8


def _is_command(item: Any) -> bool:
    return (
        isinstance(item, (list, tuple)) and len(item) >= 1
        and isinstance(item[0], int) and not isinstance(item[0], bool)
        and CMD_CREATE <= item[0] <= CMD_SET
    )


def _relational_value(value: Any):
    """Return the list of commands a value expresses, or None if it is not one.

    A plain list of ids is Odoo's shorthand for SET."""
    if not isinstance(value, (list, tuple)) or not value:
        return None
    if all(_is_command(v) for v in value):
        return [list(v) for v in value]
    if all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        return [[CMD_SET, 0, list(value)]]
    return None


def _deny_unlink_msg(profile: Any, model: str, field: str, comodel: str, code: int) -> str:
    return (
        "%s.%s command %d can delete %s records, which needs mode write+unlink; "
        "instance %s is at %s.\n%s"
        % (model, field, code, comodel, profile.qualified, getattr(profile, "mode", "read"),
           _raise_hint(profile, "write+unlink"))
    )


def check_nested_values(profile: Any, model: str, values: Any, op: str, fields_of,
                        _depth: int = 0) -> None:
    """Refuse x2many commands in `values` that reach a hard-denied model or delete
    records without write+unlink. `values` is one vals dict or a list of them;
    `op` is create|write for the record these values belong to; `fields_of(model)`
    returns fields_get-style metadata ({field: {"type", "relation"}}) or raises.
    """
    if isinstance(values, (list, tuple)):
        for v in values:
            check_nested_values(profile, model, v, op, fields_of, _depth)
        return
    if not isinstance(values, dict):
        return
    if _depth > MAX_NESTING:
        raise GuardError("x2many commands nested deeper than %d levels are refused" % MAX_NESTING)

    meta = None
    resolved = False
    allow =getattr(profile, "allow_write_models", frozenset())
    unlink_ok = _RANK.get(getattr(profile, "mode", "read"), 0) >= _RANK["write+unlink"]

    for field, value in values.items():
        commands = _relational_value(value)
        if commands is None:
            continue
        if meta is None:
            try:
                meta = fields_of(model)
            except Exception:  # noqa: BLE001 - unresolvable means refuse below
                meta = None
            resolved = isinstance(meta, dict) and bool(meta)
            if not resolved:
                meta = {}
        spec = meta.get(field) if isinstance(meta.get(field), dict) else None
        if spec is None:
            if not resolved or all(_is_command(v) for v in value):
                raise GuardError(
                    "%s.%s carries x2many commands, but its comodel could not be resolved "
                    "(fields_get gave no metadata for it), so the nested write was refused. "
                    "Write the related records with their own odoo_write / odoo_create call."
                    % (model, field)
                )
            continue  # a list of ints on an unknown/non-relational field
        ftype = spec.get("type")
        if ftype not in X2MANY_TYPES:
            continue  # e.g. a json/properties field holding a list
        comodel = spec.get("relation")
        if not isinstance(comodel, str) or not comodel:
            raise GuardError(
                "%s.%s is %s but fields_get reported no comodel, so its commands were refused."
                % (model, field, ftype)
            )
        if comodel in HARD_DENY_WRITE_MODELS and comodel not in allow:
            raise GuardError(
                "%s.%s reaches %s, which is blocked: this model can escalate privilege, "
                "execute code, or alter schema/secrets. Nested x2many commands get the same "
                "hard-deny as a direct write.\nIf you genuinely need it, the developer adds "
                "%s to \"allow_write_models\" in the profile." % (model, field, comodel, comodel)
            )
        for cmd in commands:
            code = cmd[0]
            if not unlink_ok and (
                code == CMD_DELETE
                or (ftype == "one2many" and op == "write" and code in _O2M_MAY_DELETE)
            ):
                raise GuardError(_deny_unlink_msg(profile, model, field, comodel, code))
            if code in (CMD_CREATE, CMD_UPDATE) and len(cmd) >= 3:
                check_nested_values(profile, comodel, cmd[2],
                                    "create" if code == CMD_CREATE else "write",
                                    fields_of, _depth + 1)


def check_context(context: Any) -> dict:
    if context is None:
        return {}
    if not isinstance(context, dict):
        raise GuardError("context must be an object/dict")
    bad = sorted(set(context) & DENY_CONTEXT_KEYS)
    if bad:
        raise GuardError(
            "context keys %s are refused: they suppress tracking/logging or alter "
            "import semantics, which would hide this activity from the Odoo audit trail."
            % ", ".join(bad)
        )
    return context


def check_domain(domain: Any) -> list:
    """Odoo domains are lists. Reject strings outright - a string domain would be
    eval'd server-side in some code paths and is an injection vector."""
    if domain is None:
        return []
    if isinstance(domain, str):
        raise GuardError(
            "domain must be a list of tuples, not a string. "
            'Example: [["name", "ilike", "acme"]]'
        )
    if not isinstance(domain, list):
        raise GuardError("domain must be a list, e.g. [[\"active\", \"=\", true]]")
    return domain


def check_ids(ids: Any) -> list:
    if ids is None:
        return []
    if isinstance(ids, int):
        return [ids]
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise GuardError("ids must be an integer or a list of integers")
    return ids


def clamp_limit(limit: Any, default: int, hard_max: int) -> int:
    if limit is None:
        return default
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise GuardError("limit must be an integer")
    if limit <= 0:
        return default
    return min(limit, hard_max)


# --------------------------------------------------------------------------
# Redaction
# --------------------------------------------------------------------------

_SECRET_HINT = re.compile(
    r"(api[_-]?key|password|passwd|secret|token|authorization|bearer)", re.I
)


def redact(value: Any, secrets: Iterable[str] = ()) -> Any:
    """Strip credential material out of anything headed for the model or a log.

    Two mechanisms: exact-value replacement for known secrets, and key-name
    heuristics for dicts we did not construct.
    """
    real = [s for s in secrets if s and isinstance(s, str) and len(s) >= 6]

    def _scrub_text(text: str) -> str:
        for s in real:
            text = text.replace(s, "***REDACTED***")
        return text

    def _walk(node: Any) -> Any:
        if isinstance(node, str):
            return _scrub_text(node)
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                # The key-name heuristic only masks strings: those can carry
                # secret material. Booleans and numbers cannot, and masking them
                # would destroy useful diagnostics such as {"api_key_set": true}.
                if isinstance(k, str) and _SECRET_HINT.search(k) and isinstance(v, str) and v:
                    out[k] = "***REDACTED***"
                else:
                    out[k] = _walk(v)
            return out
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, tuple):
            return tuple(_walk(v) for v in node)
        return node

    return _walk(value)
