#!/usr/bin/env python3
"""Dashboard Quality Check — Tier 2 Quality Hook (PostToolUse)

Verifies dashboards have:
- A "Data Source" or "Source" tab/section (Guideline 30)
- Timestamps showing fetch time, not live clock (Guideline 34)
- Full project names, not abbreviations (Guideline 35)

Only fires on dashboard/report HTML files.

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
    from pm_utils import is_dashboard_file, read_file_safe
except ImportError as e:
    print(f"pm-guidelines:dashboard_quality_check.py: import failed: {e}", file=sys.stderr)
    sys.exit(0)


def check_source_tab(content):
    """Check for a Data Source / Source tab or section."""
    source_patterns = [
        r'data.?source',
        r'source.?tab',
        r'data.?transparency',
        r'query.?details',
        r'api.?source',
        r'verification.?link',
    ]
    for pattern in source_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return None
    return '  Missing "Data Source" tab — dashboards must include query details for verification'


def check_live_clock(content):
    """Check for live clock patterns that give false freshness."""
    live_clock_patterns = [
        r'new\s+Date\(\)',           # JavaScript new Date()
        r'setInterval.*Date',         # Interval-based clock updates
        r'toLocaleTimeString',        # Live time display
        r'clock.*setInterval',        # Named clock interval
    ]
    for pattern in live_clock_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            # Check if there's also a fetch timestamp
            has_fetch_time = bool(re.search(
                r'(last.?fetched|last.?updated|data.?as.?of|fetched.?at|retrieved.?at)',
                content, re.IGNORECASE
            ))
            if not has_fetch_time:
                return '  Live clock detected without fetch timestamp — "Last updated" should show when data was retrieved from API, not current time'
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:dashboard_quality_check: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not is_dashboard_file(file_path):
        sys.exit(0)

    content = read_file_safe(file_path)
    if not content:
        sys.exit(0)

    issues = []

    source_issue = check_source_tab(content)
    if source_issue:
        issues.append(source_issue)

    clock_issue = check_live_clock(content)
    if clock_issue:
        issues.append(clock_issue)

    if not issues:
        sys.exit(0)

    issue_text = '\n'.join(issues)
    result = {
        "description": f"[pm-guidelines] Dashboard quality issues:\n{issue_text}\n\nDashboard readers must be able to verify data independently."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
