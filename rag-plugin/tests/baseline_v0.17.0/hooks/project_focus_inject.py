#!/usr/bin/env python3
"""rag-plugin /project-focus context injector (UserPromptSubmit hook, v0.10.0).

Reads ``~/.claude/rag-plugin/state/project-focus.json`` (v2 schema), resolves
the **effective** focus for the current cwd via:

    workspace > global > none

and injects a system reminder accordingly.

Strict precedence rules (D-028):

  - **Workspace match** — inject the focused project for this cwd.
  - **Global only** — inject the project, BUT label it explicitly as global
    so Claude understands it applies because the user used ``--global``,
    not because it matches the current workspace.
  - **Other-workspace-only** — focus exists for a different workspace; this
    cwd has no focus and no global. Inject a NEUTRAL notice that does NOT
    leak the other project's name. Claude must NOT use foreign focus.
  - **None** — silent-pass.

Composes alongside ``prompt_retrieval_reminder.py`` — Claude Code supports
multiple UserPromptSubmit hooks; both can inject independently.

Hook contract:
  - Reads stdin JSON (Claude Code UserPromptSubmit payload). Discarded.
  - Reads the local state file by importing the script's loader so v1->v2
    migration runs automatically.
  - On no state / disabled state / any error: silent-pass (no output).
  - Exit 0 in all cases. Never blocks, never denies.

Privacy:
  - Never reads or persists the user's prompt.
  - Never logs.
  - State file only.

Override for tests / harnesses:
  - ``$RAG_PLUGIN_FOCUS_STATE_FILE`` overrides the state file path. Used by
    ``test_project_focus.py`` to drive the hook with synthetic state files.

Python 3 stdlib only.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

HOOK_VERSION = "0.10.0"
DEFAULT_STATE_FILE = Path.home() / ".claude" / "rag-plugin" / "state" / "project-focus.json"


def _silent() -> None:
    sys.exit(0)


def _state_file() -> Path:
    override = os.environ.get("RAG_PLUGIN_FOCUS_STATE_FILE")
    if override:
        return Path(override)
    return DEFAULT_STATE_FILE


def _load_focus_engine(state_file: Path):
    """Load project_focus.py with STATE_FILE pointed at our state path.

    Importing the script gives us _norm, resolve_workspace_key,
    resolve_effective_focus, read_state, and the migration logic — single
    source of truth.
    """
    script = Path(__file__).resolve().parent.parent / "scripts" / "project_focus.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("rag_plugin_focus_engine", script)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rag_plugin_focus_engine"] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop("rag_plugin_focus_engine", None)
        return None
    # Patch state-file paths so reads/migration target the chosen file.
    try:
        mod.STATE_FILE = state_file
        mod.STATE_DIR = state_file.parent
    except Exception:
        return None
    return mod


def _build_workspace_context(record: dict[str, Any]) -> str:
    name = str(record.get("project_name", "")).strip()
    path = str(record.get("project_path", "")).strip()
    method = str(record.get("match_method", "unknown"))
    warning = record.get("warning", "")

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
        f"Match method: {method}. To clear: /rag:project-focus clear. "
        f"To inspect: /rag:project-focus status.",
    ]
    if warning:
        parts.append("")
        parts.append(f"WARNING (from focus state): {warning}")
    return "\n".join(parts)


def _build_global_context(record: dict[str, Any]) -> str:
    name = str(record.get("project_name", "")).strip()
    path = str(record.get("project_path", "")).strip()
    method = str(record.get("match_method", "manual"))
    warning = record.get("warning", "")

    parts: list[str] = [
        f"REMINDER (rag-plugin v{HOOK_VERSION} project-focus hook):",
        "",
        f"EXPLICIT GLOBAL FOCUS is ACTIVE — focused project: `{name}`"
        + (f" at `{path}`" if path else "") + ".",
        "",
        "This focus applies because the user explicitly ran "
        "`/rag:project-focus set --global <name>`. It does NOT match the current "
        "working directory; it is a deliberate user-level override that fires whenever "
        "no workspace-specific focus is set for the current cwd.",
        "",
        "When calling `search_knowledge_base` for project-specific questions:",
        f"  1. If the tool supports a project filter parameter, pass it: project=\"{name}\".",
        "  2. If not, post-filter the results by project metadata (source / path / name) and "
        f"keep only entries that match `{name}`"
        + (f" or are under `{path}`" if path else "") + ".",
        "  3. If filtering cannot be guaranteed from the response shape, WARN the user that "
        "strict focus could not be technically enforced for this query.",
        "",
        "Cross-project retrieval is allowed only when the user explicitly asks "
        "(e.g. \"compare across projects\", \"all projects\").",
        "",
        f"Source: explicit --global override. Match method: {method}. "
        "To clear: /rag:project-focus clear --global. "
        "To set workspace-specific focus instead: /rag:project-focus.",
    ]
    if warning:
        parts.append("")
        parts.append(f"WARNING (from focus state): {warning}")
    return "\n".join(parts)


def _build_other_workspace_notice() -> str:
    """Neutral notice when other-workspace focus exists but none applies here.

    Must NOT leak the other project's name (could cause Claude to use it as
    a project= filter). Must explicitly state focus is NOT applied here.
    """
    return "\n".join([
        f"REMINDER (rag-plugin v{HOOK_VERSION} project-focus hook):",
        "",
        "Project focus exists for another workspace, but it is NOT applied here.",
        "",
        "The current working directory has no workspace-specific focus and no explicit "
        "global focus. Do NOT carry over the other workspace's project filter into searches "
        "from this directory — it would leak unrelated project context. Treat retrieval as "
        "unfocused unless and until the user sets focus for this workspace.",
        "",
        "To inspect: /rag:project-focus status. "
        "To set focus for this workspace: /rag:project-focus.",
    ])


def main() -> None:
    try:
        sys.stdin.read()
    except Exception:
        _silent()
        return

    state_file = _state_file()
    if not state_file.exists():
        _silent()
        return

    engine = _load_focus_engine(state_file)
    if engine is None:
        _silent()
        return

    try:
        bundle = engine.read_state()
    except Exception:
        _silent()
        return

    if not isinstance(bundle, dict):
        _silent()
        return

    try:
        cwd = Path.cwd()
        workspace_key = engine.resolve_workspace_key(cwd)
        effective, source = engine.resolve_effective_focus(bundle, workspace_key)
    except Exception:
        _silent()
        return

    if source == "workspace" and effective:
        context = _build_workspace_context(effective)
    elif source == "global" and effective:
        context = _build_global_context(effective)
    elif source == "other-workspace-only":
        context = _build_other_workspace_notice()
    else:
        _silent()
        return

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    try:
        sys.stdout.write(json.dumps(output))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
