#!/usr/bin/env python3
"""PreToolUse hook: human confirmation for Azure DevOps write tools.

Owns the "ask" half of the write gate (rules/write-gate.md, "Hook-enforced
confirmation"). hooks.json routes ONLY the gated write tools here, so every call
that reaches this script is a write: it emits

    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "ask",
                            "permissionDecisionReason": "<what / where>"}}

and Claude Code shows the human a confirmation prompt with that reason. The
gated tool set lives in rules/write-gate.md (list) and the hooks.json matcher
(enforcement); tests/test_write_confirm.py keeps the two in sync. This script
holds no tool list of its own.

The five tools validated by pre_write_validate.py are NOT routed here.

Stdlib-only. Fail-OPEN (no output, exit 0) on any internal error or after 8s:
the normal Claude Code permission flow then still applies.
"""
import json
import os
import sys
import threading

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# tool_input keys that identify WHERE a write lands, in display order.
_TARGET_KEYS = (
    "project", "repositoryId", "pullRequestId", "threadId", "commentId",
    "workItemId", "id", "ids", "parentId", "pipelineId", "definitionId", "buildId",
    "stageName", "branchName", "sourceRefName", "targetRefName", "wikiIdentifier",
    "path", "team", "planId", "suiteId", "testCaseId",
)
# tool_input keys that describe WHAT changes (status/vote = merge/abandon/approve).
_CHANGE_KEYS = ("status", "vote", "state", "autoComplete", "deleteSourceBranch",
                "mergeStrategy", "action")


def _short(value, limit=80):
    if isinstance(value, (dict, list)):
        if isinstance(value, list) and len(value) > 5:
            text = f"[{len(value)} items]"
        else:
            text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _reason(tool, tool_input):
    action = tool.replace("_", " ")
    parts = []
    for key in _TARGET_KEYS + _CHANGE_KEYS:
        value = tool_input.get(key)
        if value not in (None, "", [], {}):
            parts.append(f"{key}={_short(value)}")
    for key in ("updates", "items", "workItems", "testCases"):
        value = tool_input.get(key)
        if isinstance(value, list) and value:
            parts.append(f"{len(value)} {key}")
            break
    where = "; ".join(parts) if parts else "no target identifiers in the request"
    return (
        f"[DevOps] Azure DevOps WRITE: {action} ({where}). Confirm this is the "
        "change you approved - see rules/write-gate.md."
    )


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except (OSError, ValueError):
        return
    if not isinstance(payload, dict):
        return
    name = str(payload.get("tool_name") or "")
    if "azure-devops__" not in name:
        return
    tool = name.rsplit("azure-devops__", 1)[-1]
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": _reason(tool, tool_input),
    }}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-open: our bug must never block or silently approve an ADO write
    _timer.cancel()
    sys.exit(0)
