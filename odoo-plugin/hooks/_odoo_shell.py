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
# Wrapper -> the short and long options that consume the NEXT token as their value.
# Everything else starting with "-" is a flag. Without this table `sudo -u postgres
# dropdb x` was read as program `postgres`.
_WRAPPERS = {
    "sudo": ({"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "-R"},
             {"--user", "--group", "--close-from", "--chdir", "--host", "--prompt",
              "--role", "--type", "--other-user", "--command-timeout", "--chroot"}),
    "doas": ({"-u", "-C"}, set()),
    "env": ({"-u", "-C", "-S"}, {"--unset", "--chdir", "--split-string"}),
    "nice": ({"-n"}, {"--adjustment"}),
    "ionice": ({"-c", "-n", "-p", "-P", "-u"}, {"--class", "--classdata", "--pid"}),
    "time": ({"-f", "-o"}, {"--format", "--output"}),
    "timeout": ({"-s", "-k"}, {"--signal", "--kill-after"}),
    "nohup": (set(), set()),
    "exec": ({"-a"}, set()),
    "command": (set(), set()),
    "builtin": (set(), set()),
    "stdbuf": ({"-i", "-o", "-e"}, {"--input", "--output", "--error"}),
    "setsid": (set(), set()),
    "xargs": ({"-I", "-i", "-n", "-P", "-d", "-L", "-l", "-s", "-a", "-E", "-e"},
              {"--max-args", "--max-procs", "--delimiter", "--max-lines", "--max-chars",
               "--arg-file", "--eof", "--replace", "--process-slot-var"}),
}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "ash", "fish"}
_PWSH = {"powershell", "pwsh"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_MAX_DEPTH = 4

# docker/podman exec and compose exec/run: options that take a value.
_EXEC_VALUE_OPTS = {"-e", "--env", "--env-file", "-u", "--user", "-w", "--workdir",
                    "--detach-keys", "--index"}
_RUN_VALUE_OPTS = _EXEC_VALUE_OPTS | {"-v", "--volume", "-p", "--publish", "--name",
                                      "--entrypoint", "-l", "--label", "--network",
                                      "--cap-add", "--cap-drop", "--pull"}
_COMPOSE_GLOBAL_VALUE_OPTS = {"-f", "--file", "-p", "--project-name", "--project-directory",
                              "--env-file", "--profile", "--ansi", "--parallel", "--progress"}


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


def _skip_options(argv: list, i: int, short_vals: set, long_vals: set) -> int:
    """Index of the first non-option token at or after `i`, skipping option values."""
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            return i + 1
        if not tok.startswith("-") or tok == "-":
            return i
        if tok.startswith("--"):
            i += 2 if ("=" not in tok and tok in long_vals) else 1
        elif tok in short_vals:
            i += 2  # -u postgres
        else:
            i += 1  # a flag, or a value attached to its option (-upostgres, -oL)
    return i


def _strip_prefix(argv: list) -> list:
    """Drop leading VAR=value assignments and wrappers like sudo / env / timeout,
    together with the wrappers' options AND their option values."""
    i = 0
    while i < len(argv):
        tok = argv[i]
        name = _base(tok)
        if _ASSIGN_RE.match(tok):
            i += 1
        elif name in _WRAPPERS:
            if name in ("command", "builtin") and i + 1 < len(argv) and argv[i + 1] in ("-v", "-V"):
                return []  # `command -v dropdb` looks a program up, it does not run it
            short_vals, long_vals = _WRAPPERS[name]
            i = _skip_options(argv, i + 1, short_vals, long_vals)
            if name == "timeout" and i < len(argv):
                i += 1  # the DURATION positional
        else:
            break
    return argv[i:]


def _base(tok: str) -> str:
    name = os.path.basename(tok.replace("\\", "/")).lower()
    return name[:-4] if name.endswith(".exe") else name


def _shell_c_index(argv: list):
    """For `bash -c CMD`, `bash -lc CMD`, `sh -e -c CMD` return the index of CMD."""
    for i, tok in enumerate(argv[1:], start=1):
        if tok == "--" or not tok.startswith("-"):
            return None
        if not tok.startswith("--") and "c" in tok[1:] and tok[1:].isalpha():
            return i + 1 if i + 1 < len(argv) else None
    return None


def _container_inner(argv: list):
    """The command run inside a container by `docker|podman exec`, `docker compose
    exec|run` or `docker-compose exec|run`; None when argv is not one of those."""
    name = _base(argv[0])
    args = argv[1:]
    if name in ("docker", "podman") and args[:1] == ["exec"]:
        i = _skip_options(args, 1, {"-e", "-u", "-w"}, _EXEC_VALUE_OPTS)
        return args[i + 1:] if i < len(args) else []
    if name in ("docker", "podman") and args[:1] == ["compose"]:
        sub = args[1:]
    elif name in ("docker-compose", "podman-compose"):
        sub = args
    else:
        return None
    j = _skip_options(sub, 0, {"-f", "-p"}, _COMPOSE_GLOBAL_VALUE_OPTS)
    if j >= len(sub) or sub[j] not in ("exec", "run"):
        return None
    opts = _RUN_VALUE_OPTS if sub[j] == "run" else _EXEC_VALUE_OPTS
    k = _skip_options(sub, j + 1, {"-e", "-u", "-w", "-v", "-p", "-l"}, opts)
    return sub[k + 1:] if k < len(sub) else []


def _expand(argv: list, depth: int) -> list:
    """Unwrap one simple command into the argv lists that really run."""
    argv = _strip_prefix(argv)
    if not argv or depth > _MAX_DEPTH:
        return [argv] if argv else []
    name = _base(argv[0])
    if name in _SHELLS:
        idx = _shell_c_index(argv)
        if idx is not None:
            return commands(argv[idx], depth + 1)
    if name in _PWSH:
        for i, tok in enumerate(argv[1:], start=1):
            low = tok.lower()
            if low in ("-command", "-c", "/command", "/c") and i + 1 < len(argv):
                return commands(" ".join(argv[i + 1:]), depth + 1)
    if name == "cmd":
        for i, tok in enumerate(argv[1:], start=1):
            if tok.lower() in ("/c", "/k") and i + 1 < len(argv):
                return commands(" ".join(argv[i + 1:]), depth + 1)
    if name == "eval" and len(argv) > 1:
        return commands(" ".join(argv[1:]), depth + 1)
    inner = _container_inner(argv)
    if inner:
        return _expand(inner, depth + 1)
    return [argv]


def commands(text: str, depth: int = 0) -> list:
    """The argv list of every simple command in `text`, unwrapping `bash -c` (and
    -lc), `sudo -u USER`, `env`, `timeout`, `nohup`, `xargs`, `eval`, `powershell
    -Command`, `cmd /c` and commands run in a container by `docker exec` /
    `docker compose exec|run`."""
    result = []
    if not isinstance(text, str) or depth > _MAX_DEPTH:
        return result
    for seg in _segments(text):
        result.extend(_expand(_argv(seg), depth))
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
_MARKERS = ("odoo-bin", "__manifest__.py", "odoo.conf", "odoo-service.local.md")
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
