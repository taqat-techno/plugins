#!/usr/bin/env python3
"""Bilingual Parity Check — Tier 2 Quality Hook (PostToolUse)

After editing bilingual HTML, verifies both language spans were updated.
Detects data-i18n pairs and lang-en/lang-ar class pairs.

Only fires on files that actually contain bilingual markers.

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
    from pm_utils import is_html_file, read_file_safe
except ImportError as e:
    print(f"pm-guidelines:bilingual_parity_check.py: import failed: {e}", file=sys.stderr)
    sys.exit(0)


def is_bilingual(content):
    """Check if file contains bilingual markers."""
    return bool(
        re.search(r'data-i18n', content) or
        re.search(r'class=["\'][^"\']*lang-(en|ar)', content) or
        re.search(r'lang=["\']ar["\']', content)
    )


def check_i18n_completeness(content):
    """Check that data-i18n keys have both EN and AR content."""
    issues = []

    # Find all data-i18n key values
    i18n_keys = re.findall(r'data-i18n=["\']([^"\']+)["\']', content)
    unique_keys = set(i18n_keys)

    # For each key, check if both language spans exist
    for key in unique_keys:
        # Find all elements with this key
        pattern = rf'data-i18n=["\']({re.escape(key)})["\'][^>]*>([^<]*)<'
        matches = re.findall(pattern, content)

        # Check for empty translations
        for _, text in matches:
            if not text.strip():
                issues.append(f'  Empty translation for key "{key}" — fill in both EN and AR content')
                break

    return issues


def check_lang_class_pairs(content):
    """Check that lang-en and lang-ar spans appear in pairs."""
    issues = []

    # Count lang-en and lang-ar class occurrences
    en_count = len(re.findall(r'class=["\'][^"\']*lang-en', content))
    ar_count = len(re.findall(r'class=["\'][^"\']*lang-ar', content))

    if en_count != ar_count:
        issues.append(f'  Language span mismatch: {en_count} English spans vs {ar_count} Arabic spans — every EN span needs an AR sibling')

    return issues


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:bilingual_parity_check: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not is_html_file(file_path):
        sys.exit(0)

    content = read_file_safe(file_path)
    if not content or not is_bilingual(content):
        sys.exit(0)

    issues = []
    issues.extend(check_i18n_completeness(content))
    issues.extend(check_lang_class_pairs(content))

    if not issues:
        sys.exit(0)

    issue_text = '\n'.join(issues[:5])
    result = {
        "description": f"[pm-guidelines] Bilingual parity issues:\n{issue_text}\n\nAlways update both EN and AR for every text change. Verify RTL visually."
    }
    print(json.dumps(result))
    sys.exit(0)


if __name__ == '__main__':
    main()
