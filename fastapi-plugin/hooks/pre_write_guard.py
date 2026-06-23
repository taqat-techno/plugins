#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): ADVISORY nudges for risky FastAPI edits.

This hook NEVER blocks and NEVER mutates anything. It prints one-line nudges to
stderr and ALWAYS exits 0. It inspects the content being written/edited and the
target path, and warns on a few deterministic, documented-risky shapes:

  Any Python file containing an `async def`:
    1. A blocking call inside async code — time.sleep(...), requests.<verb>(...),
       or a sync `psycopg2`/`urllib.request.urlopen` call. In an async path
       operation these block the whole event loop (every concurrent request).

  Config / settings files (config.py, settings.py, or a BaseSettings file):
    2. A hardcoded secret literal — SECRET_KEY / PASSWORD / API key / TOKEN
       assigned a non-empty string literal that is not read from the environment.

  Any file wiring CORS (CORSMiddleware):
    3. allow_origins=["*"] together with allow_credentials=True — a spec-invalid,
       credential-leaking combination the browser silently drops or that exposes
       authenticated responses to any origin.

  Alembic migration files (*/versions/*.py):
    4. A `downgrade()` whose body is only `pass` (or `...`) — the revision is not
       reversible; a real downgrade should undo what upgrade() did.

It stays SILENT on env-driven config, sync (def) routes, scoped CORS, and real
downgrades. Reads the PreToolUse JSON payload on stdin (content at
tool_input.content for Write, tool_input.new_string for Edit). Stdlib-only.
Fail-OPEN on any error.
"""
import json
import os
import re
import sys
import threading

# Fail-OPEN after 3s — advisory only, never wedge a Write/Edit.
_timer = threading.Timer(3.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()


def _is_config(path, content):
    p = path.replace("\\", "/").lower()
    base = os.path.basename(p)
    if base in ("config.py", "settings.py") or "config" in base or "settings" in base:
        return True
    # Any file declaring a pydantic BaseSettings subclass.
    return bool(re.search(r"\bBaseSettings\b|pydantic_settings", content))


def _is_migration(path):
    p = path.replace("\\", "/").lower()
    return "/versions/" in p or "/alembic/" in p or "migration" in os.path.basename(p)


# --- async event-loop blocking checks ----------------------------------------
_ASYNC_DEF_RE = re.compile(r"^\s*async\s+def\b", re.MULTILINE)
_SLEEP_RE = re.compile(r"\btime\.sleep\s*\(")
_REQUESTS_RE = re.compile(r"\brequests\.(get|post|put|patch|delete|head|request)\s*\(")
_URLOPEN_RE = re.compile(r"\burllib\.request\.urlopen\s*\(|\burlopen\s*\(")


def _check_async_blocking(content):
    if not _ASYNC_DEF_RE.search(content):
        return []
    out = []
    if _SLEEP_RE.search(content):
        out.append("[fastapi] advisory: `time.sleep(...)` inside async code blocks the entire "
                   "event loop (stalls every concurrent request). Use `await asyncio.sleep(...)`.")
    if _REQUESTS_RE.search(content):
        out.append("[fastapi] advisory: a synchronous `requests.*` call inside async code blocks "
                   "the event loop. Use an async client (`httpx.AsyncClient`) with `await`, or push "
                   "the blocking call through `await run_in_threadpool(...)`.")
    if _URLOPEN_RE.search(content):
        out.append("[fastapi] advisory: a blocking `urlopen(...)` inside async code stalls the "
                   "event loop. Use an async HTTP client or `run_in_threadpool`.")
    return out[:2]  # at most two nudges


# --- config secret check -----------------------------------------------------
_SECRET_LITERAL_RE = re.compile(
    r"^\s*(SECRET_KEY|[A-Za-z_]*PASSWORD|[A-Za-z_]*API_?KEY|[A-Za-z_]*TOKEN|[A-Za-z_]*SECRET)\s*[:=]\s*['\"][^'\"]+['\"]",
    re.MULTILINE,
)
_ENV_HINT_RE = re.compile(r"os\.environ|os\.getenv|getenv\s*\(|environ\s*\[", re.IGNORECASE)


def _check_config(content):
    for m in _SECRET_LITERAL_RE.finditer(content):
        line = m.group(0)
        if _ENV_HINT_RE.search(line):
            continue  # default supplied to a BaseSettings field is read from env at runtime
        name = m.group(1)
        return [f"[fastapi] advisory: `{name}` looks like a hardcoded secret literal in a config "
                "file. Read it from the environment via a pydantic-settings `BaseSettings` field "
                "(no inline default for prod secrets) — never commit secrets to source. A committed "
                "secret must be rotated, not just deleted."]
    return []


# --- CORS check --------------------------------------------------------------
_CORS_WILDCARD_RE = re.compile(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]")
_CORS_CREDS_RE = re.compile(r"allow_credentials\s*=\s*True")


def _check_cors(content):
    if "CORSMiddleware" not in content and "allow_origins" not in content:
        return []
    if _CORS_WILDCARD_RE.search(content) and _CORS_CREDS_RE.search(content):
        return ["[fastapi] advisory: `allow_origins=['*']` with `allow_credentials=True` is "
                "invalid per the CORS spec and unsafe — browsers reject the combination, and it "
                "would otherwise expose authenticated responses to any origin. List explicit "
                "origins when credentials are allowed."]
    return []


# --- alembic downgrade check -------------------------------------------------
_DOWNGRADE_RE = re.compile(r"def\s+downgrade\s*\([^)]*\)\s*:\s*(.*?)(?=\n(?:def|class|\Z)|\Z)", re.DOTALL)
_BODY_NOOP_RE = re.compile(r"^\s*(pass|\.\.\.)\s*$", re.MULTILINE)


def _check_migration(content):
    m = _DOWNGRADE_RE.search(content)
    if not m:
        return []
    body = m.group(1)
    # Strip comments/docstrings to judge whether the body actually does anything.
    stripped = re.sub(r"#.*", "", body)
    stripped = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", stripped)
    meaningful = [ln for ln in stripped.splitlines() if ln.strip() and not _BODY_NOOP_RE.match(ln)]
    if not meaningful:
        return ["[fastapi] advisory: this Alembic revision's `downgrade()` is empty (just `pass`). "
                "The migration is not reversible — write a real downgrade that undoes `upgrade()`, "
                "or document explicitly why a rollback is impossible."]
    return []


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = (data.get("tool_input") or {}) if isinstance(data, dict) else {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path or not path.replace("\\", "/").lower().endswith(".py"):
        _timer.cancel()
        sys.exit(0)

    # Content for Write, new_string for Edit.
    content = tool_input.get("content") or tool_input.get("new_string") or ""
    if not isinstance(content, str) or not content:
        _timer.cancel()
        sys.exit(0)

    warnings = []
    warnings += _check_async_blocking(content)
    warnings += _check_cors(content)
    if _is_config(path, content):
        warnings += _check_config(content)
    if _is_migration(path):
        warnings += _check_migration(content)

    if warnings:
        print("\n".join(warnings), file=sys.stderr)

    _timer.cancel()
    sys.exit(0)  # ALWAYS allow — advisory only


if __name__ == "__main__":
    main()
