#!/usr/bin/env python3
"""
sprint-recap PreToolUse hook - credential commit gate.

The plugin writes a plaintext credentials file on purpose (that is the whole
point of `publish --with-credentials`), which means there is now a password file
sitting in the working tree. Gitignore alone does not protect it: `git add -f`,
a broad `git add -A` from a parent directory whose ignore rules do not apply, or
a hand-written path all get past it.

This hook inspects Bash commands for git staging/committing that references a
sprint-recap secret artifact and BLOCKS it.

Blocked paths:
  * .sprint-recap.local.json          (base URLs + every role's password)
  * .sprint-recap/credentials/**      (generated plaintext credential pages)
  * *-credentials.html                (the generated file, moved anywhere)

Exit codes:
  0 - allow
  2 - block (Claude Code treats non-zero as a block)
"""
from __future__ import annotations

import json
import re
import sys

SECRET_PATTERNS = [
    re.compile(r"\.sprint-recap\.local\.json", re.IGNORECASE),
    re.compile(r"\.sprint-recap[\\/]credentials", re.IGNORECASE),
    re.compile(r"[-\w]*credentials\.html", re.IGNORECASE),
]

# Only gate commands that actually put something into git.
STAGING = re.compile(
    r"\bgit\b[^|;&]*\b(add|commit|stash\s+push|update-index)\b", re.IGNORECASE
)
# `git add -A` / `git add .` stage everything, including a force-added secret.
BROAD_ADD = re.compile(r"\bgit\s+add\b[^|;&]*(-A\b|--all\b|\s\.(?:\s|$))", re.IGNORECASE)
FORCE_ADD = re.compile(r"\bgit\s+add\b[^|;&]*(-f\b|--force\b)", re.IGNORECASE)


def path_bearing(command: str) -> str:
    """The part of a command that can actually name a path to stage.

    A commit MESSAGE is not a path. `git commit -F - <<'EOF'` with a body that
    explains why credentials must never be committed, or `-m "... do not commit
    .sprint-recap.local.json ..."`, must not trip this gate: it exists to stop
    the file entering git, not to stop anyone writing about it. Matching the
    raw command string blocks the very commit that documents the rule.
    """
    # A heredoc body is message text, never an argument list. Once a heredoc
    # operator appears, only the first line can carry paths.
    if re.search(r"<<-?\s*['\"]?\w+", command):
        command = command.split("\n", 1)[0]
    # Same for an inline -m/--message body.
    # `\b` would not match before `-m`: both the space and the dash are
    # non-word characters, so there is no boundary between them.
    command = re.sub(
        r"(?<!\S)(?:-m|--message)(?:=|\s+)('[^']*'|\"[^\"]*\")", " ", command
    )
    return command


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - a hook must never break the session
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    raw_command = str(tool_input.get("command") or "")
    if not raw_command or not STAGING.search(raw_command):
        return 0
    command = path_bearing(raw_command)

    for pattern in SECRET_PATTERNS:
        hit = pattern.search(command)
        if hit:
            print(
                "[sprint-recap] BLOCKED: this command stages a credential "
                "artifact (" + hit.group(0) + ").\n"
                "These files hold plaintext logins and must never enter git "
                "history - history is not erased by a later delete.\n"
                "Commit the guide (05-publish/*.html) instead; it is written "
                "without secrets for exactly this reason.",
                file=sys.stderr,
            )
            return 2

    if FORCE_ADD.search(command):
        print(
            "[sprint-recap] BLOCKED: `git add --force` bypasses .gitignore, "
            "which is the only thing keeping .sprint-recap.local.json and the "
            "generated credentials page out of this repo.\n"
            "Stage the specific files you mean by name instead.",
            file=sys.stderr,
        )
        return 2

    if BROAD_ADD.search(command):
        # Not a block: a broad add is normal and usually safe because the paths
        # are gitignored. Warn so the ignore rules get verified rather than
        # assumed.
        print(
            "[sprint-recap] note: broad `git add` detected. Confirm "
            ".sprint-recap.local.json and .sprint-recap/credentials/ are "
            "ignored here (`git check-ignore -v <path>`).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
