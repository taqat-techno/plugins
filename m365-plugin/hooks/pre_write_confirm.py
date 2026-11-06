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
    "m365_setup_save": "SAVE the Microsoft 365 setup: client id {client_id}, tenant {tenant}, permissions mode {scope_mode}, sign-in method {auth_mode} (a dash means unchanged). Approve only values your admin gave you.",
    "email_delete": "MOVE message {message_id} to Deleted Items (recoverable from there).",
    "onedrive_share_link": "CREATE an organization-wide view link for OneDrive item {item_id}.",
}


_LIMIT = 200


def _show(value):
    """The value exactly as it will act, with control characters made visible (no newline can fake a second line)."""
    text = str(value)
    return "".join(ch if ch.isprintable() else "?" for ch in text)


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
    keys = ("draft_id", "stage_id", "message_id", "item_id", "client_id", "tenant", "scope_mode", "auth_mode")
    values = {k: tool_input.get(k, "-") for k in keys}
    if any(len(str(v)) > _LIMIT for v in values.values()):
        # A value too long to show in full could hide what the call really does: do not offer a prompt, refuse.
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                  "permissionDecisionReason": "Microsoft 365: refused, an argument is too long to show you in full."}}, ensure_ascii=False))
        return 0
    try:
        reason = "Microsoft 365: " + template.format(**{k: _show(v) for k, v in values.items()})
    except Exception:
        reason = "Microsoft 365: " + template
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
