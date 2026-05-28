#!/usr/bin/env python3
"""
docs-wiki PreToolUse hook — stray docs/ folder warning.

Intercepts Write / Edit tool calls. If the target file is inside a stray docs
folder (docs/, doc/, documentation/, project-docs/ by default) AND a wiki
is present (sibling clone OR in-repo wiki/ OR adapter-configured wikiPath),
this hook surfaces the conflict per wiki-vs-stray-docs.

Behavior:
  - Edit to existing stray-docs file → WARN (advisory; exit 0).
  - Write to NEW stray-docs file     → BLOCK (exit 2) unless overridden.

Retired folders + exception paths are configured in `.docs-wiki.local.json`
and pass through without warning.

Override mechanism:
  Environment variable DOCS_WIKI_ALLOW_STRAY=1 disables the hook for the
  current session. Use sparingly.

Exit codes:
  0 — allow (not a stray write, OR Edit to existing file, OR override set)
  2 — block (new file in stray docs folder with wiki present)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


CONFIG_FILENAME = ".docs-wiki.local.json"
OVERRIDE_ENV = "DOCS_WIKI_ALLOW_STRAY"
DEFAULT_STRAY_PATTERNS = [r"(^|/)docs/", r"(^|/)doc/", r"(^|/)documentation/", r"(^|/)project-docs/"]
DEFAULT_RETIRED_FOLDERS = ["_archived/", "_legacy/", "_deprecated/", "historical/", "attic/"]


def main() -> int:
    if os.environ.get(OVERRIDE_ENV) == "1":
        return 0  # override active

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # cannot parse → allow

    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}

    file_path = _extract_file_path(tool_name, tool_input)
    if not file_path:
        return 0

    cwd = Path.cwd()
    config = _load_config(cwd) or {}
    stray_patterns = config.get("strayPatterns") or DEFAULT_STRAY_PATTERNS
    retired_folders = config.get("retiredFolders") or DEFAULT_RETIRED_FOLDERS
    exceptions = config.get("exceptions") or []

    file_str = str(file_path).replace("\\", "/")

    # Bail early if exception or retired.
    for ex in exceptions:
        if ex.rstrip("/") in file_str:
            return 0
    for retired in retired_folders:
        if retired.rstrip("/") in file_str:
            return 0

    # Is this a stray-docs path?
    if not _matches_any(file_str, stray_patterns):
        return 0

    # Is a wiki present?
    wiki_path = _detect_wiki(cwd, config)
    if wiki_path is None:
        return 0  # no wiki → skill does not apply

    # Stray + wiki + not exception + not retired = action depends on Write vs Edit.
    is_new_file = tool_name == "Write" and not file_path.exists()

    if is_new_file:
        # Hard refusal.
        print(
            f"[docs-wiki] BLOCKED — new file in stray docs folder with wiki present.\n"
            f"  Target: {file_str}\n"
            f"  Wiki present: {wiki_path}\n"
            f"  Per wiki-vs-stray-docs: creating new content in docs/ creates a second\n"
            f"  source of truth that will drift from the wiki.\n\n"
            f"  Options:\n"
            f"    A) Migrate the content to the wiki (use /wiki-new).\n"
            f"    B) Add this path to the exceptions list (rare; auto-generated content only):\n"
            f"       Edit {CONFIG_FILENAME}: \"exceptions\": [\"docs/api/\"]\n"
            f"    C) Genuinely keep separate (rare). Set the env var to override this session:\n"
            f"       Windows PowerShell:  $env:{OVERRIDE_ENV} = '1'\n"
            f"       bash / zsh:          export {OVERRIDE_ENV}=1\n"
            f"       Then add a knownStrays entry with reason to {CONFIG_FILENAME} so future\n"
            f"       sessions do not re-flag.",
            file=sys.stderr,
        )
        return 2

    # Edit to existing stray-docs file → advisory warning.
    print(
        f"[docs-wiki] WARNING — edit to existing stray docs file.\n"
        f"  Target: {file_str}\n"
        f"  Wiki present: {wiki_path}\n"
        f"  This file lives in a stray docs folder; the wiki is the configured source\n"
        f"  of truth for documentation. Consider migrating the content to the wiki\n"
        f"  (use /wiki-new) OR reconcile via /wiki-drift before editing.\n"
        f"  Edit proceeding (advisory only). Set {OVERRIDE_ENV}=1 to silence this warning\n"
        f"  for the session.",
        file=sys.stderr,
    )
    return 0  # advisory only — let the edit proceed


def _extract_file_path(tool_name: str, tool_input: dict) -> Path | None:
    """Extract the target file path for Write or Edit tool calls."""
    if tool_name not in ("Write", "Edit"):
        return None
    for key in ("file_path", "filePath", "path"):
        v = tool_input.get(key)
        if isinstance(v, str) and v.strip():
            return Path(v.strip())
    return None


def _matches_any(haystack: str, patterns: list[str]) -> bool:
    for pat in patterns:
        try:
            if re.search(pat, haystack):
                return True
        except re.error:
            continue
    return False


def _detect_wiki(cwd: Path, config: dict) -> Path | None:
    """Return the wiki path if a wiki is present; else None."""
    # 1. Adapter-configured wikiPath.
    configured = config.get("wikiPath")
    if configured:
        try:
            p = Path(configured)
            if not p.is_absolute():
                p = (cwd / p).resolve()
            if p.exists():
                return p
        except Exception:
            pass

    # 2. Sibling .wiki clone (GitHub Wiki convention).
    repo_basename = cwd.name
    sibling = cwd.parent / f"{repo_basename}.wiki"
    if sibling.exists() and sibling.is_dir():
        return sibling

    # 3. In-repo wiki/ folder.
    in_repo = cwd / "wiki"
    if in_repo.exists() and in_repo.is_dir():
        # Only treat as wiki if it looks like one (has at least one .md file).
        if any(in_repo.rglob("*.md")):
            return in_repo

    return None


def _load_config(start: Path) -> dict | None:
    for d in (start, *start.parents):
        candidate = d / CONFIG_FILENAME
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                return None
    return None


if __name__ == "__main__":
    sys.exit(main())
