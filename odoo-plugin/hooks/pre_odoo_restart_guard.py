#!/usr/bin/env python3
"""PreToolUse hook (Bash): ADVISORY nudges for risky Odoo stack restart / clone shapes.

This hook NEVER blocks, NEVER mutates files, NEVER kills processes. It only hands a
one-line nudge to Claude as PreToolUse additionalContext JSON on stdout and ALWAYS
exits 0. Claude receives it next to the tool result, so it informs the next call
rather than this one. It warns on three documented-dangerous command shapes:

  1. Unbounded Odoo readiness polling: `curl --retry-connrefused` aimed at an
     Odoo-like port/endpoint with no bound (`--max-time` / `--retry-max-time` /
     `--retry-delay`). An unbounded retry storm can take down the backend, notably
     through IDE port-forwarding.
  2. Stop and start in one command line: `pkill ...` followed by an Odoo launch
     (`odoo-bin`, `python -m odoo`). The pkill pattern self-matches this command line
     and can SIGTERM the chain (exit 144) before the start runs.
  3. Raw Odoo DB clone in an Odoo project: `CREATE DATABASE ... TEMPLATE` via psql /
     `createdb -T` copies only SQL and leaves the filestore / attachments broken.

It matches the commands that run (parsed from the shell line), not text inside echo,
grep patterns or commit messages. It is silent on the safe forms: a bounded curl, a
pkill and an odoo-bin in separate tool calls, `odoo-bin db duplicate`.

Fails open: bad input, an exception or the 3 s watchdog all end in exit 0.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_vendor"))
sys.path.insert(0, HERE)

import hooklib  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# An Odoo-like target: an 80xx port, a /web endpoint, or a *.localhost host.
_ODOO_TARGET_RE = re.compile(r":80\d\d(?:\b|/)|/web(?:/|\b)|\.localhost\b", re.IGNORECASE)
_BOUND_FLAGS = ("--max-time", "-m", "--retry-max-time", "--retry-delay")
_CREATE_TEMPLATE_RE = re.compile(r"create\s+database\b[^;]*\btemplate\b", re.IGNORECASE)

CURL_ADVICE = (
    "[odoo] advisory: `curl --retry-connrefused` against an Odoo port with no "
    "`--max-time`/`--retry-max-time`/`--retry-delay` can retry-storm and take down "
    "the backend (notably through IDE port-forwarding). Use a BOUNDED poll (fixed "
    "retry count + delay + `--max-time`), or grep the logfile for "
    "'HTTP service ... running'."
)
PKILL_ADVICE = (
    "[odoo] advisory: `pkill ... && ... odoo-bin` in one chain - the pkill "
    "pattern self-matches this command line (including the odoo-bin part) and "
    "can SIGTERM the chain (exit 144) before the start runs. Split stop and "
    "start into SEPARATE calls and kill by resolved PID."
)
TEMPLATE_ADVICE = (
    "[odoo] advisory: cloning a database via `CREATE DATABASE ... TEMPLATE` / "
    "`createdb -T` copies only SQL. If this is an Odoo DB, the filestore / "
    "attachments are NOT copied and will be broken. Use Odoo duplication that "
    "copies the filestore: `odoo-bin db duplicate` or "
    "`exp_duplicate_database(src, dst)`."
)


def _is_odoo_launch(argv) -> bool:
    import _odoo_shell as sh

    name = sh.prog(argv)
    if name in ("odoo-bin", "odoo"):
        return True
    if name.startswith("python") or name == "py":
        if "-m" in argv:
            i = argv.index("-m")
            return i + 1 < len(argv) and argv[i + 1] == "odoo"
        script = sh.python_script(argv)
        return bool(script) and script[0] in ("odoo-bin", "odoo", "odoo-bin.py")
    return False


def advisories(command: str, cwd: str) -> list:
    import _odoo_shell as sh

    out = []
    cmds = sh.commands(command)
    for argv in cmds:
        if sh.prog(argv) == "curl" and "--retry-connrefused" in argv:
            joined = " ".join(argv)
            bounded = any(a in _BOUND_FLAGS or a.split("=", 1)[0] in _BOUND_FLAGS for a in argv)
            if _ODOO_TARGET_RE.search(joined) and not bounded:
                out.append(CURL_ADVICE)
                break
    for i, argv in enumerate(cmds):
        if sh.prog(argv) == "pkill" and any(_is_odoo_launch(a) for a in cmds[i + 1:]):
            out.append(PKILL_ADVICE)
            break
    for argv in cmds:
        name = sh.prog(argv)
        clone = (name == "createdb" and any(a in ("-T", "--template") or a.startswith("--template=")
                                            for a in argv)) or \
                (name == "psql" and bool(_CREATE_TEMPLATE_RE.search(" ".join(argv))
                                         or _CREATE_TEMPLATE_RE.search(command)))
        if clone and sh.is_odoo_project(cwd):
            out.append(TEMPLATE_ADVICE)
            break
    return out


def main() -> int:
    hooklib.watchdog(3.0)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    command = hooklib.tool_input(payload).get("command", "")
    if not isinstance(command, str) or not command:
        return 0
    low = command.lower()
    if not any(t in low for t in ("curl", "pkill", "psql", "createdb")):
        return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    warnings = advisories(command, cwd or os.getcwd())
    if warnings:
        hooklib.context("PreToolUse", "\n".join(warnings))
    return 0  # ALWAYS allow - advisory only


if __name__ == "__main__":
    hooklib.run(main)
