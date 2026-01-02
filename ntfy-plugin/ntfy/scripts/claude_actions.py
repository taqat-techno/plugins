#!/usr/bin/env python3
"""
Claude Actions - Session-Aware Notification System for Claude Code
===================================================================

This module provides notification functions that Claude uses when
notification mode is enabled. All functions are SESSION-AWARE:
- Check if notification mode is ON
- Use session topic (custom or default)
- Only notify when mode is enabled

When notification mode is ON, Claude MUST use these functions.
When OFF, these functions return None/default values silently.

Usage:
    from claude_actions import (
        need_action,      # When Claude needs user decision
        task_done,        # When task completes (with next steps)
        ask_proceed,      # Yes/No approval
        ask_choice,       # Multiple choice
        get_user_input,   # Free text input
        blocked,          # When Claude is stuck
        error_occurred,   # On errors
        should_notify     # Check if mode is ON
    )

Author: TaqaTechno
License: MIT
"""

import sys
from pathlib import Path
from typing import Optional, List, Union

# Add plugin directory to path
PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PLUGIN_DIR))

from interactive import ask_user, ask_yes_no, ask_confirm
from notify import send_notification, load_config, get_topic
from session import (
    is_notification_mode_on,
    get_session_topic,
    increment_task_count,
    increment_notification_count,
    get_session_state
)


# =============================================================================
# SESSION-AWARE HELPERS
# =============================================================================

def should_notify() -> bool:
    """
    Check if Claude should send notifications.

    Returns True if notification mode is ON.
    Claude should call this before any notification logic.

    Example:
        if should_notify():
            # Send notification
        else:
            # Just proceed silently
    """
    return is_notification_mode_on()


def _get_web_url() -> str:
    """Get the web URL for the current session topic."""
    config = load_config()
    server = config.get('server', 'https://ntfy.sh')
    topic = get_session_topic()
    return f"{server.rstrip('/')}/{topic}"


def _override_topic_temporarily():
    """Context manager to use session topic."""
    import json
    config_file = PLUGIN_DIR / "config.json"

    # Load current config
    with open(config_file, 'r') as f:
        config = json.load(f)

    original_topic = config.get('topic')
    session_topic = get_session_topic()

    # Update to session topic
    config['topic'] = session_topic
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    return original_topic, session_topic


def _restore_topic(original_topic: str):
    """Restore original topic after notification."""
    import json
    config_file = PLUGIN_DIR / "config.json"

    with open(config_file, 'r') as f:
        config = json.load(f)

    config['topic'] = original_topic
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

# =============================================================================
# MANDATORY ACTION NOTIFICATIONS
# =============================================================================

def need_action(
    title: str,
    message: str,
    options: List[str] = None,
    timeout: int = 300,
    allow_text: bool = True,
    force: bool = False
) -> Optional[str]:
    """
    Call this whenever Claude needs user input/decision.

    SESSION-AWARE: Only sends notification if notification mode is ON,
    unless force=True.

    Args:
        title: What action is needed (e.g., "Database Selection")
        message: Details about the decision
        options: List of choices (if None, expects free text)
        timeout: Seconds to wait (default: 5 minutes)
        allow_text: If True, user can also type custom response
        force: If True, send even if notification mode is OFF

    Returns:
        User's selection or typed response, None if mode OFF or timeout

    Example:
        response = need_action(
            "Deployment Target",
            "Where should I deploy?",
            ["Production", "Staging", "Development"]
        )
    """
    # Check if notification mode is on (unless forced)
    if not force and not should_notify():
        print(f"[CLAUDE] Action needed: {title} (notification mode OFF - skipping notification)")
        return None

    if options is None:
        options = ["Continue", "Cancel"]

    # Use session topic
    original_topic, session_topic = _override_topic_temporarily()
    web_url = _get_web_url()

    try:
        increment_notification_count()

        # Add web URL instruction to message
        full_message = message
        if allow_text:
            full_message += f"\n\n(You can also type a custom response)"

        print(f"\n[CLAUDE] Waiting for user action: {title}")
        print(f"[CLAUDE] Topic: {session_topic}")
        print(f"[CLAUDE] Respond at: {web_url}")

        response = ask_user(
            title=f"Action Required: {title}",
            message=full_message,
            options=options,
            timeout=timeout,
            priority="urgent",
            tags=["bell", "warning"],
            platform="ios"
        )

        return response
    finally:
        _restore_topic(original_topic)


