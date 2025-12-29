#!/usr/bin/env python3
"""
Notification Checker - Fail-Safe Notification Delivery
=======================================================

This module provides robust notification delivery with:
- Automatic retry with exponential backoff
- Local fallback logging if network fails
- Deduplication to prevent spam
- Queue management for batch notifications

This is the RECOMMENDED module for Claude Code to use.

Usage:
    from notification_checker import ensure_notification

    # Primary function - handles all retries and logging
    ensure_notification("Task Complete", "Details here")

    # Convenience functions
    task_complete("Migration Done", "500 records processed")
    action_required("Choose Option", "A or B?")
    blocked("Missing Dependency", "Run: pip install pandas")

Author: TaqaTechno
License: MIT
"""

import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Add plugin directory to path
PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PLUGIN_DIR))

from notify import (
    send_notification,
    notify_task_complete,
    notify_action_required,
    notify_blocked,
    notify_error,
    notify_info,
    notify_success,
    load_config
)


# =============================================================================
# DEDUPLICATION
# =============================================================================

_recent_notifications = {}  # hash -> timestamp
DEDUP_WINDOW_SECONDS = 30


def _get_notification_hash(title: str, message: str) -> str:
    """Generate hash for deduplication."""
    content = f"{title}:{message}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def _is_duplicate(title: str, message: str) -> bool:
    """Check if notification was recently sent."""
    global _recent_notifications

    # Clean old entries
    now = datetime.now()
    cutoff = now - timedelta(seconds=DEDUP_WINDOW_SECONDS)
    _recent_notifications = {
        h: t for h, t in _recent_notifications.items()
        if t > cutoff
    }

    # Check for duplicate
    hash_key = _get_notification_hash(title, message)
    if hash_key in _recent_notifications:
        return True

    # Record this notification
    _recent_notifications[hash_key] = now
    return False


# =============================================================================
# RETRY LOGIC
# =============================================================================

def ensure_notification(
    title: str,
    message: str,
    priority: str = None,
    tags: List[str] = None,
    max_retries: int = 3,
    allow_duplicate: bool = False,
    silent: bool = False
) -> dict:
    """
    Send notification with guaranteed delivery (retries + fallback).

    This is the PRIMARY function Claude should use for all notifications.
    It handles retries, deduplication, and fallback logging automatically.

    Args:
        title: Notification title
        message: Notification message
        priority: Priority level (auto-detected from title if not provided)
        tags: Emoji tags (auto-detected from title if not provided)
        max_retries: Maximum retry attempts (default: 3)
        allow_duplicate: Send even if recently sent (default: False)
        silent: Don't print status messages (default: False)

    Returns:
        dict: {success: bool, message: str, attempts: int}

    Example:
        ensure_notification(
            "Task Complete: Data Migration",
            "Migrated 500 records from source to destination"
        )
    """
    from notification_logger import log_notification

    # Check for duplicate
    if not allow_duplicate and _is_duplicate(title, message):
        if not silent:
            print(f"[SKIP] Duplicate notification suppressed: {title[:40]}...")
        return {
            'success': True,
            'message': "Duplicate suppressed",
            'attempts': 0,
            'skipped': True
        }

    # Auto-detect priority from title
    if not priority:
        title_upper = title.upper()
        if "ACTION REQUIRED" in title_upper or "URGENT" in title_upper:
            priority = "urgent"
        elif "BLOCKED" in title_upper or "ERROR" in title_upper or "FAILED" in title_upper:
            priority = "high"
        elif "COMPLETE" in title_upper or "SUCCESS" in title_upper:
            priority = "high"
        else:
            priority = "default"

    # Auto-detect tags from title
    if not tags:
        title_upper = title.upper()
        if "COMPLETE" in title_upper or "SUCCESS" in title_upper:
            tags = ["white_check_mark", "computer"]
        elif "ACTION" in title_upper or "REQUIRED" in title_upper:
            tags = ["warning", "bell"]
        elif "BLOCKED" in title_upper:
            tags = ["x", "stop_sign"]
        elif "ERROR" in title_upper or "FAILED" in title_upper:
            tags = ["rotating_light", "skull"]
        else:
            tags = ["computer"]

    # Log to local history first (even if network fails)
    log_notification(title, message, priority, tags)

    # Retry loop with exponential backoff
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            if not silent:
                print(f"\n[Attempt {attempt}/{max_retries}] Sending notification...")

            result = send_notification(
                title=title,
                message=message,
                priority=priority,
                tags=tags,
                bypass_rate_limit=(attempt > 1)  # Bypass rate limit on retries
            )

            if result['success']:
                if not silent:
                    print(f"[SUCCESS] Notification sent on attempt {attempt}")
                return {
                    'success': True,
                    'message': result['message'],
                    'attempts': attempt
                }
            else:
                last_error = result['message']
                if not silent:
                    print(f"[FAILED] Attempt {attempt}: {last_error}")

        except Exception as e:
            last_error = str(e)
            if not silent:
                print(f"[ERROR] Attempt {attempt}: {last_error}")

        # Wait before retry (exponential backoff: 2s, 4s, 8s...)
        if attempt < max_retries:
            wait_time = 2 ** attempt
            if not silent:
                print(f"[RETRY] Waiting {wait_time} seconds...")
            time.sleep(wait_time)

    # All retries failed
    if not silent:
        print(f"\n[FAILED] All {max_retries} attempts failed")
        print(f"[ERROR] Last error: {last_error}")

    # Fallback to local file logging
    _fallback_log(title, message, last_error)

    return {
        'success': False,
        'message': f"All {max_retries} attempts failed: {last_error}",
        'attempts': max_retries
    }


