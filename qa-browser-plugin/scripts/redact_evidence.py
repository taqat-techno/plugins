#!/usr/bin/env python3
"""Redact or scan qa-browser evidence files for credentials and session secrets.

    python redact_evidence.py <path> [<path> ...]          # redact in place
    python redact_evidence.py --check <path> [<path> ...]  # scan only; exit 1 on a hit

Paths may be files or directories (walked recursively). Text evidence is
handled: .json, .har, .ndjson, .log, .txt, .md. Images (screenshots) cannot be
scanned and are counted as "not scanned" - review them by eye before sharing.

What is masked:
  * JSON values under sensitive keys (password, otp, totp, token, secret,
    cookie, authorization, session, csrf, api key, ...), at any depth;
  * HAR-style header / cookie lists ({"name": "Cookie", "value": ...});
  * `Header: value` lines for Authorization, Cookie, Set-Cookie, X-API-Key,
    X-Auth-Token, X-CSRF-Token, Proxy-Authorization;
  * every secret shape hooklib.redact() knows (JWTs, bearer/basic credentials,
    provider tokens, key=value secrets, URL passwords, private keys).

Matched values are never printed. Output is one line per file with a count.
Exit codes: 0 clean (or redacted), 1 secrets found in --check mode, 2 usage error.
Shape-based: a secret with no recognisable key or form is not caught.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks" / "_vendor"))
import hooklib  # noqa: E402

MASK = "[REDACTED]"
TEXT_SUFFIXES = {".json", ".har", ".ndjson", ".log", ".txt", ".md"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SENSITIVE_KEY_RE = re.compile(
    r"(?i)^(?:pass(?:word|wd)?|pwd|otp|totp(?:secret)?|mfa(?:code)?|secret|client_secret|"
    r"token|access_token|refresh_token|id_token|auth(?:orization)?|proxy-authorization|"
    r"cookie|set-cookie|session(?:id)?|sid|csrf(?:token)?|x-csrf-token|xsrf-token|"
    r"x-api-key|api[_-]?key|x-auth-token)$")
HEADER_LINE_RE = re.compile(
    r"(?im)^(\s*(?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|"
    r"x-auth-token|x-csrf-token)\s*:\s*)(\S.*)$")


def _redact_json(node):
    """Return (new_node, hits)."""
    hits = 0
    if isinstance(node, dict):
        # HAR header / cookie entry: {"name": "Cookie", "value": "..."}
        name = node.get("name")
        if isinstance(name, str) and "value" in node and SENSITIVE_KEY_RE.match(name.strip()):
            if node["value"] not in ("", None, MASK):
                node = dict(node, value=MASK)
                hits += 1
        out = {}
        for key, value in node.items():
            if (isinstance(key, str) and SENSITIVE_KEY_RE.match(key.strip())
                    and isinstance(value, (str, int, float)) and value not in ("", MASK)):
                out[key] = MASK
                hits += 1
                continue
            out[key], h = _redact_json(value)
            hits += h
        return out, hits
    if isinstance(node, list):
        out = []
        for item in node:
            new, h = _redact_json(item)
            out.append(new)
            hits += h
        return out, hits
    if isinstance(node, str):
        new = _redact_text(node)
        return new, (0 if new == node else 1)
    return node, 0


def _redact_text(text: str) -> str:
    text = HEADER_LINE_RE.sub(lambda m: m.group(1) + MASK if m.group(2) != MASK else m.group(0),
                              text)
    return hooklib.redact(text, MASK)


def redact_content(raw: str, suffix: str) -> tuple[str, int]:
    """Redact one file's text. Returns (new_text, number_of_changes)."""
    if suffix in {".json", ".har"}:
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if data is not None:
            new, hits = _redact_json(data)
            return (json.dumps(new, indent=2, ensure_ascii=False) + "\n", hits) if hits else (raw, 0)
    if suffix == ".ndjson":
        lines, hits = [], 0
        for line in raw.splitlines():
            try:
                new, h = _redact_json(json.loads(line))
                lines.append(json.dumps(new, ensure_ascii=False) if h else line)
                hits += h
            except ValueError:
                red = _redact_text(line)
                hits += red != line
                lines.append(red)
        return ("\n".join(lines) + ("\n" if raw.endswith("\n") else ""), hits) if hits else (raw, 0)
    new = _redact_text(raw)
    if new == raw:
        return raw, 0
    changed = sum(1 for a, b in zip(raw.splitlines(), new.splitlines()) if a != b) or 1
    return new, changed


def iter_files(paths):
    for p in paths:
        path = Path(p)
        if path.is_dir():
            yield from sorted(f for f in path.rglob("*") if f.is_file())
        elif path.is_file():
            yield path


def main(argv: list[str]) -> int:
    check = "--check" in argv
    paths = [a for a in argv if a != "--check"]
    if not paths or any(a.startswith("-") for a in paths):
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    total_hits, images, dirty = 0, 0, []
    for f in iter_files(paths):
        suffix = f.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            images += 1
            continue
        if suffix not in TEXT_SUFFIXES:
            continue
        try:
            raw = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new, hits = redact_content(raw, suffix)
        if not hits:
            continue
        total_hits += hits
        dirty.append(f)
        if check:
            print(f"SECRET  {f}: {hits} value(s)")
        else:
            f.write_bytes(new.encode("utf-8"))
            print(f"REDACTED {f}: {hits} value(s)")
    print(f"{'scan' if check else 'redact'}: {len(dirty)} file(s) with secrets, "
          f"{total_hits} value(s); {images} image(s) not scanned (review by eye)")
    return 1 if (check and dirty) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
