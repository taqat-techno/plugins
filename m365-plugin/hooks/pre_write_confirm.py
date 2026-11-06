#!/usr/bin/env python3
"""PreToolUse hook: ask the human before the outward-facing Microsoft 365 writes.

hooks.json routes ONLY the tools listed under "confirm" in data/tools.json here (a test keeps the matcher
and the list in step), so every call that reaches this script is one of them: it answers
permissionDecision "ask" with a plain sentence about what is about to happen. Claude Code then shows the
human a confirmation prompt.

The server enforces the real safety (draft -> preview -> digest -> send); this hook adds the human's yes.
Stdlib only. Fails CLOSED: on any internal error it still asks, because the matcher already narrowed the
call to a confirm-gated tool.
"""
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

_WHAT = {
    "email_send_draft": "SEND the email draft {draft_id}. It leaves your mailbox for real and cannot be undone. Check that the recipients, subject and body shown by the preview are right.",
    "calendar_commit": "CREATE the staged calendar event {stage_id}. Invitations are sent to the attendees.",
    "teams_commit": "SEND the staged Teams message {stage_id} now. It is delivered at once and cannot be unsent.",
    "email_discard_draft": "DELETE the draft {draft_id} from your Drafts folder.",
    "m365_setup_save": "SAVE the Microsoft 365 setup (client id {client_id}; token file {refresh_token_file}; secret file {client_secret_file}). Approve only paths you recognise: the plugin will read those files.",
    "email_delete": "MOVE message {message_id} to Deleted Items (recoverable from there).",
    "onedrive_share_link": "CREATE an organization-wide view link for OneDrive item {item_id}.",
}


def _tool_name(raw_name):
    # mcp__plugin_m365_m365__email_send_draft  or  mcp__m365__email_send_draft
    return str(raw_name or "").rsplit("__", 1)[-1]


def main():
    name, tool_input = "", {}
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        name = _tool_name(data.get("tool_name"))
        tool_input = data.get("tool_input") or {}
    except Exception:
        pass
    template = _WHAT.get(name, "make a change in Microsoft 365 that others can see or that cannot be undone.")
    try:
        reason = "Microsoft 365: " + template.format(**{k: str(tool_input.get(k, "-"))[:120] for k in ("draft_id", "stage_id", "message_id", "item_id", "client_id", "refresh_token_file", "client_secret_file")})
    except Exception:
        reason = "Microsoft 365: " + template
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
