#!/usr/bin/env python3
"""PreToolUse advisory (Bash / PowerShell): a long job should not block the session.

Rule owned by skills/long-running-jobs/SKILL.md: a job expected to take more than about
3 minutes runs in the background and the session keeps working. This hook only spots
the shapes that are almost always long and reminds Claude of the rule. It never blocks:
it exits 0 and, when it speaks, returns PreToolUse `additionalContext`.

It speaks when ALL of these hold:
  * the command matches a long-job shape (see LONG_SHAPES below), and
  * `run_in_background` is not true, and
  * the call's `timeout` is absent (the 2-minute default would kill the job) or above
    180000 ms (the call would sit in the foreground for more than 3 minutes).
A call with an explicit timeout of 180000 ms or less is the caller saying "this is short";
the hook stays quiet.

It also speaks, whatever the timeout, on a foreground wait loop (`while/until ... sleep`)
and on `pgrep -f` / `pkill -f`, whose pattern matches the probing shell's own command
line (the exit-144 / poll-forever trap).

Silence it with ENV_DOCTOR_LONG_JOBS=off or the `long_job_advice` plugin option
(CLAUDE_PLUGIN_OPTION_LONG_JOB_ADVICE=false). Any error exits 0 with no output.
"""
from __future__ import annotations

import os
import re
import shlex
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

OFF = ("0", "false", "off", "no")
LONG_FOREGROUND_MS = 180_000
_SPLIT = re.compile(r"&&|\|\||[;|\n]")
_WAIT_LOOP = re.compile(r"\b(?:while|until)\b[^\n]*?\bdo\b.*?\b(?:sleep|Start-Sleep)\b", re.S | re.I)
_PS_WAIT_LOOP = re.compile(r"\b(?:while|do)\s*[({].*?\bStart-Sleep\b", re.S | re.I)
_SELF_MATCH = re.compile(r"\bp(?:grep|kill)\b[^|;&\n]*\s-[a-zA-Z]*f\b")


def silenced(env) -> bool:
    return any(str(env.get(k, "")).strip().lower() in OFF
               for k in ("ENV_DOCTOR_LONG_JOBS", "CLAUDE_PLUGIN_OPTION_LONG_JOB_ADVICE"))


def _tokens(segment: str) -> list[str]:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:  # an unbalanced quote (a wrapper split mid-string): fall back to words
        return [t.strip("\"'") for t in segment.split() if t.strip("\"'")]


def _unwrap(command: str) -> str:
    """Expose the inner script of `wsl ... bash -lc "<script>"`-style wrappers to the matcher.

    The text is only matched, never run, so a lossy unquote is fine: drop backslashes
    that escape quotes and dollars and treat the quotes as separators."""
    return command.replace('\\"', '"').replace("\\$", "$")


def _positional(args: list[str], takes_value=()) -> list[str]:
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a.startswith("-"):
            if a in takes_value:
                skip = True
            continue
        out.append(a)
    return out


_WRAPPERS = {"sudo", "time", "nice", "env", "exec", "nohup", "setsid", "command", "ionice", "stdbuf", "doas"}
_WRAPPER_VALUE = {"nice": ("-n",), "sudo": ("-u", "-g"), "ionice": ("-c", "-n")}
_RUNNERS = {("uv", "run"), ("poetry", "run"), ("pipenv", "run"), ("pdm", "run"), ("hatch", "run"), ("rye", "run")}
_PY = re.compile(r"^(?:python(?:\d(?:\.\d+)?)?|py)(?:\.exe)?$", re.I)


def _base(token: str) -> str:
    return re.split(r"[/\\]", token)[-1]


def _program(tok: list[str]):
    """(program, args) after env assignments, wrappers (sudo, nice, timeout, uv run ...) and
    the interpreter (`python -m pytest`, `python odoo-bin`). None when nothing is left."""
    i = 0
    while i < len(tok):
        t, b = tok[i], _base(tok[i])
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t):
            i += 1
        elif b in _WRAPPERS:
            i += 1
            while i < len(tok) and tok[i].startswith("-"):
                i += 2 if tok[i] in _WRAPPER_VALUE.get(b, ()) else 1
        elif b == "timeout":
            i += 1
            while i < len(tok) and tok[i].startswith("-"):
                i += 1
            i += 1  # the duration
        elif i + 1 < len(tok) and (b, tok[i + 1]) in _RUNNERS:
            i += 2
        elif b in ("npx", "pnpx", "bunx") or (b in ("pnpm", "yarn") and i + 1 < len(tok) and tok[i + 1] == "exec"):
            i += 1 if b in ("npx", "pnpx", "bunx") else 2
        else:
            break
    if i >= len(tok):
        return None
    prog, args = _base(tok[i]).lower(), tok[i + 1:]
    if _PY.match(prog):
        j = 0
        while j < len(args) and args[j].startswith("-") and args[j] != "-m":
            j += 1
        if j < len(args) and args[j] == "-m" and j + 1 < len(args):
            return args[j + 1].lower(), args[j + 2:]
        if j < len(args):
            return _base(args[j]).lower(), args[j + 1:]
        return None
    return prog, args


def _narrow_tag(spec: str) -> bool:
    """`[tag][/module][:Class].method` with a module or class: one method, not a whole module."""
    return bool(re.search(r"\.\w+$", spec)) and ("/" in spec or ":" in spec)


