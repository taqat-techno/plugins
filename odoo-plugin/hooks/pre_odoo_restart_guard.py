#!/usr/bin/env python3
"""PreToolUse hook (Bash): ADVISORY nudges for risky Odoo stack restart / clone shapes.

This hook NEVER blocks, NEVER mutates files, NEVER kills processes. It only prints a
one-line nudge to stderr and ALWAYS exits 0. It warns on three deterministic,
documented-dangerous Bash command shapes:

  1. Unbounded Odoo readiness polling: `curl --retry-connrefused` aimed at an
     Odoo-like port/endpoint with no bound (`--max-time` / `--retry-max-time` /
     `--retry-delay`). An unbounded retry storm can take down the backend, notably
     through IDE port-forwarding.
  2. Combined stop+start in one chain: `pkill ... && ... odoo-bin` — the pkill
     pattern self-matches this command line (including the odoo-bin part) and can
     SIGTERM the chain (exit 144) before the start runs.
  3. Raw Odoo DB clone: `CREATE DATABASE ... TEMPLATE` / `createdb -T` — copies only
     SQL and leaves the Odoo filestore / attachments broken.

It stays SILENT on the safe forms: a bounded curl, a split pkill and odoo-bin in
separate commands, `odoo-bin db duplicate`, and any non-Odoo command.

Reads the Claude Code PreToolUse JSON payload on stdin; the Bash command is at
tool_input.command. Stdlib-only. Fail-OPEN (exit 0) on any parse error or timeout.
"""
import json
import os
import re
import sys
import threading

# Fail-OPEN after 3s. This hook does only cheap regex work; >3s means something is
# wrong, and since it is advisory we simply exit 0 (never wedge a Bash call).
_timer = threading.Timer(3.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# --- pattern 1: unbounded Odoo readiness poll --------------------------------
# An Odoo-like target: an 80xx port, a /web endpoint, or a *.localhost host.
_ODOO_TARGET_RE = re.compile(r":80\d\d(?:\b|/)|/web(?:/|\b)|\.localhost\b", re.IGNORECASE)
# Any of these flags means the retry loop is throttled/bounded -> safe -> silent.
_BOUNDED_RE = re.compile(r"--max-time\b|--retry-max-time\b|--retry-delay\b", re.IGNORECASE)


def _warn_unbounded_curl(cmd):
    low = cmd.lower()
    if "curl" not in low or "--retry-connrefused" not in low:
        return None
    if not _ODOO_TARGET_RE.search(cmd):
        return None
    if _BOUNDED_RE.search(cmd):
        return None  # bounded -> safe -> silent
    return (
        "[odoo] advisory: `curl --retry-connrefused` against an Odoo port with no "
        "`--max-time`/`--retry-max-time`/`--retry-delay` can retry-storm and take down "
        "the backend (notably through IDE port-forwarding). Use a BOUNDED poll (fixed "
        "retry count + delay + `--max-time`), or grep the logfile for "
        "'HTTP service ... running'."
    )


# --- pattern 2: combined stop+start (pkill ... && ... odoo launcher) ----------
_ODOO_LAUNCH = r"(?:odoo-bin|odoo\s+-c|-m\s+odoo|setup/odoo)"
_PKILL_CHAIN_RE = re.compile(r"\bpkill\b[^\n]*&&[^\n]*" + _ODOO_LAUNCH, re.IGNORECASE)


def _warn_pkill_chain(cmd):
    if _PKILL_CHAIN_RE.search(cmd):
        return (
            "[odoo] advisory: `pkill ... && ... odoo-bin` in one chain — the pkill "
            "pattern self-matches this command line (including the odoo-bin part) and "
            "can SIGTERM the chain (exit 144) before the start runs. Split stop and "
            "start into SEPARATE calls and kill by resolved PID."
        )
    return None


# --- pattern 3: raw Odoo DB clone via psql TEMPLATE / createdb -T -------------
_CREATE_TEMPLATE_RE = re.compile(r"create\s+database\b[^\n;]*\btemplate\b", re.IGNORECASE)
_CREATEDB_T_RE = re.compile(r"\bcreatedb\b[^\n;]*(?:-T\b|--template\b)", re.IGNORECASE)


def _warn_psql_template(cmd):
    if _CREATE_TEMPLATE_RE.search(cmd) or _CREATEDB_T_RE.search(cmd):
        return (
            "[odoo] advisory: cloning a database via `CREATE DATABASE ... TEMPLATE` / "
            "`createdb -T` copies only SQL. If this is an Odoo DB, the filestore / "
            "attachments are NOT copied and will be broken. Use Odoo duplication that "
            "copies the filestore: `odoo-bin db duplicate` or "
            "`exp_duplicate_database(src, dst)`."
        )
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
    # Fast path: none of the trigger tokens -> nothing to advise.
    if not any(t in low for t in ("curl", "pkill", "psql", "createdb", "create database")):
        _timer.cancel()
        sys.exit(0)

    warnings = [
        w
        for w in (
            _warn_unbounded_curl(command),
            _warn_pkill_chain(command),
            _warn_psql_template(command),
        )
        if w
    ]
    if warnings:
        print("\n".join(warnings), file=sys.stderr)

    _timer.cancel()
    sys.exit(0)  # ALWAYS allow — advisory only


if __name__ == "__main__":
    main()
