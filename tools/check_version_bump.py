#!/usr/bin/env python3
"""Fail when a plugin changed between two commits without a version bump and CHANGELOG entry.

Claude Code's updater detects new plugin code only through the `version` in plugin.json,
so a change without a bump never reaches users who already installed the plugin.

    python tools/check_version_bump.py <base-ref> [<head-ref>]   # head defaults to HEAD
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, check=True,
                          text=True, encoding="utf-8").stdout


def version_at(ref: str, plugin: str) -> str | None:
    try:
        return json.loads(git("show", f"{ref}:{plugin}/.claude-plugin/plugin.json")).get("version")
    except subprocess.CalledProcessError:
        return None


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    base, head = argv[0], (argv[1] if len(argv) > 1 else "HEAD")
    if set(base) == {"0"}:  # first push of a branch: nothing to compare against
        print("version-bump check: no base commit, skipped")
        return 0
    changed = git("diff", "--name-only", f"{base}..{head}").split()
    plugins = sorted({p.split("/")[0] for p in changed if p.split("/")[0].endswith("-plugin")})
    problems = []
    for plugin in plugins:
        if not (ROOT / plugin / ".claude-plugin" / "plugin.json").is_file():
            continue  # plugin removed or renamed away in this range
        old, new = version_at(base, plugin), version_at(head, plugin)
        if old is not None and old == new:
            problems.append(f"{plugin}: files changed but plugin.json version is still {new}")
            continue
        changelog = ROOT / plugin / "CHANGELOG.md"
        if new and (not changelog.is_file() or f"## [{new}]" not in changelog.read_text(encoding="utf-8")):
            problems.append(f"{plugin}: version {new} has no '## [{new}]' entry in CHANGELOG.md")
    if problems:
        print("version-bump check failed:")
        for p in problems:
            print("  " + p)
        return 1
    print(f"version-bump check: ok ({len(plugins)} plugin(s) changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
