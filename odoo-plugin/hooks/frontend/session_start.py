#!/usr/bin/env python3
"""
SessionStart hook: Detect Odoo version and inject frontend context.
Outputs JSON in official hookSpecificOutput format.
Exit 0 always.
"""

import json
import os
import re
import sys
import threading

# Internal timeout guard - fail-open after 8 seconds
_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Read stdin (required by hook protocol)
try:
    sys.stdin.read()
except Exception:
    pass

BOOTSTRAP_MAP = {
    "14": "4.5.0", "15": "4.5.0",
    "16": "5.1.3", "17": "5.1.3", "18": "5.1.3", "19": "5.1.3",
}

OWL_MAP = {
    "14": None, "15": None,
    "16": "1.x", "17": "1.x", "18": "2.x", "19": "2.x",
}


def detect_odoo_version():
    """Detect Odoo version from workspace directory structure (no recursion)."""
    cwd = os.getcwd()
    try:
        for item in os.listdir(cwd):
            full = os.path.join(cwd, item)
            if os.path.isdir(full):
                m = re.match(r'^odoo(\d{2})$', item)
                if m:
                    ver = m.group(1)
                    bs = BOOTSTRAP_MAP.get(ver, "5.1.3")
                    owl = OWL_MAP.get(ver)
                    parts = [f"Odoo {ver}", f"Bootstrap {bs}"]
                    if owl:
                        parts.append(f"Owl {owl}")
                    return f"[Odoo Frontend] Detected: {', '.join(parts)}. Use publicWidget for website themes."
    except (OSError, PermissionError):
        pass
    return ""


try:
    ctx = detect_odoo_version()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx
        }
    }
    print(json.dumps(output))
except Exception:
    # Fail-safe: always output valid JSON
    print('{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}')

_timer.cancel()
sys.exit(0)
