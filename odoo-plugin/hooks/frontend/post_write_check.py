#!/usr/bin/env python3
"""PostToolUse hook: advisory reminders after Write/Edit operations.

Receives JSON on stdin with tool_input containing file_path and content.
Always exits 0. Outputs JSON hookSpecificOutput to stdout.

Hardened: internal timeout guard, JSON output format, fail-open.
"""
import json
import os
import re
import sys
import threading

# Internal timeout: fail-open after 5 seconds
_timer = threading.Timer(5.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Bootstrap 4 classes that should be Bootstrap 5 in Odoo 16+
BS4_PATTERN = re.compile(
    r"\b(ml-|mr-|pl-|pr-|text-left|text-right|float-left|float-right"
    r"|font-weight-bold|sr-only)\b"
)

BS4_REPLACEMENTS = (
    "ml-*->ms-*, mr-*->me-*, pl-*->ps-*, pr-*->pe-*, "
    "text-left->text-start, text-right->text-end, "
    "float-left->float-start, float-right->float-end, "
    "font-weight-bold->fw-bold, sr-only->visually-hidden"
)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

    if not file_path:
        sys.exit(0)

    basename = os.path.basename(file_path).lower()
    ext = os.path.splitext(file_path)[1].lower()
    reminders = []

    # --- SCSS/SASS checks ---
    if ext in (".scss", ".sass"):
        reminders.append("SCSS modified. Regenerate assets or restart with --dev=css")
        if "primary_variables" in basename:
            reminders.append("Primary variables changed. Ensure o-color-1..5 follow semantic meanings.")

    # --- JavaScript checks ---
    if ext == ".js" and content:
        if "@odoo-module" not in content:
            reminders.append("JS file should start with /** @odoo-module **/ annotation.")
        if "publicWidget" in content and ("Widget.extend" in content or "registry" in content):
            reminders.append("publicWidget detected. Check 'this.editableMode' in start().")

    # --- Theme XML checks ---
    if ext == ".xml" and "theme_" in file_path.replace("\\", "/").lower():
        reminders.append("Theme data modified. Update theme module.")

    # --- Bootstrap 4 class detection ---
    if ext in (".xml", ".html", ".scss") and content:
        if BS4_PATTERN.search(content):
            reminders.append(f"Bootstrap 4 classes detected. For Odoo 16+: {BS4_REPLACEMENTS}")

    if reminders:
        output = {"hookSpecificOutput": {"additionalContext": "\n".join(reminders)}}
        print(json.dumps(output))

    _timer.cancel()
    sys.exit(0)


if __name__ == "__main__":
    main()
