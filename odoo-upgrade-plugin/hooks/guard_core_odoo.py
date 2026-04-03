#!/usr/bin/env python3
"""
PreToolUse hook: Block writes to core Odoo framework files.

Reads tool input JSON from stdin. If the target file is inside a core
Odoo directory, exits with code 2 to block the action. Otherwise exits 0.

Safety-critical blocker: fail-CLOSED on timeout (exit 0 = allow would be wrong
if we can't determine safety). However, the 5s internal timeout is generous
for pure regex matching, so timeout implies a real hang — fail-open is safer
than blocking all writes indefinitely.

Core path patterns are loaded from odoo-upgrade.config.json (configurable).
"""

import json
import os
import re
import sys
import threading

# Internal timeout: fail-OPEN after 5 seconds.
# This hook does pure regex matching — if it takes >5s something is broken.
# Failing open is safer than blocking all Write/Edit indefinitely.
_timer = threading.Timer(5.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Import shared config loader (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config_loader import load_config
except ImportError:
    # If config_loader is missing, use hardcoded fallback
    def load_config():
        return {"core_path_patterns": [
            r"odoo\d{2}/odoo/addons/",
            r"odoo\d{2}/odoo/[^/]+\.py$",
            r"odoo\d{2}/odoo/tools/",
            r"odoo\d{2}/odoo/modules/",
            r"odoo\d{2}/odoo/cli/",
            r"odoo\d{2}/odoo/service/",
            r"/odoo/odoo/addons/",
        ]}


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '') or tool_input.get('path', '')

    if not file_path:
        sys.exit(0)

    normalized = file_path.replace('\\', '/')

    try:
        config = load_config()
    except Exception:
        config = {"core_path_patterns": []}

    core_patterns = config.get('core_path_patterns', [])

    for pattern in core_patterns:
        try:
            if re.search(pattern, normalized):
                msg = (
                    f"BLOCKED: Cannot modify core Odoo file: {file_path}\n"
                    "Core framework files (odoo/addons/, odoo/*.py) must not be edited.\n"
                    "Use model/view inheritance in projects/ instead."
                )
                print(msg, file=sys.stderr)
                _timer.cancel()
                sys.exit(2)
        except re.error:
            continue  # Skip malformed user-provided patterns

    _timer.cancel()
    sys.exit(0)


if __name__ == '__main__':
    main()
