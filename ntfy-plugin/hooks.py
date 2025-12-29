#!/usr/bin/env python3
"""
ntfy Hooks - Automatic Notification Triggers
=============================================

This module provides hooks for automatic notifications in Claude Code.
Hooks are triggered by specific events during Claude's operation.

Supported Hooks:
- on_tool_complete: After any tool execution
- on_task_start: When a new task begins
- on_task_end: When a task completes
- on_error: When an error occurs
- on_user_input_needed: When Claude needs user input
- on_long_task: When a task runs longer than threshold

Integration:
    This module can be used standalone or integrated with Claude Code's
    hook system. See CLAUDE.md for integration instructions.

Author: TaqaTechno
License: MIT
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable

# Add plugin directory to path
PLUGIN_DIR = Path(__file__).parent
sys.path.insert(0, str(PLUGIN_DIR))

from notify import load_config
from notification_checker import (
    ensure_notification,
    task_complete,
    action_required,
    blocked,
    error as notify_error
)


# =============================================================================
# TASK TRACKING
# =============================================================================

_task_start_times: Dict[str, float] = {}
_task_count = 0


def _get_task_id() -> str:
    """Generate unique task ID."""
    global _task_count
    _task_count += 1
    return f"task_{_task_count}_{int(time.time())}"


def _format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


# =============================================================================
# HOOK FUNCTIONS
# =============================================================================

def on_task_start(
    task_name: str,
    task_id: str = None,
    details: str = None,
    notify: bool = False
) -> str:
    """
    Called when a new task begins.

    Args:
        task_name: Name/description of the task
        task_id: Optional task ID (generated if not provided)
        details: Additional task details
        notify: Send notification on start (default: False)

    Returns:
        str: Task ID for tracking
    """
    task_id = task_id or _get_task_id()
    _task_start_times[task_id] = time.time()

    config = load_config()

    if notify and config.get('auto_notify', {}).get('on_task_start', False):
        ensure_notification(
            title=f"Task Started: {task_name}",
            message=details or f"Started at {datetime.now().strftime('%H:%M:%S')}",
            priority="low",
            tags=["hourglass_flowing_sand", "computer"],
            silent=True
        )

    return task_id


def on_task_end(
    task_name: str,
    task_id: str = None,
    success: bool = True,
    details: str = None,
    notify: bool = True
) -> Dict[str, Any]:
    """
    Called when a task completes.

    Args:
        task_name: Name/description of the task
        task_id: Task ID from on_task_start (optional)
        success: Whether the task succeeded
        details: Completion details
        notify: Send notification (default: True)

    Returns:
        dict: {duration: str, notified: bool}
    """
    # Calculate duration
    duration = None
    if task_id and task_id in _task_start_times:
        elapsed = time.time() - _task_start_times[task_id]
        duration = _format_duration(elapsed)
        del _task_start_times[task_id]

    config = load_config()
    notified = False

    if notify and config.get('auto_notify', {}).get('on_task_complete', True):
        if success:
            result = task_complete(
                task_name=task_name,
                details=details or "Completed successfully.",
                duration=duration,
                silent=True
            )
            notified = result['success']
        else:
            result = blocked(
                blocker_name=f"Task Failed: {task_name}",
                details=details or "Task did not complete successfully.",
                silent=True
            )
            notified = result['success']

    return {
        'duration': duration,
        'notified': notified
    }


def on_tool_complete(
    tool_name: str,
    success: bool = True,
    output: str = None,
    error_msg: str = None
) -> Dict[str, Any]:
    """
    Called after any tool execution completes.

    This is the main hook for Claude Code tool integration.

    Args:
        tool_name: Name of the tool (e.g., "Bash", "Write", "Read")
        success: Whether the tool succeeded
        output: Tool output (truncated for notification)
        error_msg: Error message if failed

    Returns:
        dict: {notified: bool, priority: str}
    """
    config = load_config()
    notified = False
    priority = "default"

    # Only notify on errors if configured
    if not success and config.get('auto_notify', {}).get('on_error', True):
        result = notify_error(
            error_type=f"{tool_name} Failed",
            details=error_msg or output or "Tool execution failed.",
            silent=True
        )
        notified = result['success']
        priority = "high"

    return {
        'notified': notified,
        'priority': priority
    }


def on_error(
    error_type: str,
    error_message: str,
    traceback: str = None,
    recoverable: bool = True
) -> Dict[str, Any]:
    """
    Called when an error occurs.

    Args:
        error_type: Type of error (e.g., "ConnectionError", "ValidationError")
        error_message: Error message
        traceback: Optional traceback
        recoverable: Whether the error can be recovered from

    Returns:
        dict: {notified: bool}
    """
    config = load_config()
    notified = False

    if config.get('auto_notify', {}).get('on_error', True):
        priority = "high" if not recoverable else "default"
        title = f"ERROR: {error_type}" if recoverable else f"CRITICAL: {error_type}"

        details = error_message
        if traceback:
            details += f"\n\nTraceback:\n{traceback[-300:]}"

        result = ensure_notification(
            title=title,
            message=details,
            priority=priority,
            tags=["rotating_light", "skull"] if not recoverable else ["warning"],
            silent=True
        )
        notified = result['success']

    return {'notified': notified}


def on_user_input_needed(
    prompt: str,
    options: list = None,
    context: str = None,
    timeout_minutes: int = None
) -> Dict[str, Any]:
    """
    Called when Claude needs user input/decision.

    Args:
        prompt: What input is needed
        options: Available options to choose from
        context: Additional context
        timeout_minutes: Reminder after N minutes (optional)

    Returns:
        dict: {notified: bool}
    """
    config = load_config()
    notified = False

    if config.get('auto_notify', {}).get('on_action_required', True):
        message = prompt
        if context:
            message = f"{context}\n\n{prompt}"
        if options:
            message += "\n\nOptions:\n" + "\n".join(f"  {i+1}. {opt}" for i, opt in enumerate(options))
        if timeout_minutes:
            message += f"\n\n(Will remind in {timeout_minutes} minutes if no response)"

        result = action_required(
            action_name="User Input Needed",
            details=message,
            silent=True
        )
        notified = result['success']

    return {'notified': notified}


def on_long_task(
    task_name: str,
    elapsed_seconds: float,
    estimated_remaining: float = None,
    progress_percent: float = None
) -> Dict[str, Any]:
    """
    Called when a task exceeds the long-task threshold.

    Args:
        task_name: Name of the task
        elapsed_seconds: How long it's been running
        estimated_remaining: Estimated seconds remaining (optional)
        progress_percent: Progress percentage (optional)

    Returns:
        dict: {notified: bool}
    """
    config = load_config()
    notified = False

    threshold = config.get('auto_notify', {}).get('long_task_threshold_seconds', 60)

    if elapsed_seconds >= threshold and config.get('auto_notify', {}).get('on_long_task', True):
        message = f"Task has been running for {_format_duration(elapsed_seconds)}"

        if progress_percent is not None:
            message += f"\n\nProgress: {progress_percent:.1f}%"

        if estimated_remaining is not None:
            message += f"\nEstimated remaining: {_format_duration(estimated_remaining)}"

        result = ensure_notification(
            title=f"Long Task: {task_name}",
            message=message,
            priority="low",
            tags=["hourglass", "computer"],
            silent=True
        )
        notified = result['success']

    return {'notified': notified}


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

class TaskContext:
    """
    Context manager for automatic task tracking and notification.

    Usage:
        with TaskContext("Data Migration", notify_on_complete=True) as task:
            # ... do work ...
            task.update_progress(50)

        # Automatically sends completion notification
    """

    def __init__(
        self,
        name: str,
        notify_on_start: bool = False,
        notify_on_complete: bool = True,
        notify_on_error: bool = True,
        details: str = None
    ):
        self.name = name
        self.notify_on_start = notify_on_start
        self.notify_on_complete = notify_on_complete
        self.notify_on_error = notify_on_error
        self.details = details
        self.task_id = None
        self.start_time = None
        self.progress = 0
        self.error = None

    def __enter__(self):
        self.start_time = time.time()
        self.task_id = on_task_start(
            task_name=self.name,
            details=self.details,
            notify=self.notify_on_start
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None

        if not success:
            self.error = str(exc_val)

        if success and self.notify_on_complete:
            on_task_end(
                task_name=self.name,
                task_id=self.task_id,
                success=True,
                details=self.details,
                notify=True
            )
        elif not success and self.notify_on_error:
            on_task_end(
                task_name=self.name,
                task_id=self.task_id,
                success=False,
                details=f"Error: {self.error}",
                notify=True
            )

        return False  # Don't suppress exceptions

    def update_progress(self, percent: float, message: str = None):
        """Update task progress."""
        self.progress = percent
        if message:
            self.details = message

    def get_duration(self) -> str:
        """Get current task duration."""
        if self.start_time:
            return _format_duration(time.time() - self.start_time)
        return "0s"


# =============================================================================
# DECORATOR
# =============================================================================

def notify_on_complete(
    task_name: str = None,
    notify_on_error: bool = True
) -> Callable:
    """
    Decorator for automatic task completion notification.

    Usage:
        @notify_on_complete("Data Processing")
        def process_data():
            # ... do work ...
            pass

        # Automatically notifies when function completes
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            name = task_name or func.__name__

            with TaskContext(
                name=name,
                notify_on_complete=True,
                notify_on_error=notify_on_error
            ):
                return func(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_notify(message: str, title: str = "Claude Code") -> bool:
    """
    Quick notification with minimal parameters.

    Args:
        message: Notification message
        title: Notification title (default: "Claude Code")

    Returns:
        bool: True if sent successfully
    """
    result = ensure_notification(
        title=title,
        message=message,
        silent=True
    )
    return result['success']


def notify_when_done(message: str = "Task completed!") -> bool:
    """
    Simple notification for task completion.

    Args:
        message: Completion message

    Returns:
        bool: True if sent successfully
    """
    result = task_complete(
        task_name="Claude Code Task",
        details=message,
        silent=True
    )
    return result['success']


def notify_need_input(prompt: str, options: list = None) -> bool:
    """
    Simple notification for needing user input.

    Args:
        prompt: What input is needed
        options: Available options

    Returns:
        bool: True if sent successfully
    """
    result = on_user_input_needed(
        prompt=prompt,
        options=options
    )
    return result['notified']


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("Testing ntfy hooks...")
    print("=" * 60)

    # Test task context
    print("\n1. Testing TaskContext:")
    with TaskContext("Test Task", notify_on_complete=True) as task:
        time.sleep(1)
        task.update_progress(50, "Halfway done")
        time.sleep(1)

    print("\n2. Testing quick_notify:")
    quick_notify("This is a quick test notification!")

    print("\n3. Testing on_user_input_needed:")
    on_user_input_needed(
        prompt="Which database should I use?",
        options=["PostgreSQL", "MySQL", "SQLite"]
    )

    print("\n" + "=" * 60)
    print("Hook tests completed!")
