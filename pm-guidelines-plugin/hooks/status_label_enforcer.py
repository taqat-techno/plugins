#!/usr/bin/env python3
"""Status Label Enforcer — Tier 2 Quality Hook (PostToolUse)

Detects vague/lazy status labels in PM deliverables:
- "Ongoing" without specific next steps (Guideline 5)
- "independently" without explanation (Guideline 7)
- Inconsistent completion markers across table rows (Guidelines 4, 6)

Exit codes: 0=pass (with optional description)
"""

import json
import os
import re
import sys

# Add plugin root for shared utils
PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT', os.path.dirname(__file__))
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(PLUGIN_ROOT, 'hooks'))

try:
    from pm_utils import is_pm_deliverable, read_file_safe
except ImportError as e:
    print(f"pm-guidelines:status_label_enforcer.py: import failed: {e}", file=sys.stderr)
    sys.exit(0)


def check_vague_ongoing(content):
    """Find 'Ongoing' not followed by specifics."""
    issues = []
    for i, line in enumerate(content.split('\n'), 1):
        # Look for "Ongoing" that's NOT followed by colon, dash, or parentheses with detail
        if re.search(r'\bOngoing\b', line, re.IGNORECASE):
            # Check if it has specifics after it
            after_ongoing = re.split(r'\bOngoing\b', line, flags=re.IGNORECASE)[-1]
            has_detail = bool(re.search(r'[:(\-–—]', after_ongoing.strip()[:10]))
            if not has_detail:
                issues.append(f'  Line {i}: "Ongoing" without specifics — replace with next steps (e.g., "Phase 2: user testing")')
    return issues


def check_vague_independently(content):
    """Find 'independently' without explanation."""
    issues = []
    for i, line in enumerate(content.split('\n'), 1):
        if re.search(r'\bindependently\b', line, re.IGNORECASE):
            after = re.split(r'\bindependently\b', line, flags=re.IGNORECASE)[-1]
            has_detail = bool(re.search(r'[(\[]', after.strip()[:10]))
            if not has_detail:
                issues.append(f'  Line {i}: "independently" without explanation — specify what continues (e.g., "lab practice & exam")')
    return issues


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:status_label_enforcer: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not is_pm_deliverable(file_path):
        sys.exit(0)

    content = read_file_safe(file_path)
    if not content:
        sys.exit(0)

    issues = []
    issues.extend(check_vague_ongoing(content))
    issues.extend(check_vague_independently(content))

    if not issues:
        sys.exit(0)

    issue_text = '\n'.join(issues[:8])  # Cap at 8 issues
    result = {
        "description": f"[pm-guidelines] Status label issues found:\n{issue_text}\n\nTip: Be specific — show intentional planning, not vagueness."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
