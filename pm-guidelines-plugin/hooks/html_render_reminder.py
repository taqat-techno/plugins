#!/usr/bin/env python3
"""HTML Render Reminder — Tier 2 Quality Hook (PostToolUse)

After writing/editing HTML deliverables, reminds to verify rendering.
For bilingual files, reminds to check both EN and AR.

Exit codes: 0=pass (with optional description)
"""

import json
import os
import re
import sys

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', os.path.dirname(__file__))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'hooks'))

try:
    from pm_utils import is_pm_deliverable, is_html_file, read_file_safe
except ImportError as e:
    print(f"pm-guidelines:html_render_reminder.py: import failed: {e}", file=sys.stderr)
    sys.exit(0)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:html_render_reminder: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    # Only fire on HTML files in PM directories
    if not is_html_file(file_path) or not is_pm_deliverable(file_path):
        sys.exit(0)

    # Check if bilingual
    content = read_file_safe(file_path)
    is_bilingual = bool(content and (
        re.search(r'data-i18n', content) or
        re.search(r'lang-(en|ar)', content) or
        re.search(r'lang=["\']ar["\']', content)
    ))

    msg = "[pm-guidelines] HTML modified — open in browser to verify rendering."
    if is_bilingual:
        msg += "\nBilingual file detected: check BOTH English and Arabic views. Verify RTL alignment, borders, and padding."

    result = {"description": msg}
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
