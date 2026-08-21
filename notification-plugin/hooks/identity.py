#!/usr/bin/env python3
"""notification plugin - which session, which project.

Derives the identity line shown on every notification ("project · a1b2c3") from
fields the hook payload already carries. No subprocess, no git binary, no state.

Why `cwd` and not ${CLAUDE_PROJECT_DIR}: when Claude enters a worktree,
CLAUDE_PROJECT_DIR stays at the directory the session started in while `cwd`
follows Claude. A worktree should read as its own workspace in a notification.

Hard guarantees:
  - Never raises. Every failure path returns a usable string.
  - Read-only: stats directories, opens nothing, spawns nothing.
"""

import os

SESSION_TAG_LENGTH = 6
MAX_WALK_DEPTH = 40


def project_name(cwd):
    """Repository name if `cwd` is inside one, else the directory name.

    Walks up looking for a `.git` entry. It may be a directory (normal clone) or
    a file (a worktree or a submodule), so both count.
    """
    try:
        if not cwd or not isinstance(cwd, str):
            return ""
        path = os.path.abspath(cwd)
        for _ in range(MAX_WALK_DEPTH):
            if os.path.exists(os.path.join(path, ".git")):
                return os.path.basename(path) or path
            parent = os.path.dirname(path)
            if parent == path:          # filesystem root
                break
            path = parent
        return os.path.basename(os.path.abspath(cwd)) or os.path.abspath(cwd)
    except Exception:
        return ""


def session_tag(session_id):
    """Short, stable discriminator so concurrent sessions stay distinguishable."""
    try:
        if not session_id or not isinstance(session_id, str):
            return ""
        return session_id.replace("-", "")[:SESSION_TAG_LENGTH]
    except Exception:
        return ""


def attribution(payload):
    """The identity line: 'project · a1b2c3', or whichever half is available."""
    try:
        name = project_name(payload.get("cwd"))
        tag = session_tag(payload.get("session_id"))
        if name and tag:
            return "{0} · {1}".format(name, tag)
        return name or tag or "Claude Code"
    except Exception:
        return "Claude Code"


def replace_key(payload, category):
    """Stable key for replace-in-place, so a burst updates one notification.

    Scoped to the session so two sessions never overwrite each other's alerts.
    """
    try:
        return "claude-{0}-{1}".format(session_tag(payload.get("session_id")) or "x", category)
    except Exception:
        return "claude-x-{0}".format(category)
