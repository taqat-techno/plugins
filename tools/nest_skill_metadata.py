#!/usr/bin/env python3
"""Move non-standard top-level SKILL.md frontmatter keys under `metadata:`.

Claude Code ignores keys it does not recognise, but claude.ai skill upload and the
Skills API reject them. The official free-form home for custom keys is `metadata:`.
Known keys stay where they are; everything else (owns, defers_to, last_reviewed, ...)
is re-indented under one `metadata:` block, appended to an existing one if present.

    python tools/nest_skill_metadata.py [--check]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validate_marketplace import KNOWN_SKILL_KEYS  # noqa: E402

KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(\s|$)")


def split_blocks(lines: list[str]) -> list[tuple[str | None, list[str]]]:
    blocks: list[tuple[str | None, list[str]]] = []
    for line in lines:
        m = KEY.match(line)
        if m:
            blocks.append((m.group(1), [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            blocks.append((None, [line]))
    return blocks


def transform(text: str) -> str | None:
    m = re.match(r"(?s)\A---\n(.*?)\n---(\n|\Z)", text)
    if not m:
        return None
    blocks = split_blocks(m.group(1).split("\n"))
    keep, moved, meta = [], [], None
    for key, lines in blocks:
        if key == "metadata":
            meta = lines
        elif key is None or key in KNOWN_SKILL_KEYS:
            keep.append(lines)
        else:
            moved.append(lines)
    if not moved:
        return None
    meta = meta or ["metadata:"]
    if meta[0].strip() != "metadata:":
        return None  # inline metadata value; leave the file for a human
    for lines in moved:
        meta.extend("  " + line if line.strip() else line for line in lines)
    body = [line for lines in keep for line in lines] + meta
    return "---\n" + "\n".join(body) + "\n---" + m.group(2) + text[m.end():]


def main(argv: list[str]) -> int:
    check = "--check" in argv
    changed = []
    for path in sorted(ROOT.glob("*-plugin/skills/*/SKILL.md")):
        raw = path.read_bytes()
        crlf = b"\r\n" in raw
        text = raw.decode("utf-8").replace("\r\n", "\n")
        new = transform(text)
        if new is None or new == text:
            continue
        changed.append(path.relative_to(ROOT).as_posix())
        if not check:
            path.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
    print(("would change" if check else "changed"), len(changed), "SKILL.md files")
    return 1 if (check and changed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
