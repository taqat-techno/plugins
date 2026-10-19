#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): ADVISORY nudges for risky FastAPI edits.

This hook NEVER blocks and NEVER mutates anything. It hands one-line nudges to
Claude as PreToolUse additionalContext JSON on stdout and ALWAYS exits 0. It inspects the content being written/edited and the
target path, and warns on a few deterministic, documented-risky shapes:

  Any Python file containing an `async def`:
    1. A blocking call made inside an `async def` body (checked with `ast`, so a
       sync `def` in the same file is not flagged) — time.sleep(...),
       requests.<verb>(...), or urlopen(...). In an async path operation these
       block the whole event loop. A hunk that does not parse falls back to a
       file-level regex.

  Config / settings files (config.py, settings.py, or a BaseSettings file):
    2. A hardcoded secret literal — SECRET_KEY / PASSWORD / API key / TOKEN, any
       case and optionally type-annotated (`secret_key: str = "..."`), assigned a
       non-empty string literal that is not read from the environment.

  Any file wiring CORS (CORSMiddleware):
    3. allow_origins=["*"] together with allow_credentials=True — a spec-invalid,
       credential-leaking combination the browser silently drops or that exposes
       authenticated responses to any origin.

  Alembic migration files (*/versions/*.py):
    4. A `downgrade()` whose body is only `pass` (or `...`) — the revision is not
       reversible; a real downgrade should undo what upgrade() did.

It stays SILENT on env-driven config, sync (def) routes, scoped CORS, and real
downgrades. Reads the PreToolUse JSON payload on stdin (content at
tool_input.content for Write, tool_input.new_string for Edit, edits[].new_string
for MultiEdit). Stdlib-only.
Fail-OPEN on any error.
"""
import ast
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402


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
_REQUEST_VERBS = {"get", "post", "put", "patch", "delete", "head", "request"}

_MSG = {
    "sleep": "[fastapi] advisory: `time.sleep(...)` inside an `async def` blocks the entire "
             "event loop (stalls every concurrent request). Use `await asyncio.sleep(...)`.",
    "requests": "[fastapi] advisory: a synchronous `requests.*` call inside an `async def` "
                "blocks the event loop. Use an async client (`httpx.AsyncClient`) with `await`, "
                "or push the blocking call through `await run_in_threadpool(...)`.",
    "urlopen": "[fastapi] advisory: a blocking `urlopen(...)` inside an `async def` stalls the "
               "event loop. Use an async HTTP client or `run_in_threadpool`.",
}


def _call_kind(node, sleep_names):
    func = node.func
    if isinstance(func, ast.Attribute):
        owner = func.value
        if isinstance(owner, ast.Name) and owner.id == "time" and func.attr == "sleep":
            return "sleep"
        if isinstance(owner, ast.Name) and owner.id == "requests" and func.attr in _REQUEST_VERBS:
            return "requests"
        if func.attr == "urlopen":
            return "urlopen"
    elif isinstance(func, ast.Name):
        if func.id in sleep_names:
            return "sleep"
        if func.id == "urlopen":
            return "urlopen"
    return None


def _blocking_in_async(tree):
    """Blocking calls made lexically inside an `async def`, not in a nested sync def
    or lambda (a sync `def` path operation runs in the threadpool, so blocking is fine)."""
    sleep_names = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                   and n.module == "time" for a in n.names if a.name == "sleep"}
    kinds = []

    def visit(node, in_async):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.AsyncFunctionDef):
                visit(child, True)
            elif isinstance(child, (ast.FunctionDef, ast.Lambda, ast.ClassDef)):
                visit(child, False)
            else:
                if in_async and isinstance(child, ast.Call):
                    kind = _call_kind(child, sleep_names)
                    if kind and kind not in kinds:
                        kinds.append(kind)
                visit(child, in_async)

    visit(tree, False)
    return kinds


def _check_async_blocking(content):
    if not _ASYNC_DEF_RE.search(content):
        return []
    try:
        kinds = _blocking_in_async(ast.parse(content))
    except (SyntaxError, ValueError, RecursionError):
        # A partial Edit hunk may not parse: fall back to the file-level regex.
        kinds = [k for k, rx in (("sleep", _SLEEP_RE), ("requests", _REQUESTS_RE),
                                 ("urlopen", _URLOPEN_RE)) if rx.search(content)]
    return [_MSG[k] for k in kinds][:2]  # at most two nudges


# --- config secret check -----------------------------------------------------
# A secret-shaped name, optionally type-annotated (`secret_key: str = "..."` in a
# BaseSettings class), assigned a non-empty string literal. Case-insensitive.
_SECRET_LITERAL_RE = re.compile(
    r"^\s*(secret_key|[a-z_]*password|[a-z_]*api_?key|[a-z_]*token|[a-z_]*secret)"
    r"\s*(?::\s*[^=\n]+?)?\s*=\s*[rbu]?['\"][^'\"]+['\"]",
    re.MULTILINE | re.IGNORECASE,
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
    warnings += _check_async_blocking(content)
    warnings += _check_cors(content)
    if _is_config(path, content):
        warnings += _check_config(content)
    if _is_migration(path):
        warnings += _check_migration(content)

    if warnings:
        hooklib.context("PreToolUse", "\n".join(warnings))
    return 0  # ALWAYS allow - advisory only


if __name__ == "__main__":
    hooklib.run(main)
