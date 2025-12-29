# CLAUDE.md - ntfy Notifications Plugin

This file provides guidance to Claude Code for using the ntfy notification system.

---

## NOTIFICATION PROTOCOL

Claude MUST send notifications in these situations:

| Event | Priority | When |
|-------|----------|------|
| **Task Completion** | `high` | After completing ANY significant task |
| **Action Required** | `urgent` | When user input, approval, or decision is needed |
| **Blocked/Error** | `high` | When progress is blocked or an error occurs |
| **Long-Running Task** | `low` | After 60+ seconds of continuous work |

---

## Quick Reference

### Plugin Path
```python
PLUGIN_PATH = r"${PLUGIN_DIR}"  # Replace with actual path
```

### Import Pattern
```python
import sys
sys.path.insert(0, PLUGIN_PATH)
from notification_checker import ensure_notification, task_complete, action_required, blocked
```

---

## Notification Functions

### 1. `ensure_notification()` - PRIMARY (Use This)

The main function with automatic retry, logging, and deduplication.

```python
from notification_checker import ensure_notification

ensure_notification(
    "Task Complete: API Integration",
    """Created REST API client:
    - GET /users endpoint
    - POST /orders endpoint
    - Error handling included

    Files: api_client.py (120 lines)"""
)
```

### 2. Convenience Functions

```python
from notification_checker import task_complete, action_required, blocked, error

# Task completed
task_complete(
    "Database Migration",
    "Migrated 500 records successfully",
    duration="45s"
)

# Need user input (URGENT - always sent)
action_required(
    "Choose Database Engine",
    "Which database should I use?",
    options=["PostgreSQL (recommended)", "MySQL", "SQLite"]
)

# Encountered blocker
blocked(
    "Missing Dependency",
    "Cannot import pandas module",
    suggestion="Run: pip install pandas"
)

# Error occurred
error(
    "API Connection Failed",
    "Timeout connecting to https://api.example.com"
)
```

### 3. Quick Notifications

```python
from hooks import quick_notify, notify_when_done, notify_need_input

# Simple message
quick_notify("Build completed successfully!")

# Task done
notify_when_done("All files have been processed")

# Need input
notify_need_input("Select deployment target:", ["staging", "production"])
```

---

## Notification Timing

### CORRECT Workflow:
1. Complete the task
2. **SEND NOTIFICATION IMMEDIATELY**
3. Write response to user

### WRONG Workflow:
1. Complete the task
2. Write response to user
3. ~~Forget to send notification~~

---

## Priority Reference

| Level | Name | Use When | Sound |
|-------|------|----------|-------|
| 5 | `urgent` | ACTION REQUIRED, Critical errors | Loud, persistent |
| 4 | `high` | Task complete, Blocked, Important | Long vibration |
| 3 | `default` | Informational | Normal |
| 2 | `low` | Status updates, Progress | Quiet |
| 1 | `min` | Debug, FYI | Silent |

---

## Tag/Emoji Reference

| Shortcode | Emoji | Use For |
|-----------|-------|---------|
| `white_check_mark` | ✅ | Success, Complete |
| `warning` | ⚠️ | Warnings, Attention needed |
| `x` | ❌ | Errors, Failed |
| `rotating_light` | 🚨 | Critical alerts |
| `bell` | 🔔 | Action required |
| `hourglass` | ⏳ | Long-running tasks |
| `tada` | 🎉 | Celebrations |
| `rocket` | 🚀 | Deployments |
| `computer` | 💻 | Technical tasks |
| `stop_sign` | 🛑 | Blocked |

---

## Context Manager Usage

For automatic tracking and notification:

```python
from hooks import TaskContext

with TaskContext("Data Migration", notify_on_complete=True) as task:
    # Do work here
    task.update_progress(50, "Halfway done")
    # ... more work ...
# Automatically sends notification when block completes
```

---

## Decorator Usage

```python
from hooks import notify_on_complete

@notify_on_complete("File Processing")
def process_files():
    # This function will automatically notify on completion
    pass
```

---

## Configuration Check

Before sending notifications, verify setup:

```python
from notify import get_config_status, check_connection

status = get_config_status()
if not status['configured']:
    print("Run /ntfy-setup first!")
else:
    conn = check_connection()
    print(f"Connected: {conn['connected']}")
```

---

## Examples by Scenario

### Example 1: Completed Complex Task

```python
ensure_notification(
    "Task Complete: Full-Stack Feature",
    """Implemented user authentication system:

    Backend:
    - Created User model with password hashing
    - Added JWT token generation
    - Implemented login/logout endpoints

    Frontend:
    - Built login form component
    - Added auth state management
    - Protected routes implemented

    Files modified: 8
    Lines of code: ~450"""
)
```

### Example 2: Need User Decision

```python
action_required(
    "Architecture Decision",
    """I need to implement the caching layer.

    The application would benefit from caching, but I need your preference:

    Option 1: Redis
    - Best for distributed systems
    - Requires Redis server setup
    - More complex but scalable

    Option 2: In-Memory (LRU)
    - Simple, no dependencies
    - Only works for single instance
    - Good for development

    Option 3: File-based
    - Persistent across restarts
    - Simple setup
    - Slower than memory
    """,
    options=["Redis", "In-Memory LRU", "File-based"]
)
```

### Example 3: Blocked by Error

```python
blocked(
    "Test Suite Failure",
    """3 tests are failing:

    - test_user_create: AssertionError
    - test_auth_login: ConnectionError (mock not setup)
    - test_order_total: ValueError (negative price)

    The tests were passing before adding the new feature.""",
    suggestion="""To fix:
    1. Check the mock configuration in conftest.py
    2. Validate price input in Order model
    3. Review the create user assertions"""
)
```

### Example 4: Long Running Task Update

```python
from hooks import on_long_task

# After 60+ seconds of work
on_long_task(
    task_name="Processing Large Dataset",
    elapsed_seconds=180,
    progress_percent=45.5,
    estimated_remaining=220
)
```

---

## Error Handling

Always wrap notification calls in try/except:

```python
try:
    result = ensure_notification("Title", "Message")
    if not result['success']:
        print(f"Notification failed: {result['message']}")
except Exception as e:
    # Fallback - continue with task even if notification fails
    print(f"Notification error (non-critical): {e}")
```

---

## When NOT Configured

If no topic is set, notifications will:
1. Print an error message
2. Log to `notification_history.json` locally
3. NOT send to phone

User must run `/ntfy-setup` to configure.

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/ntfy <message>` | Quick send a notification |
| `/ntfy-setup` | Interactive setup wizard |
| `/ntfy-test` | Send test notification |
| `/ntfy-status` | Check configuration |
| `/ntfy-history` | View notification history |
| `/ntfy-config` | Update settings |

---

## Best Practices

1. **Always notify on task completion** - Users are not watching the terminal
2. **Use appropriate priority** - Urgent for action required, high for completion
3. **Include actionable details** - What was done, what's needed
4. **Don't spam** - Deduplication prevents duplicate notifications
5. **Handle failures gracefully** - Continue work even if notification fails

---

## REMEMBER

**Sending notifications is CRITICAL, not optional.**

The user is not watching Claude Code. Without notifications, they won't know:
- When you're done
- When you need their input
- When something went wrong

Every significant event MUST trigger a notification.
