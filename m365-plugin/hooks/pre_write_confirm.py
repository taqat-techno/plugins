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
import os
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
    "m365_setup_save": "SAVE the Microsoft 365 setup: client id {client_id}, tenant {tenant}, permissions mode {scope_mode}, sign-in method {auth_mode}, sign-in redirect {redirect_uri} (a dash means unchanged). Approve only values your admin gave you.",
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


def _out(decision, reason, updated=None):
    spec = {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": "Microsoft 365: " + reason}
    if updated is not None:
        spec["updatedInput"] = updated
    print(json.dumps({"hookSpecificOutput": spec}, ensure_ascii=False))
    return 0


def _attach(data, tool_input):
    """email_add_attachment: show the exact file. For a pasted image, save it first and hand its path to the tool."""
    draft = tool_input.get("draft_id", "-")
    path = tool_input.get("path")
    if len(str(draft)) > _LIMIT or len(str(path or "")) > 1000:
        return _out("deny", "refused, an argument is too long to show you in full.")
    if not path and tool_input.get("chat_image") is not None:
        try:
            from chat_image import save_pasted_image
            saved, media_type, size = save_pasted_image(data.get("transcript_path"), data.get("session_id"), tool_input.get("chat_image"))
        except Exception as e:  # nothing attached; Claude is told why and can ask the user
            msg = str(e) if e.__class__.__name__ == "ChatImageError" else "the pasted image could not be saved"
            return _out("deny", f"no pasted image was attached: {_show(msg)}. Ask the user to paste it again or give a file path.")
        updated = dict(tool_input)
        updated["path"] = saved
        n = _show(tool_input.get("chat_image"))
        if not updated.get("name"):
            updated["name"] = f"screenshot-{n}{os.path.splitext(saved)[1]}"
        return _out("ask", f"ATTACH the image you pasted into this chat (#{n} counting back from the latest, {media_type}, "
                           f"{size // 1024 or 1} KB) to email draft {_show(draft)} as {_show(updated['name'])}. Nothing is sent yet.", updated)
    real = _real_path(path)
    updated = None
    shown = _show(path or "-")
    if real and os.path.normcase(real) != os.path.normcase(os.path.abspath(path)):
        # A link, junction or short name: show where it really points, and hand that exact path on, so the file the
        # person approves is the file the server reads (re-pointing the link afterwards changes nothing).
        shown = f"{_show(real)} (you gave {_show(path)}, which points there)"
    if real:
        updated = dict(tool_input)
        updated["path"] = real
    return _out("ask", f"ATTACH the file {shown} from this computer to email draft {_show(draft)}"
                       f"{(' as ' + _show(tool_input['name'])) if tool_input.get('name') else ''}. "
                       "Whoever receives the email gets this file. Nothing is sent yet.", updated)


def _real_path(path):
    """The fully resolved path of a local file, or None. Never touches network, device or stream paths: resolving
    \\\\host\\share on Windows would make the machine offer its login to that host. The server refuses those anyway."""
    p = str(path or "")
    if not p or not os.path.isabs(p) or p[:2] in ("\\\\", "//", "\\/", "/\\"):
        return None
    if os.name == "nt" and (len(p) < 3 or p[1] != ":" or p[2] not in "\\/" or ":" in p[2:]):
        return None
    try:
        real = os.path.realpath(p, strict=True) if sys.version_info >= (3, 10) else os.path.realpath(p)
    except (OSError, ValueError):
        return None
    if real[:2] in ("\\\\", "//"):
        # a link to a network share, or an extended-length form: keep the given path; the server decides
        return None if not real.startswith("\\\\?\\") else _strip_ext(real)
    return real if os.path.isfile(real) else None


def _strip_ext(real):
    rest = real[4:]
    return rest if len(rest) > 2 and rest[1] == ":" else None


def main():
    name, tool_input, data = "", {}, {}
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        name = _tool_name(data.get("tool_name"))
        tool_input = data.get("tool_input") or {}
    except Exception:
        data = data if isinstance(data, dict) else {}
    if name == "email_add_attachment":
        return _attach(data, tool_input)
    template = _WHAT.get(name, "make a change in Microsoft 365 that others can see or that cannot be undone.")
    keys = ("draft_id", "stage_id", "message_id", "item_id", "client_id", "tenant", "scope_mode", "auth_mode", "redirect_uri")
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
