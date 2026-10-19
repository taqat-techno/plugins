#!/usr/bin/env python3
"""SessionStart hook: when the workspace holds an Odoo source tree (`odooNN/`), tell
Claude the Odoo, Bootstrap and Owl versions that go with it.

Prints additionalContext JSON only when it finds one; in any other project it prints
nothing. Fails open: bad input, an exception or the 8 s watchdog all end in exit 0.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_vendor"))

import hooklib  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BOOTSTRAP_MAP = {
    "14": "4.5.0", "15": "4.5.0",
    "16": "5.1.3", "17": "5.1.3", "18": "5.1.3", "19": "5.1.3",
}

OWL_MAP = {
    "14": None, "15": None,
    "16": "1.x", "17": "1.x", "18": "2.x", "19": "2.x",
}

_DIR_RE = re.compile(r"^odoo(\d{2})$")


def detect_odoo_version(cwd: str) -> str:
    """Detect the Odoo version from the workspace directory layout (no recursion)."""
    try:
        names = sorted(os.listdir(cwd))
    except OSError:
        return ""
    for item in names:
        m = _DIR_RE.match(item)
        if m and os.path.isdir(os.path.join(cwd, item)):
            ver = m.group(1)
            parts = ["Odoo %s" % ver, "Bootstrap %s" % BOOTSTRAP_MAP.get(ver, "5.1.3")]
            if OWL_MAP.get(ver):
                parts.append("Owl %s" % OWL_MAP[ver])
            return "[Odoo Frontend] Detected: %s. Use publicWidget for website themes." % ", ".join(parts)
    return ""


def main() -> int:
    hooklib.watchdog(8.0)
    payload = hooklib.read_payload() or {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    if not cwd or not os.path.isdir(cwd):
        cwd = os.getcwd()
    ctx = detect_odoo_version(cwd)
    if ctx:
        hooklib.context("SessionStart", ctx)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
