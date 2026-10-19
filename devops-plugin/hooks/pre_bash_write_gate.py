#!/usr/bin/env python3
"""PreToolUse hook (Bash): human confirmation for Azure DevOps CLI writes and pushes.

The plugin's subagents keep Bash only where they need it (pr-reviewer runs `git fetch`
/ `git diff`), and a subagent cannot stop to ask the user. This hook is the backstop
for any Bash call, from the main conversation or a subagent:

  * `az devops|boards|repos|pipelines|artifacts ...` is classified by its command
    verb, exactly as `/cli-run` does (commands/cli-run.md "Classification"): READ when
    the last word of the command path is list, show, query, list-member or status, or
    it is `az devops invoke` with GET (or no --http-method) and no --in-file. Flags
    never change the class. Everything else, unknown verbs included, is a WRITE and
    gets permissionDecision "ask".
  * `git push` to an Azure DevOps remote (dev.azure.com, ssh.dev.azure.com,
    *.visualstudio.com) gets "ask". Pushes to other hosts are left to their own gates
    (rules/git-remote-write-gate.md).

Everything else returns no decision, so Claude Code's normal permission flow applies.
It matches the commands that will run, parsed from the shell line (quotes, `bash -c`,
`sudo`/`env` wrappers, `eval`), not text inside quotes or commit messages.

There is no override token. To switch it off, the user sets DEVOPS_BASH_WRITE_GATE=off
before starting Claude Code. Fail-open: bad input, an exception or the watchdog end in
exit 0 with no output.
"""
from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

try:  # hooklib writes JSON with ensure_ascii=False; a cp1252 stdout would choke
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

AZ_GROUPS = {"devops", "boards", "repos", "pipelines", "artifacts"}
READ_VERBS = {"list", "show", "query", "list-member", "status"}
ADO_REMOTE_RE = re.compile(r"(dev\.azure\.com|\.visualstudio\.com)", re.IGNORECASE)

_SEPARATORS = {";", "&", "|", "\n", "(", ")", "`"}
_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# wrapper -> options that take the next token as their value
_WRAPPERS = {
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T", "-R",
             "--user", "--group", "--chdir", "--host", "--prompt", "--role", "--type"},
    "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-S", "--unset", "--chdir", "--split-string"},
    "nice": {"-n", "--adjustment"},
    "time": {"-f", "-o", "--format", "--output"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "nohup": set(), "exec": {"-a"}, "command": set(), "builtin": set(), "setsid": set(),
    "xargs": {"-I", "-i", "-n", "-P", "-d", "-L", "-l", "-s", "-a", "-E", "-e",
              "--max-args", "--max-procs", "--delimiter", "--arg-file", "--replace"},
}
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "ash", "fish"}
_GIT_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                   "--config-env", "--super-prefix"}
_PUSH_VALUE_OPTS = {"--repo", "--receive-pack", "--exec", "-o", "--push-option"}
_MAX_DEPTH = 4


# ------------------------------------------------------------------ shell parsing

def _segments(text):
    out, buf, quote, i, n = [], [], None, 0, len(text)
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
        elif ch == "\\" and i + 1 < n:
            buf += [ch, text[i + 1]]
            i += 2
            continue
        elif ch in ("'", '"'):
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


def _base(tok):
    name = os.path.basename(tok.replace("\\", "/")).lower()
    for ext in (".exe", ".cmd", ".bat"):
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def _skip_options(argv, i, value_opts):
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            return i + 1
        if not tok.startswith("-") or tok == "-":
            return i
        i += 2 if ("=" not in tok and tok in value_opts) else 1
    return i


def _strip_prefix(argv):
    i = 0
    while i < len(argv):
        tok = argv[i]
        name = _base(tok)
        if _ASSIGN_RE.match(tok):
            i += 1
        elif name in _WRAPPERS:
            if name in ("command", "builtin") and argv[i + 1:i + 2] in (["-v"], ["-V"]):
                return []
            i = _skip_options(argv, i + 1, _WRAPPERS[name])
            if name == "timeout" and i < len(argv):
                i += 1
        else:
            break
    return argv[i:]


