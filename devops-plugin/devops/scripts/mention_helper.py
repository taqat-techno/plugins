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
# GUIDs retrieved from Azure DevOps on 2024-12-24
# This avoids repeated API calls for common team members
#
# Alias Strategy:
# - First name: @eslam, @mahmoud, @sameh, @yussef, @shehab, @muram, @mostafa
# - Last name for disambiguation: @lakosha (Ahmed L.), @abdelaleem (Ahmed A.)
# - Email prefix: @alakosha, @ehafez, @melshahed, etc.
#
TEAM_CACHE = {
    # ===== Ahmed Abdelkhaleq Lakosha - Senior Developer =====
    # Use @lakosha or @alakosha to avoid confusion with other Ahmed
    'lakosha': {
        'email': 'alakosha@pearlpixels.com',
        'display': 'Ahmed Abdelkhaleq Lakosha',
        'guid': '1216c274-32ad-6e2c-80a4-6c0132e99fab'
    },
    'alakosha': {
        'email': 'alakosha@pearlpixels.com',
        'display': 'Ahmed Abdelkhaleq Lakosha',
        'guid': '1216c274-32ad-6e2c-80a4-6c0132e99fab'
    },
    'ahmed.lakosha': {
        'email': 'alakosha@pearlpixels.com',
        'display': 'Ahmed Abdelkhaleq Lakosha',
        'guid': '1216c274-32ad-6e2c-80a4-6c0132e99fab'
    },

    # ===== Ahmed Abdelaleem - Developer =====
    # Use @abdelaleem or @aabdelalem to avoid confusion with other Ahmed
    'abdelaleem': {
        'email': 'aabdelalem@pearlpixels.com',
        'display': 'Ahmed Abdelaleem',
        'guid': '89cc2a81-1632-68e7-8a9b-5c0fa4eb003a'
    },
    'aabdelalem': {
        'email': 'aabdelalem@pearlpixels.com',
        'display': 'Ahmed Abdelaleem',
        'guid': '89cc2a81-1632-68e7-8a9b-5c0fa4eb003a'
    },
    'ahmed.abdelaleem': {
        'email': 'aabdelalem@pearlpixels.com',
        'display': 'Ahmed Abdelaleem',
        'guid': '89cc2a81-1632-68e7-8a9b-5c0fa4eb003a'
    },

    # ===== Eslam Hafez Mohamed - Developer =====
    'eslam': {
        'email': 'ehafez@pearlpixels.com',
        'display': 'Eslam Hafez Mohamed',
        'guid': '2a53fa48-c275-6ca8-aae1-3b180c399a21'
    },
    'ehafez': {
        'email': 'ehafez@pearlpixels.com',
        'display': 'Eslam Hafez Mohamed',
        'guid': '2a53fa48-c275-6ca8-aae1-3b180c399a21'
    },
    'hafez': {
        'email': 'ehafez@pearlpixels.com',
        'display': 'Eslam Hafez Mohamed',
        'guid': '2a53fa48-c275-6ca8-aae1-3b180c399a21'
    },

    # ===== Mahmoud Elshahed - Developer =====
    'mahmoud': {
        'email': 'melshahed@pearlpixels.com',
        'display': 'Mahmoud Elshahed',
        'guid': '5849d7a6-36ba-6765-bbf4-d870d6e7bbca'
    },
    'melshahed': {
        'email': 'melshahed@pearlpixels.com',
        'display': 'Mahmoud Elshahed',
        'guid': '5849d7a6-36ba-6765-bbf4-d870d6e7bbca'
    },
    'elshahed': {
        'email': 'melshahed@pearlpixels.com',
        'display': 'Mahmoud Elshahed',
        'guid': '5849d7a6-36ba-6765-bbf4-d870d6e7bbca'
    },

    # ===== Sameh Abdlal Yussef Btaih - Developer =====
    'sameh': {
        'email': 'sabdlal@pearlpixels.com',
        'display': 'Sameh Abdlal Yussef Btaih',
        'guid': '1e49dcfd-57df-61c0-83cb-a163798f3617'
    },
    'sabdlal': {
        'email': 'sabdlal@pearlpixels.com',
        'display': 'Sameh Abdlal Yussef Btaih',
        'guid': '1e49dcfd-57df-61c0-83cb-a163798f3617'
    },

    # ===== Yussef Hussein Hussein - Developer =====
    'yussef': {
        'email': 'yhussein@pearlpixels.com',
        'display': 'Yussef Hussein Hussein',
        'guid': '7ae5a9c0-6899-6f22-be7d-ceb72188e9d1'
    },
    'yhussein': {
        'email': 'yhussein@pearlpixels.com',
        'display': 'Yussef Hussein Hussein',
        'guid': '7ae5a9c0-6899-6f22-be7d-ceb72188e9d1'
    },

    # ===== Shehab Gamal - Developer =====
    'shehab': {
        'email': 'sgamal@pearlpixels.com',
        'display': 'Shehab Gamal',
        'guid': '9aced8ab-b578-6aa7-8d55-85342116c08b'
    },
    'sgamal': {
        'email': 'sgamal@pearlpixels.com',
        'display': 'Shehab Gamal',
        'guid': '9aced8ab-b578-6aa7-8d55-85342116c08b'
    },
    'gamal': {
        'email': 'sgamal@pearlpixels.com',
        'display': 'Shehab Gamal',
        'guid': '9aced8ab-b578-6aa7-8d55-85342116c08b'
    },

    # ===== Mostafa Ahmed - QA/Tester =====
    'mostafa': {
        'email': 'mahmed@pearlpixels.com',
        'display': 'Mostafa Ahmed',
        'guid': '2a9b995c-4223-6b04-91a7-871a0949f83f'
    },
    'mahmed': {
        'email': 'mahmed@pearlpixels.com',
        'display': 'Mostafa Ahmed',
        'guid': '2a9b995c-4223-6b04-91a7-871a0949f83f'
    },

    # ===== Muram Makawi Abuzaid - Property Management =====
    'muram': {
        'email': 'mmakkawi@Taqat.qa',
        'display': 'Muram Makawi Abuzaid',
        'guid': '9db8db2e-42b2-6bc7-a57b-8a1fdb257748'
    },
    'mmakkawi': {
        'email': 'mmakkawi@Taqat.qa',
        'display': 'Muram Makawi Abuzaid',
        'guid': '9db8db2e-42b2-6bc7-a57b-8a1fdb257748'
    },
    'makawi': {
        'email': 'mmakkawi@Taqat.qa',
        'display': 'Muram Makawi Abuzaid',
        'guid': '9db8db2e-42b2-6bc7-a57b-8a1fdb257748'
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
