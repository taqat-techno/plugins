#!/usr/bin/env python3
"""
SessionStart hook: Detect FastAPI presence, version, ORM, migration tool, and
async-vs-sync posture, and inject a short context line.

Outputs JSON in the official hookSpecificOutput format. Exit 0 always.
Read-only and fail-open: never blocks a session.
"""

import json
import os
import re
import sys
import threading

# Internal timeout guard — fail-open after 8 seconds.
_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Read stdin (required by hook protocol).
try:
    sys.stdin.read()
except Exception:
    pass


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return ""


_DEP_FILES = ("requirements.txt", "requirements/base.txt", "pyproject.toml", "Pipfile", "setup.cfg")


def detect():
    cwd = os.getcwd()

    blob = " ".join(_read(os.path.join(cwd, f)) for f in _DEP_FILES)

    # A FastAPI project is identified by a fastapi dependency declaration OR an
    # importable app entrypoint that constructs FastAPI(...).
    has_dep = bool(re.search(r"(?<![\w-])fastapi(?![\w-])", blob, re.IGNORECASE))
    entry = ""
    for cand in ("main.py", "app/main.py", "app.py", "src/main.py", "api/main.py"):
        text = _read(os.path.join(cwd, cand))
        if text and re.search(r"\bFastAPI\s*\(", text):
            entry = cand
            break
    if not has_dep and not entry:
        return ""

    parts = ["FastAPI project detected" + (f" ({entry})" if entry else " (dependency).") + "."]

    # FastAPI version from dependency declarations (no imports / no subprocess).
    m = re.search(r"fastapi[>=~ \"']+(\d+\.\d+(?:\.\d+)?)", blob, re.IGNORECASE)
    if m:
        parts.append(f"FastAPI ~{m.group(1)}.")

    # Pydantic major (v1 vs v2 changes the entire model API surface).
    pm = re.search(r"pydantic[>=~ \"']+(\d+)", blob, re.IGNORECASE)
    if pm:
        parts.append(f"Pydantic v{pm.group(1)}.")

    # ORM / data layer.
    if re.search(r"sqlmodel", blob, re.IGNORECASE):
        parts.append("SQLModel.")
    elif re.search(r"sqlalchemy", blob, re.IGNORECASE):
        parts.append("SQLAlchemy.")
    elif re.search(r"tortoise", blob, re.IGNORECASE):
        parts.append("Tortoise ORM.")

    # Async driver hint — asyncpg/aiomysql/aiosqlite imply an async stack.
    if re.search(r"asyncpg|aiomysql|aiosqlite|databases", blob, re.IGNORECASE):
        parts.append("Async DB driver.")

    # Migration tool.
    if os.path.isfile(os.path.join(cwd, "alembic.ini")) or re.search(r"alembic", blob, re.IGNORECASE):
        parts.append("Alembic.")

    # Settings library.
    if re.search(r"pydantic[-_]settings", blob, re.IGNORECASE):
        parts.append("pydantic-settings.")

    parts.append("Skills: routing/pydantic/database/migrations/config/security/testing/async-performance. "
                 "Commands: /fastapi-scaffold, /fastapi-migrate, /fastapi-test, /fastapi-security.")

    return "[FastAPI] " + " ".join(parts)


try:
    ctx = detect()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }
    print(json.dumps(output))
except Exception:
    print('{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}')

_timer.cancel()
sys.exit(0)