def task_done(
    task_name: str,
    summary: str,
    next_steps: List[str] = None,
    auto_proceed: bool = False,
    timeout: int = 180,
    force: bool = False
) -> Optional[str]:
    """
    Call this when a task completes.

    SESSION-AWARE: Only sends notification if notification mode is ON,
    unless force=True.

    If next_steps are provided, sends interactive notification so user
    can choose to proceed with one of them directly from their phone.

    Args:
        task_name: Name of completed task
        summary: What was accomplished
        next_steps: Optional list of suggested next actions
        auto_proceed: If True and no response, proceed with first next_step
        timeout: Seconds to wait for response (default: 3 minutes)
        force: If True, send even if notification mode is OFF

    Returns:
        Selected next step, "done" if user chooses to stop, None if mode OFF/timeout

    Example:
        result = task_done(
            "API Integration",
            "Created REST endpoints for users and orders",
            next_steps=["Run tests", "Deploy to staging", "Update docs"]
        )
        if result == "Run tests":
            run_tests()
    """
    # Check if notification mode is on (unless forced)
    if not force and not should_notify():
        print(f"[CLAUDE] Task complete: {task_name} (notification mode OFF)")
        return "done"

    # Use session topic
    original_topic, session_topic = _override_topic_temporarily()
    web_url = _get_web_url()

    try:
        increment_task_count()
        increment_notification_count()

        if next_steps and len(next_steps) > 0:
            # Interactive notification with next step options
            options = next_steps + ["Done (no more actions)"]

            message = f"{summary}\n\nSuggested next steps available."

            print(f"\n[CLAUDE] Task complete: {task_name}")
            print(f"[CLAUDE] Topic: {session_topic}")
            print(f"[CLAUDE] Next steps available - waiting for choice")
            print(f"[CLAUDE] Respond at: {web_url}")

            response = ask_user(
                title=f"Complete: {task_name}",
                message=message,
                options=options,
                timeout=timeout,
                priority="high",
                tags=["white_check_mark", "arrow_right"],
                platform="ios"
            )

            if response is None and auto_proceed:
                print(f"[CLAUDE] No response, auto-proceeding with: {next_steps[0]}")
                return next_steps[0]

            if response and "Done" in response:
                return "done"

            return response
        else:
            # Simple completion notification (no interaction needed)
            send_notification(
                title=f"Complete: {task_name}",
                message=summary,
                priority="high",
                tags=["white_check_mark", "tada"]
            )
            print(f"\n[CLAUDE] Task complete: {task_name}")
            print(f"[CLAUDE] Topic: {session_topic}")
            return "done"
    finally:
        _restore_topic(original_topic)


def ask_proceed(
    action: str,
    details: str = "",
    timeout: int = 120
) -> bool:
    """
    Ask user if Claude should proceed with an action.

    Args:
        action: What Claude wants to do
        details: Additional context
        timeout: Seconds to wait

    Returns:
        True if user approves, False otherwise

    Example:
        if ask_proceed("Delete old log files", "This will remove 50 files"):
            delete_logs()
    """
    config = load_config()
    topic = get_topic()
    server = config.get('server', 'https://ntfy.sh')
    web_url = f"{server.rstrip('/')}/{topic}"

    message = f"Should I proceed with: {action}?"
    if details:
        message += f"\n\n{details}"

    print(f"\n[CLAUDE] Asking permission: {action}")
    print(f"[CLAUDE] Respond at: {web_url}")

    response = ask_user(
        title=f"Proceed: {action}?",
        message=message,
        options=["Yes, proceed", "No, skip"],
        timeout=timeout,
        priority="high",
        tags=["question", "arrow_right"],
        platform="ios"
    )

    return response is not None and "Yes" in response


def ask_choice(
    question: str,
    choices: List[str],
    context: str = "",
    timeout: int = 180
) -> Optional[str]:
    """
    Ask user to choose from multiple options.

    Args:
        question: The question to ask
        choices: List of options (max 4 recommended)
        context: Additional context
        timeout: Seconds to wait

    Returns:
        Selected choice or None if timeout

    Example:
        db = ask_choice(
            "Which database?",
            ["PostgreSQL", "MySQL", "SQLite"],
            "For the new user service"
        )
    """
    config = load_config()
    topic = get_topic()
    server = config.get('server', 'https://ntfy.sh')
    web_url = f"{server.rstrip('/')}/{topic}"

    message = question
    if context:
        message = f"{context}\n\n{question}"

    print(f"\n[CLAUDE] Asking choice: {question}")
    print(f"[CLAUDE] Options: {', '.join(choices)}")
    print(f"[CLAUDE] Respond at: {web_url}")

    return ask_user(
        title=question,
        message=message,
        options=choices,
        timeout=timeout,
        priority="high",
        tags=["question", "thinking"],
        platform="ios"
    )


