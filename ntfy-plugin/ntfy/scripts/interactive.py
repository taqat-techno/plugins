#!/usr/bin/env python3
"""
Interactive Two-Way Notification System
========================================

This module enables Claude Code to send notifications with action buttons
and WAIT for the user's response. This creates true two-way communication
between Claude and the user's phone.

Features:
- Send notifications with clickable action buttons
- Poll for user's button click response
- Configurable timeout with graceful fallback
- Support for multiple choice questions
- Auto-cleanup of old responses

Usage:
    from interactive import ask_user, ask_yes_no, ask_choice

    # Simple yes/no question
    response = ask_yes_no("Deploy to production?", "All tests passed.")
    if response == "YES":
        deploy()

    # Multiple choice
    choice = ask_choice(
        "Select Database",
        "Which database should we use?",
        ["PostgreSQL", "MySQL", "SQLite"]
    )

    # Custom options with full control
    response = ask_user(
        title="Approval Needed",
        message="Ready to merge PR #123?",
        options=["Approve", "Reject", "Review Later"],
        timeout=120
    )

Author: TaqaTechno
License: MIT
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Union

# Add plugin directory to path
PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PLUGIN_DIR))

try:
    import requests
except ImportError:
    requests = None
    print("[WARNING] 'requests' module not installed. Run: pip install requests")

from notify import load_config, get_topic


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_TIMEOUT = 120  # seconds (2 minutes)
POLL_INTERVAL = 2  # seconds between polls
MAX_POLL_ATTEMPTS = 60  # Maximum poll attempts before timeout


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

def ask_user(
    title: str,
    message: str,
    options: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    priority: str = "high",
    tags: List[str] = None,
    silent: bool = False
) -> Optional[str]:
    """
    Send notification with action buttons and wait for user response.

    This is the PRIMARY function for two-way communication. It:
    1. Sends a notification with clickable action buttons
    2. Polls the ntfy topic for the user's response
    3. Returns the selected option or None on timeout

    Args:
        title: Notification title
        message: Question or prompt for the user
        options: List of choices (2-4 options recommended)
        timeout: Seconds to wait for response (default: 120)
        priority: Notification priority (default: "high")
        tags: Emoji tags (default: ["question", "bell"])
        silent: Don't print status messages

    Returns:
        str: The option the user selected, or None if timeout

    Example:
        response = ask_user(
            "Database Selection",
            "Which database should we use for this project?",
            ["PostgreSQL", "MySQL", "SQLite"],
            timeout=60
        )

        if response == "PostgreSQL":
            setup_postgres()
        elif response is None:
            print("User didn't respond, using default")
    """
    if requests is None:
        print("[ERROR] requests module required. Run: pip install requests")
        return None

    config = load_config()
    topic = get_topic()

    if not topic:
        print("[ERROR] No ntfy topic configured. Run /ntfy-setup first.")
        return None

    # Default tags for questions
    if tags is None:
        tags = ["question", "bell"]

    # Record timestamp before sending (to filter old messages)
    send_time = int(time.time())

    # Send notification with action buttons
    if not silent:
        print(f"\n[NTFY] Sending question to your phone...")
        print(f"[NTFY] Options: {', '.join(options)}")

    success = _send_notification_with_actions(
        title=title,
        message=message,
        options=options,
        priority=priority,
        tags=tags,
        topic=topic,
        config=config
    )

    if not success:
        print("[ERROR] Failed to send notification")
        return None

    if not silent:
        print(f"[NTFY] Waiting for your response (timeout: {timeout}s)...")
        print("[NTFY] Tap a button on your phone to respond.")

    # Poll for response
    response = _poll_for_response(
        topic=topic,
        config=config,
        expected_values=[opt.upper() for opt in options],
        since_time=send_time,
        timeout=timeout,
        silent=silent
    )

    if response:
        # Match back to original option (case-insensitive)
        for opt in options:
            if opt.upper() == response.upper():
                if not silent:
                    print(f"\n[NTFY] User selected: {opt}")
                return opt
        return response
    else:
        if not silent:
            print(f"\n[NTFY] No response received (timeout after {timeout}s)")
        return None


def ask_yes_no(
    title: str,
    message: str,
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False
) -> Optional[str]:
    """
    Send a Yes/No question and wait for response.

    Args:
        title: Question title
        message: Question details
        timeout: Seconds to wait
        silent: Don't print status

    Returns:
        "YES", "NO", or None if timeout

    Example:
        if ask_yes_no("Continue?", "Process 500 files?") == "YES":
            process_files()
    """
    return ask_user(
        title=title,
        message=message,
        options=["Yes", "No"],
        timeout=timeout,
        priority="high",
        tags=["question", "white_check_mark", "x"],
        silent=silent
    )


def ask_choice(
    title: str,
    message: str,
    choices: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False
) -> Optional[str]:
    """
    Present multiple choices and wait for selection.

    Args:
        title: Question title
        message: Question details
        choices: List of options (2-4 recommended)
        timeout: Seconds to wait
        silent: Don't print status

    Returns:
        Selected choice string, or None if timeout

    Example:
        db = ask_choice(
            "Database",
            "Select database type:",
            ["PostgreSQL", "MySQL", "SQLite"]
        )
    """
    return ask_user(
        title=title,
        message=message,
        options=choices,
        timeout=timeout,
        priority="high",
        tags=["question", "thinking"],
        silent=silent
    )


def ask_confirm(
    action: str,
    details: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False
) -> bool:
    """
    Ask for confirmation before proceeding.

    Args:
        action: What action needs confirmation
        details: Additional details
        timeout: Seconds to wait
        silent: Don't print status

    Returns:
        True if confirmed, False otherwise

    Example:
        if ask_confirm("Delete all logs", "This cannot be undone"):
            delete_logs()
    """
    message = f"Please confirm: {action}"
    if details:
        message += f"\n\n{details}"

    response = ask_user(
        title=f"Confirm: {action}",
        message=message,
        options=["Confirm", "Cancel"],
        timeout=timeout,
        priority="urgent",
        tags=["warning", "bell"],
        silent=silent
    )

    return response == "Confirm"


def ask_approval(
    item: str,
    description: str,
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False
) -> Optional[str]:
    """
    Request approval with Approve/Reject/Later options.

    Args:
        item: What needs approval
        description: Details about the item
        timeout: Seconds to wait
        silent: Don't print status

    Returns:
        "APPROVE", "REJECT", "LATER", or None if timeout

    Example:
        result = ask_approval("PR #123", "Adds user authentication feature")
        if result == "APPROVE":
            merge_pr()
    """
    return ask_user(
        title=f"Approval: {item}",
        message=description,
        options=["Approve", "Reject", "Later"],
        timeout=timeout,
        priority="urgent",
        tags=["clipboard", "bell"],
        silent=silent
    )


# =============================================================================
# INTERNAL FUNCTIONS
# =============================================================================

def _send_notification_with_actions(
    title: str,
    message: str,
    options: List[str],
    priority: str,
    tags: List[str],
    topic: str,
    config: dict
) -> bool:
    """
    Send notification with action buttons via HTTP header format.

    ntfy action format: "http, Label, URL, body=VALUE"
    """
    server = config.get('server', 'https://ntfy.sh')
    url = f"{server.rstrip('/')}/{topic}"

    # Build action header
    # Each action sends its value back to the same topic
    actions = []
    for option in options:
        # Action format: http, Label, URL, body=VALUE
        action_value = option.upper().replace(" ", "_")
        actions.append(f"http, {option}, {url}, body={action_value}")

    action_header = "; ".join(actions)

    # Build headers
    headers = {
        "Title": title.encode('ascii', 'ignore').decode('ascii'),
        "Priority": priority,
        "Tags": ",".join(tags) if tags else "question",
        "Actions": action_header
    }

    try:
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send notification: {e}")
        return False


def _poll_for_response(
    topic: str,
    config: dict,
    expected_values: List[str],
    since_time: int,
    timeout: int,
    silent: bool = False
) -> Optional[str]:
    """
    Poll ntfy topic for user's button click response.

    Args:
        topic: ntfy topic name
        config: Plugin configuration
        expected_values: List of expected response values (uppercase)
        since_time: Unix timestamp to filter messages after
        timeout: Maximum seconds to wait
        silent: Don't print progress

    Returns:
        The response value if found, None if timeout
    """
    server = config.get('server', 'https://ntfy.sh')
    poll_url = f"{server.rstrip('/')}/{topic}/json?poll=1&since={since_time}"

    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        attempt += 1
        elapsed = int(time.time() - start_time)

        if not silent and attempt % 5 == 0:
            remaining = timeout - elapsed
            print(f"[NTFY] Still waiting... ({remaining}s remaining)")

        try:
            response = requests.get(poll_url, timeout=5)

            if response.status_code == 200:
                # Parse JSON lines response
                for line in response.text.strip().split('\n'):
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)

                        # Skip if this is our outgoing notification
                        if msg.get('title') or msg.get('actions'):
                            continue

                        # Check if message matches expected values
                        msg_text = msg.get('message', '').upper().strip()

                        for expected in expected_values:
                            if msg_text == expected or msg_text == expected.replace("_", " "):
                                return msg_text

                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            if not silent:
                print(f"[WARN] Poll error: {e}")

        # Wait before next poll
        time.sleep(POLL_INTERVAL)

    return None


def _clear_old_responses(topic: str, config: dict) -> int:
    """
    Clear old responses from the topic (by reading them).

    Returns number of messages cleared.
    """
    server = config.get('server', 'https://ntfy.sh')
    poll_url = f"{server.rstrip('/')}/{topic}/json?poll=1&since=1h"

    try:
        response = requests.get(poll_url, timeout=5)
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            return len([l for l in lines if l])
    except:
        pass

    return 0


# =============================================================================
# QUICK FUNCTIONS
# =============================================================================

def quick_ask(message: str, options: List[str], timeout: int = 60) -> Optional[str]:
    """
    Quick ask with minimal parameters.

    Example:
        choice = quick_ask("Continue?", ["Yes", "No"])
    """
    return ask_user(
        title="Quick Question",
        message=message,
        options=options,
        timeout=timeout,
        silent=True
    )


# =============================================================================
# TESTING
# =============================================================================

def test_interactive():
    """Test the interactive notification system."""
    print("=" * 60)
    print("Interactive Notification Test")
    print("=" * 60)
    print("")

    response = ask_user(
        title="Test Question",
        message="This is a test of the interactive notification system.\n\n"
                "Please tap one of the buttons below:",
        options=["Option A", "Option B", "Option C"],
        timeout=60
    )

    print("")
    print("=" * 60)
    if response:
        print(f"SUCCESS! You selected: {response}")
    else:
        print("No response received (timeout)")
    print("=" * 60)

    return response


if __name__ == "__main__":
    test_interactive()
