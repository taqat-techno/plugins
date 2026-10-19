#!/usr/bin/env python3
"""
sprint-recap SessionStart hook - advisory configuration check.

Silent unless this project actually uses sprint-recap (a .sprint-recap/ folder
or a config file exists). Never blocks; it only surfaces the two mistakes that
cost the most later:
  * the local config is not gitignored, so passwords are one commit from GitHub
  * a generated credentials page is already tracked by git

Output contract: findings go to STDOUT as
  {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}
with exit 0. Stderr from an exit-0 SessionStart hook is never shown to Claude
(or the user), so warnings written there were silently dropped. No output at
all when there is nothing to report.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

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
    hooklib.watchdog(8.0)
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
            "Run /sprint-recap:target set."
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

    stale_auth = [p for p in recap.glob("runs/*/*/.auth") if p.is_dir()] if recap.is_dir() else []
    if stale_auth:
        notes.append(
            "Cached session cookies from an older sprint-recap version remain in "
            + ", ".join(p.relative_to(root).as_posix() for p in stale_auth[:3])
            + ". Delete them; capture no longer keeps session state on disk."
        )

    if notes:
        emit(notes)
    return 0


def emit(notes: list) -> None:
    """Hand the findings to Claude as SessionStart additionalContext JSON."""
    text = "[sprint-recap]\n" + "\n".join("  - " + note for note in notes)
    hooklib.context("SessionStart", text)


if __name__ == "__main__":
    hooklib.run(main)  # fails open: an advisory hook must never break the session
