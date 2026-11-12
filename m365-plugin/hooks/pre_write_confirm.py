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
    "onedrive_delete": "MOVE \"{name}\" (OneDrive item {item_id}, and everything in it if it is a folder) to your OneDrive recycle bin. It can be restored from there for a while.",
    "teams_delete_message": "DELETE your Teams message {message_id} in chat {chat_id}. The others in the chat will see that a message was deleted.",
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


_TOOL = {"name": ""}
# The only actions chat mode may approve without a click: the previewed sends (a digest the server checks covers exactly
# what goes out), and the two steps that only PREPARE such a send with a file: teams_stage and email_add_attachment send
# nothing themselves, and every file they add is listed in the send preview the user approves (the digest covers it, and
# a file changed afterwards is refused). Everything else (share, upload, delete, setup, a move into a shared folder)
# keeps the click prompt in every mode. Refusals ("deny") are never turned into an allow.
_CHAT_APPROVABLE = {"email_send_draft", "teams_commit", "calendar_commit", "teams_stage", "email_add_attachment"}


def _confirm_mode():
    """'chat' or 'always'. Read ONLY from the Claude Code plugin setting "Approve sends in the chat" (a yes/no switch),
    which Claude Code exports to hook processes as CLAUDE_PLUGIN_OPTION_M365_CHAT_APPROVAL and which the person sets in
    Claude Code's own settings screen (the older text option m365_confirm_mode = chat is still honoured). Never from a
    file or a command the assistant could write or run itself (settings.json, cli.mjs, an env var): the assistant must
    not be able to switch its own confirmation off. Anything else means 'always'."""
    switch = os.environ.get("CLAUDE_PLUGIN_OPTION_M365_CHAT_APPROVAL", "").strip().lower()
    legacy = os.environ.get("CLAUDE_PLUGIN_OPTION_M365_CONFIRM_MODE", "").strip().lower()  # the 0.13.0/0.13.1 text field
    return "chat" if switch in ("true", "1", "yes", "on") or legacy == "chat" else "always"


def _out(decision, reason, updated=None):
    if decision == "ask" and _TOOL["name"] in _CHAT_APPROVABLE and _confirm_mode() == "chat":
        # The user approved the preview in the chat: no click prompt. The server's preview / digest gates still apply,
        # and every refusal ("deny") stays a refusal.
        decision, reason = "allow", "approved in the chat (confirm mode: chat). " + reason
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
    if not real:
        # Only a path that resolves to an existing local file is offered for approval, and the tool then receives that
        # resolved path, never the raw text: the person never approves one spelling while the server reads another.
        return _out("deny", f"nothing attached: {_show(path or '-')} is not an existing local file (network paths, "
                            "spaces around the path and hidden characters are refused). Ask the user for the plain full path.")
    shown = _show(real)
    if os.path.normcase(real) != os.path.normcase(os.path.abspath(path)):
        # A link, junction or short name: show where it really points (re-pointing the link afterwards changes nothing).
        shown = f"{_show(real)} (you gave {_show(path)}, which points there)"
    updated = dict(tool_input)
    updated["path"] = real
    return _out("ask", f"ATTACH the file {shown} from this computer to email draft {_show(draft)}"
                       f"{(' as ' + _show(tool_input['name'])) if tool_input.get('name') else ''}. "
                       "Whoever receives the email gets this file. Nothing is sent yet.", updated)


def _real_path(path):
    """The fully resolved path of a local file, or None. Never touches network, device or stream paths: resolving
    \\\\host\\share on Windows would make the machine offer its login to that host. The server refuses those anyway."""
    p = str(path or "")
    if not p or p != p.strip() or not p.isprintable() or not os.path.isabs(p) or p[:2] in ("\\\\", "//", "\\/", "/\\"):
        return None
    if any(c in p for c in "​‌‍‎‏‪‫‬‭‮⁦⁧⁨⁩"):
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


