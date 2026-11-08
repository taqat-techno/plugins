"""Save an image the user pasted into the Claude Code chat as a file the m365 server may attach.

A pasted screenshot exists only inside the session transcript (a base64 image block in a user message), never as a file,
so the server alone cannot attach it. The PreToolUse hook calls save_pasted_image() for email_add_attachment with
chat_image, and passes the saved path on to the tool.

Only images the USER pasted count: entries of type "user" that are not tool results and not from a subagent. An image
returned by a tool (a web page screenshot, a file Claude read) is never picked, so a page cannot plant one. The file is
written under <M365_HOME>/chat-files/<session>/, the one folder the server accepts pasted images from. Stdlib only.
"""
import base64
import hashlib
import json
import os
import re
from pathlib import Path

_TYPES = {"image/png": (".png", b"\x89PNG\r\n\x1a\n"), "image/jpeg": (".jpg", b"\xff\xd8\xff"),
          "image/gif": (".gif", b"GIF8"), "image/webp": (".webp", b"RIFF")}
_MAX = 25 * 1024 * 1024


class ChatImageError(Exception):
    pass


def m365_home():
    env = os.environ.get("M365_HOME", "").strip()
    return Path(env) if env else Path.home() / ".m365-plugin"


def pasted_images(transcript_path):
    """The user's pasted images in conversation order, as (media_type, base64 data)."""
    out = []
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"image"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("type") != "user" or entry.get("isSidechain") or entry.get("toolUseResult") is not None:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                continue
            for block in content:
                src = block.get("source") if isinstance(block, dict) and block.get("type") == "image" else None
                if isinstance(src, dict) and src.get("type") == "base64" and src.get("media_type") in _TYPES:
                    out.append((src["media_type"], src.get("data") or ""))
    return out


def save_pasted_image(transcript_path, session_id, number):
    """Save the number-th most recent pasted image (1 = latest). Returns (path, media_type, size)."""
    try:
        n = int(number)
    except (TypeError, ValueError):
        raise ChatImageError("chat_image must be a number (1 = the most recent pasted image)")
    if n < 1:
        raise ChatImageError("chat_image must be 1 or more")
    if not transcript_path or not os.path.isfile(transcript_path):
        raise ChatImageError("this chat's history could not be read")
    images = pasted_images(transcript_path)
    if n > len(images):
        raise ChatImageError(f"there are only {len(images)} pasted image(s) in this chat")
    media_type, data = images[-n]
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        raise ChatImageError("the pasted image could not be read")
    ext, magic = _TYPES[media_type]
    if not raw.startswith(magic) or (media_type == "image/webp" and raw[8:12] != b"WEBP"):
        raise ChatImageError("the pasted data is not the image type it claims to be")
    if len(raw) > _MAX:
        raise ChatImageError("the pasted image is larger than 25 MB")
    session = re.sub(r"[^A-Za-z0-9_-]", "", str(session_id or ""))[:64] or "session"
    folder = m365_home() / "chat-files" / session
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"pasted-{hashlib.sha256(raw).hexdigest()[:16]}{ext}"
    if not path.exists():
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    return str(path), media_type, len(raw)
