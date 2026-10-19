#!/usr/bin/env python3
"""Print the current TOTP code for a QA test account, reading the seed from an env var.

    python totp.py QA_ADMIN_TOTP              # 6-digit code, 30 s period, SHA-1
    python totp.py QA_ADMIN_TOTP --digits 8 --period 60

The argument is the NAME of an environment variable that holds the base32 seed
(set it before launching Claude Code). The seed itself is never printed and
never passes through the conversation; only the short-lived code does.
RFC 6238, stdlib only. Exit 2 when the variable is unset or not valid base32.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import sys
import time


def totp(seed_b32: str, at: float | None = None, digits: int = 6, period: int = 30) -> str:
    clean = seed_b32.replace(" ", "").replace("-", "").upper()
    key = base64.b32decode(clean + "=" * (-len(clean) % 8))
    counter = int((time.time() if at is None else at) // period)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def _opt(argv: list[str], name: str, default: int) -> int:
    if name in argv:
        return int(argv[argv.index(name) + 1])
    return default


def main(argv: list[str]) -> int:
    names = [a for i, a in enumerate(argv)
             if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    if not names:
        print("usage: totp.py <ENV_VAR_NAME> [--digits N] [--period S]", file=sys.stderr)
        return 2
    seed = os.environ.get(names[0], "")
    if not seed.strip():
        print(f"{names[0]} is not set in this environment (set it before launching "
              f"Claude Code).", file=sys.stderr)
        return 2
    try:
        at = float(argv[argv.index("--at") + 1]) if "--at" in argv else None
        print(totp(seed, at, _opt(argv, "--digits", 6), _opt(argv, "--period", 30)))
    except (ValueError, TypeError, IndexError):
        print(f"{names[0]} does not hold a valid base32 TOTP seed.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
