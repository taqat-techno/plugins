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
            "[env-doctor] If the environment misbehaves "
            "(MCP not loading, WSL/login/LSP issues), run /env-doctor."
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
