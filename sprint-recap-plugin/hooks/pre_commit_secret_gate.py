#!/usr/bin/env python3
"""
sprint-recap PreToolUse hook - credential commit gate.

The plugin writes a plaintext credentials file on purpose (that is the whole
point of `publish --with-credentials`), so a password file can sit in the
working tree. Gitignore alone does not protect it: `git add -f`, a broad
`git add -A` from a directory whose ignore rules do not apply, or a hand-written
path all get past it.

Only git commands that actually run are inspected: the command is split into
its `&&` / `||` / `;` / `&` / `|` / newline segments, runner prefixes (env
assignments, sudo, env, exec, nohup, time, xargs, nice, `{`, `(`) are skipped,
`bash|sh|zsh -c '<script>'` is parsed recursively, and a segment counts only
when its program is `git` and its subcommand stages or commits (add, commit,
stash push, update-index). Commit messages (-m) and heredoc bodies are never
treated as paths. As a fail-closed backstop, a line that still mentions both a
git staging verb and a secret path (an `echo ... | xargs git add`, a `$(...)`
the parser does not model) gets permissionDecision "ask" instead of passing.

Decisions:
  * a segment naming a sprint-recap secret artifact -> BLOCK (exit 2, stderr).
    These hold plaintext logins or session cookies; history keeps them forever.
      .sprint-recap.local.json          (base URLs + every role's password)
      .sprint-recap/credentials/**      (generated plaintext credential pages)
      *-credentials.html                (the generated file, moved anywhere)
      .sprint-recap/**/.auth/           (Playwright storage state: live cookies)
  * `git add -f/--force` in a sprint-recap project -> permissionDecision "ask".
    Force-adding bypasses the ignore rules that keep those files out; the user
    decides. Outside a sprint-recap project the hook says nothing.
  * a broad `git add -A` / `git add .` in a sprint-recap project -> a note as
    additionalContext (exit-0 stderr never reaches the model).

A "sprint-recap project" is the hook's cwd or an ancestor holding
.sprint-recap.local.json or a .sprint-recap/ directory.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

SECRET_PATTERNS = [
    re.compile(r"\.sprint-recap\.local\.json", re.IGNORECASE),
    re.compile(r"\.sprint-recap[\\/]credentials", re.IGNORECASE),
    re.compile(r"[-\w]*credentials\.html", re.IGNORECASE),
    # Versions before 0.4 cached each role's storage state (cookies) at
    # .sprint-recap/runs/<sprint>/<capture dir>/.auth/<role>.json.
    re.compile(r"\.sprint-recap[\\/](?:[^\s'\"|;&]*[\\/])?\.auth(?![\w.-])", re.IGNORECASE),
]

STAGING_SUBCOMMANDS = ("add", "commit", "update-index")
# git global options that take a value: `git -C dir add ...`, `git -c k=v commit`.
_GLOBAL_WITH_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace")
# `&&`, `||`, and single `;`, `&` (background), `|` (pipe) and newlines.
_SEGMENT_SPLIT = re.compile(r"&&|\|\||[;&|\n]")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
# Words that run the rest of the line as a command (their own -flags are skipped).
_PREFIXES = ("sudo", "command", "env", "exec", "nohup", "time", "xargs", "nice",
             "{", "(", "!")
# Prefix options that take a separate value (`sudo -u dev git ...`, `xargs -I {} git ...`).
_VALUE_FLAGS = {
    "sudo": ("-u", "-g", "-U", "-C", "-D", "-h", "-p", "-r", "-t"),
    "xargs": ("-I", "-L", "-n", "-P", "-d", "-E", "-s", "-a"),
    "nice": ("-n",),
    "env": ("-u", "-C", "-S"),
}
# `bash -c '<script>'`, `sh -lc "..."`, `zsh -c ...`: the script is a command line.
_SHELL_C = re.compile(
    r"^(?:\S*[\\/])?(?:ba|z|da|k)?sh(?:\.exe)?\s+(?:-[A-Za-z]+\s+)*?-[A-Za-z]*c[A-Za-z]*\s+(.*)$",
    re.S)
# Backstop: any git staging verb anywhere in the command.
_STAGING_TOKEN = re.compile(r"\bgit\b.*\b(?:add|commit|stash|update-index)\b", re.S | re.I)
_FORCE = re.compile(r"(?<!\S)(?:-f|--force|-[A-Za-z]*f[A-Za-z]*)(?!\S)")
_BROAD = re.compile(r"(?<!\S)(?:-A|--all|\.)(?!\S)")


def path_bearing(command: str) -> str:
    """The part of a command that can actually name a path to stage.

    A commit MESSAGE is not a path. `git commit -F - <<'EOF'` with a body that
    explains why credentials must never be committed, or `-m "... do not commit
    .sprint-recap.local.json ..."`, must not trip this gate: it exists to stop
    the file entering git, not to stop anyone writing about it.
    """
    # A heredoc body is message text, never an argument list. Once a heredoc
    # operator appears, only the first line can carry paths.
    if re.search(r"<<-?\s*['\"]?\w+", command):
        command = command.split("\n", 1)[0]
    # Same for an inline -m/--message body. (`\b` would not match before `-m`:
    # both the space and the dash are non-word characters.)
    command = re.sub(
        r"(?<!\S)(?:-m|--message)(?:=|\s+)('[^']*'|\"[^\"]*\")", " ", command
    )
    return command


def git_staging_segments(command: str, depth: int = 0) -> list[tuple[str, str]]:
    """(subcommand, argument text) for every segment that runs a staging git command."""
    out = []
    for segment in _SEGMENT_SPLIT.split(command):
        segment = segment.strip().lstrip("({ ").strip()
        shell = _SHELL_C.match(segment)
        if shell and depth < 3:
            inner = shell.group(1).strip().strip("'\"")
            out.extend(git_staging_segments(inner, depth + 1))
            continue
        words = segment.split()
        while words and (_ENV_ASSIGN.match(words[0]) or words[0] in _PREFIXES):
            prefix = words.pop(0)
            while words and words[0].startswith("-"):
                flag = words.pop(0)
                if words and flag in _VALUE_FLAGS.get(prefix, ()):
                    words.pop(0)
        if words:
            words[0] = words[0].strip("'\"")
        if not words or os.path.basename(words[0]).lower() not in ("git", "git.exe"):
            continue
        i = 1
        while i < len(words) and words[i].startswith("-"):
            i += 2 if words[i] in _GLOBAL_WITH_VALUE else 1
        if i >= len(words):
            continue
        sub = words[i].lower()
        rest = words[i + 1:]
        if sub == "stash" and rest[:1] == ["push"]:
            out.append(("stash push", " ".join(rest[1:])))
        elif sub in STAGING_SUBCOMMANDS:
            out.append((sub, " ".join(rest)))
    return out


def in_sprint_recap_project(cwd: str) -> bool:
    try:
        here = Path(cwd).resolve()
    except (OSError, RuntimeError):
        return False
    for folder in (here, *here.parents):
        if (folder / ".sprint-recap.local.json").is_file() or (folder / ".sprint-recap").is_dir():
            return True
    return False


def _backstop_hit(command: str):
    """A secret path AND a git staging verb anywhere in the (message-stripped) line."""
    if not _STAGING_TOKEN.search(command):
        return None
    for pattern in SECRET_PATTERNS:
        hit = pattern.search(command)
        if hit:
            return hit
    return None


def _backstop(command: str) -> int:
    """Fail closed when the segment parser could not prove the line is harmless.

    Shell syntax this parser does not model (subshells, functions, aliases, odd
    quoting) could still stage a secret, so the user decides instead of the line
    passing silently.
    """
    hit = _backstop_hit(command)
    if hit:
        hooklib.ask(
            "[sprint-recap] This command mentions git staging and a credential artifact ("
            + hit.group(0) + ") in a form the commit gate cannot parse safely. Allow it "
            "only if it does not put that file into git."
        )
    return 0


def main() -> int:
    hooklib.watchdog(8.0)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool_input = hooklib.tool_input(payload) or payload.get("toolInput") or {}
    raw_command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if "git" not in raw_command:
        return 0
    bearing = path_bearing(raw_command)
    segments = git_staging_segments(bearing)
    if not segments:
        return _backstop(bearing)

    for _sub, args in segments:
        for pattern in SECRET_PATTERNS:
            hit = pattern.search(args)
            if hit:
                print(
                    "[sprint-recap] BLOCKED: this command stages a credential "
                    "artifact (" + hit.group(0) + ").\n"
                    "These files hold plaintext logins or live session cookies and "
                    "must never enter git history - history is not erased by a "
                    "later delete.\n"
                    "Commit the guide (05-publish/*.html) instead; it is written "
                    "without secrets for exactly this reason.",
                    file=sys.stderr,
                )
                return 2

    # A secret path elsewhere in the line (e.g. piped into `xargs git add`).
    if _backstop_hit(bearing):
        return _backstop(bearing)

    if not in_sprint_recap_project(str(payload.get("cwd") or os.getcwd())):
        return 0

    adds = [args for sub, args in segments if sub == "add"]
    if any(_FORCE.search(args) for args in adds):
        hooklib.ask(
            "[sprint-recap] `git add --force` bypasses .gitignore, which is what keeps "
            ".sprint-recap.local.json, .sprint-recap/credentials/ and session state out "
            "of this repo. Allow only if you are sure no secret is in the paths named."
        )
        return 0
    if any(_BROAD.search(args) for args in adds):
        # Not a block: a broad add is normal and usually safe because the paths
        # are gitignored. Ask Claude to verify the ignore rules, not assume them.
        hooklib.context(
            "PreToolUse",
            "[sprint-recap] note: broad `git add` detected. Confirm "
            ".sprint-recap.local.json, .sprint-recap/credentials/ and "
            ".sprint-recap/**/.auth/ are ignored here "
            "(`git check-ignore -v <path>`).",
        )
    return 0


if __name__ == "__main__":
    hooklib.run(main)