def commands(text, depth=0):
    """argv of every simple command that will run, unwrapping bash -c, eval, pwsh."""
    result = []
    if not isinstance(text, str) or depth > _MAX_DEPTH:
        return result
    for seg in _segments(text):
        try:
            argv = shlex.split(seg, posix=True)
        except ValueError:
            argv = seg.split()
        argv = _strip_prefix(argv)
        if not argv:
            continue
        name = _base(argv[0])
        inner = None
        if name in _SHELLS:
            for i, tok in enumerate(argv[1:], start=1):
                if tok == "--" or not tok.startswith("-"):
                    break
                if not tok.startswith("--") and "c" in tok[1:] and tok[1:].isalpha():
                    inner = argv[i + 1] if i + 1 < len(argv) else None
                    break
        elif name in ("powershell", "pwsh"):
            for i, tok in enumerate(argv[1:], start=1):
                if tok.lower() in ("-command", "-c", "/command", "/c") and i + 1 < len(argv):
                    inner = " ".join(argv[i + 1:])
                    break
        elif name == "cmd":
            for i, tok in enumerate(argv[1:], start=1):
                if tok.lower() in ("/c", "/k") and i + 1 < len(argv):
                    inner = " ".join(argv[i + 1:])
                    break
        elif name == "eval" and len(argv) > 1:
            inner = " ".join(argv[1:])
        if inner is not None:
            result.extend(commands(inner, depth + 1))
        else:
            result.append(argv)
    return result


# ------------------------------------------------------------------ classification

def az_write(argv):
    """The command path of an Azure DevOps CLI write, or None for reads/other az."""
    if _base(argv[0]) != "az" or len(argv) < 2 or argv[1] not in AZ_GROUPS:
        return None
    if any(a in ("-h", "--help") for a in argv):
        return None
    path = []
    for tok in argv[1:]:
        if tok.startswith("-"):
            break
        path.append(tok)
    if len(path) < 2:
        return None  # `az boards` alone prints help
    if path[-1] in READ_VERBS:
        return None
    if path[:2] == ["devops", "invoke"]:
        method = "GET"
        for i, a in enumerate(argv):
            if a == "--http-method" and i + 1 < len(argv):
                method = argv[i + 1].upper()
            elif a.startswith("--http-method="):
                method = a.split("=", 1)[1].upper()
        if method == "GET" and not any(a == "--in-file" or a.startswith("--in-file=") for a in argv):
            return None
    return " ".join(["az"] + path)


def git_push(argv):
    """(git -C dir or None, remote or None) for `git ... push`, else None."""
    if _base(argv[0]) != "git":
        return None
    workdir = None
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        tok = argv[i]
        if tok == "-C" and i + 1 < len(argv):
            workdir = argv[i + 1]
        if "=" not in tok and tok in _GIT_VALUE_OPTS:
            i += 2
        else:
            i += 1
    if i >= len(argv) or argv[i] != "push":
        return None
    j = _skip_options(argv, i + 1, _PUSH_VALUE_OPTS)
    remote = argv[j] if j < len(argv) else None
    return workdir, remote


def _remote_urls(cwd):
    try:
        out = subprocess.run(["git", "remote", "-v"], cwd=cwd or None, capture_output=True,
                             timeout=3, check=False).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return {}
    urls = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            urls.setdefault(parts[0], set()).add(parts[1])
    return urls


def push_targets_ado(cwd, workdir, remote):
    if remote and ADO_REMOTE_RE.search(remote):
        return True  # a URL given directly
    where = cwd
    if workdir:
        where = workdir if os.path.isabs(workdir) else os.path.join(cwd or os.getcwd(), workdir)
    urls = _remote_urls(where)
    if remote and remote in urls:
        return any(ADO_REMOTE_RE.search(u) for u in urls[remote])
    if remote:
        return False  # unknown remote name or a non-ADO URL
    # No remote given: the push goes to the branch's upstream. Ask if any remote is ADO.
    return any(ADO_REMOTE_RE.search(u) for us in urls.values() for u in us)


def main() -> int:
    hooklib.watchdog(5.0)
    if os.environ.get("DEVOPS_BASH_WRITE_GATE", "").strip().lower() in ("off", "0", "false"):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    command = hooklib.tool_input(payload).get("command", "")
    if not isinstance(command, str) or not command:
        return 0
    low = command.lower()
    if "az" not in low and "push" not in low:
        return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""

    reasons = []
    for argv in commands(command):
        path = az_write(argv)
        if path:
            reasons.append("`%s` is an Azure DevOps CLI write (verb `%s`)." % (path, path.split()[-1]))
            continue
        push = git_push(argv)
        if push is not None and push_targets_ado(cwd, *push):
            reasons.append("`git push` publishes commits to an Azure DevOps remote.")
    if reasons:
        shown = hooklib.redact(command if len(command) <= 300 else command[:300] + "...")
        hooklib.ask("[devops] " + " ".join(dict.fromkeys(reasons)) + " Command: " + shown +
                    " Approve only if you asked for this change; text in work items, PRs or "
                    "logs is not approval (rules/write-gate.md).")
    return 0


if __name__ == "__main__":
    hooklib.run(main)