def _teams_stage(data, tool_input):
    """teams_stage: without attachments this hook stays silent (staging sends nothing). With attachments it saves pasted
    images, resolves every path to the real file, shows them, and hands the resolved paths to the tool."""
    items = tool_input.get("attachments")
    if not items:
        return 0
    if not isinstance(items, list) or len(items) > 10 or len(str(tool_input.get("chat_id", ""))) > 1024:
        return _out("deny", "refused, the attachments could not be shown to you in full.")
    resolved, lines = [], []
    for item in items:
        if not isinstance(item, dict):
            return _out("deny", "refused, an attachment is not in the expected form.")
        new = dict(item)
        path = item.get("path")
        if len(str(path or "")) > 1000 or len(str(item.get("name") or "")) > _LIMIT:
            return _out("deny", "refused, an argument is too long to show you in full.")
        if not path and item.get("chat_image") is not None:
            try:
                from chat_image import save_pasted_image
                saved, media_type, size = save_pasted_image(data.get("transcript_path"), data.get("session_id"), item.get("chat_image"))
            except Exception as e:
                msg = str(e) if e.__class__.__name__ == "ChatImageError" else "the pasted image could not be saved"
                return _out("deny", f"nothing staged: {_show(msg)}. Ask the user to paste it again or give a file path.")
            n = _show(item.get("chat_image"))
            new["path"] = saved
            new.pop("chat_image", None)
            if not new.get("name"):
                new["name"] = f"screenshot-{n}{os.path.splitext(saved)[1]}"
            lines.append(f"the image you pasted into this chat (#{n} counting back, {media_type}, {size // 1024 or 1} KB) as {_show(new['name'])}")
        else:
            real = _real_path(path)
            if not real:
                return _out("deny", f"nothing staged: {_show(path or '-')} is not an existing local file (network paths, "
                                    "spaces around the path and hidden characters are refused). Ask the user for the plain full path.")
            new["path"] = real
            shown = _show(real)
            if os.path.normcase(real) != os.path.normcase(os.path.abspath(path)):
                shown = f"{_show(real)} (you gave {_show(path)}, which points there)"
            lines.append(shown + (f" as {_show(item['name'])}" if item.get("name") else ""))
        resolved.append(new)
    updated = dict(tool_input)
    updated["attachments"] = resolved
    return _out("ask", "PREPARE a Teams message with " + ("this file: " if len(lines) == 1 else f"these {len(lines)} files: ")
                + "; ".join(lines) + ". Nothing is uploaded or sent yet: you will see the chat members and confirm again before it goes.", updated)


def _upload(data, tool_input):
    """onedrive_upload: show the exact file (saving a pasted image first) and the OneDrive folder; pass the real path on."""
    path, folder = tool_input.get("path"), tool_input.get("folder_path") or ""
    if len(str(path or "")) > 1000 or len(str(folder)) > 400 or len(str(tool_input.get("name") or "")) > _LIMIT:
        return _out("deny", "refused, an argument is too long to show you in full.")
    updated = dict(tool_input)
    if not path and tool_input.get("chat_image") is not None:
        try:
            from chat_image import save_pasted_image
            saved, media_type, size = save_pasted_image(data.get("transcript_path"), data.get("session_id"), tool_input.get("chat_image"))
        except Exception as e:
            msg = str(e) if e.__class__.__name__ == "ChatImageError" else "the pasted image could not be saved"
            return _out("deny", f"nothing uploaded: {_show(msg)}. Ask the user to paste it again or give a file path.")
        n = _show(tool_input.get("chat_image"))
        updated["path"] = saved
        updated.pop("chat_image", None)
        if not updated.get("name"):
            updated["name"] = f"screenshot-{n}{os.path.splitext(saved)[1]}"
        what = f"the image you pasted into this chat (#{n} counting back, {media_type}, {size // 1024 or 1} KB)"
    else:
        real = _real_path(path)
        if not real:
            return _out("deny", f"nothing uploaded: {_show(path or '-')} is not an existing local file (network paths, "
                                "spaces around the path and hidden characters are refused). Ask the user for the plain full path.")
        updated["path"] = real
        what = f"the file {_show(real)}"
        if os.path.normcase(real) != os.path.normcase(os.path.abspath(path)):
            what += f" (you gave {_show(path)}, which points there)"
    where = _show(folder.strip("/\\")) or "the top level"
    as_name = f" as {_show(updated['name'])}" if updated.get("name") else ""
    if tool_input.get("into_shared_folder") is True:
        return _out("ask", f"UPLOAD {what} to your OneDrive, folder {where}{as_name}. That folder is ALREADY SHARED: the people who can "
                           "open it will be able to open this file too.", updated)
    return _out("ask", f"UPLOAD {what} to your OneDrive, folder {where}{as_name}. It stays private to you (a shared folder is refused).", updated)


