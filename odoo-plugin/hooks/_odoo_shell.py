"""Shared helpers for the odoo plugin's Bash hooks (not a hook itself).

Two jobs:

* `commands(text)` turns a Bash command line into the argv lists that will actually
  run, so a guard matches the program being executed and not text inside quotes,
  comments, `echo` arguments, grep patterns or commit messages.
* `is_odoo_project(cwd)` decides whether the session is working on an Odoo stack, so
  the guards stay silent in every other project.

Stdlib only, no I/O beyond a few stat/listdir/small reads under the cwd's ancestors.
"""
from __future__ import annotations

import os
import re
import shlex

_SEPARATORS = {";", "&", "|", "\n", "(", ")", "`"}
_WRAPPERS = {"sudo", "env", "time", "nohup", "exec", "command", "builtin", "nice", "doas"}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _segments(text: str) -> list:
    """Split on ; & | newline ( ) ` outside quotes. `#` outside quotes at a word
    start begins a comment that runs to the end of the line."""
    out, buf = [], []
    quote = None
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            buf.append(ch)
            buf.append(text[i + 1])
            i += 2
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == "#" and (not buf or buf[-1].isspace()):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif ch in _SEPARATORS or (ch == "$" and i + 1 < n and text[i + 1] == "("):
            out.append("".join(buf))
            buf = []
            if ch == "$":
                i += 1
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def _argv(segment: str) -> list:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _strip_prefix(argv: list) -> list:
    """Drop leading VAR=value assignments and wrappers like sudo / env / time."""
    i = 0
    while i < len(argv):
        tok = argv[i]
        if _ASSIGN_RE.match(tok):
            i += 1
        elif os.path.basename(tok) in _WRAPPERS:
            i += 1
            # sudo -u user / env -i: skip that wrapper's options
            while i < len(argv) and argv[i].startswith("-"):
                i += 1
        else:
            break
    return argv[i:]


def commands(text: str, depth: int = 0) -> list:
    """The argv list of every simple command in `text`, recursing into `bash -c`."""
    result = []
    if not isinstance(text, str) or depth > 2:
        return result
    for seg in _segments(text):
        argv = _strip_prefix(_argv(seg))
        if not argv:
            continue
        prog = os.path.basename(argv[0]).lower()
        if prog in _SHELLS and "-c" in argv:
            idx = argv.index("-c")
            if idx + 1 < len(argv):
                result.extend(commands(argv[idx + 1], depth + 1))
                continue
        result.append(argv)
    return result


def prog(argv: list) -> str:
    """Lower-case program name without directory or .exe."""
    name = os.path.basename(argv[0].replace("\\", "/")).lower() if argv else ""
    return name[:-4] if name.endswith(".exe") else name


def python_script(argv: list):
    """For `python [opts] script.py args...` return (script basename, args), else None."""
    name = prog(argv)
    if not (name.startswith("python") or name == "py"):
        return None
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        if argv[i] == "-m":
            return None
        i += 1
    if i >= len(argv):
        return None
    return os.path.basename(argv[i].replace("\\", "/")).lower(), argv[i + 1:]


# --------------------------------------------------------------------------- scope

_COMPOSE_NAMES = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
_MARKERS = ("odoo-bin", "__manifest__.py", "odoo.conf", ".odoo-mcp.json", "odoo-service.local.md")
_ODOO_DIR_RE = re.compile(r"^odoo-?\d{2}(\.\d)?$", re.IGNORECASE)


def compose_mentions_odoo(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            return b"odoo" in fh.read(256 * 1024).lower()
    except OSError:
        return False


def is_odoo_project(cwd: str, max_up: int = 4) -> bool:
    """True when `cwd` (or one of its first few ancestors) looks like an Odoo stack:
    an Odoo compose file, odoo-bin, a module manifest, an odoo.conf, an `odooNN/`
    source directory, or this plugin's own per-project files."""
    try:
        here = os.path.abspath(cwd or os.getcwd())
    except OSError:
        return False
    for level in range(max_up + 1):
        try:
            names = os.listdir(here)
        except OSError:
            names = []
        for name in names:
            low = name.lower()
            if low in _MARKERS:
                return True
            if low in _COMPOSE_NAMES and compose_mentions_odoo(os.path.join(here, name)):
                return True
            if level == 0 and _ODOO_DIR_RE.match(name) and os.path.isdir(os.path.join(here, name)):
                return True
        if level == 0:
            # A checkout of addons: a direct child that is a module.
            for name in names[:200]:
                if os.path.isfile(os.path.join(here, name, "__manifest__.py")):
                    return True
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return False
