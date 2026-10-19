#!/usr/bin/env python3
"""Copy shared/hooklib.py into every plugin that vendors it, or check the copies.

A plugin opts in by having a hooks/_vendor/ directory. Claude Code caches each plugin
on its own, so hooks cannot import across plugins; each one ships its own copy.

    python tools/sync_vendor.py           # write the canonical copy into every opted-in plugin
    python tools/sync_vendor.py --check   # exit 1 if any copy differs from shared/hooklib.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = ROOT / "shared" / "hooklib.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def targets() -> list[Path]:
    return sorted(p / "hooklib.py" for p in ROOT.glob("*-plugin/hooks/_vendor") if p.is_dir())


def main(argv: list[str]) -> int:
    check = "--check" in argv
    want = digest(CANONICAL)
    drift = []
    for target in targets():
        if target.is_file() and digest(target) == want:
            continue
        if check:
            drift.append(target.relative_to(ROOT).as_posix())
        else:
            target.write_bytes(CANONICAL.read_bytes())
            print(f"synced {target.relative_to(ROOT).as_posix()}")
    if drift:
        print("hooklib copies differ from shared/hooklib.py (run python tools/sync_vendor.py):")
        for path in drift:
            print(f"  {path}")
        return 1
    if check:
        print(f"ok: {len(targets())} vendored hooklib copies match shared/hooklib.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