def _fallback_log(title: str, message: str, error: str):
    """Write failed notification to fallback log."""
    try:
        log_file = PLUGIN_DIR / 'failed_notifications.log'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"FAILED NOTIFICATION - {timestamp}\n")
            f.write(f"{'='*80}\n")
            f.write(f"Title: {title}\n")
            f.write(f"Message:\n{message}\n")
            f.write(f"Error: {error}\n")
            f.write(f"{'='*80}\n")

        print(f"\n[FALLBACK] Notification logged to: {log_file}")
        print("[ACTION] Check log file and verify network connectivity")

    except Exception as e:
        print(f"[CRITICAL] Could not write to fallback log: {e}")


# =============================================================================
# CONVENIENCE FUNCTIONS (with retry)
# =============================================================================

def task_complete(
    task_name: str,
    details: str = "",
    duration: str = None,
    silent: bool = False
) -> dict:
    """
    Send task completion notification with retry.

    Args:
        task_name: Name of the completed task
        details: What was done
        duration: How long it took (e.g., "2m 30s")
        silent: Don't print status messages

    Example:
        task_complete("Database Migration", "Migrated 500 user records", "45s")
    """
    message = details if details else "Task completed successfully."
    if duration:
        message += f"\n\nDuration: {duration}"

    return ensure_notification(
        title=f"Task Complete: {task_name}",
        message=message,
        priority="high",
        tags=["white_check_mark", "computer"],
        silent=silent
    )


def action_required(
    action_name: str,
    details: str = "",
    options: List[str] = None,
    silent: bool = False
) -> dict:
    """
    Send action required notification with retry (always delivered).

    Args:
        action_name: What action/input is needed
        details: Context about the decision
        options: List of choices available
        silent: Don't print status messages

    Example:
        action_required("Database Selection", "Which DB?", ["PostgreSQL", "MySQL"])
    """
    message = details
    if options:
        message += "\n\nOptions:\n" + "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
    message += "\n\nPlease respond in Claude Code."

    return ensure_notification(
        title=f"ACTION REQUIRED: {action_name}",
        message=message,
        priority="urgent",
        tags=["warning", "bell"],
        allow_duplicate=True,  # Action required is always important
        silent=silent
    )


def blocked(
    blocker_name: str,
    details: str = "",
    suggestion: str = None,
    silent: bool = False
) -> dict:
    """
    Send blocked/stuck notification with retry.

    Args:
        blocker_name: What is blocking progress
        details: Error or context
        suggestion: How to fix it
        silent: Don't print status messages

    Example:
        blocked("Missing Module", "pandas not found", "Run: pip install pandas")
    """
    message = details
    if suggestion:
        message += f"\n\nTo fix:\n{suggestion}"

    return ensure_notification(
        title=f"BLOCKED: {blocker_name}",
        message=message,
        priority="high",
        tags=["x", "stop_sign"],
        allow_duplicate=True,
        silent=silent
    )


def error(
    error_type: str,
    details: str = "",
    silent: bool = False
) -> dict:
    """
    Send error notification with retry.

    Args:
        error_type: Type of error (e.g., "ConnectionError", "ValidationError")
        details: Error message or traceback
        silent: Don't print status messages

    Example:
        error("API Error", "Failed to connect to server: timeout")
    """
    return ensure_notification(
        title=f"ERROR: {error_type}",
        message=details,
        priority="high",
        tags=["rotating_light", "skull"],
        allow_duplicate=True,
        silent=silent
    )


def info(title: str, message: str, silent: bool = False) -> dict:
    """Send informational notification with retry."""
    return ensure_notification(
        title=title,
        message=message,
        priority="default",
        tags=["information_source"],
        silent=silent
    )


def success(title: str, message: str, silent: bool = False) -> dict:
    """Send success/celebration notification with retry."""
    return ensure_notification(
        title=title,
        message=message,
        priority="default",
        tags=["tada", "rocket"],
        silent=silent
    )


# =============================================================================
# BATCH NOTIFICATIONS
# =============================================================================

_notification_queue = []


def queue_notification(title: str, message: str, priority: str = "default"):
    """Add notification to queue for batch sending."""
    _notification_queue.append({
        'title': title,
        'message': message,
        'priority': priority,
        'queued_at': datetime.now().isoformat()
    })


def flush_queue(silent: bool = False) -> dict:
    """Send all queued notifications as a single batch message."""
    global _notification_queue

    if not _notification_queue:
        return {'success': True, 'message': "Queue empty", 'count': 0}

    count = len(_notification_queue)

    # Combine into single notification
    combined_message = f"Batch of {count} notifications:\n\n"
    for i, notif in enumerate(_notification_queue, 1):
        combined_message += f"--- {i}. {notif['title']} ---\n"
        combined_message += f"{notif['message'][:200]}\n\n"

    result = ensure_notification(
        title=f"Batch Update: {count} items",
        message=combined_message,
        priority="default",
        tags=["package", "computer"],
        silent=silent
    )

    # Clear queue
    _notification_queue = []

    return {
        'success': result['success'],
        'message': result['message'],
        'count': count
    }


def get_queue_size() -> int:
    """Get number of notifications in queue."""
    return len(_notification_queue)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing fail-safe notification system...")
    print("=" * 60)

    result = ensure_notification(
        "Notification System Test",
        "This is a test of the fail-safe notification system with retry logic.\n\n"
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "Features:\n"
        "- Automatic retry with exponential backoff\n"
        "- Deduplication\n"
        "- Local fallback logging",
        priority="high",
        tags=["test_tube", "white_check_mark"]
    )

    print("\n" + "=" * 60)
    print(f"Result: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"Attempts: {result['attempts']}")
