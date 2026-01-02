#!/usr/bin/env python3
"""
Interactive Two-Way Notification System (iOS + Android Compatible)
===================================================================

This module enables Claude Code to send notifications with action buttons
and WAIT for the user's response. Supports BOTH iOS and Android!

PLATFORM DIFFERENCES:
- Android: Uses native action buttons (tap button directly)
- iOS: Uses text-based replies (tap notification → type response)

iOS LIMITATION:
ntfy action buttons are NOT supported on iOS (only Android + Web).
This module provides a cross-platform solution using numbered replies.

Features:
- Cross-platform support (iOS + Android)
- Send notifications with clickable action buttons (Android)
- Text-based reply fallback (iOS)
- Poll for user's response
- Configurable timeout with graceful fallback
- Auto-detect platform preference

Usage:
    from interactive import ask_user, ask_yes_no, ask_choice

    # Works on both iOS and Android!
    response = ask_yes_no("Deploy?", "All tests passed.")
    if response == "YES":
        deploy()

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

# Platform modes
PLATFORM_AUTO = "auto"  # Try to detect best method
PLATFORM_ANDROID = "android"  # Use action buttons (Android/Web)
PLATFORM_IOS = "ios"  # Use text-based replies (iOS)
PLATFORM_UNIVERSAL = "universal"  # Works on all platforms


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
    silent: bool = False,
    platform: str = None
) -> Optional[str]:
    """
    Send notification with action buttons and wait for user response.

    CROSS-PLATFORM: Works on both iOS and Android!

    - Android: Shows clickable action buttons
    - iOS: Shows numbered options, user replies with number or text

    Args:
        title: Notification title
        message: Question or prompt for the user
        options: List of choices (2-4 options recommended)
        timeout: Seconds to wait for response (default: 120)
        priority: Notification priority (default: "high")
        tags: Emoji tags (default: ["question", "bell"])
        silent: Don't print status messages
        platform: Force platform mode ("ios", "android", "universal", or None for config)

    Returns:
        str: The option the user selected, or None if timeout

    Example:
        response = ask_user(
            "Database Selection",
            "Which database should we use?",
            ["PostgreSQL", "MySQL", "SQLite"],
            timeout=60
        )
    """
    if requests is None:
        print("[ERROR] requests module required. Run: pip install requests")
        return None

    config = load_config()
    topic = get_topic()

    if not topic:
        print("[ERROR] No ntfy topic configured. Run /ntfy-setup first.")
        return None

    # Determine platform mode
    if platform is None:
        platform = config.get('platform', PLATFORM_UNIVERSAL)

    # Default tags for questions
    if tags is None:
        tags = ["question", "bell"]

    # Record timestamp before sending
    send_time = int(time.time())

    if not silent:
        print(f"\n[NTFY] Sending question to your phone...")
        print(f"[NTFY] Options: {', '.join(options)}")
        print(f"[NTFY] Platform mode: {platform}")

    # Send notification based on platform
    if platform == PLATFORM_ANDROID:
        success = _send_android_notification(
            title, message, options, priority, tags, topic, config
        )
        expected_values = [opt.upper().replace(" ", "_") for opt in options]
    elif platform == PLATFORM_IOS:
        success = _send_ios_notification(
            title, message, options, priority, tags, topic, config
        )
        expected_values = _get_ios_expected_values(options)
    else:  # PLATFORM_UNIVERSAL or PLATFORM_AUTO
        success = _send_universal_notification(
            title, message, options, priority, tags, topic, config
        )
        expected_values = _get_universal_expected_values(options)

    if not success:
        print("[ERROR] Failed to send notification")
        return None

    if not silent:
        print(f"[NTFY] Waiting for your response (timeout: {timeout}s)...")
        server = config.get('server', 'https://ntfy.sh')
        web_url = f"{server.rstrip('/')}/{topic}"
        if platform in [PLATFORM_IOS, PLATFORM_UNIVERSAL]:
            print(f"[NTFY] iOS: Open browser -> {web_url} -> type your choice")
        if platform in [PLATFORM_ANDROID, PLATFORM_UNIVERSAL]:
            print("[NTFY] Android: Tap an action button to respond")

    # Poll for response
    response = _poll_for_response(
        topic=topic,
        config=config,
        expected_values=expected_values,
        options=options,
        since_time=send_time,
        timeout=timeout,
        silent=silent
    )

    if response:
        # Match back to original option
        matched = _match_response_to_option(response, options)
        if not silent:
            print(f"\n[NTFY] User selected: {matched}")
        return matched
    else:
        if not silent:
            print(f"\n[NTFY] No response received (timeout after {timeout}s)")
        return None


def ask_yes_no(
    title: str,
    message: str,
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False,
    platform: str = None
) -> Optional[str]:
    """
    Send a Yes/No question and wait for response.
    Works on both iOS and Android!

    Returns:
        "Yes", "No", or None if timeout
    """
    response = ask_user(
        title=title,
        message=message,
        options=["Yes", "No"],
        timeout=timeout,
        priority="high",
        tags=["question", "white_check_mark", "x"],
        silent=silent,
        platform=platform
    )
    return response


def ask_choice(
    title: str,
    message: str,
    choices: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False,
    platform: str = None
) -> Optional[str]:
    """
    Present multiple choices and wait for selection.
    Works on both iOS and Android!

    Returns:
        Selected choice string, or None if timeout
    """
    return ask_user(
        title=title,
        message=message,
        options=choices,
        timeout=timeout,
        priority="high",
        tags=["question", "thinking"],
        silent=silent,
        platform=platform
    )


def ask_confirm(
    action: str,
    details: str = "",
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False,
    platform: str = None
) -> bool:
    """
    Ask for confirmation before proceeding.
    Works on both iOS and Android!

    Returns:
        True if confirmed, False otherwise
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
        silent=silent,
        platform=platform
    )

    return response == "Confirm"


