#!/usr/bin/env python
"""
SessionStart hook: Detect Odoo version and inject frontend context.
Reads JSON on stdin (required by Claude Code hooks).
Exit 0 always. Stdout becomes conversation context.
"""

import sys
import os
import json
import re
from pathlib import Path

# Read stdin (required by hook protocol)
sys.stdin.read()

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
    # Strategy 1: Look for odoo{VERSION}/ directories
    for item in search_dir.iterdir():
        if item.is_dir():
            match = re.match(r'^odoo(\d{2})$', item.name)
            if match:
                ver = match.group(1)
                # Normalize: "17" → "17"
                return {
                    "version": ver,
                    "bootstrap": BOOTSTRAP_MAP.get(ver, "5.1.3"),
                    "owl": OWL_MAP.get(ver),
                    "source": f"directory {item.name}/",
                }

    # Strategy 2: Look for release.py in odoo/ subdirectory
    for odoo_dir in search_dir.glob("**/odoo/release.py"):
        try:
            content = odoo_dir.read_text(encoding="utf-8")
            match = re.search(r"version_info\s*=\s*\((\d+),", content)
            if match:
                ver = match.group(1)
                return {
                    "version": ver,
                    "bootstrap": BOOTSTRAP_MAP.get(ver, "5.1.3"),
                    "owl": OWL_MAP.get(ver),
                    "source": str(odoo_dir),
                }
        except (OSError, UnicodeDecodeError):
            continue

    return None


def count_themes(search_dir: Path) -> int:
    """Count theme modules in projects/ directories."""
    count = 0
    for projects_dir in search_dir.glob("**/projects"):
        if projects_dir.is_dir():
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for module in project.iterdir():
                        if module.is_dir() and module.name.startswith("theme_"):
                            count += 1
    return count


def main():
    # Determine workspace root (go up from plugin to find Odoo workspace)
    cwd = Path(os.getcwd())

    result = detect_odoo_version(cwd)

    if result:
        ver = result["version"]
        bs = result["bootstrap"]
        owl = result["owl"]
        js_note = f", Owl {owl}" if owl else ""
        print(f"[Odoo Frontend] Detected: Odoo {ver}, Bootstrap {bs}{js_note}. Use publicWidget for website themes.")

        # Check for existing themes
        theme_count = count_themes(cwd)
        if theme_count > 0:
            print(f"[Odoo Frontend] Found {theme_count} theme module(s) in workspace.")
    else:
        print("[Odoo Frontend] No Odoo installation detected. Run /odoo-frontend for manual setup.")

    sys.exit(0)


if __name__ == "__main__":
    main()
