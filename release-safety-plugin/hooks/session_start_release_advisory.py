#!/usr/bin/env python3
"""SessionStart hook: prints one short, safe advisory line. Never blocks."""
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    try:
        print(
            "[release-safety] Before calling a fix 'done' or running a risky "
            "migration/cutover, run /release-verify (prove it in the target env)."
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
