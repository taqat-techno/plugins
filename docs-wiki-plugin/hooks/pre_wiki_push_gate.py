#!/usr/bin/env python3
"""
docs-wiki PreToolUse hook — wiki push approval gate.

Intercepts Bash tool calls. If the command is a `git push` AND the working
directory (or the `-C <path>` argument, or the `--git-dir` argument) points
inside a wiki repo path, BLOCKS the push unless the per-session approval is set.

Wiki repo detection (in priority order):
  1. The command contains `-C <path>` and that path matches a wiki pattern.
  2. The command's cwd matches a wiki pattern.
  3. The command runs in the project root AND the project root contains a configured wiki path.

Wiki patterns (default + adapter-configurable):
  - Path basename ends with `.wiki` (GitHub Wiki sibling clone convention).
  - Path is listed in `.docs-wiki.local.json` under `wikiPath`.

Approval mechanism:
  Environment variable DOCS_WIKI_PUSH_APPROVED=1 grants per-session approval.
  The user must set it deliberately for THIS shell session before the push runs.

Force-push refusal:
  Any `--force` / `-f` / `--force-with-lease` is ALWAYS blocked, even with approval.
  Force-push erases history; the wiki repo's history is the publish record.

Exit codes:
  0 — allow (not a wiki push OR approval set OR not a push at all)
  2 — block (wiki push without approval, or force-push attempted)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path


CONFIG_FILENAME = ".docs-wiki.local.json"
APPROVAL_ENV = "DOCS_WIKI_PUSH_APPROVED"
FORCE_FLAGS = ("--force", "-f", "--force-with-lease")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # cannot parse → do not block (hook is best-effort)

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    command = (tool_input.get("command") or "").strip()
    if not command:
        return 0

    # Only act on git push.
    if not _is_git_push(command):
        return 0

    # Tokenize the command — best-effort; we do not need a full parser.
    try:
        tokens = shlex.split(command, posix=(os.name != "nt"))
    except ValueError:
        tokens = command.split()

    # Resolve the working directory of the git invocation.
    wiki_repo_path = _resolve_git_repo_path(tokens, cwd=Path.cwd())

    # If no -C / --git-dir, fall back to current cwd.
    if wiki_repo_path is None:
        wiki_repo_path = Path.cwd()

    if not _is_wiki_repo(wiki_repo_path):
        return 0  # not a wiki push → allow

    # Wiki push detected.
    if _has_force_flag(tokens):
        print(
            f"[docs-wiki] BLOCKED — wiki force-push refused.\n"
            f"  Repo: {wiki_repo_path}\n"
            f"  Command: {command}\n"
            f"  Per wiki-safe-updates: force-push to the wiki erases published history.\n"
            f"  Use revert + push instead:\n"
            f"      git -C {wiki_repo_path} revert <bad-sha>\n"
            f"      git -C {wiki_repo_path} push   (re-prompt for push approval)",
            file=sys.stderr,
        )
        return 2

    if os.environ.get(APPROVAL_ENV) == "1":
        # Approval present — log to stderr for audit trail; allow.
        print(
            f"[docs-wiki] wiki push ALLOWED — {APPROVAL_ENV}=1 set for this session.\n"
            f"  Repo: {wiki_repo_path}\n"
            f"  Approval is per-session; the next push re-prompts.",
            file=sys.stderr,
        )
        # NOTE: we do NOT auto-unset the env var. The user controls session scope.
        return 0

    print(
        f"[docs-wiki] BLOCKED — wiki push requires explicit per-session approval.\n"
        f"  Repo: {wiki_repo_path}\n"
        f"  Command: {command}\n"
        f"  To approve THIS push (per session, one push):\n"
        f"      Windows PowerShell:  $env:{APPROVAL_ENV} = '1'\n"
        f"      bash / zsh:          export {APPROVAL_ENV}=1\n"
        f"  Then re-run the push.\n"
        f"  The approval lasts for the current shell session only.",
        file=sys.stderr,
    )
    return 2


def _is_git_push(command: str) -> bool:
    """Match `git push`, optionally with -C <path>, --git-dir, etc."""
    return bool(re.search(r"\bgit\b[\s\S]*\bpush\b", command))


def _has_force_flag(tokens: list[str]) -> bool:
    return any(t in FORCE_FLAGS for t in tokens)


def _resolve_git_repo_path(tokens: list[str], cwd: Path) -> Path | None:
    """Extract the target repo path from git invocation flags."""
    # -C <path>
    for i, tok in enumerate(tokens):
        if tok == "-C" and i + 1 < len(tokens):
            candidate = Path(tokens[i + 1])
            if not candidate.is_absolute():
                candidate = (cwd / candidate).resolve()
            return candidate
        if tok.startswith("--git-dir="):
            candidate = Path(tok.split("=", 1)[1])
            if not candidate.is_absolute():
                candidate = (cwd / candidate).resolve()
            # --git-dir points to .git; the repo is its parent.
            return candidate.parent
        if tok == "--git-dir" and i + 1 < len(tokens):
            candidate = Path(tokens[i + 1])
            if not candidate.is_absolute():
                candidate = (cwd / candidate).resolve()
            return candidate.parent
    return None


def _is_wiki_repo(path: Path) -> bool:
    """Detect if a path is a wiki repo."""
    if not path.exists():
        return False

    # Heuristic 1: path basename ends with `.wiki`
    if path.name.endswith(".wiki"):
        return True

    # Heuristic 2: adapter cache lists this path as a wikiPath
    config = _load_config(Path.cwd())
    if config:
        configured = config.get("wikiPath")
        if configured:
            try:
                if Path(configured).resolve() == path.resolve():
                    return True
            except Exception:
                pass

    return False


def _load_config(start: Path) -> dict | None:
    """Walk up from `start` looking for `.docs-wiki.local.json`."""
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
