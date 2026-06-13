#!/usr/bin/env python3
"""agent-safety-guards UserPromptSubmit advisory hook.

Reads the stdin JSON that Claude Code sends on every user prompt submission.
If the submitted prompt contains a token-shaped string, it prints ONE short
reminder line that a pasted secret should be treated as compromised (revoke +
reissue with least scope, never reuse).

Hard guarantees (per plugin house rules):
  - NON-FATAL: never blocks, never denies, never asks. Exit 0 in all cases.
  - Never echoes the matched value or any surrounding text. The reminder is a
    fixed string; the prompt content is never reproduced.
  - Stdlib only. No third-party dependencies. Cross-platform.
  - Silent-pass on any error or on no match (prints nothing).

Detection is intentionally conservative and shape-based (no network, no
validation of whether the token is "real"). It looks for:
  - common secret/key prefixes (e.g. sk-, ghp_, AKIA..., xoxb-, and similar),
  - an explicit "Bearer <token>" authorization marker,
  - a long unbroken base64/base64url run (>= 40 chars), which is the typical
    shape of an opaque API token,
  - a PEM private-key header.

False positives are acceptable here because the only consequence is one extra
advisory line; the hook never changes behavior. It exists to nudge good
credential hygiene, not to gate anything.
"""

import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# --- token-shape detectors (conservative, shape-only) ----------------------

# Common provider / tooling secret prefixes followed by a run of token chars.
# Generic and well-known shapes only; no product- or account-specific strings.
_PREFIX = re.compile(
    r"\b("
    r"sk-[A-Za-z0-9_\-]{16,}"          # generic "secret key" style
    r"|rk-[A-Za-z0-9_\-]{16,}"         # generic "restricted key" style
    r"|pk-[A-Za-z0-9_\-]{16,}"         # generic publishable-style key
    r"|gh[pousr]_[A-Za-z0-9]{20,}"     # VCS personal/oauth token shape
    r"|github_pat_[A-Za-z0-9_]{20,}"   # fine-grained VCS token shape
    r"|xox[baprs]-[A-Za-z0-9\-]{10,}"  # chat-platform bot/app token shape
    r"|AKIA[0-9A-Z]{16}"               # cloud access-key-id shape
    r"|ASIA[0-9A-Z]{16}"               # temporary cloud access-key-id shape
    r"|AIza[0-9A-Za-z_\-]{20,}"        # cloud API-key shape
    r"|glpat-[A-Za-z0-9_\-]{16,}"      # repo-host personal token shape
    r"|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}"  # JWT
    r")"
)

# Explicit Authorization: Bearer marker followed by a token-ish run.
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{16,}", re.IGNORECASE)

# A long unbroken base64 / base64url run — the typical shape of an opaque
# API token. Requires length >= 40 and a mix that is not a plain English word.
_LONG_B64 = re.compile(r"\b[A-Za-z0-9+/_\-]{40,}={0,2}\b")

# PEM private-key header.
_PEM = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")


def _looks_like_secret(text):
    """Return True if the text contains a token-shaped string.

    Never returns or stores the matched value — only a boolean.
    """
    if not text:
        return False
    if _PREFIX.search(text):
        return True
    if _BEARER.search(text):
        return True
    if _PEM.search(text):
        return True
    # The long-base64 heuristic is the loosest, so require that the matched
    # run actually mixes character classes (digits + letters), which rules out
    # long all-alpha words and long all-digit IDs.
    for m in _LONG_B64.finditer(text):
        run = m.group(0)
        has_alpha = any(c.isalpha() for c in run)
        has_digit = any(c.isdigit() for c in run)
        if has_alpha and has_digit:
            return True
    return False


def _read_prompt():
    """Extract the prompt text from the stdin JSON. Silent-pass on any error."""
    try:
        raw = sys.stdin.read()
    except Exception:
        return ""
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except Exception:
        # If stdin was not JSON, treat the raw text itself as the prompt body.
        return raw
    if isinstance(data, dict):
        for key in ("prompt", "user_prompt", "userPrompt", "text", "content"):
            val = data.get(key)
            if isinstance(val, str):
                return val
    return ""


def main():
    try:
        prompt = _read_prompt()
        if _looks_like_secret(prompt):
            print(
                "[agent-safety] A secret pasted into a session is COMPROMISED: "
                "revoke it and reissue a fresh least-scope credential; never "
                "reuse or commit the leaked value."
            )
    except Exception:
        # Advisory only — never let the hook disturb the turn.
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
