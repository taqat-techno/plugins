#!/usr/bin/env python3
"""
Session-Based Notification Mode
================================

This module manages notification mode state for Claude Code sessions.

When notification mode is ON:
- Claude MUST notify on every task completion
- Claude MUST send interactive notifications when action is needed
- Claude MUST notify when blocked or encountering errors

Commands:
    /ntfy-mode on [topic]  - Enable notification mode
    /ntfy-mode off         - Disable notification mode
    /ntfy-mode status      - Check current state

Author: TaqaTechno
License: MIT
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Session state file location
PLUGIN_DIR = Path(__file__).parent
SESSION_FILE = PLUGIN_DIR / "session_state.json"
CONFIG_FILE = PLUGIN_DIR / "config.json"

# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================

def _load_session() -> Dict[str, Any]:
    """Load current session state."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return _default_session()


def _save_session(state: Dict[str, Any]) -> bool:
    """Save session state."""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save session: {e}")
        return False


def _default_session() -> Dict[str, Any]:
    """Return default session state."""
    return {
        "notification_mode": False,
        "session_topic": None,  # None = use default from config
        "session_start": None,
        "auto_notify_complete": True,
        "auto_notify_action": True,
        "auto_notify_error": True,
        "auto_notify_progress": True,
        "task_count": 0,
        "notification_count": 0
    }


def _get_default_topic() -> str:
    """Get default topic from config."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('topic', 'claude-notifications')
    except:
        return 'claude-notifications'


# =============================================================================
# PUBLIC API
# =============================================================================

def enable_notification_mode(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Enable notification mode for this session.

    Args:
        topic: Optional custom topic for this session.
               If None, uses the default topic from config.

    Returns:
        Session state dict with mode enabled
    """
    state = _load_session()
    state["notification_mode"] = True
    state["session_topic"] = topic  # None means use default
    state["session_start"] = datetime.now().isoformat()
    state["task_count"] = 0
    state["notification_count"] = 0

    _save_session(state)

    effective_topic = topic or _get_default_topic()

    print("")
    print("=" * 60)
    print("  NOTIFICATION MODE: ON")
    print("=" * 60)
    print(f"  Topic: {effective_topic}")
    print(f"  Started: {state['session_start']}")
    print("")
    print("  Claude will now automatically:")
    print("    - Notify on task completion (with next steps)")
    print("    - Send interactive notifications for decisions")
    print("    - Alert on errors/blocks and wait for response")
    print("")
    print(f"  Respond via: https://ntfy.sh/{effective_topic}")
    print("=" * 60)
    print("")

    return state


def disable_notification_mode() -> Dict[str, Any]:
    """
    Disable notification mode.

    Returns:
        Session state dict with mode disabled
    """
    state = _load_session()

    # Store stats before disabling
    tasks = state.get("task_count", 0)
    notifs = state.get("notification_count", 0)
    start = state.get("session_start", "unknown")

    # Reset state
    state = _default_session()
    _save_session(state)

    print("")
    print("=" * 60)
    print("  NOTIFICATION MODE: OFF")
    print("=" * 60)
    print(f"  Session started: {start}")
    print(f"  Tasks completed: {tasks}")
    print(f"  Notifications sent: {notifs}")
    print("")
    print("  Claude will no longer auto-notify.")
    print("  Use /ntfy commands for manual notifications.")
    print("=" * 60)
    print("")

    return state


def is_notification_mode_on() -> bool:
    """
    Check if notification mode is currently enabled.

    Returns:
        True if notification mode is ON
    """
    state = _load_session()
    return state.get("notification_mode", False)


def get_session_topic() -> str:
    """
    Get the current session topic.

    Returns the custom session topic if set,
    otherwise returns the default topic from config.

    Returns:
        Topic string for notifications
    """
    state = _load_session()
    custom_topic = state.get("session_topic")
    if custom_topic:
        return custom_topic
    return _get_default_topic()


def get_session_state() -> Dict[str, Any]:
    """
    Get the full session state.

    Returns:
        Complete session state dictionary
    """
    state = _load_session()
    state["effective_topic"] = get_session_topic()
    state["default_topic"] = _get_default_topic()
    return state


def increment_task_count() -> int:
    """Increment and return the task count."""
    state = _load_session()
    state["task_count"] = state.get("task_count", 0) + 1
    _save_session(state)
    return state["task_count"]


def increment_notification_count() -> int:
    """Increment and return the notification count."""
    state = _load_session()
    state["notification_count"] = state.get("notification_count", 0) + 1
    _save_session(state)
    return state["notification_count"]


