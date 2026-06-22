#!/usr/bin/env python3
"""PreToolUse hook (Bash): guard destructive Django management / DB commands.

Two tiers:

  BLOCK (exit 2) — irreversible data destruction via Django/DB tooling, unless the
  user opts in with the override token ALLOW_DJANGO_DESTRUCTIVE in the same command:
    * manage.py flush            (deletes ALL rows from every table)
    * manage.py sqlflush         (emits the SQL to do the above — execution risk)
    * manage.py reset_db         (django-extensions: drops & recreates the DB)
    * dropdb / DROP DATABASE     (destroys the whole database)

  ADVISORY (exit 0, stderr nudge) — not destructive but desynchronizes migration
  state and is a frequent foot-gun:
    * manage.py migrate ... --fake

Stays SILENT on normal commands (migrate, makemigrations, test, runserver, etc.).
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

_OVERRIDE = "ALLOW_DJANGO_DESTRUCTIVE"

# manage.py (or ./manage.py, python -m, django-admin) invocation prefix.
_MANAGE = r"(?:python[0-9.]*\s+)?(?:-m\s+)?(?:\./)?(?:manage\.py|django-admin|django-admin\.py)"

_FLUSH_RE = re.compile(_MANAGE + r"\b[^\n|&;]*\bflush\b", re.IGNORECASE)
_SQLFLUSH_RE = re.compile(_MANAGE + r"\b[^\n|&;]*\bsqlflush\b", re.IGNORECASE)
_RESET_DB_RE = re.compile(_MANAGE + r"\b[^\n|&;]*\breset_db\b", re.IGNORECASE)
_DROPDB_RE = re.compile(r"\bdropdb\b", re.IGNORECASE)
_DROP_DATABASE_RE = re.compile(r"\bdrop\s+database\b", re.IGNORECASE)

_FAKE_RE = re.compile(_MANAGE + r"\b[^\n|&;]*\bmigrate\b[^\n|&;]*--fake\b", re.IGNORECASE)


def _classify_block(cmd):
    # migrate --fake-initial is a legitimate, safer variant — do not match it as --fake.
    if _FLUSH_RE.search(cmd):
        return ("`manage.py flush` deletes ALL data from every table in the database")
    if _SQLFLUSH_RE.search(cmd):
        return ("`manage.py sqlflush` emits SQL that deletes all data; running its output "
                "wipes every table")
    if _RESET_DB_RE.search(cmd):
        return ("`manage.py reset_db` drops and recreates the entire database")
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
    if not any(t in low for t in ("flush", "reset_db", "dropdb", "drop database", "--fake")):
        _timer.cancel()
        sys.exit(0)

    reason = _classify_block(command)
    if reason:
        if _OVERRIDE in command:
            _timer.cancel()
            sys.exit(0)  # explicit opt-in
        print(
            "BLOCKED: " + reason + ". This is irreversible and has no undo. Back up the "
            "database first (e.g. pg_dump / a fixture dump). To proceed anyway, re-run with "
            "the override token " + _OVERRIDE + " present in the same command.",
            file=sys.stderr,
        )
        _timer.cancel()
        sys.exit(2)

    # Advisory: migrate --fake (but not --fake-initial alone).
    if _FAKE_RE.search(command) and "--fake-initial" not in low:
        print(
            "[django] advisory: `migrate --fake` marks migrations as applied WITHOUT running "
            "them, desynchronizing the DB from migration state. Use it only when the schema is "
            "PROVEN to already match - otherwise prefer a real migrate or a merge migration.",
            file=sys.stderr,
        )

    _timer.cancel()
    sys.exit(0)


if __name__ == "__main__":
    main()
