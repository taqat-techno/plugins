#!/usr/bin/env python3
"""
sprint-recap SessionStart hook - advisory configuration check.

Silent unless this project actually uses sprint-recap (a .sprint-recap/ folder
or a config file exists). Never blocks; it only surfaces the two mistakes that
cost the most later:
  * the local config is not gitignored, so passwords are one commit from GitHub
  * a generated credentials page is already tracked by git
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CONFIG = ".sprint-recap.local.json"
RECAP_DIR = ".sprint-recap"


def tracked(path: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "ls-files", "--error-unmatch", path],
            capture_output=True, text=True, timeout=10,
        )
        return out.returncode == 0
    except Exception:
        return False


def ignored(path: str) -> bool:
    try:
        out = subprocess.run(
            ["git", "check-ignore", "-q", path],
            capture_output=True, text=True, timeout=10,
        )
        return out.returncode == 0
    except Exception:
        return False


def main() -> int:
    root = Path.cwd()
    config = root / CONFIG
    recap = root / RECAP_DIR
    if not config.exists() and not recap.exists():
        return 0

    notes = []
    if config.exists():
        if tracked(CONFIG):
            notes.append(
                "CRITICAL: " + CONFIG + " is TRACKED by git. It holds every "
                "role's password. Run: git rm --cached " + CONFIG
            )
        elif not ignored(CONFIG):
            notes.append(
                CONFIG + " is not gitignored. Add it to .gitignore before your "
                "next commit."
            )
    else:
        notes.append(
            "sprint-recap run data exists but " + CONFIG + " is missing. "
            "Run /sprint-recap-target set."
        )

    creds = recap / "credentials"
    if creds.is_dir():
        leaked = [p.name for p in creds.glob("*.html")
                  if tracked(str((Path(RECAP_DIR) / "credentials" / p.name)))]
        if leaked:
            notes.append(
                "CRITICAL: tracked credential page(s): " + ", ".join(leaked)
            )
        elif any(creds.glob("*.html")):
            notes.append(
                "Plaintext credential page(s) present in " + RECAP_DIR
                + "/credentials/. Delete them when the sprint review is done."
            )

    if notes:
        print("[sprint-recap]", file=sys.stderr)
        for note in notes:
            print("  - " + note, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
