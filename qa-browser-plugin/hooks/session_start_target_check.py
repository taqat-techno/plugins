#!/usr/bin/env python3
"""
qa-browser SessionStart hook — friendly reminder.

Checks for `.qa-browser.local.json` in CWD (typical project root). If absent,
prints a non-blocking reminder so the user knows to run /qa-target before /qa-smoke.
If present, performs a quick safety check (gitignored, not tracked) and prints
a warning if anything looks off.

Exit codes:
  0 — always (this hook is informational only)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


CONFIG_FILENAME = ".qa-browser.local.json"


def main() -> int:
    cwd = Path.cwd()
    config_path = cwd / CONFIG_FILENAME

    # Quiet exit if there is no indication this project uses qa-browser at all.
    # We only chirp on session start if the user has previously configured.
    if not config_path.exists():
        # First-time user: no config yet. Stay silent — /qa-target will explain.
        return 0

    # Config exists. Run safety checks.
    issues: list[str] = []

    # 1. Is the file tracked by git?
    if _is_git_repo(cwd) and _is_tracked(cwd, CONFIG_FILENAME):
        issues.append(
            f"DANGER: {CONFIG_FILENAME} is tracked by git. Run:\n"
            f"    git rm --cached {CONFIG_FILENAME}\n"
            f"    echo '{CONFIG_FILENAME}' >> .gitignore\n"
            f"    git add .gitignore && git commit -m '[CHORE] gitignore qa-browser credentials'"
        )

    # 2. Is the file listed in .gitignore?
    if _is_git_repo(cwd) and not _is_in_gitignore(cwd, CONFIG_FILENAME):
        issues.append(
            f"WARNING: {CONFIG_FILENAME} is not in .gitignore. Add it:\n"
            f"    echo '{CONFIG_FILENAME}' >> .gitignore"
        )

    # 3. Quick credential / URL sanity (no parsing of secrets)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        target_url = data.get("targetUrl", "")
        markers = data.get("productionMarkers") or ["prod", "production"]
        if target_url and _matches_any(target_url.lower(), [m.lower() for m in markers]):
            issues.append(
                f"WARNING: targetUrl ({target_url}) matches a production marker. "
                f"qa-browser will refuse navigation unless you pass --allow-production."
            )
    except Exception:
        issues.append(f"WARNING: could not parse {CONFIG_FILENAME} (invalid JSON?).")

    if issues:
        print("[qa-browser] safety check found issues:", file=sys.stderr)
        for issue in issues:
            print("  - " + issue, file=sys.stderr)
    # Always exit 0 — this hook is advisory.
    return 0


def _is_git_repo(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"
    except Exception:
        return False


def _is_tracked(path: Path, filename: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", filename],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def _is_in_gitignore(path: Path, filename: str) -> bool:
    gitignore = path / ".gitignore"
    if not gitignore.exists():
        return False
    try:
        contents = gitignore.read_text(encoding="utf-8").splitlines()
        for line in contents:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped == filename or stripped == "/" + filename:
                return True
        return False
    except Exception:
        return False


def _matches_any(haystack: str, needles: list[str]) -> bool:
    return any(n in haystack for n in needles if n)


if __name__ == "__main__":
    sys.exit(main())
