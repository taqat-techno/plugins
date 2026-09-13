#!/usr/bin/env python3
"""notification plugin - the one piece of short-lived state.

Claude Code presents an AskUserQuestion dialog through its permission-prompt
path, so a single question raises TWO hook events: PreToolUse, which carries the
question text, and - a few seconds later - Notification/permission_prompt, which
carries only the generic "Claude needs your permission". That second payload
names no tool, so no payload-only rule can tell it apart from a real permission
prompt. This module bridges the two with a per-session marker file (D-013):

    question notified   -> mark_question(session)
    permission prompt   -> question_pending(session) ? suppress : notify
    question answered   -> clear_question(session)     PostToolUse
    user types again    -> clear_question(session)     UserPromptSubmit
    turn ended          -> clear_question(session)     Stop / StopFailure

A question dismissed with Esc fires no PostToolUse; the next prompt clears it,
and the marker also expires on its own after QUESTION_WINDOW seconds, so it can
never silence a later, real permission prompt for long.

Hard guarantees:
  - Lives only under ${CLAUDE_PLUGIN_DATA}/state (D-005), never the plugin root.
  - Never raises. Every failure fails TOWARD notifying: an unwritable or
    unreadable marker means a possible duplicate, never a lost alert.
  - Self-cleaning: markers older than STALE_AFTER are swept on every write.
"""

import os
import re
import time

import policy

# hooks.json verbs that change state but never notify.
ANSWERED = "answered"      # PostToolUse on AskUserQuestion
PROMPTED = "prompted"      # UserPromptSubmit
CONTROL_VERBS = (ANSWERED, PROMPTED)

QUESTION_WINDOW = 120      # seconds a question covers the permission prompt it raises
STALE_AFTER = 24 * 3600    # seconds before an orphaned marker is swept

_PREFIX = "question-"
_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")


def state_dir():
    return os.path.join(policy.data_dir(), "state")


def _marker(session_id):
    if not isinstance(session_id, str):
        return None
    safe = _UNSAFE.sub("", session_id)[:64]
    return os.path.join(state_dir(), _PREFIX + safe) if safe else None


def mark_question(session_id):
    """Record that this session's question has been notified. True on success."""
    try:
        path = _marker(session_id)
        if not path:
            return False
        os.makedirs(state_dir(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(str(time.time()))
        _sweep()
        return True
    except Exception:
        return False


def question_pending(session_id):
    """True while a recently notified question is still open in this session."""
    try:
        path = _marker(session_id)
        if not path or not os.path.isfile(path):
            return False
        return time.time() - os.path.getmtime(path) <= QUESTION_WINDOW
    except Exception:
        return False


def clear_question(session_id):
    """Forget this session's question. True when a marker was removed."""
    try:
        path = _marker(session_id)
        if path and os.path.isfile(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def _sweep():
    try:
        now = time.time()
        for name in os.listdir(state_dir()):
            if not name.startswith(_PREFIX):
                continue
            path = os.path.join(state_dir(), name)
            try:
                if now - os.path.getmtime(path) > STALE_AFTER:
                    os.remove(path)
            except Exception:
                continue
    except Exception:
        pass