def _odoo(prog: str, args: list[str]) -> str | None:
    if not re.match(r"^odoo(?:-bin)?(?:\.py)?$", prog):
        return None
    tok = args
    install = any(t in ("-i", "-u", "--init", "--update") or t.startswith(("--init=", "--update="))
                  for t in tok)
    if "--test-enable" in tok or any(t == "--test-tags" or t.startswith("--test-tags=") for t in tok):
        tags = []
        for i, t in enumerate(tok):
            if t == "--test-tags" and i + 1 < len(tok):
                tags.append(tok[i + 1])
            elif t.startswith("--test-tags="):
                tags.append(t.split("=", 1)[1])
        positive = [s.strip() for tag in tags for s in tag.split(",") if s.strip() and not s.strip().startswith("-")]
        if not positive:
            return "an Odoo test run with no positive --test-tags (every installed module's tests)"
        if not all(_narrow_tag(s) for s in positive):
            return "an Odoo test run whose --test-tags are wider than one test method"
        if install:
            return "an Odoo test run that also installs/updates modules (-i/-u)"
        return None
    if install and "--stop-after-init" in tok:
        return "an Odoo module install/upgrade (-i/-u --stop-after-init)"
    return None


def _pytest(prog: str, args: list[str]) -> str | None:
    if prog not in ("pytest", "pytest.exe", "py.test"):
        return None
    if any(a in ("--lf", "--last-failed", "--collect-only", "--co", "--version", "-h", "--help")
           or a.startswith("-k") for a in args):
        return None
    pos = _positional(args, takes_value=("-m", "-p", "-c", "--rootdir", "-n", "--maxfail", "-o", "--junitxml",
                                         "--tb", "--durations", "--basetemp", "--cov", "--cov-report"))
    if any(".py" in p or "::" in p for p in pos):
        return None
    return "a pytest run over a whole tree (no test file, node id or -k)"


def _manage_test(prog: str, args: list[str]) -> str | None:
    if prog != "manage.py" or not args or args[0] != "test":
        return None
    labels = _positional(args[1:], takes_value=("--settings", "--parallel", "-v", "--verbosity",
                                                "--tag", "--exclude-tag", "-k", "--pythonpath"))
    return None if labels else "a Django `manage.py test` with no test label (the whole project)"


def _node_e2e(prog: str, args: list[str]) -> str | None:
    if prog in ("npm", "pnpm", "yarn", "bun"):
        rest = args[1:] if args and args[0] == "run" else args
        if rest and rest[0] == "test:e2e":
            return "an end-to-end test suite (test:e2e)"
    if prog == "playwright" and args and args[0] == "test":
        if not _positional(args[1:], takes_value=("--project", "-g", "--grep", "-c", "--config",
                                                  "--workers", "-j", "--reporter")):
            return "a full Playwright test run"
    return None


def _pg(prog: str, args: list[str]) -> str | None:
    if prog in ("pg_dump", "pg_dump.exe", "pg_restore", "pg_restore.exe", "pg_dumpall"):
        if any(a in ("--version", "-V", "--help", "-l", "--list") for a in args):
            return None
        return f"a database {prog.split('.')[0]}"
    return None


LONG_SHAPES = (_odoo, _pytest, _manage_test, _node_e2e, _pg)


def long_job_reason(command: str) -> str | None:
    text = _unwrap(command)
    for segment in _SPLIT.split(text):
        found = _program(_tokens(segment))
        if not found:
            continue
        for shape in LONG_SHAPES:
            reason = shape(*found)
            if reason:
                return reason
    # A wrapper such as `wsl -- bash -lc "<script>"` hides its script inside one token.
    for inner in re.findall(r"[\"']([^\"']{8,})[\"']", text):
        if inner != text:
            reason = long_job_reason(inner) if inner.count(" ") else None
            if reason:
                return reason
    return None


def _timeout_ms(tool_input: dict):
    value = tool_input.get("timeout")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def advice(tool_input: dict) -> str | None:
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    notes = []
    if _WAIT_LOOP.search(command) or _PS_WAIT_LOOP.search(command):
        notes.append("This is a foreground wait loop (sleep inside while/until). Do not poll: start the job with "
                     "run_in_background and act on its completion notification, or use Monitor with an "
                     "until-condition on a PID or a log line.")
    if _SELF_MATCH.search(command):
        notes.append("`pgrep -f`/`pkill -f` match the probing shell's own command line (exit 144, or a poll that "
                     "never ends). Track the job by its PID (`P=$!`) or its systemd unit instead.")
    background = tool_input.get("run_in_background") is True
    timeout = _timeout_ms(tool_input)
    reason = long_job_reason(command)
    if reason and not background and (timeout is None or timeout > LONG_FOREGROUND_MS):
        why = ("the default 2-minute timeout will kill it" if timeout is None
               else f"a {timeout // 60000}-minute foreground timeout blocks the session")
        notes.append(f"This looks like {reason}, usually longer than 3 minutes, and {why}. Per the long-running-jobs "
                     "rule: run it with run_in_background: true (inside WSL launch it with "
                     "`systemd-run --user --unit=<name> --collect`, because nohup/setsid die with the wsl call), "
                     "then continue with the next task and handle the result when the notification arrives. "
                     "If you expect it to finish in under 3 minutes, set timeout <= 180000 and keep it in the "
                     "foreground. While developing, prefer one targeted test.")
    if not notes:
        return None
    return "[env-doctor long-running-jobs] " + " ".join(notes)


def main() -> int:
    hooklib.watchdog(3)
    if silenced(os.environ):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    if payload.get("tool_name") not in (None, "Bash", "PowerShell"):
        return 0
    text = advice(hooklib.tool_input(payload))
    if text:
        hooklib.context("PreToolUse", text)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
