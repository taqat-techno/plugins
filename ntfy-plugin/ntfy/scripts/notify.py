#!/usr/bin/env python3
"""
ntfy.sh Notification System for Claude Code
============================================

Push notifications to iOS/Android/Desktop via ntfy.sh - 100% FREE!

This plugin enables Claude Code to send push notifications to your devices
whenever tasks are completed, input is required, or errors occur.

Features:
- No account required (topic name = address)
- Priority levels (min, low, default, high, urgent)
- Emoji tags for visual categorization
- Action buttons for quick responses
- File attachments
- Scheduled delivery
- Click actions (open URLs)
- Local notification history

Usage:
    from notify import send_notification, notify_task_complete

    # Simple notification
    send_notification("Hello!", "This is a test message")

    # Task completion
    notify_task_complete("Data Migration", "Migrated 500 records")

    # Action required
    notify_action_required("Choose Database", "PostgreSQL or MySQL?")

Author: TaqaTechno
License: MIT
"""

import json
import time
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Union

try:
    import requests
except ImportError:
    requests = None
    print("[WARNING] 'requests' module not installed. Run: pip install requests")


# =============================================================================
# CONFIGURATION
# =============================================================================

PLUGIN_DIR = Path(__file__).parent
CONFIG_FILE = PLUGIN_DIR / "config.json"
HISTORY_FILE = PLUGIN_DIR / "notification_history.json"
FAILED_LOG = PLUGIN_DIR / "failed_notifications.log"

# Rate limiting state
_last_send_time = 0
_send_count_this_minute = 0
_minute_start = 0

# Default configuration
DEFAULT_CONFIG = {
    "server": "https://ntfy.sh",
    "topic": "",
    "default_priority": "default",
    "auto_notify": {
        "on_task_complete": True,
        "on_action_required": True,
        "on_error": True,
        "on_long_task": True,
        "long_task_threshold_seconds": 60
    },
    "priorities": {
        "task_complete": "high",
        "action_required": "urgent",
        "blocked": "high",
        "error": "high",
        "info": "default",
        "success": "default"
    },
    "tags": {
        "task_complete": ["white_check_mark", "computer"],
        "action_required": ["warning", "bell"],
        "blocked": ["x", "stop_sign"],
        "error": ["rotating_light", "skull"],
        "info": ["information_source"],
        "success": ["tada", "rocket"]
    },
    "rate_limit": {
        "enabled": True,
        "max_per_minute": 10,
        "cooldown_seconds": 5
    },
    "logging": {
        "enabled": True,
        "max_history": 1000,
        "log_file": "notification_history.json"
    },
    "authentication": {
        "enabled": False,
        "token": "",
        "username": "",
        "password": ""
    }
}


# =============================================================================
# CONFIGURATION MANAGEMENT
# =============================================================================

def load_config() -> dict:
    """Load configuration from config.json with defaults."""
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # Deep merge
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")

    return config


