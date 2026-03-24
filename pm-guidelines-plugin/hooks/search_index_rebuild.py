#!/usr/bin/env python3
"""Search Index Rebuild — Tier 3 Lifecycle Hook (PostToolUse)

After git pull in indexed projects, reminds to rebuild search index.
Only fires if the project contains search-index.js or build-index.js.

Exit codes: 0=pass (with optional description)
"""

import json
import os
import re
import sys
from pathlib import Path


def has_search_index():
    """Check if project has a search index build system."""
    cwd = Path(os.getcwd())
    index_files = [
        'search-index.js',
        'build-index.js',
        'build-search-index.js',
        'generate-index.js',
    ]
    for f in index_files:
        matches = list(cwd.rglob(f))
        if matches:
            return matches[0]
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:search_index_rebuild: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    command = tool_input.get('command', '')

    # Only fire on git pull commands
    if not re.search(r'\bgit\s+pull\b', command):
        sys.exit(0)

    # Check for search index files
    index_file = has_search_index()
    if not index_file:
        sys.exit(0)

    result = {
        "description": f"[pm-guidelines] Pulled changes. This project has a search index at '{index_file.name}'.\n\nRebuild it: node {index_file}\n\nAlso check if any new HTML pages need to be added to the FILES array in the build script."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
