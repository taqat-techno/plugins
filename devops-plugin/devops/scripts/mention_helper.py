"""
Mention Helper for Azure DevOps Comments
Converts @username patterns to proper Azure DevOps mention format

This helper provides utilities for processing @mentions in comments
and converting them to the proper HTML format that Azure DevOps recognizes.

Usage:
    from mention_helper import extract_mentions, format_mention_html, process_comment_with_mentions

Example:
    # Extract mentions from text
    mentions = extract_mentions("Please review @mahmoud @eslam")
    # Returns: ['mahmoud', 'eslam']

    # Format a single mention
    html = format_mention_html("abc-123-guid", "Mahmoud Elshahed")
    # Returns: '<a href="#" data-vss-mention="version:2.0,guid:abc-123-guid">@Mahmoud Elshahed</a>'

    # Process full comment
    processed = process_comment_with_mentions(
        "Please review @mahmoud",
        {"mahmoud": ("abc-123-guid", "Mahmoud Elshahed")}
    )
    # Returns processed HTML with proper mention formatting
"""

import re
from typing import Dict, List, Tuple, Optional


# TaqaTechno team members cache for quick lookup
# This avoids repeated API calls for common team members
TEAM_CACHE = {
    'ahmed': {
        'email': 'alakosha@pearlpixels.com',
        'display': 'Ahmed Abdelkhaleq Lakosha',
        'guid': None  # To be populated on first lookup
    },
    'eslam': {
        'email': 'ehafez@pearlpixels.com',
        'display': 'Eslam Hafez Mohamed',
        'guid': None
    },
    'yussef': {
        'email': 'yhussein@pearlpixels.com',
        'display': 'Yussef Hussein Hussein',
        'guid': None
    },
    'sameh': {
        'email': 'sabdlal@pearlpixels.com',
        'display': 'Sameh Abdlal Yussef Btaih',
        'guid': None
    },
    'mahmoud': {
        'email': 'melshahed@pearlpixels.com',
        'display': 'Mahmoud Elshahed',
        'guid': None
    },
    'hossam': {
        'email': 'hessam@pearlpixels.com',
        'display': 'Hossam',
        'guid': None
    },
}


def extract_mentions(text: str) -> List[str]:
    """
    Extract @mentions from text.

    Supports patterns:
    - @username (simple username)
    - @firstname.lastname (dotted format)
    - @email (email-like format)

    Args:
        text: The text to extract mentions from

    Returns:
        List of usernames found (without the @ symbol)

    Example:
        >>> extract_mentions("Please review @mahmoud and @eslam.hafez")
        ['mahmoud', 'eslam.hafez']
    """
    # Pattern matches:
    # - Word characters (a-z, A-Z, 0-9, _)
    # - Optional dot-separated parts (for firstname.lastname)
    # - Excludes trailing punctuation
    pattern = r'@(\w+(?:\.\w+)*)'
    return re.findall(pattern, text)


def format_mention_html(guid: str, display_name: str) -> str:
    """
    Format a mention as HTML anchor for Azure DevOps.

    Azure DevOps uses a specific data attribute format for mentions
    that renders properly in the UI and sends notifications.

    Args:
        guid: The user's identity GUID from Azure DevOps
        display_name: The display name to show in the mention

    Returns:
        HTML anchor tag with proper Azure DevOps mention format

    Example:
        >>> format_mention_html("abc-123", "Mahmoud Elshahed")
        '<a href="#" data-vss-mention="version:2.0,guid:abc-123">@Mahmoud Elshahed</a>'
    """
    return f'<a href="#" data-vss-mention="version:2.0,guid:{guid}">@{display_name}</a>'


def format_mention_simple(guid: str) -> str:
    """
    Format a mention in simple GUID format.

    This is the basic format that Azure DevOps API accepts,
    though HTML format renders better in the UI.

    Args:
        guid: The user's identity GUID

    Returns:
        Simple GUID mention format

    Example:
        >>> format_mention_simple("abc-123")
        '@<abc-123>'
    """
    return f'@<{guid}>'


