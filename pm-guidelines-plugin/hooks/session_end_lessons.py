#!/usr/bin/env python3
"""Session End Lessons — Tier 3 Lifecycle Hook (Stop)

At session end, prompts for lessons capture if the session
was non-trivial (enough activity to warrant reflection).

Exit codes: 0=pass (with optional description)
"""

import json
import os
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        # Stop hook may not receive structured input — this is normal
        input_data = {}

    result = {
        "description": "[pm-guidelines] Session ending — consider capturing lessons:\n\n- Were there any corrections or surprises worth saving to memory?\n- Did any validated approaches work well? (Save positive patterns too)\n- Update session log in MEMORY.md if repo data was analyzed.\n\nSave lessons at end of every session — don't wait to be asked."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