def ask_approval(
    item: str,
    description: str,
    timeout: int = DEFAULT_TIMEOUT,
    silent: bool = False,
    platform: str = None
) -> Optional[str]:
    """
    Request approval with Approve/Reject/Later options.
    Works on both iOS and Android!

    Returns:
        "Approve", "Reject", "Later", or None if timeout
    """
    return ask_user(
        title=f"Approval: {item}",
        message=description,
        options=["Approve", "Reject", "Later"],
        timeout=timeout,
        priority="urgent",
        tags=["clipboard", "bell"],
        silent=silent,
        platform=platform
    )


# =============================================================================
# PLATFORM-SPECIFIC NOTIFICATION SENDERS
# =============================================================================

def _send_android_notification(
    title: str,
    message: str,
    options: List[str],
    priority: str,
    tags: List[str],
    topic: str,
    config: dict
) -> bool:
    """
    Send notification with HTTP action buttons (Android only).
    """
    server = config.get('server', 'https://ntfy.sh')
    url = f"{server.rstrip('/')}/{topic}"

    # Build action buttons that POST back to the topic
    actions = []
    for option in options:
        action_value = option.upper().replace(" ", "_")
        actions.append(f"http, {option}, {url}, body={action_value}")

    action_header = "; ".join(actions)

    headers = {
        "Title": title.encode('ascii', 'ignore').decode('ascii'),
        "Priority": priority,
        "Tags": ",".join(tags) if tags else "question",
        "Actions": action_header
    }

    try:
        response = requests.post(url, data=message.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send notification: {e}")
        return False


def _send_ios_notification(
    title: str,
    message: str,
    options: List[str],
    priority: str,
    tags: List[str],
    topic: str,
    config: dict
) -> bool:
    """
    Send notification with numbered options for iOS text reply.

    iOS doesn't support action buttons, so we:
    1. Include numbered options in the message
    2. Add the web URL for easy reply (iOS app doesn't have easy publish)
    3. User opens browser → goes to ntfy.sh/topic → types response
    """
    server = config.get('server', 'https://ntfy.sh')
    url = f"{server.rstrip('/')}/{topic}"

    # Build web response URL
    web_url = f"{server.rstrip('/')}/{topic}"

    # Build message with numbered options + web URL
    options_text = "\n\nReply with number or text:\n"
    for i, opt in enumerate(options, 1):
        options_text += f"  {i} = {opt}\n"
    options_text += f"\nRespond via browser:\n{web_url}"

    full_message = message + options_text

    # Click action opens the web topic for easy reply
    click_url = web_url  # Opens browser to ntfy.sh/topic

    headers = {
        "Title": title.encode('ascii', 'ignore').decode('ascii'),
        "Priority": priority,
        "Tags": ",".join(tags) if tags else "question",
        "Click": click_url,  # Tap opens browser for reply
    }

    try:
        response = requests.post(url, data=full_message.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send notification: {e}")
        return False


def _send_universal_notification(
    title: str,
    message: str,
    options: List[str],
    priority: str,
    tags: List[str],
    topic: str,
    config: dict
) -> bool:
    """
    Send notification that works on BOTH iOS and Android.

    - Android: Gets action buttons (tap button directly)
    - iOS: Gets numbered options + web URL to respond via browser
    """
    server = config.get('server', 'https://ntfy.sh')
    url = f"{server.rstrip('/')}/{topic}"

    # Build web response URL for iOS users
    web_url = f"{server.rstrip('/')}/{topic}"

    # Build message with numbered options (for iOS)
    options_text = "\n\n"
    options_text += "Android: Tap a button below\n"
    options_text += "iOS: Reply with number via browser:\n"
    for i, opt in enumerate(options, 1):
        options_text += f"  {i} = {opt}\n"
    options_text += f"\niOS respond: {web_url}"

    full_message = message + options_text

    # Build action buttons (for Android)
    actions = []
    for option in options:
        action_value = option.upper().replace(" ", "_")
        actions.append(f"http, {option}, {url}, body={action_value}")

    action_header = "; ".join(actions)

    # Click action opens browser for reply (iOS)
    click_url = web_url

    headers = {
        "Title": title.encode('ascii', 'ignore').decode('ascii'),
        "Priority": priority,
        "Tags": ",".join(tags) if tags else "question",
        "Actions": action_header,  # Android buttons
        "Click": click_url,  # iOS opens browser
    }

    try:
        response = requests.post(url, data=full_message.encode('utf-8'), headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"[ERROR] Failed to send notification: {e}")
        return False


# =============================================================================
# RESPONSE HANDLING
# =============================================================================

def _get_ios_expected_values(options: List[str]) -> List[str]:
    """Get expected response values for iOS text replies."""
    values = []
    for i, opt in enumerate(options, 1):
        values.append(str(i))  # "1", "2", "3"
        values.append(opt.upper())  # "YES", "NO"
        values.append(opt.lower())  # "yes", "no"
        values.append(opt)  # "Yes", "No" (exact)
    return values


def _get_universal_expected_values(options: List[str]) -> List[str]:
    """Get expected response values for universal mode (iOS + Android)."""
    values = []
    for i, opt in enumerate(options, 1):
        # Numbers (iOS)
        values.append(str(i))
        # Text variations
        values.append(opt.upper())
        values.append(opt.lower())
        values.append(opt)
        # Android action format
        values.append(opt.upper().replace(" ", "_"))
    return values


def _match_response_to_option(response: str, options: List[str]) -> str:
    """Match a response back to the original option."""
    response_clean = response.strip()

    # Check if it's a number
    if response_clean.isdigit():
        idx = int(response_clean) - 1
        if 0 <= idx < len(options):
            return options[idx]

    # Check direct match (case-insensitive)
    for opt in options:
        if response_clean.upper() == opt.upper():
            return opt
        if response_clean.upper() == opt.upper().replace(" ", "_"):
            return opt

    # Return cleaned response if no match
    return response_clean


def _poll_for_response(
    topic: str,
    config: dict,
    expected_values: List[str],
    options: List[str],
    since_time: int,
    timeout: int,
    silent: bool = False
) -> Optional[str]:
    """
    Poll ntfy topic for user's response (works for both platforms).
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
                for line in response.text.strip().split('\n'):
                    if not line:
                        continue

                    try:
                        msg = json.loads(line)

                        # Skip our outgoing notification
                        if msg.get('title') or msg.get('actions'):
                            continue

                        # Check message content
                        msg_text = msg.get('message', '').strip()

                        # Check against expected values
                        for expected in expected_values:
                            if msg_text.upper() == expected.upper():
                                return msg_text
                            if msg_text == expected:
                                return msg_text

                        # Also check if it's a valid number response
                        if msg_text.isdigit():
                            idx = int(msg_text) - 1
                            if 0 <= idx < len(options):
                                return msg_text

                    except json.JSONDecodeError:
                        continue

        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            if not silent:
                print(f"[WARN] Poll error: {e}")

        time.sleep(POLL_INTERVAL)

    return None


# =============================================================================
# QUICK FUNCTIONS
# =============================================================================

def quick_ask(message: str, options: List[str], timeout: int = 60) -> Optional[str]:
    """Quick ask with minimal parameters."""
    return ask_user(
        title="Quick Question",
        message=message,
        options=options,
        timeout=timeout,
        silent=True
    )


# =============================================================================
# PLATFORM CONFIGURATION
# =============================================================================

def set_platform(platform: str) -> bool:
    """
    Set the default platform mode.

    Options:
        "ios" - Use text-based replies (for iOS users)
        "android" - Use action buttons (for Android users)
        "universal" - Works on both (default)
    """
    if platform not in [PLATFORM_IOS, PLATFORM_ANDROID, PLATFORM_UNIVERSAL]:
        print(f"[ERROR] Invalid platform. Use: ios, android, or universal")
        return False

    config = load_config()
    config['platform'] = platform

    config_path = PLUGIN_DIR / 'config.json'
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"[OK] Platform set to: {platform}")
    return True


def get_platform() -> str:
    """Get the current platform mode."""
    config = load_config()
    return config.get('platform', PLATFORM_UNIVERSAL)


# =============================================================================
# TESTING
# =============================================================================

def test_interactive(platform: str = None):
    """Test the interactive notification system."""
    print("=" * 60)
    print("Interactive Notification Test")
    print("=" * 60)
    print("")
    print("Platform modes:")
    print("  - 'universal': Works on iOS and Android (default)")
    print("  - 'ios': Optimized for iOS (text replies)")
    print("  - 'android': Optimized for Android (action buttons)")
    print("")

    current_platform = platform or get_platform()
    print(f"Testing with platform: {current_platform}")
    print("")

    response = ask_user(
        title="Test Question",
        message="This is a test of the interactive notification system.\n\n"
                "Please respond using your preferred method.",
        options=["Option A", "Option B", "Option C"],
        timeout=60,
        platform=platform
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
    import sys
    platform = sys.argv[1] if len(sys.argv) > 1 else None
    test_interactive(platform)
