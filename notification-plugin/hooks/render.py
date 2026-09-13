#!/usr/bin/env python3
"""notification plugin - event to notification text.

Turns one Claude Code hook payload into a (klass, title, body, attribution)
tuple. Every character it emits is a field the payload already contained; there
is no summarisation, no model call, and no transcript read.

Layout - clean and minimal, the same on every platform:

    title        ❓ claude_plugins needs your answer      icon, project, what happened
    body         Which migration strategy should I use?  the actual content
    attribution  session 2ecaaa                          which session

Hard guarantees:
  - Pure function of the payload. No I/O, no subprocess, no network.
  - Never raises. A missing or wrong-typed field degrades the text, never the run.
  - All text is treated as UNTRUSTED DATA: control characters and ANSI escape
    sequences are stripped, newlines collapsed, and length clipped, before the
    text reaches any backend.

Two intrusiveness classes:
  ATTENTION      you are being asked for something - stays longer, with sound.
  INFORMATIONAL  something finished - transient, silent.
"""

import re

ATTENTION = "attention"
INFORMATIONAL = "informational"

# Category -> (class, icon, title template). Keys match the argv verb in
# hooks.json. `{who}` is the project name, or "Claude" when none is known.
CATEGORIES = {
    "question":   (ATTENTION,     "❓", "{who} needs your answer"),
    "permission": (ATTENTION,     "🔐", "{who} needs your approval"),
    "failure":    (ATTENTION,     "❌", "{who} hit an error"),
    "task":       (INFORMATIONAL, "☑️", "{who} finished a task"),
    "turn":       (INFORMATIONAL, "✅", "{who} is done"),
}

TITLE_LIMIT = 80
PROJECT_LIMIT = 40
BODY_LIMIT = 180

# The only text Claude Code puts in a permission_prompt payload today. Repeating
# it under a title that already says "needs your approval" tells the reader
# nothing, so it is replaced with where to act.
_GENERIC_PERMISSION = "claude needs your permission"

# StopFailure `error` values, as a person would say them.
_ERROR_LABELS = {
    "rate_limit": "Rate limit reached",
    "overloaded": "The API is overloaded",
    "authentication_failed": "Authentication failed",
    "billing_error": "Billing problem",
    "invalid_request": "Invalid request",
    "server_error": "API server error",
    "max_output_tokens": "Output token limit reached",
    "unknown": "Unknown error",
}
_API_ERROR_PREFIX = re.compile(r"^\s*API Error:\s*", re.IGNORECASE)

# CSI / OSC / single-character escape sequences.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")
# C0 and C1 control characters, minus the whitespace we normalise separately.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_WHITESPACE = re.compile(r"\s+")

# Markdown, which Claude's final message almost always is.
_FENCE = re.compile(r"(```|~~~).*?(?:\1|\Z)", re.DOTALL)
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_INLINE_CODE = re.compile(r"`+([^`]+)`+")
# `__` is deliberately not treated as emphasis: it would eat `__init__`.
_STRONG = re.compile(r"(\*\*|~~)(?=\S)(.+?)(?<=\S)\1")
_EMPHASIS = re.compile(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])")
_LINE_MARKER = re.compile(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+(?:\[[ xX]\]\s+)?|\d+[.)]\s+)")
_RULE = re.compile(r"^\s*(?:[-*_=]\s*){3,}$")
_SENTENCE_END = ".!?:;…"
_TABLE_RULE = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*(?::?-+:?)?\s*$")


def clean(value, limit):
    """Normalise untrusted text to a single safe display line.

    Strips ANSI sequences and control characters, collapses all whitespace
    (including newlines) to single spaces, removes leading dashes so the value
    can never be parsed as a command-line option, and clips to `limit` - at a
    word boundary when one is close enough.
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
            cut = value[: max(limit - 1, 0)]
            space = cut.rfind(" ")
            if space >= limit * 0.6:
                cut = cut[:space]
            value = cut.rstrip(" ,;:—-") + "…"
        return value
    except Exception:
        return ""


def plain_text(markdown):
    """Reduce Markdown to the words a reader would see. Never raises."""
    try:
        if not isinstance(markdown, str):
            return ""
        text = _FENCE.sub(" ", markdown)
        text = _IMAGE.sub(r"\1", text)
        text = _LINK.sub(r"\1", text)
        text = _INLINE_CODE.sub(r"\1", text)
        text = _STRONG.sub(r"\2", text)
        text = _EMPHASIS.sub(r"\1", text)
        lines = []
        for line in text.splitlines():
            if _RULE.match(line) or _TABLE_RULE.match(line):
                continue
            if line.lstrip().startswith("|"):
                line = line.replace("|", " ")
            line = _LINE_MARKER.sub("", line).strip()
            if line:
                lines.append(line)
        # Headings and list items carry no punctuation of their own; once they
        # share one line, a full stop keeps "Done" and "Fixed the bug" apart.
        joined = [line if line[-1] in _SENTENCE_END else line + "." for line in lines[:-1]]
        return " ".join(joined + lines[-1:])
    except Exception:
        return ""


def _questions(payload):
    """The AskUserQuestion questions, as a list of dicts."""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    questions = tool_input.get("questions")
    if not isinstance(questions, list):
        return []
    return [item for item in questions if isinstance(item, dict)]


def _content(category, payload):
    """Return (text, suffix). The suffix survives clipping of the text."""
    if category == "question":
        questions = _questions(payload)
        fallback = "Claude is waiting for your answer"
        if not questions:
            return fallback, ""
        # The question text is what the user must answer; the header is a short label.
        text = questions[0].get("question") or questions[0].get("header") or fallback
        extra = len(questions) - 1
        return text, (" (+{0} more)".format(extra) if extra > 0 else "")

    if category == "permission":
        message = payload.get("message")
        if isinstance(message, str) and message.strip().rstrip(".").lower() != _GENERIC_PERMISSION:
            return message, ""
        return "A request is waiting for your approval in the terminal", ""

    if category == "task":
        return payload.get("task_subject") or payload.get("task_description") or "A task was completed", ""

    if category == "turn":
        return plain_text(payload.get("last_assistant_message")) or "Claude finished and is waiting for you", ""

    if category == "failure":
        error = payload.get("error")
        error = error.strip() if isinstance(error, str) and error.strip() else "unknown"
        label = _ERROR_LABELS.get(error) or error.replace("_", " ").capitalize()
        detail = payload.get("last_assistant_message") or payload.get("error_details") or ""
        detail = _API_ERROR_PREFIX.sub("", plain_text(detail if isinstance(detail, str) else str(detail)))
        if detail and label.lower() not in detail.lower():
            return "{0} — {1}".format(label, detail), ""
        return detail or label, ""

    return "", ""


def build(category, payload, project="", tag=""):
    """Return (klass, title, body, attribution) or None when nothing should be sent."""
    try:
        entry = CATEGORIES.get(category)
        if entry is None:
            return None
        klass, icon, template = entry
        who = clean(project, PROJECT_LIMIT) or "Claude"
        title = clean("{0} {1}".format(icon, template.format(who=who)), TITLE_LIMIT)
        text, suffix = _content(category, payload)
        body = clean(text, BODY_LIMIT - len(suffix))
        if not body:
            return None
        tag = clean(tag, 16)
        attribution = "session {0}".format(tag) if tag else ""
        return klass, title, body + suffix, attribution
    except Exception:
        return None
