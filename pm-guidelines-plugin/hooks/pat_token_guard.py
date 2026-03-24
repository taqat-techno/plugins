#!/usr/bin/env python3
"""PAT Token Guard — Tier 1 Security Hook (PreToolUse)

Blocks Write/Edit/Bash operations that contain secrets:
- Azure DevOps PATs (52-char base32)
- GitHub tokens (ghp_, gho_, ghs_, ghr_, github_pat_)
- Generic API keys (sk-, Bearer tokens)
- npm tokens, AWS keys

Exit codes: 0=pass, 2=block
"""

import json
import re
import sys

# Context keywords that indicate a nearby string is a secret
SECRET_CONTEXT_KEYWORDS = re.compile(
    r'(token|pat|password|secret|credential|authorization|api.?key|access.?key)',
    re.IGNORECASE
)

# Patterns that strongly indicate secrets (high confidence)
SECRET_PATTERNS = [
    # GitHub tokens
    (r'ghp_[A-Za-z0-9_]{36,}', 'GitHub Personal Access Token'),
    (r'gho_[A-Za-z0-9_]{36,}', 'GitHub OAuth Token'),
    (r'ghs_[A-Za-z0-9_]{36,}', 'GitHub Server Token'),
    (r'ghr_[A-Za-z0-9_]{36,}', 'GitHub Refresh Token'),
    (r'github_pat_[A-Za-z0-9_]{22,}', 'GitHub Fine-grained PAT'),
    # OpenAI / AI provider keys
    (r'sk-[A-Za-z0-9]{32,}', 'API Secret Key (sk-)'),
    # npm tokens
    (r'npm_[A-Za-z0-9]{36,}', 'npm Token'),
    # AWS
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    # Generic Bearer tokens (long ones only)
    (r'Bearer\s+[A-Za-z0-9\-._~+/]{40,}', 'Bearer Token'),
]

# Paths/content to exclude from scanning (avoid false positives)
EXCLUDE_PATH_PATTERNS = [
    r'\.env\.example',
    r'\.env\.template',
    r'README\.md',
    r'CLAUDE\.md',
    r'\.gitignore',
]


def get_content_to_scan(tool_input, tool_name):
    """Extract the content to scan based on tool type."""
    if tool_name == 'Bash':
        return tool_input.get('command', '')
    elif tool_name == 'Write':
        return tool_input.get('content', '')
    elif tool_name == 'Edit':
        return tool_input.get('new_string', '')
    return ''


def is_excluded_path(file_path):
    """Check if the file path should be excluded from scanning."""
    if not file_path:
        return False
    for pattern in EXCLUDE_PATH_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    return False


def scan_for_secrets(content):
    """Scan content for secret patterns. Returns list of (match, type) tuples."""
    found = []
    has_secret_context = bool(SECRET_CONTEXT_KEYWORDS.search(content))

    for pattern, secret_type in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            found.append((match[:12] + '...', secret_type))

    # Azure DevOps PAT: only check if content has secret-context keywords
    if has_secret_context:
        pat_matches = re.findall(r'\b[a-z2-7]{52}\b', content)
        for match in pat_matches:
            # Skip if part of a longer base32 sequence (hash/encoded data)
            if re.search(r'[a-z2-7]{60,}', content):
                continue
            found.append((match[:12] + '...', 'Azure DevOps PAT'))

    return found


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        print(f"pm-guidelines:pat_token_guard: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Check if path is excluded
    file_path = tool_input.get('file_path', '')
    if is_excluded_path(file_path):
        sys.exit(0)

    # Get content to scan
    content = get_content_to_scan(tool_input, tool_name)
    if not content:
        sys.exit(0)

    # Scan for secrets
    secrets = scan_for_secrets(content)
    if not secrets:
        sys.exit(0)

    # Block with details
    secret_list = '\n'.join(f'  - {stype}: {preview}' for preview, stype in secrets[:3])
    result = {
        "decision": "block",
        "reason": f"[pm-guidelines] Blocked: detected potential secret(s):\n{secret_list}\n\nNever write secrets to files or commands. Use environment variables or secure vaults."
    }
    print(json.dumps(result))
    sys.exit(2)


if __name__ == '__main__':
    main()
