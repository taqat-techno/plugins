#!/usr/bin/env python3
"""PreToolUse hook (Bash): guard destructive FastAPI/Alembic/DB commands.

Two tiers:

  BLOCK (exit 2) — irreversible schema/data destruction, unless the user opts in
  with the override token ALLOW_FASTAPI_DESTRUCTIVE in the same command:
    * alembic downgrade base       (rolls every migration back — drops the schema)
    * dropdb / DROP DATABASE       (destroys the whole database)

  ADVISORY (exit 0, stderr nudge) — not destructive but desynchronizes migration
  state and is a frequent foot-gun:
    * alembic stamp ...            (marks a revision as applied WITHOUT running it)

Stays SILENT on normal commands (alembic upgrade/revision, uvicorn, pytest, etc.).
Reads the PreToolUse JSON payload on stdin; the command is at tool_input.command.
Stdlib-only. The block path fails CLOSED only on a clear match; any parse error or
non-matching command exits 0 (fail-open) so it never wedges unrelated work.
"""
import json
import os
import re
import sys
import threading

# Fail-OPEN after 3s — cheap regex work; a hang should not block all Bash calls.
_timer = threading.Timer(3.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

_OVERRIDE = "ALLOW_FASTAPI_DESTRUCTIVE"

# alembic invocation prefix (alembic, python -m alembic, poetry run alembic, ...).
_ALEMBIC = r"(?:python[0-9.]*\s+-m\s+)?alembic"

_DOWNGRADE_BASE_RE = re.compile(_ALEMBIC + r"\b[^\n|&;]*\bdowngrade\b[^\n|&;]*\bbase\b", re.IGNORECASE)
_DROPDB_RE = re.compile(r"\bdropdb\b", re.IGNORECASE)
_DROP_DATABASE_RE = re.compile(r"\bdrop\s+database\b", re.IGNORECASE)

_STAMP_RE = re.compile(_ALEMBIC + r"\b[^\n|&;]*\bstamp\b", re.IGNORECASE)


def _classify_block(cmd):
    if _DOWNGRADE_BASE_RE.search(cmd):
        return ("`alembic downgrade base` rolls back every migration, dropping the entire schema "
                "managed by Alembic")
    if _DROPDB_RE.search(cmd) or _DROP_DATABASE_RE.search(cmd):
        return ("this drops the entire database")
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = (data.get("tool_input") or {}) if isinstance(data, dict) else {}
    command = tool_input.get("command", "")
    if not command or not isinstance(command, str):
        sys.exit(0)

    low = command.lower()
    # Fast path: no trigger token at all.
    if not any(t in low for t in ("downgrade", "dropdb", "drop database", "stamp")):
        _timer.cancel()
        sys.exit(0)

    reason = _classify_block(command)
    if reason:
        if _OVERRIDE in command:
            _timer.cancel()
            sys.exit(0)  # explicit opt-in
        print(
            "BLOCKED: " + reason + ". This is irreversible and has no undo. Back up the "
            "database first (e.g. pg_dump / a snapshot). To proceed anyway, re-run with the "
            "override token " + _OVERRIDE + " present in the same command.",
            file=sys.stderr,
        )
        _timer.cancel()
        sys.exit(2)

    # Advisory: alembic stamp (desyncs DB from migration history).
    if _STAMP_RE.search(command):
        print(
            "[fastapi] advisory: `alembic stamp` marks a revision as applied WITHOUT running its "
            "upgrade(), desynchronizing the DB from migration state. Use it only when the schema "
            "is PROVEN to already match the target revision — otherwise prefer a real "
            "`alembic upgrade`.",
            file=sys.stderr,
        )

    _timer.cancel()
    sys.exit(0)


if __name__ == "__main__":
    main()
