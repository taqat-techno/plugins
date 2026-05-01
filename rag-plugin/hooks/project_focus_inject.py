#!/usr/bin/env python3
"""rag-plugin /project-focus context injector (UserPromptSubmit hook, v0.9.0).

If `~/.claude/rag-plugin/state/project-focus.json` exists with `enabled: true`,
this hook injects a short system reminder telling Claude to scope every
`search_knowledge_base` call to the focused project — by passing a project
filter parameter when supported, or by post-filtering results by project
metadata when not.

Composes alongside `prompt_retrieval_reminder.py` — Claude Code supports
multiple UserPromptSubmit hooks; both can inject independently.

Hook contract:
  - Reads stdin JSON (Claude Code UserPromptSubmit payload).
  - Reads the local state file. No HTTP, no MCP.
  - On enabled state: emits `hookSpecificOutput.additionalContext`.
  - On no state / disabled state / any error: silent-pass (no output).
  - Exit 0 in all cases.

Privacy:
  - Never reads or persists the user's prompt.
  - Never logs anywhere.
  - Reads state file only.

Python 3 stdlib only.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HOOK_VERSION = "0.9.0"
STATE_FILE = Path.home() / ".claude" / "rag-plugin" / "state" / "project-focus.json"


def _silent() -> None:
    sys.exit(0)


def main() -> None:
    # We don't actually need the prompt; just consume stdin so the harness is happy.
    try:
        sys.stdin.read()
    except Exception:
        _silent()
        return

    if not STATE_FILE.exists():
        _silent()
        return

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        _silent()
        return

    if not isinstance(state, dict) or not state.get("enabled"):
        _silent()
        return

    name = str(state.get("project_name", "")).strip()
    path = str(state.get("project_path", "")).strip()
    method = str(state.get("match_method", "unknown"))
    warning = state.get("warning", "")

    if not name:
        _silent()
        return

    parts: list[str] = [
        f"REMINDER (rag-plugin v{HOOK_VERSION} project-focus hook):",
        "",
        f"/project-focus is ACTIVE — strict mode. Focused project: `{name}`"
        + (f" at `{path}`" if path else "") + ".",
        "",
        "When calling `search_knowledge_base` for project-specific questions:",
        f"  1. If the tool supports a project filter parameter, pass it: project=\"{name}\".",
        "  2. If not, post-filter the results by project metadata (source / path / name) and "
        f"keep only entries that match `{name}`"
        + (f" or are under `{path}`" if path else "") + ".",
        "  3. If filtering cannot be guaranteed from the response shape, WARN the user that "
        "strict focus could not be technically enforced for this query.",
        "",
        "If no focused-project results are found, say so. Do NOT silently fall back to other "
        "projects. Cross-project retrieval is allowed only when the user explicitly asks "
        "(e.g. \"compare across projects\", \"global knowledge\", \"all projects\").",
        "",
        f"Match method: {method}. To clear: /project-focus clear. To inspect: /project-focus status.",
    ]
    if warning:
        parts.append("")
        parts.append(f"WARNING (from focus state): {warning}")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(parts),
        }
    }
    try:
        sys.stdout.write(json.dumps(output))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
