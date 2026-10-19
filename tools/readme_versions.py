#!/usr/bin/env python3
"""Keep the version column of the root README's plugin table in sync with plugin.json.

    python tools/readme_versions.py           # rewrite the column
    python tools/readme_versions.py --check   # exit 1 if any cell is stale
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROW = re.compile(r"^(\| *\d+ *\| )\*\*([a-z0-9-]+)\*\* \| `([^`]+)` \|", re.M)


def versions() -> dict[str, str]:
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    out = {}
    for entry in market["plugins"]:
        manifest = ROOT / entry["source"] / ".claude-plugin" / "plugin.json"
        out[entry["name"]] = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    return out


def main(argv: list[str]) -> int:
    path = ROOT / "README.md"
    raw = path.read_bytes()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    want = versions()
    stale = []

    def fix(m: re.Match) -> str:
        name, have = m.group(2), m.group(3)
        if name in want and have != want[name]:
            stale.append(f"{name}: README says {have}, plugin.json says {want[name]}")
            return f"{m.group(1)}**{name}** | `{want[name]}` |"
        return m.group(0)

    new = ROW.sub(fix, text)
    if "--check" in argv:
        for s in stale:
            print("stale: " + s)
        print("README versions: " + ("ok" if not stale else f"{len(stale)} stale"))
        return 1 if stale else 0
    if new != text:
        path.write_bytes((new.replace("\n", "\r\n") if crlf else new).encode("utf-8"))
    print(f"README versions: updated {len(stale)} cell(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