def show_status() -> Dict[str, Any]:
    """
    Display current notification mode status.

    Returns:
        Session state dictionary
    """
    state = get_session_state()
    mode = "ON" if state["notification_mode"] else "OFF"

    print("")
    print("=" * 60)
    print(f"  NOTIFICATION MODE: {mode}")
    print("=" * 60)

    if state["notification_mode"]:
        print(f"  Topic: {state['effective_topic']}")
        if state.get("session_topic"):
            print(f"    (Custom topic for this session)")
        else:
            print(f"    (Using default topic)")
        print(f"  Session started: {state.get('session_start', 'N/A')}")
        print(f"  Tasks completed: {state.get('task_count', 0)}")
        print(f"  Notifications sent: {state.get('notification_count', 0)}")
        print("")
        print(f"  Respond via: https://ntfy.sh/{state['effective_topic']}")
    else:
        print("  Notification mode is disabled.")
        print("  Enable with: /ntfy-mode on [optional-topic]")

    print("=" * 60)
    print("")

    return state


# =============================================================================
# NOTIFICATION MODE CHECKER DECORATOR
# =============================================================================

def notify_if_enabled(func):
    """
    Decorator that makes a function only execute if notification mode is ON.

    Usage:
        @notify_if_enabled
        def my_notification_function():
            # Only runs if mode is ON
            pass
    """
    def wrapper(*args, **kwargs):
        if is_notification_mode_on():
            return func(*args, **kwargs)
        return None
    return wrapper


# =============================================================================
# SESSION-AWARE NOTIFICATION FUNCTIONS
# =============================================================================

def session_notify(
    title: str,
    message: str,
    priority: str = "high",
    tags: list = None
) -> bool:
    """
    Send notification using session topic (only if mode is ON).

    Returns:
        True if sent, False if mode is OFF or failed
    """
    if not is_notification_mode_on():
        return False

    import sys
    sys.path.insert(0, str(PLUGIN_DIR))
    from notify import send_notification

    topic = get_session_topic()
    increment_notification_count()

    # Temporarily override topic
    from notify import load_config
    config = load_config()
    original_topic = config.get('topic')

    try:
        # Use session topic
        config['topic'] = topic
        result = send_notification(
            title=title,
            message=message,
            priority=priority,
            tags=tags or ["bell"]
        )
        return result
    finally:
        # Restore original
        config['topic'] = original_topic


def session_ask(
    title: str,
    message: str,
    options: list,
    timeout: int = 180
) -> Optional[str]:
    """
    Send interactive notification using session topic (only if mode is ON).

    Returns:
        User response, or None if mode is OFF or timeout
    """
    if not is_notification_mode_on():
        return None

    import sys
    sys.path.insert(0, str(PLUGIN_DIR))

    topic = get_session_topic()
    increment_notification_count()

    # Import and use interactive with session topic
    from interactive import ask_user, load_config

    config = load_config()
    original_topic = config.get('topic')

    try:
        config['topic'] = topic

        # Update config file temporarily
        with open(CONFIG_FILE, 'r') as f:
            file_config = json.load(f)
        file_config['topic'] = topic
        with open(CONFIG_FILE, 'w') as f:
            json.dump(file_config, f, indent=2)

        response = ask_user(
            title=title,
            message=message,
            options=options,
            timeout=timeout,
            platform="ios"
        )

        return response
    finally:
        # Restore original topic
        with open(CONFIG_FILE, 'r') as f:
            file_config = json.load(f)
        file_config['topic'] = original_topic
        with open(CONFIG_FILE, 'w') as f:
            json.dump(file_config, f, indent=2)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def cli_handler(args: str = "") -> str:
    """
    Handle /ntfy-mode command.

    Args:
        args: Command arguments ("on", "off", "status", "on custom-topic")

    Returns:
        Status message
    """
    args = args.strip().lower()
    parts = args.split(maxsplit=1)

    if not parts or parts[0] == "status":
        show_status()
        return "status"

    command = parts[0]

    if command == "on":
        topic = parts[1] if len(parts) > 1 else None
        enable_notification_mode(topic)
        return "enabled"

    elif command == "off":
        disable_notification_mode()
        return "disabled"

    else:
        print(f"Unknown command: {command}")
        print("Usage: /ntfy-mode [on|off|status] [topic]")
        return "error"


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        args = " ".join(sys.argv[1:])
        cli_handler(args)
    else:
        show_status()
