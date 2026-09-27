#!/usr/bin/env python3
"""PreToolUse hook: validation context for Azure DevOps write operations.

Reads the PreToolUse JSON payload on stdin (tool_name + tool_input).

  Exit 2 + stderr  hard block; Claude sees stderr as the denial reason. Used only
                   for clear violations detectable without the model:
                     * non-PM/Lead moving a work item to Closed/Removed
                     * a developer role creating a Bug
                     * a comment with unresolved @mentions
  Exit 0 + JSON    soft reminder as hookSpecificOutput.additionalContext. Plain
                   stdout/stderr from an exit-0 PreToolUse hook never reaches the
                   model, and additionalContext without hookEventName fails schema
                   validation, so both keys are always emitted. No permissionDecision
                   is set: the normal permission flow is untouched.

Design: hooks inject REMINDERS. The LLM + rules/ + data/ do the actual validation.

Ported from the former bash hook (pre-write-validate.sh). The target state is
read from the parsed JSON-Patch update whose path is /fields/System.State; the
other fields keep the bash regexes over the raw payload text. Stdlib-only.
Fail-OPEN on any error or after 8 seconds.
"""
import json
import os
import re
import sys
import threading
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

# Fail-OPEN after 8s: a hang must not freeze every ADO write.
_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _first_string_field(raw, key):
    """First `"key": "value"` in the raw payload, or "" (the bash grep|head -1)."""
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', raw)
    return m.group(1) if m else ""


def _profile_path():
    return Path.home() / ".claude" / "devops.md"


def _user_role(profile):
    """Role from the profile: YAML `role:` line first, else the Markdown table row."""
    try:
        lines = profile.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in lines:
        if line.startswith("role:"):
            role = line[len("role:"):].strip().replace('"', "")
            if role:
                return role
            break
    for line in lines:
        if "primary role" in line.lower():
            role = re.sub(r".*\|\s*\*\*Primary Role\*\*\s*\|\s*", "", line)
            return re.sub(r"\s*\|.*", "", role).strip()
    return ""


def _advise(text):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}))


def _block(text):
    print(text, file=sys.stderr)
    _timer.cancel()
    sys.exit(2)


def _target_state(raw):
    """Value of the update whose JSON-Patch path is System.State, or "".

    wit_update_work_item sends updates=[{op, path: "/fields/System.State", value}].
    The bash hook grepped for a quoted "System.State" token and then took the
    first "value" in the payload, so it never matched the real path and would
    have read the wrong value whenever another field was updated first.
    """
    try:
        updates = (json.loads(raw).get("tool_input") or {}).get("updates") or []
    except (ValueError, AttributeError):
        return ""
    if not isinstance(updates, list):
        return ""
    for upd in updates:
        if not isinstance(upd, dict):
            continue
        path = str(upd.get("path") or "").strip().lower()
        if path.rstrip("/").endswith("system.state"):
            value = upd.get("value")
            return value.strip() if isinstance(value, str) else ""
    return ""


def _update_work_item(raw, profile):
    target_state = _target_state(raw)
    if not target_state:
        return

    # HARD BLOCK: Close/Remove restriction (universalRules).
    if target_state in ("Closed", "Removed") and profile.is_file():
        role = _user_role(profile)
        if role not in ("pm", "lead"):
            _block(
                f"[DevOps] BLOCKED: Role '{role}' cannot transition to '{target_state}'. "
                "Only PM/Lead can close or remove work items. See data/state_machine.json "
                "universalRules."
            )

    _advise(
        f"[DevOps] State change to '{target_state}' detected. Follow data/state_machine.json "
        "pre-flight: check role permissions, required fields, and confirm via "
        "rules/write-gate.md."
    )


def _create_work_item(raw, profile):
    wi_type = _first_string_field(raw, "workItemType")

    # HARD BLOCK: Bug creation authority (developers cannot create bugs).
    if wi_type == "Bug" and profile.is_file():
        role = _user_role(profile)
        if role in ("developer", "backend", "fullstack", "frontend", "devops"):
            _block(
                f"[DevOps] BLOCKED: Role '{role}' cannot create Bugs. Create a "
                "[Dev-Internal-fix] Task instead. See data/state_machine.json "
                "businessRules.bugCreationAuthority."
            )

    if wi_type in ("Task", "Bug", "Enhancement"):
        parent = "User Story/PBI"
    elif wi_type in ("User Story", "Product Backlog Item"):
        parent = "Feature"
    elif wi_type == "Feature":
        parent = "Epic"
    else:
        return
    _advise(
        f"[DevOps] Creating {wi_type} - ensure parent {parent} is linked per "
        "data/hierarchy_rules.json."
    )


def _add_comment(raw):
    # HARD BLOCK: unresolved @mentions.
    if re.search(r"@[a-zA-Z]", raw) and "data-vss-mention" not in raw:
        _block(
            "[DevOps] BLOCKED: Unresolved @mentions detected. Resolve to GUIDs and use HTML "
            "format before posting. See rules/guards.md Guard 2."
        )


def _create_pull_request(raw):
    repo_id = _first_string_field(raw, "repositoryId")
    if repo_id and not _GUID_RE.match(repo_id):
        _advise(
            f"[DevOps] repositoryId '{repo_id}' is not a GUID. Resolve per "
            "rules/guards.md Guard 3."
        )


def main():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    except OSError:
        return
    # Namespace-agnostic: plugin tools are "mcp__plugin_devops_azure-devops__<tool>",
    # legacy ones "mcp__azure-devops__<tool>". Keep only the bare tool segment.
    tool = _first_string_field(raw, "tool_name").rsplit("azure-devops__", 1)[-1]
    profile = _profile_path()

    if tool == "wit_update_work_item":
        _update_work_item(raw, profile)
    elif tool == "wit_create_work_item":
        _create_work_item(raw, profile)
    elif tool == "wit_add_work_item_comment":
        _add_comment(raw)
    elif tool == "repo_create_pull_request":
        _create_pull_request(raw)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass  # fail-open: our bug must never block an ADO write
    _timer.cancel()
    sys.exit(0)
