#!/usr/bin/env python3
"""PreToolUse hook: blocks Write/Edit of XML files containing inline JavaScript.

Receives JSON on stdin with tool_input containing file_path and content.
Exit 0 = allow, Exit 2 = block (message on stderr).

Hardened: internal timeout guard, fast-path string check before regex.
"""
import json
import os
import re
import sys
import threading

# ── Internal timeout guard (defense-in-depth) ──────────────────────────────
# If this script hangs (e.g., massive file regex), force-exit after 3 seconds.
# Fail-OPEN on timeout: exit 0 so Write/Edit is not blocked by our failure.
_timer = threading.Timer(3.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

    if not file_path or not content:
        sys.exit(0)

    # Only check XML files
    if not file_path.lower().endswith(".xml"):
        sys.exit(0)

    # Fast path: cheap string check before expensive regex
    if "<script" not in content or "</script>" not in content:
        sys.exit(0)

    # Full regex check for inline <script> tags with non-empty body
    if re.search(r"<script[^>]*>[^<]+</script>", content, re.DOTALL):
        print(
            "Inline JavaScript detected in XML template. "
            "Create a separate .js file in static/src/js/ instead.",
            file=sys.stderr,
        )
        _timer.cancel()
        sys.exit(2)

    _timer.cancel()
    sys.exit(0)


if __name__ == "__main__":
    main()
