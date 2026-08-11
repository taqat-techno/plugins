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


def check_write_allowed(profile: Any, model: str, op: str) -> None:
    """Gate every state-changing operation. `op` is create|write|unlink."""
    if profile.mode != "write":
        raise GuardError(
            "profile %r is read-only (mode=%s), so %s on %s was refused.\n"
            "To allow writes, set \"mode\": \"write\" in the profile. "
            "Keep production profiles read-only."
            % (profile.name, profile.mode, op, model)
        )

    if profile.production and not profile.allow_production_writes:
        raise GuardError(
            "profile %r is marked \"production\": true, so %s on %s was refused.\n"
            "Production writes require \"allow_production_writes\": true, set deliberately."
            % (profile.name, op, model)
        )

    if model in HARD_DENY_WRITE_MODELS and model not in profile.allow_write_models:
        raise GuardError(
            "writing to %s is blocked: this model can escalate privilege, execute "
            "code, or alter schema/secrets.\n"
            "If you genuinely need it, add it to \"allow_write_models\" in the profile "
            "and understand the risk." % model
        )

    if op == "unlink" and not profile.allow_unlink:
        raise GuardError(
            "delete (unlink) is disabled for profile %r.\n"
            "Set \"allow_unlink\": true in the profile to permit deletion. "
            "Consider archiving (active=False) instead - it is reversible."
            % profile.name
        )


def check_call_allowed(profile: Any, model: str, method: str) -> None:
    """odoo_call gate: read-only methods pass; anything else needs write mode."""
    if method in READ_ONLY_METHODS:
        return
    if profile.mode != "write":
        raise GuardError(
            "%s.%s is not on the read-only method list, so it may change state.\n"
            "Profile %r is read-only (mode=%s). Set \"mode\": \"write\" to allow it, "
            "or use odoo_search / odoo_read_group for reads."
            % (model, method, profile.name, profile.mode)
        )
    if profile.production and not profile.allow_production_writes:
        raise GuardError(
            "profile %r is marked production; calling the potentially state-changing "
            "method %s.%s was refused. Set \"allow_production_writes\": true to permit it."
            % (profile.name, model, method)
        )


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
