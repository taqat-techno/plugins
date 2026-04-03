#!/usr/bin/env python
"""
SessionStart hook: Detect Odoo version and inject frontend context.
Reads JSON on stdin (required by Claude Code hooks).
Exit 0 always. Stdout becomes conversation context.

Optimized: no recursive glob, internal timeout guard, early termination.
"""

import sys
import os
import re
import threading
from pathlib import Path

# ── Internal timeout guard (defense-in-depth) ──────────────────────────────
# If this script hangs for any reason, force-exit after 8 seconds.
# The hook-runner wrapper has a 10s timeout; this exits cleanly before that.
_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Read stdin (required by hook protocol)
try:
    sys.stdin.read()
except Exception:
    pass

PLUGIN_ROOT = Path(__file__).parent.parent

# Version → Bootstrap mapping
BOOTSTRAP_MAP = {
    "14": "4.5.0", "15": "4.5.0",
    "16": "5.1.3", "17": "5.1.3", "18": "5.1.3", "19": "5.1.3",
}

OWL_MAP = {
    "14": None, "15": None,
    "16": "1.x", "17": "1.x", "18": "2.x", "19": "2.x",
}


def detect_odoo_version(search_dir: Path) -> dict:
    """Detect Odoo version from workspace directory structure."""
    # Strategy 1: Look for odoo{VERSION}/ directories (fast, no recursion)
    try:
        for item in search_dir.iterdir():
            if item.is_dir():
                match = re.match(r'^odoo(\d{2})$', item.name)
                if match:
                    ver = match.group(1)
                    return {
                        "version": ver,
                        "bootstrap": BOOTSTRAP_MAP.get(ver, "5.1.3"),
                        "owl": OWL_MAP.get(ver),
                        "source": f"directory {item.name}/",
                    }
    except (OSError, PermissionError):
        pass

    # Strategy 2: Check targeted paths only (NO recursive glob)
    # Look for odoo/release.py in the CWD itself or one level up
    for candidate in [
        search_dir / "odoo" / "release.py",
        search_dir.parent / "odoo" / "release.py",
    ]:
        if candidate.is_file():
            try:
                content = candidate.read_text(encoding="utf-8")
                match = re.search(r"version_info\s*=\s*\((\d+),", content)
                if match:
                    ver = match.group(1)
                    return {
                        "version": ver,
                        "bootstrap": BOOTSTRAP_MAP.get(ver, "5.1.3"),
                        "owl": OWL_MAP.get(ver),
                        "source": str(candidate),
                    }
            except (OSError, UnicodeDecodeError):
                continue

    return None


def main():
    cwd = Path(os.getcwd())
    result = detect_odoo_version(cwd)

    if result:
        ver = result["version"]
        bs = result["bootstrap"]
        owl = result["owl"]
        js_note = f", Owl {owl}" if owl else ""
        print(f"[Odoo Frontend] Detected: Odoo {ver}, Bootstrap {bs}{js_note}. Use publicWidget for website themes.")
    # Removed: count_themes() -- recursive glob was slow and advisory-only
    # Removed: "No Odoo installation detected" message -- reduces noise

    _timer.cancel()
    sys.exit(0)


if __name__ == "__main__":
    main()