def save_config(config: dict) -> bool:
    """Save configuration to config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")
        return False


def get_topic() -> str:
    """Get configured topic name."""
    config = load_config()
    return config.get('topic', '')


def setup_topic(topic_name: str, server: str = None) -> bool:
    """
    Configure ntfy topic and optionally server.

    Args:
        topic_name: Your unique ntfy topic name
        server: Optional custom server URL (default: https://ntfy.sh)

    Returns:
        bool: True if configuration saved successfully
    """
    config = load_config()
    config['topic'] = topic_name

    if server:
        config['server'] = server

    if save_config(config):
        print(f"[OK] Topic configured: {topic_name}")
        print(f"[OK] Server: {config['server']}")
        print("")
        print("Next steps:")
        print("1. Install 'ntfy' app on your phone (iOS/Android)")
        print(f"2. Subscribe to topic: {topic_name}")
        print("3. Run /ntfy-test to verify")
        return True

    return False


def get_config_status() -> dict:
    """Get current configuration status."""
    config = load_config()
    topic = config.get('topic', '')
    server = config.get('server', 'https://ntfy.sh')

    return {
        'configured': bool(topic),
        'topic': topic,
        'server': server,
        'auto_notify': config.get('auto_notify', {}),
        'rate_limit': config.get('rate_limit', {}),
        'auth_enabled': config.get('authentication', {}).get('enabled', False)
    }


# =============================================================================
# RATE LIMITING
# =============================================================================

def _check_rate_limit() -> tuple:
    """
    Check if we're within rate limits.

    Returns:
        tuple: (allowed: bool, wait_seconds: float)
    """
    global _last_send_time, _send_count_this_minute, _minute_start

    config = load_config()
    rate_config = config.get('rate_limit', {})

    if not rate_config.get('enabled', True):
        return True, 0

    now = time.time()
    max_per_minute = rate_config.get('max_per_minute', 10)
    cooldown = rate_config.get('cooldown_seconds', 5)

    # Reset minute counter
    if now - _minute_start > 60:
        _minute_start = now
        _send_count_this_minute = 0

    # Check cooldown
    time_since_last = now - _last_send_time
    if time_since_last < cooldown:
        return False, cooldown - time_since_last

    # Check per-minute limit
    if _send_count_this_minute >= max_per_minute:
        return False, 60 - (now - _minute_start)

    return True, 0


def _update_rate_limit():
    """Update rate limit counters after successful send."""
    global _last_send_time, _send_count_this_minute
    _last_send_time = time.time()
    _send_count_this_minute += 1


# =============================================================================
# CORE NOTIFICATION FUNCTIONS
# =============================================================================

def send_notification(
    title: str,
    message: str,
    priority: str = None,
    tags: List[str] = None,
    click: str = None,
    actions: List[Dict] = None,
    attach: str = None,
    filename: str = None,
    delay: str = None,
    email: str = None,
    icon: str = None,
    markdown: bool = False,
    topic: str = None,
    bypass_rate_limit: bool = False
) -> dict:
    """
    Send a push notification via ntfy.

    Args:
        title: Notification title (will be sanitized for HTTP headers)
        message: Notification body (supports UTF-8)
        priority: "min", "low", "default", "high", "urgent" (or 1-5)
        tags: List of emoji shortcodes (e.g., ["warning", "computer"])
        click: URL to open when notification is clicked
        actions: List of action button definitions
        attach: URL of file to attach
        filename: Filename for attachment
        delay: Delivery delay (e.g., "30m", "2h", "tomorrow 9am")
        email: Email address to forward notification to
        icon: URL of custom notification icon
        markdown: Enable markdown formatting
        topic: Override configured topic
        bypass_rate_limit: Skip rate limit check (for critical notifications)

    Returns:
        dict: {success: bool, message: str, response: dict|None}
    """
    if requests is None:
        return {
            'success': False,
            'message': "requests module not installed. Run: pip install requests",
            'response': None
        }

    config = load_config()

    # Get topic
    topic = topic or config.get('topic', '')
    if not topic:
        return {
            'success': False,
            'message': "No topic configured. Run /ntfy-setup first.",
            'response': None
        }

    # Check rate limit
    if not bypass_rate_limit:
        allowed, wait_time = _check_rate_limit()
        if not allowed:
            return {
                'success': False,
                'message': f"Rate limited. Wait {wait_time:.1f} seconds.",
                'response': None
            }

    # Build URL
    server = config.get('server', 'https://ntfy.sh')
    url = f"{server.rstrip('/')}/{topic}"

    # Build headers
    headers = {}

    # Title (must be ASCII for HTTP header)
    if title:
        # Encode non-ASCII characters
        title_safe = title.encode('ascii', 'ignore').decode('ascii')
        if title_safe:
            headers['Title'] = title_safe

    # Priority
    priority = priority or config.get('default_priority', 'default')
    headers['Priority'] = str(priority)

    # Tags
    if tags:
        headers['Tags'] = ','.join(tags) if isinstance(tags, list) else str(tags)

    # Click action
    if click:
        headers['Click'] = click

    # Attachment
    if attach:
        headers['Attach'] = attach
    if filename:
        headers['Filename'] = filename

    # Delay
    if delay:
        headers['Delay'] = delay

    # Email
    if email:
        headers['Email'] = email

    # Icon
    if icon:
        headers['Icon'] = icon

    # Markdown
    if markdown:
        headers['Markdown'] = 'yes'

    # Actions (JSON format)
    if actions:
        # Convert to header format
        action_strs = []
        for action in actions:
            if action.get('action') == 'view':
                action_strs.append(f"view, {action.get('label', 'Open')}, {action.get('url', '')}")
            elif action.get('action') == 'http':
                method = action.get('method', 'POST')
                action_strs.append(f"http, {action.get('label', 'Execute')}, {action.get('url', '')}, method={method}")
        if action_strs:
            headers['Actions'] = '; '.join(action_strs)

    # Authentication
    auth_config = config.get('authentication', {})
    if auth_config.get('enabled'):
        if auth_config.get('token'):
            headers['Authorization'] = f"Bearer {auth_config['token']}"
        elif auth_config.get('username') and auth_config.get('password'):
            credentials = f"{auth_config['username']}:{auth_config['password']}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers['Authorization'] = f"Basic {encoded}"

    # Send request
    try:
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            _update_rate_limit()
            _log_notification(title, message, priority, tags, True)

            return {
                'success': True,
                'message': f"Notification sent: {title}",
                'response': response.json() if response.text else None
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            _log_notification(title, message, priority, tags, False, error_msg)

            return {
                'success': False,
                'message': error_msg,
                'response': None
            }

    except requests.exceptions.Timeout:
        _log_notification(title, message, priority, tags, False, "Timeout")
        return {'success': False, 'message': "Request timed out", 'response': None}

    except requests.exceptions.ConnectionError:
        _log_notification(title, message, priority, tags, False, "Connection error")
        return {'success': False, 'message': "Could not connect to server", 'response': None}

    except Exception as e:
        _log_notification(title, message, priority, tags, False, str(e))
        return {'success': False, 'message': str(e), 'response': None}


def send_json_notification(payload: dict) -> dict:
    """
    Send notification using JSON format (more flexible).

    Args:
        payload: Full notification payload with topic, message, title, etc.

    Returns:
        dict: {success: bool, message: str, response: dict|None}
    """
    if requests is None:
        return {'success': False, 'message': "requests module not installed", 'response': None}

    config = load_config()

    # Ensure topic is set
    if 'topic' not in payload:
        payload['topic'] = config.get('topic', '')

    if not payload['topic']:
        return {'success': False, 'message': "No topic configured", 'response': None}

    server = config.get('server', 'https://ntfy.sh')

    headers = {'Content-Type': 'application/json'}

    # Authentication
    auth_config = config.get('authentication', {})
    if auth_config.get('enabled') and auth_config.get('token'):
        headers['Authorization'] = f"Bearer {auth_config['token']}"

    try:
        response = requests.post(
            server,
            json=payload,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            _update_rate_limit()
            return {'success': True, 'message': "Notification sent", 'response': response.json()}
        else:
            return {'success': False, 'message': f"HTTP {response.status_code}", 'response': None}

    except Exception as e:
        return {'success': False, 'message': str(e), 'response': None}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def notify_task_complete(
    task_name: str,
    details: str = "",
    duration: str = None,
    click_url: str = None
) -> dict:
    """
    Send task completion notification.

    Args:
        task_name: Name of the completed task
        details: Additional details about what was done
        duration: How long the task took (e.g., "2m 30s")
        click_url: URL to open when notification clicked
    """
    config = load_config()
    priority = config.get('priorities', {}).get('task_complete', 'high')
    tags = config.get('tags', {}).get('task_complete', ['white_check_mark', 'computer'])

    message = details if details else "Task completed successfully."
    if duration:
        message += f"\n\nDuration: {duration}"

    return send_notification(
        title=f"Task Complete: {task_name}",
        message=message,
        priority=priority,
        tags=tags,
        click=click_url
    )


def notify_action_required(
    action_name: str,
    details: str = "",
    options: List[str] = None,
    click_url: str = None
) -> dict:
    """
    Send action required notification (highest priority).

    Args:
        action_name: What action/input is needed
        details: Details about what is required
        options: List of options to choose from
        click_url: URL to open when notification clicked
    """
    config = load_config()
    priority = config.get('priorities', {}).get('action_required', 'urgent')
    tags = config.get('tags', {}).get('action_required', ['warning', 'bell'])

    message = details
    if options:
        message += "\n\nOptions:\n" + "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
    message += "\n\nPlease respond in Claude Code."

    return send_notification(
        title=f"ACTION REQUIRED: {action_name}",
        message=message,
        priority=priority,
        tags=tags,
        click=click_url,
        bypass_rate_limit=True  # Action required is always critical
    )


def notify_blocked(
    blocker_name: str,
    details: str = "",
    suggestion: str = None
) -> dict:
    """
    Send blocked/stuck notification.

    Args:
        blocker_name: What is blocking progress
        details: Error details or what user needs to do
        suggestion: Suggested fix
    """
    config = load_config()
    priority = config.get('priorities', {}).get('blocked', 'high')
    tags = config.get('tags', {}).get('blocked', ['x', 'stop_sign'])

    message = details
    if suggestion:
        message += f"\n\nSuggested fix:\n{suggestion}"

    return send_notification(
        title=f"BLOCKED: {blocker_name}",
        message=message,
        priority=priority,
        tags=tags,
        bypass_rate_limit=True
    )


def notify_error(
    error_type: str,
    details: str = "",
    traceback: str = None
) -> dict:
    """
    Send error notification.

    Args:
        error_type: Type of error
        details: Error message
        traceback: Optional traceback (will be truncated)
    """
    config = load_config()
    priority = config.get('priorities', {}).get('error', 'high')
    tags = config.get('tags', {}).get('error', ['rotating_light', 'skull'])

    message = details
    if traceback:
        # Truncate traceback to last 500 chars
        message += f"\n\nTraceback:\n{traceback[-500:]}"

    return send_notification(
        title=f"ERROR: {error_type}",
        message=message,
        priority=priority,
        tags=tags,
        bypass_rate_limit=True
    )


def notify_info(title: str, message: str) -> dict:
    """Send informational notification."""
    config = load_config()
    priority = config.get('priorities', {}).get('info', 'default')
    tags = config.get('tags', {}).get('info', ['information_source'])

    return send_notification(
        title=title,
        message=message,
        priority=priority,
        tags=tags
    )


def notify_success(title: str, message: str) -> dict:
    """Send success/celebration notification."""
    config = load_config()
    priority = config.get('priorities', {}).get('success', 'default')
    tags = config.get('tags', {}).get('success', ['tada', 'rocket'])

    return send_notification(
        title=title,
        message=message,
        priority=priority,
        tags=tags
    )


# =============================================================================
# LOGGING
# =============================================================================

def _log_notification(
    title: str,
    message: str,
    priority: str,
    tags: List[str],
    success: bool,
    error: str = None
):
    """Log notification to history file."""
    config = load_config()

    if not config.get('logging', {}).get('enabled', True):
        return

    try:
        # Load existing history
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)

        # Add new entry
        entry = {
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'title': title,
            'message': message[:500],  # Truncate for storage
            'priority': priority,
            'tags': tags,
            'success': success,
            'error': error
        }
        history.append(entry)

        # Trim to max size
        max_history = config.get('logging', {}).get('max_history', 1000)
        if len(history) > max_history:
            history = history[-max_history:]

        # Save
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    except Exception as e:
        # Fallback to failed log
        try:
            with open(FAILED_LOG, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now().isoformat()}] Logging failed: {e}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Success: {success}\n")
        except:
            pass


# =============================================================================
# TESTING
# =============================================================================

def test_notification() -> dict:
    """
    Send a test notification to verify setup.

    Returns:
        dict: {success: bool, message: str}
    """
    config = load_config()
    topic = config.get('topic', '')

    if not topic:
        print("[ERROR] No topic configured!")
        print("")
        print("To set up notifications:")
        print("1. Install the ntfy app on your phone (iOS/Android)")
        print("2. Open the app and tap '+' to subscribe to a topic")
        print("3. Create a unique topic name (e.g., 'claude-yourname-random123')")
        print("4. Run: /ntfy-setup")
        print("")
        return {'success': False, 'message': "No topic configured"}

    print(f"[INFO] Sending test notification to: {topic}")

    result = send_notification(
        title="Test from Claude Code",
        message=f"If you see this, notifications are working!\n\n"
                f"Server: {config.get('server', 'https://ntfy.sh')}\n"
                f"Topic: {topic}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        priority="high",
        tags=["tada", "white_check_mark", "computer"],
        bypass_rate_limit=True
    )

    if result['success']:
        print("[OK] Test notification sent successfully!")
        print("[INFO] Check your phone for the notification")
    else:
        print(f"[FAILED] {result['message']}")

    return result


def check_connection() -> dict:
    """
    Check if ntfy server is reachable.

    Returns:
        dict: {connected: bool, server: str, latency_ms: float}
    """
    config = load_config()
    server = config.get('server', 'https://ntfy.sh')

    try:
        start = time.time()
        response = requests.get(f"{server}/v1/health", timeout=5)
        latency = (time.time() - start) * 1000

        return {
            'connected': response.status_code == 200,
            'server': server,
            'latency_ms': round(latency, 2),
            'status': 'healthy' if response.status_code == 200 else 'unhealthy'
        }
    except Exception as e:
        return {
            'connected': False,
            'server': server,
            'latency_ms': None,
            'status': str(e)
        }


# =============================================================================
# ALIASES
# =============================================================================

# Short aliases for common operations
notify = notify_task_complete
complete = notify_task_complete
action = notify_action_required
blocked = notify_blocked
error = notify_error
info = notify_info
success = notify_success


# =============================================================================
# CLI INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("ntfy.sh Notification System for Claude Code")
    print("=" * 60)
    print("")

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--setup" and len(sys.argv) > 2:
            setup_topic(sys.argv[2])

        elif command == "--test":
            test_notification()

        elif command == "--status":
            status = get_config_status()
            conn = check_connection()
            print(f"Configured: {status['configured']}")
            print(f"Topic: {status['topic'] or '(not set)'}")
            print(f"Server: {status['server']}")
            print(f"Connected: {conn['connected']}")
            if conn['latency_ms']:
                print(f"Latency: {conn['latency_ms']}ms")

        elif command == "--send" and len(sys.argv) > 2:
            message = " ".join(sys.argv[2:])
            result = send_notification("Claude Code", message)
            print(result['message'])

        elif command == "--help":
            print("Usage:")
            print("  python notify.py --setup TOPIC    Set your ntfy topic")
            print("  python notify.py --test           Send test notification")
            print("  python notify.py --status         Check configuration")
            print("  python notify.py --send MESSAGE   Send a quick message")
            print("  python notify.py --help           Show this help")

        else:
            print(f"Unknown command: {command}")
            print("Run: python notify.py --help")

    else:
        # Show status
        status = get_config_status()

        if status['configured']:
            print(f"Topic: {status['topic']}")
            print(f"Server: {status['server']}")
            print("")
            print("Run: python notify.py --test")
        else:
            print("No topic configured.")
            print("")
            print("Quick Setup:")
            print("1. Install 'ntfy' app on your phone")
            print("2. Create a unique topic in the app")
            print("3. Run: python notify.py --setup YOUR_TOPIC")