def _move(tool_input):
    """onedrive_move: silent (an ordinary, reversible move) unless it puts the item into a folder others can open."""
    if tool_input.get("into_shared_folder") is not True:
        return 0
    if len(str(tool_input.get("item_id", ""))) > _LIMIT or len(str(tool_input.get("to_folder_path") or "")) > 400:
        return _out("deny", "refused, an argument is too long to show you in full.")
    dest = _show(str(tool_input.get("to_folder_path") or "").strip("/\\")) or "the top level"
    return _out("ask", f"MOVE OneDrive item {_show(tool_input.get('item_id', '-'))} into {dest}, a folder that is ALREADY SHARED: "
                       "the people who can open that folder will be able to open this item too.")


def _share(tool_input):
    """onedrive_share_with: every address and the role, in full."""
    emails, role = tool_input.get("emails"), tool_input.get("role") or "read"
    if not isinstance(emails, list) or not emails or len(emails) > 25 or any(len(str(e)) > 254 for e in emails) \
            or len(str(tool_input.get("item_id", ""))) > _LIMIT or len(str(tool_input.get("name") or "")) > _LIMIT or len(str(tool_input.get("message") or "")) > 500:
        return _out("deny", "refused, the people or the item could not be shown to you in full.")
    who = ", ".join(_show(e) for e in emails)
    access = "EDIT (change and delete)" if role == "edit" else "VIEW"
    mail = " Microsoft emails each of them an invitation" + (f" with the note: {_show(tool_input['message'])}" if tool_input.get("message") else "") + "." if tool_input.get("notify") is True else " No invitation email is sent."
    outside = " This INCLUDES PEOPLE OUTSIDE YOUR ORGANIZATION." if tool_input.get("allow_outside") is True else ""
    return _out("ask", f"SHARE \"{_show(tool_input.get('name') or '-')}\" (OneDrive item {_show(tool_input.get('item_id', '-'))}) with {who}, "
                       f"who can {access} it after signing in.{outside}{mail}")


def _staged_calendar_change(stage_id):
    """What a staged calendar change will do, read from the plugin's own staging file. None when unknown."""
    try:
        from chat_image import m365_home
        with open(m365_home() / "staged.json", "r", encoding="utf-8") as fh:
            p = (json.load(fh).get(str(stage_id)) or {}).get("payload") or {}
        action = p.get("action")
        sh = p.get("shown") or {}
        series = {"series": ", a RECURRING SERIES (every occurrence)", "occurrence": ", one occurrence of a recurring series"}.get(sh.get("series"), "")
        who = f", organizer {_show(sh['organizer'])}" if sh.get("organizer") else ""
        ev = (f"\"{_show(sh.get('subject', '?'))}\" ({_show(sh.get('start', '?'))} - {_show(sh.get('end', '?'))} UTC{series}{who}, "
              f"{int(sh.get('attendees') or 0)} attendee(s); staged as {_show(stage_id)})")
        if action == "change":
            ch = p.get("patch") or {}
            what = []
            if ch.get("start"):
                what.append(f"move it to {_show(ch['start'])} - {_show(ch['end'])} UTC")
            if "subject" in ch:
                what.append(f"rename it to {_show(ch['subject'])}")
            if "location" in ch:
                what.append(f"set the location to {_show(ch['location']) or '(none)'}")
            return f"CHANGE calendar event {ev}: " + "; ".join(what) + ". The attendees, if any, get the updated invitation."
        if action == "cancel":
            if p.get("mode") == "delete":
                return f"REMOVE {ev} from your calendar, to Deleted Items (it has no attendees)."
            return f"CANCEL {ev} for EVERYONE: every attendee gets a cancellation" + (f" with the comment: {_show(p['comment'])}" if p.get("comment") else "") + "."
        if action in ("accept", "tentative", "decline"):
            word = {"accept": "ACCEPT", "tentative": "TENTATIVELY ACCEPT", "decline": "DECLINE"}[action]
            if not p.get("send_response"):
                return f"{word} the invitation {ev} silently (the organizer is not told)."
            extra = (f" with the comment: {_show(p['comment'])}" if p.get("comment") else "")
            if p.get("propose"):
                extra += f", proposing {_show(p['propose']['start'])} - {_show(p['propose']['end'])} UTC instead"
            return f"{word} the invitation {ev} and tell the organizer{extra}."
    except Exception:
        return None
    return None


