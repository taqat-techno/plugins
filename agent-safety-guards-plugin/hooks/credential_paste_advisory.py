#!/usr/bin/env python3
"""agent-safety-guards UserPromptSubmit advisory hook.

When the submitted prompt contains something shaped like a credential, hand Claude one
fixed reminder (UserPromptSubmit additionalContext JSON): a secret pasted into a session
is compromised, so revoke it and issue a new least-scope one.

Guarantees:
  - Never blocks, denies or asks. Exit 0 in every case.
  - Never echoes the matched value or any prompt text; the reminder is a fixed string.
  - Stdlib only (plus the vendored hooklib). Fails open on any error.

Detection is shape-based and conservative. It looks for well-known token prefixes
(GitHub, GitLab, Slack, AWS, Google, OpenAI/Anthropic-style sk-), JWTs, Bearer/Basic
credentials, PEM private keys, credential assignments (password=..., api_key: ...),
URLs with an embedded password, and long random-looking base64 runs. It deliberately
does NOT fire on git commit SHAs, sha256/sha512 digests, npm integrity strings, UUIDs,
file paths, or words that merely contain "sk-" (task-sk-rename).
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

REMINDER = ("[agent-safety] The prompt appears to contain a credential. A secret pasted into a session "
            "is COMPROMISED: revoke it and issue a fresh least-scope credential; never reuse, echo or "
            "commit the leaked value.")

_PREFIX = re.compile(
    r"(?<![A-Za-z0-9_-])("
    r"sk-(?:ant-|proj-|live-|test-)?[A-Za-z0-9_\-]{20,}"
    r"|rk_(?:live|test)_[A-Za-z0-9]{16,}"
    r"|sk_(?:live|test)_[A-Za-z0-9]{16,}"
    r"|gh[pousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|glpat-[A-Za-z0-9_\-]{20,}"
    r"|xox[baprs]-[A-Za-z0-9\-]{10,}"
    r"|(?:AKIA|ASIA)[0-9A-Z]{16}"
    r"|AIza[0-9A-Za-z_\-]{35}"
    r"|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
    r")"
)
_AUTH = re.compile(r"\b(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=\-]{20,}")
_PEM = re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")
_ASSIGN = re.compile(
    r"(?i)\b(?:password|passwd|pwd|secret|client_secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
    r"\s*[=:]\s*['\"]?([^\s'\"&,;]{8,})")
_URL_PASSWORD = re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:([^@\s/]{4,})@", re.I)
_LONG = re.compile(r"(?<![A-Za-z0-9+/_\-])[A-Za-z0-9+/_\-]{40,}={0,2}")
_DIGEST_PREFIX = re.compile(r"(?i)(?:sha(?:1|224|256|384|512)|md5)[-:]$")
_PLACEHOLDER = re.compile(r"(?i)^(?:<[^>]*>|\*+|x{4,}|\.{3,}|\$\{?[A-Z_]+\}?|%[A-Z_]+%|changeme|example\w*|your[_-]?\w+)$")


def _random_looking(run: str, before: str) -> bool:
    if _DIGEST_PREFIX.search(before) or re.match(r"(?i)sha(?:1|256|384|512)-", run):
        return False
    if re.fullmatch(r"[0-9a-fA-F]+", run):  # commit SHAs, hex digests
        return False
    if run.count("/") >= 2 and "+" not in run and not run.endswith("="):  # paths
        return False
    if run.count("-") + run.count("_") >= 3 and not re.search(r"[0-9]", run):  # slugs
        return False
    has_upper = any(c.isupper() for c in run)
    has_lower = any(c.islower() for c in run)
    has_digit = any(c.isdigit() for c in run)
    return has_upper and has_lower and has_digit


def looks_like_secret(text: str) -> bool:
    """True if the text contains a credential-shaped string. Returns only a boolean."""
    if not text:
        return False
    if _PREFIX.search(text) or _AUTH.search(text) or _PEM.search(text):
        return True
    for m in _ASSIGN.finditer(text):
        value = m.group(1)
        if not _PLACEHOLDER.match(value) and not re.fullmatch(r"[a-z]+", value):
            return True
    for m in _URL_PASSWORD.finditer(text):
        if not _PLACEHOLDER.match(m.group(1)):
            return True
    for m in _LONG.finditer(text):
        if _random_looking(m.group(0), text[max(0, m.start() - 8):m.start()]):
            return True
    return False


# kept for older callers and tests
_looks_like_secret = looks_like_secret


def _read_prompt() -> str:
    payload = hooklib.read_payload()
    if not payload:
        return ""
    for key in ("prompt", "user_prompt", "userPrompt", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def main() -> int:
    hooklib.watchdog(3)
    if looks_like_secret(_read_prompt()):
        hooklib.context("UserPromptSubmit", REMINDER)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
