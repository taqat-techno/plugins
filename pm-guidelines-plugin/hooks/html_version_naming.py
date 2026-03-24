#!/usr/bin/env python3
"""HTML Version Naming — Tier 2 Quality Hook (PreToolUse)

Before writing a deliverable file, checks if the filename uses
version suffixes (_v2, _v3) when a previous version already exists.

Exit codes: 0=pass (with optional description)
"""

import json
import os
import re
import sys
from pathlib import Path

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', os.path.dirname(__file__))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'hooks'))

try:
    from pm_utils import is_pm_deliverable
except ImportError:
    def is_pm_deliverable(p):
        return os.path.splitext(p)[1].lower() in {'.html', '.htm', '.md'}


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:html_version_naming: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not is_pm_deliverable(file_path):
        sys.exit(0)

    path = Path(file_path)
    stem = path.stem
    ext = path.suffix

    # Already has version suffix — fine
    if re.search(r'_v\d+$', stem):
        sys.exit(0)

    # Check if file already exists (overwrite without versioning)
    if not path.exists():
        sys.exit(0)

    # File exists and new write has no version suffix — warn
    # Find existing versions
    parent = path.parent
    existing_versions = sorted(parent.glob(f'{stem}_v*{ext}'))
    if existing_versions:
        latest = existing_versions[-1].stem
        latest_num = re.search(r'_v(\d+)$', latest)
        next_num = int(latest_num.group(1)) + 1 if latest_num else 2
    else:
        next_num = 2

    suggestion = f'{stem}_v{next_num}{ext}'
    result = {
        "description": f"[pm-guidelines] Overwriting '{path.name}' without version suffix.\n\nSuggestion: use '{suggestion}' to preserve version history.\nKeep old versions in versioned folders (v1/, v2/) for audit trails."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
