#!/usr/bin/env python3
"""PreToolUse hook (Bash): hard-block Docker commands that destroy Odoo-stack volumes.

An Odoo Docker stack keeps its Postgres database and its Odoo filestore in named
volumes. Destroying those volumes is irreversible. This hook blocks the three
deterministic ways a Bash command can wipe them:

  1. `docker compose down -v` / `--volumes`  (legacy `docker-compose down -v` too)
  2. `docker volume rm ...`
  3. `docker volume prune ...`

UNLESS an explicit override token appears in the SAME command line:
  - the literal string  ALLOW_VOLUME_DELETE
  - or the flag         --i-understand-data-loss

Reads JSON on stdin (Claude Code PreToolUse payload). The Bash command is read
from tool_input.command.

Exit 0 = allow (silent). Exit 2 = deny with a one-line reason on stderr.

Design notes:
- Stdlib-only, fast, no secrets read or printed.
- Conservative: matches only clearly-destructive, deterministically-detectable
  signals so reads and ordinary docker commands pass silently.
- Fail-OPEN on any internal error or timeout: if we cannot parse the payload or
  the matcher hangs, we exit 0 so the user is never hard-blocked by our bug.
"""
import json
import os
import re
import sys
import threading

# Internal timeout guard: fail-OPEN after 3 seconds. This hook does only cheap
# string/regex work, so >3s means something is wrong; allowing is safer than
# wedging every Bash call.
_timer = threading.Timer(3.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Override tokens. Presence of EITHER anywhere in the command line allows the
# destructive operation through. The user is explicitly opting into data loss.
_OVERRIDE_TOKENS = ("ALLOW_VOLUME_DELETE", "--i-understand-data-loss")

# `docker compose down ... -v` or `... --volumes` (modern plugin form) and the
# legacy hyphenated `docker-compose down ...` form. We require the `down`
# subcommand AND a volumes flag to be present; bare `down` (no -v) is safe and
# must pass silently.
_COMPOSE_DOWN_RE = re.compile(
    r"\bdocker(?:-compose|\s+compose)\b[^\n;&|]*\bdown\b", re.IGNORECASE
)
# A standalone -v / --volumes token (not part of a longer flag like --volumes-from
# or a path). Word-ish boundaries on both sides.
_VOLUMES_FLAG_RE = re.compile(r"(?<![\w-])(?:-v|--volumes)(?![\w-])")

# `docker volume rm ...` and `docker volume prune ...` (allowing intervening
# flags between `volume` and the verb, e.g. `docker volume rm -f name`).
_VOLUME_RM_RE = re.compile(
    r"\bdocker\s+volume\b[^\n;&|]*\b(?:rm|prune)\b", re.IGNORECASE
)


def _has_override(command: str) -> bool:
    return any(tok in command for tok in _OVERRIDE_TOKENS)


def _classify(command: str):
    """Return a short reason string if the command destroys volumes, else None."""
    # compose down WITH a volumes flag
    if _COMPOSE_DOWN_RE.search(command) and _VOLUMES_FLAG_RE.search(command):
        return "compose down with -v/--volumes deletes the Postgres DB + Odoo filestore volumes"
    # docker volume rm / prune
    m = _VOLUME_RM_RE.search(command)
    if m:
        verb = "prune" if "prune" in m.group(0).lower() else "rm"
        return f"docker volume {verb} destroys named Odoo-stack volumes (DB + filestore)"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = data.get("tool_input", {}) or {}
    command = tool_input.get("command", "")
    if not command or not isinstance(command, str):
        sys.exit(0)

    # Fast path: if there is no "docker" token at all, nothing to do.
    if "docker" not in command.lower():
        sys.exit(0)

    reason = _classify(command)
    if reason is None:
        _timer.cancel()
        sys.exit(0)

    if _has_override(command):
        # User explicitly opted into data loss in the same command. Allow.
        _timer.cancel()
        sys.exit(0)

    print(
        "BLOCKED: " + reason + ". This is irreversible and has no undo. "
        "Back up the DB dump + filestore first; to proceed anyway, re-run with "
        "the explicit override token ALLOW_VOLUME_DELETE (or the "
        "--i-understand-data-loss flag) in the same command.",
        file=sys.stderr,
    )
    _timer.cancel()
    sys.exit(2)


if __name__ == "__main__":
    main()
