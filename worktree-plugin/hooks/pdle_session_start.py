#!/usr/bin/env python3
"""SessionStart advisory for Plan-Driven Lane Execution.

Prints a short role notice when a session starts in a repository that is running
lanes. Without it, every newly launched worker has to be told its role by hand.

SAFETY CONTRACT - this hook must never be able to harm a session:
  * exits 0 unconditionally, whatever happens;
  * writes nothing to stderr and creates no files;
  * emits at most a few lines of additionalContext;
  * no-ops instantly when .claude/lanes/ does not exist, which is the case for
    every repository not running PDLE and for every legacy user of this plugin.

It is the only hook this plugin ships, it is opt-in, and /worktree:init --remove
takes it back out.
"""

import json
import os
import sys

MAX_LANES_LISTED = 12


def _repo_root(start):
    """Walk up looking for a directory containing .claude/lanes. Cheap and
    dependency-free - no git subprocess, because a hook must be fast."""
    cur = _norm(start)
    if not cur:
        return None
    cur = os.path.abspath(cur)
    while True:
        if os.path.isdir(os.path.join(cur, ".claude", "lanes")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def _read_lane(path):
    """Parse the porcelain lane record.

    Returns (scalars, owns). Scalars keep their first value; `owns` is
    repeatable and is collected in full. They are kept apart rather than mixed
    into one dict so a caller can never accidentally treat the list as a path.
    """
    scalars = {}
    owns = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                key = parts[0]
                val = parts[1].strip() if len(parts) > 1 else ""
                if key == "owns":
                    if val:
                        owns.append(val)
                else:
                    scalars.setdefault(key, val)
    except OSError:
        return {}, []
    return scalars, owns


def _norm(p):
    """Canonical comparable path. Tolerates the three spellings in play on
    Windows: C:\\x from the session payload, C:/x from git, and the MSYS /c/x
    form. Comparing these naively is the single most likely silent bug here."""
    p = (p or "").replace("\\", "/")
    if os.name == "nt" and len(p) > 2 and p[0] == "/" and p[2:3] == "/" and p[1].isalpha():
        p = p[1] + ":" + p[2:]
    try:
        p = os.path.abspath(p)
    except (OSError, ValueError):
        return ""
    return os.path.normcase(p).replace("\\", "/").rstrip("/")


def build_notice(cwd):
    root = _repo_root(cwd)
    if not root:
        return ""

    lanes_dir = os.path.join(root, ".claude", "lanes")
    try:
        names = sorted(n for n in os.listdir(lanes_dir) if n.endswith(".lane"))
    except OSError:
        return ""
    if not names:
        return ""

    here = _norm(cwd)
    mine = None
    mine_owns = []
    unassigned = 0
    for name in names[:200]:
        rec, owns = _read_lane(os.path.join(lanes_dir, name))
        if not rec:
            continue
        if not rec.get("owner"):
            unassigned += 1
        wt = rec.get("worktree", "")
        if wt:
            wt_abs = wt if os.path.isabs(wt) else os.path.join(root, wt)
            if _norm(wt_abs) == here:
                mine = rec
                mine_owns = owns

    lines = [
        "[worktree] This repository is running Plan-Driven Lane Execution "
        "(%d lane%s defined, %d unassigned)."
        % (len(names), "" if len(names) == 1 else "s", unassigned)
    ]

    if mine:
        lane = mine.get("lane", "?")
        owns_text = ", ".join(mine_owns)
        owner = mine.get("owner", "")
        lines.append(
            "This session's working directory IS lane '%s'%s%s."
            % (
                lane,
                " (owns %s)" % owns_text if owns_text else "",
                " assigned to '%s'" % owner if owner else " - currently unassigned",
            )
        )
        lines.append(
            "If you are that worker: read .claude/lanes/briefs/%s.md, work only "
            "inside this lane's ownership set, and do NOT commit, merge or push "
            "- a packet ends staged and reported. Use /worktree:report to close "
            "a packet." % lane
        )
    else:
        lines.append(
            "If you were started as a worker, run /worktree:join to register a "
            "unique name. If you are the orchestrator, run /worktree:lead. "
            "/worktree:board shows current state."
        )

    lines.append(
        "Workers never commit, merge, push, or dispatch; the main agent "
        "integrates centrally."
    )
    return "\n".join(lines)


def main():
    cwd = os.getcwd()
    try:
        raw = sys.stdin.read()
        if raw:
            payload = json.loads(raw)
            cwd = payload.get("cwd") or payload.get("workingDirectory") or cwd
    except Exception:
        pass  # a malformed or absent payload must not stop the session

    context = ""
    try:
        context = build_notice(cwd)
    except Exception:
        context = ""

    try:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
