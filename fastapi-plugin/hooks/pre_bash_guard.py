#!/usr/bin/env python3
"""PreToolUse hook (Bash): ask before destructive FastAPI / Alembic / database commands.

Scope: active only in a FastAPI project, meaning `fastapi` is declared in a
pyproject.toml, requirements*.txt, Pipfile, setup.cfg or setup.py found walking up
from the session cwd (or from a `cd` target in the command), or at most two
directories below CLAUDE_PROJECT_DIR. Elsewhere it exits 0.

It parses the shell command (quote removal included, so `down''grade` is
`downgrade`) and matches the commands that will RUN, not text inside quotes,
comments, `echo`, `grep` patterns or commit messages. SQL is only inspected where it
reaches a SQL client (`psql -c`, a heredoc, a `<<<` here-string, or a pipe into one).

  ASK (permissionDecision "ask": the user confirms; the model cannot bypass it)
    * alembic downgrade base   (also `python -m alembic`, `poetry run alembic`, `-c ini`)
    * dropdb, mysqladmin drop  (destroys the whole database)
    * DROP DATABASE, DROP SCHEMA ... CASCADE, TRUNCATE sent to psql / mysql /
      mariadb / sqlcmd

  Wrappers are unwrapped first: sudo, env, nice, nohup, timeout, watch, eval,
  poetry/uv/pipenv/pdm run (with their options), docker / podman / docker compose
  run|exec, kubectl exec --, bash/sh/zsh -c (also -lc, -ec, ...), ssh host '...',
  heroku run.

  ADVISORY (additionalContext, never blocks)
    * alembic stamp            (marks a revision applied WITHOUT running it)

`--help` / `--version` invocations and offline `--sql` runs are left alone.

Opt-out, for the user only: set the plugin option `destructive_guard` to false
(`/config`), or export ALLOW_FASTAPI_DESTRUCTIVE=1 before launching Claude Code. Both
are read from the hook's own environment, which the model's commands cannot set.
Fails open on any parse error or unexpected input.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

TRIGGERS = ("downgrade", "dropdb", "drop", "stamp", "truncate")


# --------------------------------------------------------------------------- shell
# Shared verbatim with django-plugin/hooks/pre_bash_guard.py: from this marker to
# the next section marker the two files must stay identical (a test checks it).

_HELP = {"--help", "--version"}
_KEYWORDS = {"{", "!", "if", "then", "else", "elif", "do", "while", "until"}
_SEPARATORS = {";", "&&", "||", "&", "(", ")"}
_PIPES = {"|", "|&"}
_SQL_CLIENTS = {"psql", "mysql", "mariadb", "sqlcmd", "cockroach", "clickhouse-client"}
_RUNNERS = {"poetry", "uv", "pipenv", "pdm", "hatch", "rye"}
_PREFIXES = {"sudo", "doas", "exec", "time", "nohup", "nice", "command", "builtin", "env",
             "xargs"}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
_CONTAINERS = {"docker", "podman", "nerdctl", "docker-compose", "podman-compose"}
# Options that consume the next word (an `--opt=value` form never does).
_PREFIX_VALUE_OPTS = {"-u", "-g", "-n", "-C", "-h", "-p", "-U", "-D", "--user", "--group",
                      "--host", "--chdir", "--unset", "-a", "-I", "-L", "-P"}
_RUNNER_VALUE_OPTS = {"--env-file", "--with", "--with-requirements", "--with-editable",
                      "--python", "-p", "--package", "--directory", "--project", "--group",
                      "--only-group", "--no-group", "--extra", "--index", "--index-url",
                      "--extra-index-url", "--default-index", "--config-file", "--cache-dir",
                      "-C", "-P", "-w"}
_CONTAINER_GLOBAL_VALUE_OPTS = {"-f", "--file", "-p", "--project-name", "--project-directory",
                                "--env-file", "--profile", "--ansi", "--progress", "-c",
                                "--context", "-H", "--host", "--log-level", "--config",
                                "--parallel"}
_CONTAINER_RUN_VALUE_OPTS = {
    "-e", "--env", "--env-file", "-u", "--user", "-w", "--workdir", "-v", "--volume",
    "--name", "-p", "--publish", "--entrypoint", "-l", "--label", "--label-file", "--network",
    "--net", "--network-alias", "--mount", "--platform", "--add-host", "--hostname", "-h",
    "--pull", "--cpus", "-m", "--memory", "--index", "--detach-keys", "--cidfile", "--dns",
    "--device", "--gpus", "--ipc", "--pid", "--restart", "--runtime", "--shm-size",
    "--stop-signal", "--ulimit", "--userns", "--volumes-from", "--cap-add", "--cap-drop",
    "--security-opt", "--tmpfs", "--log-driver", "--log-opt", "--expose", "--link",
    "--health-cmd", "--pod",
}
_SSH_VALUE_OPTS = {"-b", "-c", "-D", "-E", "-e", "-F", "-I", "-i", "-J", "-L", "-l", "-m",
                   "-O", "-o", "-p", "-Q", "-R", "-S", "-W", "-w", "-B", "-P"}
_HEROKU_VALUE_OPTS = {"-a", "--app", "-r", "--remote", "-s", "--size", "-e", "--env", "--type"}
_TIMEOUT_VALUE_OPTS = {"-s", "--signal", "-k", "--kill-after"}
_WATCH_VALUE_OPTS = {"-n", "--interval", "-q", "--equexit"}
_SHELL_VALUE_OPTS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}

_SQL_LITERAL_RE = re.compile(r"'(?:[^']|'')*'")
_SQL_DESTRUCTIVE = (
    (re.compile(r"\bdrop\s+database\b", re.IGNORECASE), "DROP DATABASE"),
    (re.compile(r"\bdrop\s+schema\b[^;]*?\bcascade\b", re.IGNORECASE), "DROP SCHEMA ... CASCADE"),
    (re.compile(r"\btruncate\s+(?:table\s+)?(?:only\s+)?[\w\"`\[]", re.IGNORECASE), "TRUNCATE"),
)
_ANSI_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"', "a": "\a",
                 "b": "\b", "e": "\x1b", "f": "\f", "v": "\v"}


def destructive_sql(text):
    """The label of the first destructive statement in `text` ("DROP DATABASE", ...),
    ignoring SQL string literals ('drop database' as a value); else None."""
    text = _SQL_LITERAL_RE.sub("''", text)
    for rx, label in _SQL_DESTRUCTIVE:
        if rx.search(text):
            return label
    return None


def dequote(text):
    """Raw text with quote and backslash characters removed: a cheap approximation of
    shell quote removal, so the substring prefilter sees `fl''ush` as `flush`."""
    return re.sub(r"[\\'\"]", "", text)


class _Tok(list):
    """[text, kind]; kind is 'word', 'op' or 'heredoc' (text = the heredoc body)."""


def tokenize(src, subs):
    """Split a shell command into word and operator tokens, applying quote removal.

    Quoted text stays one word and adjacent quoted/unquoted pieces join (`"flu"sh` is
    `flush`, `$'flush'` is `flush`). Comments are dropped. The bodies of `$(...)`,
    backticks and `<(...)` are appended to `subs` so they can be parsed as commands
    of their own. Heredoc bodies become one 'heredoc' token at the `<<` position; a
    `<<<` here-string is an op whose following word is its body.
    Raises ValueError on an unterminated quote.
    """
    toks, word, i, n = [], None, 0, len(src)
    pending = []  # (token, delimiter, strip_tabs)

    def flush():
        nonlocal word
        if word is not None:
            toks.append(_Tok(["".join(word), "word"]))
            word = None

    def capture(start, open_ch, close_ch):
        depth, j = 1, start
        while j < n and depth:
            if src[j] == open_ch:
                depth += 1
            elif src[j] == close_ch:
                depth -= 1
            j += 1
        subs.append(src[start:j - 1])
        return j

    while i < n:
        c = src[i]
        if c in " \t\r":
            flush()
            i += 1
        elif c == "\n":
            flush()
            toks.append(_Tok([";", "op"]))
            i += 1
            for tok, delim, strip in pending:
                body = []
                while i < n:
                    j = src.find("\n", i)
                    line = src[i:] if j == -1 else src[i:j]
                    i = n if j == -1 else j + 1
                    if (line.lstrip("\t") if strip else line) == delim:
                        break
                    body.append(line)
                tok[0] = "\n".join(body)
            pending = []
        elif c == "#" and word is None:
            while i < n and src[i] != "\n":
                i += 1
        elif c == "$" and src[i + 1:i + 2] == "'":
            j, buf = i + 2, []
            while True:
                if j >= n:
                    raise ValueError("unterminated $'...' quote")
                ch = src[j]
                if ch == "\\" and j + 1 < n:
                    buf.append(_ANSI_ESCAPES.get(src[j + 1], src[j + 1]))
                    j += 2
                elif ch == "'":
                    break
                else:
                    buf.append(ch)
                    j += 1
            word = (word or []) + ["".join(buf)]
            i = j + 1
        elif c == "'":
            j = src.find("'", i + 1)
            if j == -1:
                raise ValueError("unterminated single quote")
            word = (word or []) + [src[i + 1:j]]
            i = j + 1
        elif c == '"':
            j, buf = i + 1, []
            while True:
                if j >= n:
                    raise ValueError("unterminated double quote")
                ch = src[j]
                if ch == "\\" and j + 1 < n:
                    buf.append(src[j + 1])
                    j += 2
                elif ch == '"':
                    break
                elif ch == "$" and src[j + 1:j + 2] == "(" and src[j + 2:j + 3] != "(":
                    j = capture(j + 2, "(", ")")
                elif ch == "`":
                    k = src.find("`", j + 1)
                    k = n if k == -1 else k
                    subs.append(src[j + 1:k])
                    j = k + 1
                else:
                    buf.append(ch)
                    j += 1
            word = (word or []) + ["".join(buf)]
            i = j + 1
        elif c == "\\":
            if src[i + 1:i + 2] != "\n":
                word = (word or []) + [src[i + 1:i + 2]]
            i += 2
        elif c == "$" and src[i + 1:i + 2] == "(" and src[i + 2:i + 3] != "(":
            i = capture(i + 2, "(", ")")
            word = word or []
        elif c == "`":
            k = src.find("`", i + 1)
            k = n if k == -1 else k
            subs.append(src[i + 1:k])
            i = k + 1
            word = word or []
        elif c in "<>" and src[i + 1:i + 2] == "(":
            flush()
            i = capture(i + 2, "(", ")")
        elif src[i:i + 3] == "<<<":
            flush()
            toks.append(_Tok(["<<<", "op"]))
            i += 3
        elif c == "<" and src[i + 1:i + 2] == "<":
            flush()
            strip = src[i + 2:i + 3] == "-"
            i += 3 if strip else 2
            while i < n and src[i] in " \t":
                i += 1
            j = i
            while j < n and src[j] not in " \t\r\n;&|":
                j += 1
            delim = src[i:j].strip("'\"")
            tok = _Tok(["", "heredoc"])
            toks.append(tok)
            pending.append((tok, delim, strip))
            i = j
        elif c in ";&|()<>":
            flush()
            two = src[i:i + 2]
            if two in ("&&", "||", "|&", ";;", ">>", "&>"):
                toks.append(_Tok([two, "op"]))
                i += 2
            else:
                toks.append(_Tok([c, "op"]))
                i += 1
        else:
            word = (word or []) + [c]
            i += 1
    flush()
    return toks


def pipelines(src, depth=0):
    """Yield pipelines (lists of stages); a stage is (argv, heredoc_bodies)."""
    if depth > 3:
        return
    subs = []
    toks = tokenize(src, subs)
    pipeline, argv, docs = [], [], []
    skip_next = herestring = False
    for text, kind in toks:
        if kind == "heredoc":
            docs.append(text)
        elif kind == "op" and (text in _SEPARATORS or text == ";;" or text in _PIPES):
            if argv or docs:
                pipeline.append((argv, docs))
            argv, docs = [], []
            if text not in _PIPES and pipeline:
                yield pipeline
                pipeline = []
        elif kind == "op" and text == "<<<":  # the next word is fed to stdin
            herestring = True
        elif kind == "op":  # redirection: the next word is a file, not an argument
            skip_next = text in (">", ">>", "&>", "<")
        elif herestring:
            herestring = False
            docs.append(text)
        elif skip_next:
            skip_next = False
        else:
            argv.append(text)
    if argv or docs:
        pipeline.append((argv, docs))
    if pipeline:
        yield pipeline
    for sub in subs:
        yield from pipelines(sub, depth + 1)


def _base(word):
    name = word.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def _skip_options(rest, value_opts):
    """Drop leading options (and the value of each one in `value_opts`); stops at `--`."""
    rest = list(rest)
    while rest and rest[0].startswith("-") and rest[0] != "-":
        opt = rest.pop(0)
        if opt == "--":
            break
        if "=" not in opt and opt in value_opts and rest:
            rest.pop(0)
    return rest


def _container_command(argv):
    """The command run by `docker [compose] run|exec [opts] <image|service> CMD...`,
    or None when argv is some other container subcommand (build, ps, ...)."""
    rest = list(argv[1:])
    while rest:
        tok = rest.pop(0)
        if tok.startswith("-"):
            if "=" not in tok and tok in _CONTAINER_GLOBAL_VALUE_OPTS and rest:
                rest.pop(0)
        elif tok in ("compose", "container"):
            continue
        elif tok in ("run", "exec"):
            rest = _skip_options(rest, _CONTAINER_RUN_VALUE_OPTS)
            return rest[1:]
        else:
            return None
    return None


def _shell_script(argv):
    """The script of `bash -c '...'` (also -lc, -ec, -xc, `-l -c`), else None."""
    rest, has_c = list(argv[1:]), False
    while rest:
        tok = rest[0]
        if tok == "--":
            rest.pop(0)
            break
        if tok in _SHELL_VALUE_OPTS:
            rest = rest[2:]
        elif tok.startswith("--"):
            rest.pop(0)
        elif len(tok) > 1 and tok[0] in "-+":
            has_c = has_c or (tok[0] == "-" and "c" in tok[1:])
            rest.pop(0)
        else:
            break
    if not has_c:
        return None
    return rest[0] if rest else ""


def unwrap(argv, depth=0):
    """Strip env assignments, prefixes (sudo, env, nice, nohup, timeout, ...) and
    runners (poetry/uv run, docker [compose] run|exec, kubectl exec --, ...). Returns
    the argv that executes, or [("script", text)] when what runs is a shell script
    (`sh -c`, `eval`, `ssh host '...'`, `watch`, `heroku run`)."""
    argv = list(argv)
    while argv:
        head = _base(argv[0])
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[0]) or argv[0] in _KEYWORDS:
            argv = argv[1:]
        elif head == "command" and len(argv) > 1 and argv[1] in ("-v", "-V"):
            return []  # a lookup, not an execution
        elif head in _PREFIXES:
            argv = _skip_options(argv[1:], _PREFIX_VALUE_OPTS)
        elif head == "timeout":
            argv = _skip_options(argv[1:], _TIMEOUT_VALUE_OPTS)
            argv = argv[1:] if argv and re.match(r"^\d", argv[0]) else argv
        elif head in _RUNNERS and len(argv) > 1 and argv[1] == "run":
            argv = _skip_options(argv[2:], _RUNNER_VALUE_OPTS)
        elif head in _CONTAINERS:
            inner = _container_command(argv)
            if inner is None:
                break
            argv = inner
        elif head in ("kubectl", "oc") and "exec" in argv[1:3] and "--" in argv:
            argv = argv[argv.index("--") + 1:]
        elif head in _SHELLS:
            script = _shell_script(argv) if depth < 3 else None
            if script is None:
                break
            return [("script", script)]
        elif head == "eval":
            return [("script", " ".join(argv[1:]))]
        elif head == "watch":
            return [("script", " ".join(_skip_options(argv[1:], _WATCH_VALUE_OPTS)))]
        elif head == "ssh":
            rest = _skip_options(argv[1:], _SSH_VALUE_OPTS)
            return [("script", " ".join(rest[1:]))] if len(rest) > 1 else []
        elif head == "heroku" and len(argv) > 1 and argv[1] in ("run", "run:detached"):
            return [("script", " ".join(_skip_options(argv[2:], _HEROKU_VALUE_OPTS)))]
        else:
            break
    return argv


def scan(command, depth=0):
    """All decisions for a command: a list of ('ask'|'advise', text), plus cd targets."""
    found, cds = [], []
    for pipeline in pipelines(command):
        upstream = []
        for argv, docs in pipeline:
            if argv and argv[0] == "cd" and len(argv) > 1:
                cds.append(argv[1])
            verdict = classify(argv, docs, " ".join(upstream))
            if verdict and verdict[0] == "script":
                if depth < 3:
                    try:
                        more, more_cds = scan(verdict[1], depth + 1)
                    except ValueError:
                        more, more_cds = [], []  # unparseable inner script: skip it
                    found += more
                    cds += more_cds
            elif verdict:
                found.append(verdict)
            upstream.extend(argv)
            upstream.extend(docs)
    return found, cds


# --------------------------------------------------------------------------- alembic


def alembic_args(argv):
    """The arguments after `alembic` / `python -m alembic`, else None."""
    if not argv:
        return None
    head = _base(argv[0])
    if head == "alembic":
        return argv[1:]
    if re.match(r"^(python[0-9.]*|pythonw|py)$", head):
        rest = argv[1:]
        while rest:
            tok = rest.pop(0)
            if tok == "-m":
                return rest[1:] if rest and rest[0] == "alembic" else None
            if tok == "-c":
                return None
            if tok in ("-W", "-X") and rest:
                rest.pop(0)
            elif not tok.startswith("-"):
                return None
    return None


def split_subcommand(args):
    """(subcommand, positional args, options) of an alembic invocation."""
    sub, pos, opts, rest = None, [], [], list(args)
    while rest:
        tok = rest.pop(0)
        if tok.startswith("-"):
            opts.append(tok)
            if tok in ("-c", "--config", "-n", "--name", "-x", "--tag") and rest:
                rest.pop(0)
        elif sub is None:
            sub = tok
        else:
            pos.append(tok)
    return sub, pos, opts


def classify(argv, docs, upstream_text):
    """('ask', reason) | ('advise', text) | ('script', text) | None for one stage."""
    argv = unwrap(argv)
    if argv and isinstance(argv[0], tuple):
        return ("script", argv[0][1])
    if not argv or any(a in _HELP for a in argv[1:]):
        return None
    head = _base(argv[0])
    args = alembic_args(argv)
    if args is not None:
        sub, pos, opts = split_subcommand(args)
        if sub == "help" or "-h" in opts:
            return None
        if sub == "downgrade" and "--sql" not in opts:
            target = pos[0].rsplit(":", 1)[-1].lower() if pos else ""
            if target == "base":
                return ("ask", "`alembic downgrade base` rolls back every migration, dropping "
                               "the entire schema managed by Alembic and its data")
        if sub == "stamp" and "--sql" not in opts:
            return ("advise", "[fastapi] advisory: `alembic stamp` marks a revision as applied "
                              "WITHOUT running its upgrade(), desynchronizing the DB from "
                              "migration state. Use it only when the schema is PROVEN to already "
                              "match the target revision - otherwise prefer a real "
                              "`alembic upgrade`.")
        return None
    if head == "dropdb":
        return ("ask", "`dropdb` destroys the entire database")
    if head == "mysqladmin" and "drop" in [a.lower() for a in argv[1:]]:
        return ("ask", "`mysqladmin drop` destroys the entire database")
    if head in _SQL_CLIENTS:
        label = destructive_sql(" ".join(argv[1:]) + " " + " ".join(docs) + " " + upstream_text)
        if label:
            return ("ask", f"this sends {label} to `{head}`")
    return None


# --------------------------------------------------------------------------- scope

_SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "site-packages",
              "dist", "build", ".tox", ".mypy_cache"}
_DEP_RE = re.compile(r"(?<![\w.-])fastapi(?![\w-])", re.IGNORECASE)


def _declares_fastapi(directory):
    try:
        names = os.listdir(directory)
    except OSError:
        return False
    files = [n for n in names if n in ("pyproject.toml", "Pipfile", "setup.cfg", "setup.py")
             or (n.startswith("requirements") and n.endswith(".txt"))]
    if "requirements" in names and os.path.isdir(os.path.join(directory, "requirements")):
        try:
            files += [os.path.join("requirements", n)
                      for n in os.listdir(os.path.join(directory, "requirements"))
                      if n.endswith(".txt")]
        except OSError:
            pass
    for name in files:
        try:
            with open(os.path.join(directory, name), encoding="utf-8", errors="ignore") as fh:
                if _DEP_RE.search(fh.read(200_000)):
                    return True
        except OSError:
            continue
    return False


def _has_marker_below(root, depth=2):
    if _declares_fastapi(root):
        return True
    if depth <= 0:
        return False
    try:
        entries = list(os.scandir(root))
    except OSError:
        return False
    return any(_has_marker_below(e.path, depth - 1) for e in entries
               if e.is_dir() and e.name not in _SKIP_DIRS and not e.name.startswith("."))


def _has_marker_above(start):
    path = os.path.abspath(start)
    for _ in range(40):
        if _declares_fastapi(path):
            return True
        parent = os.path.dirname(path)
        if parent == path:
            return False
        path = parent
    return False


def in_fastapi_project(payload, cds=()):
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    cwd = cwd or os.getcwd()
    starts = [cwd] + [c if os.path.isabs(c) else os.path.join(cwd, c) for c in cds]
    if any(_has_marker_above(s) for s in starts if s):
        return True
    roots = [cwd, os.environ.get("CLAUDE_PROJECT_DIR", "")]
    return any(_has_marker_below(r) for r in roots if r and os.path.isdir(r))


def guard_disabled():
    opt = os.environ.get("CLAUDE_PLUGIN_OPTION_DESTRUCTIVE_GUARD", "").strip().lower()
    if opt in ("false", "0", "no", "off"):
        return True
    return os.environ.get("ALLOW_FASTAPI_DESTRUCTIVE", "").strip().lower() in ("1", "true", "yes")


# --------------------------------------------------------------------------- main


def main():
    hooklib.watchdog(3.0)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    command = hooklib.tool_input(payload).get("command")
    if not isinstance(command, str) or not command:
        return 0
    low = dequote(command.lower())
    if not any(t in low for t in TRIGGERS):
        return 0
    try:
        found, cds = scan(command)
    except ValueError:
        return 0  # unbalanced quotes: the shell would refuse it too
    if not found or not in_fastapi_project(payload, cds):
        return 0
    asks = [text for kind, text in found if kind == "ask"]
    if asks and not guard_disabled():
        hooklib.ask("[fastapi] " + "; ".join(dict.fromkeys(asks)) + ". This is irreversible "
                    "and has no undo. Confirm a current backup (pg_dump or a snapshot) and "
                    "that this is the intended database before approving.")
        return 0
    advice = [text for kind, text in found if kind == "advise"]
    if advice:
        hooklib.context("PreToolUse", "\n".join(dict.fromkeys(advice)))
    return 0


if __name__ == "__main__":
    hooklib.run(main)
