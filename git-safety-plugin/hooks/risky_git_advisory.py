#!/usr/bin/env python3
"""git-safety PreToolUse advisory hook.

Reads the stdin JSON that Claude Code sends before a tool call. If the tool is a
shell command that contains a RISKY git operation shape, it prints ONE short
advisory line pointing at the relevant guardrail. It never blocks the command.

Hard guarantees (per plugin house rules):
  - NON-FATAL: never blocks, never denies, never asks. Exit 0 in all cases.
  - Advisory only: prints at most one short reminder; never rewrites the command.
  - Stdlib only. No third-party dependencies. Cross-platform.
  - Silent-pass on any error or on no match (prints nothing).

Detected shapes (generic, well-known git commands only):
  - `git add -A` / `git add --all` / `git add .` / `git add -u`      -> stage explicit paths
  - `git reset --hard`                                                -> destructive; hazardous on a shared tree
  - `git clean -<flags with d/f/x>`                                   -> deletes untracked files (no reflog)
  - `git stash` (push/save/pop/apply/drop, or bare)                   -> stash@{0} shifts on a shared tree
  - `git checkout -- ` / `git checkout .` / `git restore ` (discard)  -> discards uncommitted changes
  - `git push --force` / `git push -f`                                -> force push overwrites remote history
  - `git rm --cached`                                                 -> untracks a shared file team-wide on merge

The advisory exists to nudge good git hygiene, not to gate anything. False
positives are acceptable because the only consequence is one extra line.
"""

import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# (compiled pattern, advisory message) — ordered; the first match wins.
_RULES = [
    (
        re.compile(r"\bgit\s+add\s+(?:-A\b|--all\b|-u\b|\.(?:\s|$))"),
        "[git-safety] `git add -A`/`.`/`-u` co-stages files you may not own. Stage explicit "
        "paths and verify with `git diff --cached --name-only` (skill: git-safety).",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "[git-safety] `git reset --hard` discards uncommitted work with no reflog. On a tree a "
        "second session/syncer shares, it wipes the peer's work too (skill: shared-checkout-safety).",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*[dfx]"),
        "[git-safety] `git clean` deletes untracked files permanently (no reflog). Confirm the "
        "targets are disposable; never run it on a shared checkout (skill: shared-checkout-safety).",
    ),
    (
        re.compile(r"\bgit\s+stash\b"),
        "[git-safety] On a shared working tree `stash@{0}` shifts the instant a peer pops, and a "
        "stash removes the change from the tree. Prefer a `git worktree` (skill: shared-checkout-safety).",
    ),
    (
        re.compile(r"\bgit\s+checkout\s+--\s|\bgit\s+checkout\s+\.(?:\s|$)|\bgit\s+restore\s+(?!--staged)"),
        "[git-safety] `git checkout -- `/`git restore` discards uncommitted changes. Preserve first "
        "(commit / `stash push -m` / dated backup) before discarding (skill: git-safety).",
    ),
    (
        re.compile(r"\bgit\s+push\s+(?:--force\b|-f\b|--force-with-lease\b)"),
        "[git-safety] A force push rewrites remote history. Confirm no one else builds on the branch, "
        "and prefer `--force-with-lease` (skill: git-safety).",
    ),
    (
        re.compile(r"\bgit\s+rm\s+--cached\b"),
        "[git-safety] `git rm --cached` on a shared TRACKED file deletes it for the whole team on "
        "merge. Flag it as consequential and document the restore path (skill: git-safety).",
    ),
]


def _extract_command(data):
    """Pull the shell command text out of the PreToolUse stdin JSON.

    Returns "" when there is no command to inspect. Never raises.
    """
    if not isinstance(data, dict):
        return ""
    ti = data.get("tool_input")
    if isinstance(ti, dict):
        for key in ("command", "script", "cmd"):
            val = ti.get(key)
            if isinstance(val, str) and val:
                return val
    # Fallbacks for alternate shapes.
    for key in ("command", "script"):
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def _read_stdin():
    try:
        raw = sys.stdin.read()
    except Exception:
        return ""
    if not raw:
        return ""
    try:
        return json.loads(raw)
    except Exception:
        # Not JSON — treat the raw text as the command body.
        return {"tool_input": {"command": raw}}


def main():
    try:
        data = _read_stdin()
        command = _extract_command(data)
        if not command or "git" not in command:
            return
        for pattern, message in _RULES:
            if pattern.search(command):
                print(message)
                return  # one advisory line, first match only
    except Exception:
        # Advisory only — never let the hook disturb the turn.
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