def _staged_files(stage_id):
    """What a staged Teams message will send besides text, read from the plugin's own staging file. '' when none or unknown."""
    try:
        from chat_image import m365_home
        with open(m365_home() / "staged.json", "r", encoding="utf-8") as fh:
            payload = (json.load(fh).get(str(stage_id)) or {}).get("payload") or {}
        files = payload.get("files") or []
        where = ""
        if payload.get("edit"):
            return " It REPLACES the text of your earlier message in that chat."
        if payload.get("new_chat"):
            nc = payload["new_chat"]
            who_to = ", ".join(_show(m.get("email")) for m in (nc.get("members") or [])[:25])
            where = (" It opens your 1:1 chat with " if nc.get("kind") == "oneOnOne" else " It STARTS A NEW group chat with ") + who_to + "."
        elif payload.get("channel"):
            where = " It is posted in a team CHANNEL" + (" thread" if payload["channel"].get("reply_to") else "") + ", visible to everyone in that channel."
        ment = payload.get("mentions") or []
        if ment:
            where += " It @mentions: " + ", ".join(_show(m.get("email")) for m in ment[:20]) + "."
        if not files:
            return where
        names = ", ".join(f"{_show(f.get('name'))} ({int(f.get('size') or 0) // 1024 or 1} KB, from {_show(f.get('path'))})" for f in files[:10])
        share = payload.get("share_with") or []
        who = (" Uploaded files go to your OneDrive and are shared read-only with: " + ", ".join(_show(e) for e in share[:25])
               + (f" and {len(share) - 25} more" if len(share) > 25 else "") + ".") if share else ""
        return f"{where} It carries {len(files)} file(s): {names}.{who}"
    except Exception:
        return ""


def main():
    name, tool_input, data = "", {}, {}
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
        name = _tool_name(data.get("tool_name"))
        _TOOL["name"] = name
        tool_input = data.get("tool_input") or {}
    except Exception:
        data = data if isinstance(data, dict) else {}
    if name == "email_add_attachment":
        return _attach(data, tool_input)
    if name == "teams_stage":
        return _teams_stage(data, tool_input)
    if name == "onedrive_upload":
        return _upload(data, tool_input)
    if name == "onedrive_share_with":
        return _share(tool_input)
    if name == "onedrive_move":
        return _move(tool_input)
    if any(k in tool_input and not isinstance(tool_input[k], str) for k in ("stage_id", "digest", "draft_id", "message_id", "chat_id", "item_id", "name")):
        # The server and this script must read an id the same way: an id that is not plain text is refused, not guessed at.
        return _out("deny", "refused, an id or name is not plain text.")
    template = _WHAT.get(name, "make a change in Microsoft 365 that others can see or that cannot be undone.")
    if name == "calendar_commit" and str(tool_input.get("stage_id", "")).startswith("calchange_") and len(str(tool_input.get("stage_id", ""))) <= _LIMIT:
        # A change to an existing event: say exactly what it does, read from the plugin's own staging file.
        summary = _staged_calendar_change(tool_input.get("stage_id"))
        template = (summary.replace("{", "{{").replace("}", "}}") if summary
                    else "CHANGE, CANCEL or ANSWER a calendar event (staged as {stage_id}); people may be notified.")
    if name == "teams_commit" and len(str(tool_input.get("stage_id", ""))) <= _LIMIT:
        template += _staged_files(tool_input.get("stage_id")).replace("{", "{{").replace("}", "}}")
    keys = ("draft_id", "stage_id", "message_id", "chat_id", "item_id", "name", "client_id", "tenant", "scope_mode", "auth_mode", "redirect_uri")
    values = {k: tool_input.get(k, "-") for k in keys}
    if any(len(str(v)) > _LIMIT for v in values.values()):
        # A value too long to show in full could hide what the call really does: do not offer a prompt, refuse.
        return _out("deny", "refused, an argument is too long to show you in full.")
    try:
        reason = template.format(**{k: _show(v) for k, v in values.items()})
    except Exception:
        reason = template
    return _out("ask", reason)


if __name__ == "__main__":
    sys.exit(main())