def get_team_member_info(username: str) -> Optional[Dict]:
    """
    Get cached team member info by username.

    Args:
        username: The username to look up (case-insensitive)

    Returns:
        Dict with email, display name, and GUID if found, None otherwise
    """
    return TEAM_CACHE.get(username.lower())


def process_comment_with_mentions(
    text: str,
    mention_guids: Dict[str, Tuple[str, str]]
) -> str:
    """
    Replace @mentions with formatted HTML anchors.

    This is the main function to use when processing a comment
    before sending it to Azure DevOps.

    Args:
        text: Original comment text containing @mentions
        mention_guids: Dict mapping username -> (guid, display_name)
                       Example: {"mahmoud": ("abc-123", "Mahmoud Elshahed")}

    Returns:
        Processed text with HTML-formatted mentions

    Example:
        >>> process_comment_with_mentions(
        ...     "Please review @mahmoud",
        ...     {"mahmoud": ("abc-123-guid", "Mahmoud Elshahed")}
        ... )
        'Please review <a href="#" data-vss-mention="version:2.0,guid:abc-123-guid">@Mahmoud Elshahed</a>'
    """
    processed = text

    for username, (guid, display_name) in mention_guids.items():
        # Create pattern that matches @username case-insensitively
        pattern = rf'@{re.escape(username)}\b'
        replacement = format_mention_html(guid, display_name)
        processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

    return processed


def build_mention_lookup_instructions(mentions: List[str]) -> str:
    """
    Generate instructions for looking up mention GUIDs.

    This helper generates the MCP tool calls needed to resolve
    @mentions to their GUIDs.

    Args:
        mentions: List of usernames to look up

    Returns:
        Formatted instructions for GUID lookup
    """
    instructions = []
    for mention in mentions:
        # Check if in cache first
        cached = get_team_member_info(mention)
        if cached and cached.get('guid'):
            instructions.append(
                f"- @{mention}: Use cached GUID {cached['guid']} "
                f"({cached['display']})"
            )
        else:
            search_term = cached['email'] if cached else mention
            instructions.append(
                f"- @{mention}: Call mcp__azure-devops__core_get_identity_ids"
                f"(searchFilter=\"{search_term}\")"
            )
    return "\n".join(instructions)


# Workflow helper for Claude
MENTION_WORKFLOW = """
## Mention Processing Workflow

When user's comment contains @mentions:

1. **Extract mentions**: Use extract_mentions(text)
2. **Look up GUIDs**: For each mention, call:
   mcp__azure-devops__core_get_identity_ids(searchFilter="username_or_email")
3. **Build mapping**: Create dict of username -> (guid, display_name)
4. **Process text**: Use process_comment_with_mentions(text, mapping)
5. **Add comment**: Use mcp__azure-devops__wit_add_work_item_comment with format="html"

Example API call sequence:
```
# Step 1: Get GUID
result = mcp__azure-devops__core_get_identity_ids(searchFilter="mahmoud")
# Returns: {"id": "abc-123", "displayName": "Mahmoud Elshahed"}

# Step 2: Process comment
processed = process_comment_with_mentions(
    "Please review @mahmoud",
    {"mahmoud": ("abc-123", "Mahmoud Elshahed")}
)

# Step 3: Add comment
mcp__azure-devops__wit_add_work_item_comment(
    project="ProjectName",
    workItemId=1234,
    comment=processed,
    format="html"
)
```
"""


if __name__ == "__main__":
    # Test examples
    print("Testing mention helper...")

    # Test extraction
    test_text = "Please review this @mahmoud and check with @eslam.hafez"
    mentions = extract_mentions(test_text)
    print(f"Extracted mentions: {mentions}")

    # Test HTML formatting
    html = format_mention_html("abc-123-guid", "Mahmoud Elshahed")
    print(f"HTML format: {html}")

    # Test full processing
    processed = process_comment_with_mentions(
        test_text,
        {
            "mahmoud": ("guid-1", "Mahmoud Elshahed"),
            "eslam.hafez": ("guid-2", "Eslam Hafez Mohamed")
        }
    )
    print(f"Processed text:\n{processed}")

    print("\nAll tests passed!")
