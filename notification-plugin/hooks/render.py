#!/usr/bin/env python3
"""notification plugin - event to notification text.

Turns one Claude Code hook payload into a (klass, title, body, attribution)
tuple. Every character it emits is a field the payload already contained; there
is no summarisation, no model call, and no transcript read.

Hard guarantees:
  - Pure function of the payload. No I/O, no subprocess, no network.
  - Never raises. A missing or wrong-typed field degrades the text, never the run.
  - All text is treated as UNTRUSTED DATA: control characters and ANSI escape
    sequences are stripped, newlines collapsed, and length clipped, before the
    text reaches any backend.

Two intrusiveness classes:
  ATTENTION      you are being asked for something - sticky where the OS allows
                 it, with sound.
  INFORMATIONAL  something finished - transient, silent.
"""

import re

ATTENTION = "attention"
INFORMATIONAL = "informational"

# Category -> (class, title). Keys match the argv verb in hooks.json.
CATEGORIES = {
    "question":   (ATTENTION,     "❓ Claude Needs Your Answer"),
    "permission": (ATTENTION,     "🔐 Claude Needs Approval"),
    "failure":    (ATTENTION,     "❌ Claude Failed"),
    "task":       (INFORMATIONAL, "✅ Task Completed"),
    "turn":       (INFORMATIONAL, "✅ Claude Finished"),
}

TITLE_LIMIT = 80
BODY_LIMIT = 220

# CSI / OSC / single-character escape sequences.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
# C0 and C1 control characters, minus the whitespace we normalise separately.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WHITESPACE = re.compile(r"\s+")


def clean(value, limit):
    """Normalise untrusted text to a single safe display line.

    Strips ANSI sequences and control characters, collapses all whitespace
    (including newlines) to single spaces, removes leading dashes so the value
    can never be parsed as a command-line option, and clips to `limit`.
    """
    try:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        value = _ANSI.sub("", value)
        value = _CONTROL.sub("", value)
        value = _WHITESPACE.sub(" ", value).strip()
        value = value.lstrip("-").strip()
        if len(value) > limit:
            value = value[: limit - 1].rstrip() + "…"
        return value
    except Exception:
        return ""


def _first_question(payload):
    """Pull the first question out of an AskUserQuestion tool_input."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    questions = tool_input.get("questions")
    if not isinstance(questions, list) or not questions:
        return ""
    first = questions[0]
    if not isinstance(first, dict):
        return ""
    # The question text is what the user must answer; the header is a short label.
    return first.get("question") or first.get("header") or ""


def _body(category, payload):
    if category == "question":
        return _first_question(payload) or "Claude is waiting for your answer"

    if category == "permission":
        return payload.get("message") or payload.get("title") or "Claude needs your permission"

    if category == "task":
        return payload.get("task_subject") or payload.get("task_description") or "A task was completed"

    if category == "turn":
        return payload.get("last_assistant_message") or "Turn complete"

    if category == "failure":
        error = payload.get("error") or "unknown"
        detail = payload.get("last_assistant_message") or payload.get("error_details") or ""
        if detail:
            return "{0} — {1}".format(error, detail)
        return str(error)

    return ""


def build(category, payload, attribution):
    """Return (klass, title, body, attribution) or None when nothing should be sent."""
    try:
        entry = CATEGORIES.get(category)
        if entry is None:
            return None
        klass, title = entry
        body = clean(_body(category, payload), BODY_LIMIT)
        if not body:
            return None
        return klass, clean(title, TITLE_LIMIT), body, clean(attribution, TITLE_LIMIT)
    except Exception:
        return None
