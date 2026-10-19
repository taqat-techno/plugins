"""hooklib - the small runtime every Python hook in this marketplace shares.

Canonical copy: shared/hooklib.py at the repository root. Each plugin that uses it
carries a vendored copy at <plugin>/hooks/_vendor/hooklib.py, because Claude Code
caches every plugin on its own and one plugin cannot import from another. Do not edit
a vendored copy; edit this file and run `python tools/sync_vendor.py`. CI runs
`python tools/sync_vendor.py --check` and fails when a copy has drifted.

Stdlib only. Every helper fails open: a hook that cannot read its input or hits an
unexpected error should end in exit 0 with no output, so the tool call proceeds as
if the hook were not installed. Only a deliberate decision blocks.

Typical use:

    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "_vendor"))
    import hooklib

    def main():
        hooklib.watchdog()
        payload = hooklib.read_payload()
        if payload is None:
            return 0
        command = hooklib.tool_input(payload).get("command", "")
        if looks_risky(command):
            hooklib.ask("This drops the database. Confirm?")
        return 0

    if __name__ == "__main__":
        hooklib.run(main)
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading

__version__ = "1.0.0"

# --------------------------------------------------------------------------- input


def read_payload(stream=None):
    """Return the hook's JSON payload as a dict, or None when it is missing or invalid.

    Reads raw bytes and decodes them as UTF-8. On Windows, `sys.stdin.read()` decodes
    with the console code page (cp1252), which turns non-ASCII prompts and commands
    into mojibake or raises, so a guard silently stops seeing what it should match.
    """
    stream = stream if stream is not None else sys.stdin
    try:
        raw = stream.buffer.read() if hasattr(stream, "buffer") else stream.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        data = json.loads(raw) if raw and raw.strip() else None
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def tool_input(payload) -> dict:
    """The `tool_input` object of a tool-event payload, or {} when absent or malformed."""
    value = payload.get("tool_input") if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else {}


# --------------------------------------------------------------------------- safety


def watchdog(seconds: float = 8.0) -> None:
    """Exit 0 after `seconds`, whatever the hook is doing. A stuck hook must never hang
    a session; exiting 0 means the tool call proceeds."""
    timer = threading.Timer(seconds, lambda: os._exit(0))
    timer.daemon = True
    timer.start()


def run(main) -> None:
    """Call main() and exit with its return code. Any exception exits 0 (fail open);
    set HOOKLIB_DEBUG=1 to see the traceback on stderr."""
    try:
        code = main()
    except SystemExit:
        raise
    except Exception:
        if os.environ.get("HOOKLIB_DEBUG"):
            import traceback
            traceback.print_exc()
        code = 0
    sys.exit(code if isinstance(code, int) else 0)


# --------------------------------------------------------------------------- output


def _emit(obj: dict) -> None:
    # ASCII-escaped JSON: a non-ASCII reason written to a cp1252 Windows stdout would raise,
    # and the hook would silently fail open. JSON consumers decode \uXXXX back to the text.
    sys.stdout.write(json.dumps(obj, ensure_ascii=True))
    sys.stdout.flush()


def context(event: str, text: str) -> None:
    """Hand Claude extra context (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse).
    Plain stdout or stderr with exit 0 does not reach the model on every event; this does."""
    _emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def ask(reason: str, event: str = "PreToolUse") -> None:
    """Put the decision in front of the user. Prefer this to deny for irreversible
    operations: the human confirms, and the model cannot talk its way past it."""
    _emit({"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "ask",
                                  "permissionDecisionReason": reason}})


def deny(reason: str, event: str = "PreToolUse") -> None:
    """Refuse the tool call and tell the model why."""
    _emit({"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "deny",
                                  "permissionDecisionReason": reason}})


# --------------------------------------------------------------------------- redaction

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)((?:password|passwd|pwd|secret|token|api[_-]?key|pat)\s*[=:]\s*)[^\s'\"&]{6,}"),
    re.compile(r"(?i)(://[^/\s:@]+:)[^@\s/]+(@)"),
]


def redact(text: str, mask: str = "[REDACTED]") -> str:
    """Mask common secret shapes: private keys, GitHub/Anthropic/OpenAI/Slack/AWS/Google
    tokens, JWTs, bearer/basic credentials, key=value secrets, and URL passwords.
    Shape-based: it cannot recognise a secret with no distinctive form, so never treat
    redacted text as safe to publish without a human looking at it."""
    if not text:
        return text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups == 2:
            text = pattern.sub(lambda m: m.group(1) + mask + m.group(2), text)
        elif pattern.groups == 1:
            text = pattern.sub(lambda m: m.group(1) + mask, text)
        else:
            text = pattern.sub(mask, text)
    return text
