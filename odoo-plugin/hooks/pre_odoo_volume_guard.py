#!/usr/bin/env python3
"""PreToolUse hook (Bash): ask the user before a command destroys Odoo data.

It returns `permissionDecision: "ask"` - the user sees the command and the reason
and decides - for:

  1. `docker compose down -v|--volumes` (and legacy `docker-compose down -v`) on an
     Odoo stack: deletes the Postgres database and filestore volumes.
  2. `docker volume rm|remove|prune` and `docker system prune --volumes` on an Odoo
     stack, or naming a volume whose name contains "odoo".
  3. This plugin's destructive database scripts: `db_manager.py drop`,
     `db_manager.py reset-admin`, `db_manager.py restore --no-create` (restore over an
     existing database), and `dropdb` inside an Odoo project.
  4. `server_manager.py stop --all --yes`: stops every Odoo server on the machine.

Scope: only on an Odoo stack (see _odoo_shell.is_odoo_project) or when the command
itself names Odoo; silent everywhere else. It matches the commands that will run,
parsed from the shell line, never text inside quotes, comments, echo or grep.

There is no override token the model could add to the command. The user answers the
prompt. To switch the guard off, the user sets ODOO_DESTRUCTIVE_GUARD=off in the
environment before starting Claude Code.

Fails open: bad input, an exception or the 3 s watchdog all end in exit 0.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_vendor"))
sys.path.insert(0, HERE)

import hooklib  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_TRIGGERS = ("docker", "podman", "db_manager", "server_manager", "dropdb")
_ADVICE = (" This cannot be undone. Back up first (db_manager.py backup, plus the "
           "filestore). Approve only if you mean to delete this data.")


def _volumes_flag(args) -> bool:
    for a in args:
        if a in ("-v", "--volumes"):
            return True
        # combined short flags, e.g. -fv
        if a.startswith("-") and not a.startswith("--") and "v" in a[1:] and a[1:].isalpha():
            return True
    return False


def _compose_files(args, cwd):
    files = []
    for i, a in enumerate(args):
        if a in ("-f", "--file") and i + 1 < len(args):
            files.append(args[i + 1])
        elif a.startswith("--file="):
            files.append(a.split("=", 1)[1])
    return [f if os.path.isabs(f) else os.path.join(cwd, f) for f in files]


def _docker_reason(argv, cwd, odoo_project):
    """Reason string when a docker/podman argv destroys Odoo volumes, else None."""
    import _odoo_shell as sh

    name = sh.prog(argv)
    args = argv[1:]
    if name in ("docker", "podman") and args[:1] == ["compose"]:
        sub = args[1:]
    elif name in ("docker-compose", "podman-compose"):
        sub = args
    else:
        sub = None

    if sub is not None:
        if "down" in sub and _volumes_flag(sub[sub.index("down") + 1:] + sub[:sub.index("down")]):
            files = _compose_files(sub, cwd)
            odoo = any(sh.compose_mentions_odoo(f) for f in files) if files else odoo_project
            if odoo:
                return "`compose down -v` deletes this Odoo stack's database and filestore volumes."
        return None

    if name not in ("docker", "podman") or not args:
        return None
    if args[0] == "volume" and len(args) > 1:
        verb, rest = args[1], args[2:]
        if verb in ("rm", "remove"):
            names = [a for a in rest if not a.startswith("-")]
            if odoo_project or any("odoo" in n.lower() for n in names):
                return "`docker volume %s %s` destroys Odoo volumes (database, filestore)." % (
                    verb, " ".join(names) or "...")
        if verb == "prune" and odoo_project:
            return "`docker volume prune` can delete this Odoo stack's database and filestore volumes."
    if args[0] == "system" and len(args) > 1 and args[1] == "prune" and "--volumes" in args \
            and odoo_project:
        return "`docker system prune --volumes` can delete this Odoo stack's volumes."
    return None


def _script_reason(argv, odoo_project):
    import _odoo_shell as sh

    if sh.prog(argv) == "dropdb" and odoo_project:
        target = [a for a in argv[1:] if not a.startswith("-")]
        return "`dropdb %s` drops an Odoo database." % (target[-1] if target else "")
    script = sh.python_script(argv)
    if not script:
        return None
    base, args = script
    sub = args[0] if args else ""
    if base == "db_manager.py":
        db = ""
        for i, a in enumerate(args):
            if a in ("--db", "-d") and i + 1 < len(args):
                db = args[i + 1]
        if sub == "drop":
            return "db_manager.py drop deletes database %r." % db
        if sub == "reset-admin":
            return "db_manager.py reset-admin overwrites the admin password of database %r." % db
        if sub == "restore" and "--no-create" in args:
            return "db_manager.py restore --no-create restores over existing database %r." % db
    if base == "server_manager.py" and sub == "stop" and "--all" in args and "--yes" in args:
        return "server_manager.py stop --all --yes stops every Odoo server on this machine."
    return None


def main() -> int:
    hooklib.watchdog(3.0)
    if os.environ.get("ODOO_DESTRUCTIVE_GUARD", "").strip().lower() in ("off", "0", "false"):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    command = hooklib.tool_input(payload).get("command", "")
    if not isinstance(command, str) or not command:
        return 0
    low = command.lower()
    if not any(t in low for t in _TRIGGERS):
        return 0

    import _odoo_shell as sh

    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    cwd = cwd or os.getcwd()
    cache = {}

    def odoo_project():
        if "v" not in cache:
            cache["v"] = sh.is_odoo_project(cwd)
        return cache["v"]

    reasons = []
    for argv in sh.commands(command):
        name = sh.prog(argv)
        if name in ("docker", "podman", "docker-compose", "podman-compose"):
            r = _docker_reason(argv, cwd, odoo_project())
        elif name == "dropdb" or sh.python_script(argv):
            r = _script_reason(argv, odoo_project() if name == "dropdb" else True)
        else:
            r = None
        if r:
            reasons.append(r)
    if reasons:
        hooklib.ask("[odoo] " + " ".join(dict.fromkeys(reasons)) + _ADVICE)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
