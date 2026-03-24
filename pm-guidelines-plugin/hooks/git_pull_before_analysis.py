#!/usr/bin/env python3
"""Git Pull Before Analysis — Tier 3 Lifecycle Hook (PreToolUse)

Before reading data/analysis files, warns if git pull hasn't been
run in this session. Prevents analyzing stale data.

Uses a temp file per session to track pull status.

Exit codes: 0=pass (with optional description)
"""

import hashlib
import json
import os
import re
import sys
import tempfile
import time

# File extensions that are "data" files (not code)
DATA_EXTENSIONS = {
    '.xlsx', '.xls', '.csv', '.json', '.xml',
    '.html', '.htm', '.pdf', '.docx', '.pptx',
}

# Directories that contain data/analysis files
DATA_DIRECTORIES = [
    'researches', 'reports', 'deliverables', 'data',
    'dashboards', 'proposals', 'presentations', 'analysis',
]


def get_session_file():
    """Get session state file path."""
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    # Hash long session IDs
    hashed = hashlib.sha256(session_id.encode()).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), f'pm-session-{hashed}.json')


def has_pulled_this_session():
    """Check if git pull was done in this session."""
    session_file = get_session_file()
    try:
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                state = json.load(f)
            # Expire after 24 hours
            if time.time() - state.get('timestamp', 0) < 86400:
                return state.get('pulled', False)
    except (json.JSONDecodeError, IOError):
        pass
    return False


def is_data_file(file_path):
    """Check if this is a data/analysis file that should trigger the check."""
    if not file_path:
        return False

    normalized = file_path.replace('\\', '/').lower()
    ext = os.path.splitext(normalized)[1]

    # Must be a data extension
    if ext not in DATA_EXTENSIONS:
        return False

    # Must be in a data directory
    parts = normalized.split('/')
    return any(part in DATA_DIRECTORIES for part in parts)


def is_git_repo():
    """Check if CWD is inside a git repo."""
    try:
        cwd = os.getcwd()
        while True:
            if os.path.isdir(os.path.join(cwd, '.git')):
                return True
            parent = os.path.dirname(cwd)
            if parent == cwd:
                break
            cwd = parent
    except OSError:
        pass
    return False


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:git_pull_before_analysis: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not is_data_file(file_path):
        sys.exit(0)

    if not is_git_repo():
        sys.exit(0)

    if has_pulled_this_session():
        sys.exit(0)

    result = {
        "description": "[pm-guidelines] Reading data file before pulling latest.\n\nRun 'git pull' first to avoid analyzing stale data. Also check 'git diff --stat' after pull to understand what changed."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
