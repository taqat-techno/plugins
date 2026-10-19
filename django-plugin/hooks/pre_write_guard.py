#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): ADVISORY nudges for risky Django edits.

This hook NEVER blocks and NEVER mutates anything. It hands one-line nudges to
Claude as PreToolUse additionalContext JSON on stdout and ALWAYS exits 0. It inspects the content being written/edited and the
target path, and warns on a few deterministic, documented-risky shapes:

  Settings files (settings.py / settings/*.py; DEBUG and ALLOWED_HOSTS only for
  prod-bound modules, not test/dev/local ones):
    1. DEBUG = True  hardcoded (rather than env-driven).
    2. A hardcoded secret literal — SECRET_KEY / PASSWORD / API key assigned a
       non-empty string literal that is not reading from the environment.
    3. ALLOWED_HOSTS = ["*"].

  Migration files (*/migrations/*.py):
    4. RunPython without a reverse (no second positional arg / no reverse_code),
       and no explicit migrations.RunPython.noop.
    5. A data migration importing real models (from app.models import ...) instead
       of using apps.get_model(...).

  Serializers (serializers.py / *serializer*.py):
    6. fields = "__all__"  on a ModelSerializer (field-leak / mass-assignment risk).

It stays SILENT on env-driven config, reversible migrations, and explicit field
lists. Reads the PreToolUse JSON payload on stdin (content at tool_input.content
for Write, tool_input.new_string for Edit, edits[].new_string for MultiEdit).
DEBUG / ALLOWED_HOSTS nudges are skipped in test/dev/local settings modules
(test_settings.py, settings/dev.py, settings_local.py). Stdlib-only. Fail-OPEN on any error.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402


def _is_settings(path):
    p = path.replace("\\", "/").lower()
    return p.endswith("/settings.py") or "/settings/" in p or p.endswith("settings.py")


_DEV_SCOPE_RE = re.compile(r"(^|[/_.-])(test|tests|testing|dev|develop|development|local|ci)([/_.-]|$)")


def _is_dev_settings(path):
    """test_settings.py, settings/dev.py, settings_local.py, ... (DEBUG there is expected)."""
    p = path.replace("\\", "/").lower()
    name = p.rsplit("/", 1)[-1][:-3] if p.endswith(".py") else p.rsplit("/", 1)[-1]
    parent = p.rsplit("/", 2)[-2] if p.count("/") >= 1 else ""
    return bool(_DEV_SCOPE_RE.search(name)) or bool(_DEV_SCOPE_RE.search(parent) and parent != "settings")


def _is_migration(path):
    return "/migrations/" in path.replace("\\", "/").lower()


def _is_serializer(path):
    p = path.replace("\\", "/").lower()
    return p.endswith("serializers.py") or "serializer" in os.path.basename(p)


# --- settings checks ---------------------------------------------------------
_DEBUG_TRUE_RE = re.compile(r"^\s*DEBUG\s*=\s*True\b", re.MULTILINE)
_ALLOWED_STAR_RE = re.compile(r"ALLOWED_HOSTS\s*=\s*\[\s*['\"]\*['\"]\s*\]")
# A secret-shaped name assigned a non-empty *string literal* that is not env-driven.
_SECRET_LITERAL_RE = re.compile(
    r"^\s*(SECRET_KEY|[A-Z_]*PASSWORD|[A-Z_]*API_?KEY|[A-Z_]*TOKEN|[A-Z_]*SECRET)\s*=\s*['\"][^'\"]+['\"]",
    re.MULTILINE,
)
_ENV_HINT_RE = re.compile(r"environ|os\.environ|getenv|env\(|config\(|decouple|Path\(", re.IGNORECASE)


def _check_settings(content, dev_scope=False):
    out = []
    if not dev_scope and _DEBUG_TRUE_RE.search(content):
        out.append("[django] advisory: `DEBUG = True` hardcoded in a settings file. Drive it "
                   "from the environment (default False); DEBUG=True in prod leaks tracebacks, "
                   "settings, and SQL.")
    if not dev_scope and _ALLOWED_STAR_RE.search(content):
        out.append("[django] advisory: `ALLOWED_HOSTS = ['*']` accepts any Host header. Set an "
                   "explicit host list for any prod-bound settings module.")
    for m in _SECRET_LITERAL_RE.finditer(content):
        line = m.group(0)
        # Skip if the assignment clearly reads from the environment on the same line.
        if _ENV_HINT_RE.search(line):
            continue
        name = m.group(1)
        out.append(f"[django] advisory: `{name}` looks like a hardcoded secret literal in a "
                   "settings file. Read it from the environment / a secret store - never commit "
                   "secrets to source. A committed secret must be rotated, not just deleted.")
        break  # one nudge is enough
    return out


# --- migration checks --------------------------------------------------------
_RUNPYTHON_RE = re.compile(r"migrations\.RunPython\s*\(([^)]*)\)", re.DOTALL)
_NOOP_RE = re.compile(r"RunPython\.noop|reverse_code")
_REAL_IMPORT_RE = re.compile(r"^\s*from\s+[\w.]+\.models\s+import\b", re.MULTILINE)


def _check_migration(content):
    out = []
    for m in _RUNPYTHON_RE.finditer(content):
        args = m.group(1)
        # Reversible if it has a second positional arg or names reverse_code/noop.
        has_reverse = ("," in args and not args.strip().endswith(",")) or _NOOP_RE.search(args)
        if not has_reverse:
            out.append("[django] advisory: a `RunPython` here has no reverse - pass a "
                       "`reverse_code` (or `migrations.RunPython.noop` explicitly) so the "
                       "migration is reversible.")
            break
    if _RUNPYTHON_RE.search(content) and _REAL_IMPORT_RE.search(content):
        out.append("[django] advisory: this data migration imports real models "
                   "(`from app.models import ...`). Use `apps.get_model('app', 'Model')` - the "
                   "real model may have changed by the time the migration runs.")
    return out


# --- serializer checks -------------------------------------------------------
_FIELDS_ALL_RE = re.compile(r"fields\s*=\s*['\"]__all__['\"]")


def _check_serializer(content):
    if _FIELDS_ALL_RE.search(content):
        return ["[django] advisory: `fields = \"__all__\"` auto-exposes every model field "
                "(including new/sensitive ones) and invites mass-assignment. List serializer "
                "fields explicitly."]
    return []


def _content(tool_input):
    """Write content, Edit new_string, or every MultiEdit new_string."""
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    edits = tool_input.get("edits")
    if not content and isinstance(edits, list):
        content = "\n".join(e.get("new_string", "") for e in edits
                            if isinstance(e, dict) and isinstance(e.get("new_string"), str))
    return content if isinstance(content, str) else ""


def main():
    hooklib.watchdog(3.0)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool_input = hooklib.tool_input(payload)
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not isinstance(path, str) or not path.replace("\\", "/").lower().endswith(".py"):
        return 0
    content = _content(tool_input)
    if not content:
        return 0

    warnings = []
    if _is_settings(path):
        warnings += _check_settings(content, dev_scope=_is_dev_settings(path))
    if _is_migration(path):
        warnings += _check_migration(content)
    if _is_serializer(path):
        warnings += _check_serializer(content)

    if warnings:
        hooklib.context("PreToolUse", "\n".join(warnings))
    return 0  # ALWAYS allow - advisory only


if __name__ == "__main__":
    hooklib.run(main)