def get_user_input(
    prompt: str,
    context: str = "",
    timeout: int = 300
) -> Optional[str]:
    """
    Get free-text input from user via notification.

    User can type any response, not limited to predefined options.

    Args:
        prompt: What to ask
        context: Additional context
        timeout: Seconds to wait (default: 5 minutes for typing)

    Returns:
        User's typed response or None if timeout

    Example:
        name = get_user_input(
            "What should I name the new module?",
            "Creating module for inventory management"
        )
    """
    config = load_config()
    topic = get_topic()
    server = config.get('server', 'https://ntfy.sh')
    web_url = f"{server.rstrip('/')}/{topic}"

    message = prompt
    if context:
        message = f"{context}\n\n{prompt}"
    message += f"\n\nType your response at:\n{web_url}"

    print(f"\n[CLAUDE] Waiting for text input: {prompt}")
    print(f"[CLAUDE] Type response at: {web_url}")

    # Send notification with instructions
    send_notification(
        title=f"Input Needed: {prompt[:50]}",
        message=message,
        priority="urgent",
        tags=["pencil", "bell"],
        click=web_url
    )

    # Poll for any response
    import time
    import json
    try:
        import requests
    except ImportError:
        print("[ERROR] requests module required")
        return None

    start_time = time.time()
    send_time = int(start_time)
    poll_url = f"{server.rstrip('/')}/{topic}/json?poll=1&since={send_time}"

    while time.time() - start_time < timeout:
        try:
            response = requests.get(poll_url, timeout=5)
            if response.status_code == 200:
                for line in response.text.strip().split('\n'):
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        # Skip our outgoing notification
                        if msg.get('title'):
                            continue
                        msg_text = msg.get('message', '').strip()
                        if msg_text:
                            print(f"\n[CLAUDE] Received input: {msg_text}")
                            return msg_text
                    except json.JSONDecodeError:
                        continue
        except:
            pass
        time.sleep(2)

    print(f"\n[CLAUDE] No input received (timeout after {timeout}s)")
    return None


# =============================================================================
# ERROR & BLOCKED NOTIFICATIONS
# =============================================================================

def blocked(
    issue: str,
    details: str,
    options: List[str] = None,
    timeout: int = 300
) -> Optional[str]:
    """
    Notify user that Claude is blocked and needs help.

    Args:
        issue: What's blocking progress
        details: Error details or context
        options: Possible solutions to choose from
        timeout: Seconds to wait

    Returns:
        Selected solution or user's input

    Example:
        response = blocked(
            "Test failures",
            "3 tests failing in auth module",
            ["Retry", "Skip tests", "Show errors", "Abort"]
        )
    """
    if options is None:
        options = ["Retry", "Skip", "Abort"]

    config = load_config()
    topic = get_topic()
    server = config.get('server', 'https://ntfy.sh')
    web_url = f"{server.rstrip('/')}/{topic}"

    print(f"\n[CLAUDE] BLOCKED: {issue}")
    print(f"[CLAUDE] Waiting for guidance at: {web_url}")

    return ask_user(
        title=f"Blocked: {issue}",
        message=details,
        options=options,
        timeout=timeout,
        priority="urgent",
        tags=["x", "stop_sign"],
        platform="ios"
    )


def error_occurred(
    error: str,
    details: str,
    can_retry: bool = True,
    timeout: int = 180
) -> Optional[str]:
    """
    Notify user about an error and get instructions.

    Args:
        error: Error summary
        details: Full error details
        can_retry: Whether retry is possible
        timeout: Seconds to wait

    Returns:
        "retry", "skip", "abort", or None
    """
    options = []
    if can_retry:
        options.append("Retry")
    options.extend(["Skip", "Abort"])

    config = load_config()
    topic = get_topic()
    server = config.get('server', 'https://ntfy.sh')
    web_url = f"{server.rstrip('/')}/{topic}"

    print(f"\n[CLAUDE] ERROR: {error}")
    print(f"[CLAUDE] Respond at: {web_url}")

    response = ask_user(
        title=f"Error: {error}",
        message=details,
        options=options,
        timeout=timeout,
        priority="urgent",
        tags=["rotating_light", "skull"],
        platform="ios"
    )

    if response:
        return response.lower()
    return None


# =============================================================================
# TESTING
# =============================================================================

def test_claude_actions():
    """Test the Claude actions notification system."""
    print("=" * 60)
    print("Testing Claude Actions System")
    print("=" * 60)

    # Test 1: Need action
    print("\n1. Testing need_action()...")
    response = need_action(
        "Test Decision",
        "This is a test. Please select an option.",
        ["Option A", "Option B", "Option C"],
        timeout=60
    )
    print(f"   Result: {response}")

    # Test 2: Task done with next steps
    print("\n2. Testing task_done() with next steps...")
    response = task_done(
        "Test Task",
        "Test task completed successfully.",
        next_steps=["Next Step 1", "Next Step 2"],
        timeout=60
    )
    print(f"   Result: {response}")

    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_claude_actions()
