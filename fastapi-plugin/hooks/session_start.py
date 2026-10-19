#!/usr/bin/env python3
"""SessionStart hook: detect a FastAPI project and hand Claude one context line.

A FastAPI project is a `fastapi` dependency declaration, or an entrypoint that
constructs `FastAPI(...)` (main.py, app.py, app/main.py, api/main.py, src/main.py,
src/<pkg>/main.py), in the session directory or up to two levels below it
(monorepos keep the service in `backend/` or `services/api/`). When found, it
reports FastAPI / Pydantic versions, the ORM, an async driver and Alembic.

Outputs SessionStart additionalContext JSON only when a FastAPI project is found;
otherwise it prints nothing. Read-only, no imports of the project, no subprocess.
Fails open: any error ends in exit 0 with no output.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

_SKIP = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "site-packages",
         "dist", "build", ".tox"}
_DEP_FILES = ("requirements.txt", "requirements/base.txt", "pyproject.toml", "Pipfile", "setup.cfg")
_ENTRIES = ("main.py", "app/main.py", "app.py", "src/main.py", "api/main.py", "src/*/main.py")
_DEP_RE = re.compile(r"(?<![\w.-])fastapi(?![\w-])", re.IGNORECASE)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(500_000)
    except (OSError, UnicodeError):
        return ""


def _probe(d):
    """(dependency blob, entrypoint relative path or '') when `d` is a FastAPI project."""
    blob = " ".join(_read(os.path.join(d, f)) for f in _DEP_FILES)
    entry = ""
    for pattern in _ENTRIES:
        for cand in sorted(glob.glob(os.path.join(d, pattern))):
            if re.search(r"\bFastAPI\s*\(", _read(cand)):
                entry = os.path.relpath(cand, d).replace("\\", "/")
                break
        if entry:
            break
    if _DEP_RE.search(blob) or entry:
        return blob, entry
    return None


def find_project(root, depth=2):
    level = [root]
    for _ in range(depth + 1):
        nxt = []
        for d in level:
            hit = _probe(d)
            if hit:
                return d, hit[0], hit[1]
            try:
                nxt += sorted(e.path for e in os.scandir(d) if e.is_dir()
                              and e.name not in _SKIP and not e.name.startswith("."))
            except OSError:
                continue
        level = nxt
    return None


def detect(cwd):
    found = find_project(cwd)
    if not found:
        return ""
    proj, blob, entry = found
    rel = os.path.relpath(proj, cwd).replace("\\", "/")
    where = entry if entry else "dependency"
    if rel != ".":
        where = f"{rel}/{entry}" if entry else f"{rel}, dependency"
    parts = [f"FastAPI project detected ({where})."]

    m = re.search(r"fastapi(?:\[[^\]]*\])?[>=~ \"']+(\d+\.\d+(?:\.\d+)?)", blob, re.IGNORECASE)
    if m:
        parts.append(f"FastAPI ~{m.group(1)}.")
    pm = re.search(r"(?<![\w-])pydantic[>=~ \"']+(\d+)", blob, re.IGNORECASE)
    if pm:
        parts.append(f"Pydantic v{pm.group(1)}.")
    if re.search(r"\bsqlmodel\b", blob, re.IGNORECASE):
        parts.append("SQLModel.")
    elif re.search(r"\bsqlalchemy\b", blob, re.IGNORECASE):
        parts.append("SQLAlchemy.")
    elif re.search(r"\btortoise", blob, re.IGNORECASE):
        parts.append("Tortoise ORM.")
    # A dependency entry, not a word: "databases" must start a requirement line or a
    # quoted dependency string, and be followed by extras, a version spec or the end.
    if re.search(r"(?im)(?:^\s*|[\"'])(asyncpg|aiomysql|aiosqlite|databases)"
                 r"(?:\[[^\]]*\])?\s*(?:[<>=~!;\"']|$)", blob):
        parts.append("Async DB driver.")
    if os.path.isfile(os.path.join(proj, "alembic.ini")) or re.search(r"\balembic\b", blob, re.IGNORECASE):
        parts.append("Alembic.")
    if re.search(r"pydantic[-_]settings", blob, re.IGNORECASE):
        parts.append("pydantic-settings.")

    parts.append("Skills: routing/pydantic/database/migrations/config/security/testing/async-performance. "
                 "Commands: /fastapi:scaffold, /fastapi:migrate, /fastapi:test, /fastapi:security.")
    return "[FastAPI] " + " ".join(parts)


def main():
    hooklib.watchdog(8.0)
    payload = hooklib.read_payload() or {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    text = detect(cwd if cwd and os.path.isdir(cwd) else os.getcwd())
    if text:
        hooklib.context("SessionStart", text)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
