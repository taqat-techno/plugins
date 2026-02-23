---
name: ntfy-notifications
description: "Push notifications to your phone via ntfy.sh when Claude completes tasks, needs input, or encounters errors. Sends real-time alerts for task completion, action required, blocking issues, and long-running tasks. Supports automatic retry, deduplication, rate limiting, and notification history. 100% FREE - No account required!"
version: "2.0.0"
author: "TAQAT Techno"
license: "MIT"
allowed-tools:
  - Read
  - Write
  - Bash
  - WebFetch
  - Glob
  - Grep
metadata:
  service: "ntfy.sh"
  platforms: "iOS, Android, Desktop, Web"
  requires-account: false
  self-hosted: true
  priority-levels: 5
  features: "retry, deduplication, rate-limiting, history, decorators"
---

# ntfy Notifications Skill

A comprehensive push notification system for Claude Code that sends real-time alerts to your phone when tasks complete, input is needed, or errors occur.

## When to Use This Skill

Claude MUST send notifications in these situations:

| Event | Priority | When to Send |
|-------|----------|--------------|
| **Task Completion** | `high` | After completing ANY significant task |
| **Action Required** | `urgent` | When user input, approval, or decision is needed |
| **Blocked/Error** | `high` | When progress is blocked or an error occurs |
| **Long-Running Task** | `low` | After 60+ seconds of continuous work |

## MANDATORY: Interactive Notifications for Actions

**Claude MUST use interactive notifications whenever user action is needed.**

ALL notifications include the web URL so iOS users can respond via browser.

### Import Pattern for Actions
```python
import sys
PLUGIN_PATH = r"{PLUGIN_DIR}/ntfy/scripts"
sys.path.insert(0, PLUGIN_PATH)
from claude_actions import need_action, task_done, ask_proceed, ask_choice, get_user_input, blocked, error_occurred
```

### When Claude Needs User Input
```python
from claude_actions import need_action

# ALWAYS use this when you need user decision
response = need_action(
    "Database Selection",
    "Which database should I use for the project?",
    ["PostgreSQL", "MySQL", "SQLite"]
)

if response == "PostgreSQL":
    setup_postgres()
```

### When Task Completes with Optional Next Steps
```python
from claude_actions import task_done

# If there are suggested next steps, include them!
result = task_done(
    "API Integration Complete",
    "Created 5 REST endpoints with authentication",
    next_steps=["Run tests", "Deploy to staging", "Update documentation"]
)

if result == "Run tests":
    run_tests()
elif result == "Deploy to staging":
    deploy_staging()
elif result == "done":
    print("User chose to stop here")
```

### When Claude Needs Approval to Proceed
```python
from claude_actions import ask_proceed

if ask_proceed("Delete old log files", "This will remove 50 files older than 30 days"):
    delete_logs()
else:
    print("User declined, skipping deletion")
```

### When Claude is Blocked
```python
from claude_actions import blocked

response = blocked(
    "Build Failed",
    "npm install failed with dependency errors",
    ["Retry", "Use --force", "Skip", "Abort"]
)

if response == "Retry":
    retry_build()
```

### Getting Free-Text Input
```python
from claude_actions import get_user_input

module_name = get_user_input(
    "What should I name the new module?",
    "Creating module for inventory management"
)
```

---

## Notification Mode (Session-Based Auto-Notifications)

### Enabling Notification Mode

Use `/ntfy-mode` to toggle automatic notifications for the session:

```
/ntfy-mode on                  Enable with default topic
/ntfy-mode on my-custom-topic  Enable with custom topic for this session
/ntfy-mode off                 Disable notification mode
/ntfy-mode status              Check current status
```

### How Notification Mode Works

When **ON**, Claude automatically:
- Sends notification after EVERY task completion
- Includes suggested next steps as options
- Sends interactive notifications when decisions are needed
- Waits for user response via ntfy before proceeding
- Uses session topic (custom or default)

When **OFF**, Claude:
- Works normally without automatic notifications
- Only sends notifications when explicitly requested

### Session State

```python
from session import (
    is_notification_mode_on,  # Check if mode is ON
    get_session_topic,        # Get current topic
    show_status               # Display status
)

# Always check before sending notifications
if is_notification_mode_on():
    # Send notification
    pass
```

### Claude's Behavior When Mode is ON

**At the end of every task:**
```python
from claude_actions import task_done

# This automatically checks if mode is ON
result = task_done(
    "Created User Authentication",
    "Implemented login, logout, JWT tokens",
    next_steps=["Run tests", "Deploy", "Add 2FA"]
)

if result == "Run tests":
    run_tests()
elif result == "Deploy":
    deploy()
```

**When Claude needs user input:**
```python
from claude_actions import need_action

response = need_action(
    "Database Choice",
    "Which database for the project?",
    ["PostgreSQL", "MySQL", "MongoDB"]
)
# Waits for user response via ntfy
```

**When Claude is blocked:**
```python
from claude_actions import blocked

response = blocked(
    "Build Failed",
    "npm install returned errors",
    ["Retry", "Use --force", "Skip", "Abort"]
)
```

---

## Configuration

### Default Config Location
```
{PLUGIN_DIR}/ntfy/config.json
```

### Configuration Structure
```json
{
  "topic": "claude-user-unique-topic",
  "server": "https://ntfy.sh",
  "default_priority": "high",
  "auto_notify": {
    "on_task_complete": true,
    "on_action_required": true,
    "on_blocked": true,
    "on_long_task": true
  },
  "rate_limit": {
    "max_per_minute": 10,
    "cooldown_seconds": 5
  }
}
```

---

## Quick Reference

### Import Pattern
```python
import sys
PLUGIN_PATH = r"{PLUGIN_DIR}/ntfy/scripts"
sys.path.insert(0, PLUGIN_PATH)
from notification_checker import ensure_notification, task_complete, action_required, blocked
```

### Primary Function: `ensure_notification()`

The main notification function with automatic retry, logging, and deduplication.

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

---

## Notification Functions

### 1. Core Functions (notification_checker.py)

```python
from notification_checker import ensure_notification, task_complete, action_required, blocked, error

# Primary - with retry, logging, deduplication
ensure_notification(title, message, priority="high", tags=None)

# Convenience functions
task_complete(task_name, summary, duration=None)
action_required(title, description, options=None)
blocked(title, reason, suggestion=None)
error(title, details)
```

### 2. Low-Level Functions (notify.py)

```python
from notify import send_notification, get_config, check_connection

# Direct send (no retry)
send_notification(
    title="Notification Title",
    message="Message body",
    priority="high",      # min, low, default, high, urgent
    tags=["white_check_mark"],
    click_url=None,       # Open URL when clicked
    actions=None          # Action buttons
)

# Configuration
config = get_config()
status = check_connection()
```

### 3. Hooks & Decorators (hooks.py)

```python
from hooks import TaskContext, notify_on_complete, quick_notify

# Context manager - auto-notify on completion
with TaskContext("Data Migration", notify_on_complete=True) as task:
    task.update_progress(50, "Halfway done")
    # ... work ...
# Notification sent automatically

# Decorator
@notify_on_complete("File Processing")
def process_files():
    pass  # Notifies when function completes

# Quick notification
quick_notify("Build completed!")
```

---

## Priority Levels

| Level | Name | Use When | Behavior |
|-------|------|----------|----------|
| 5 | `urgent` | ACTION REQUIRED, Critical errors | Loud, persistent |
| 4 | `high` | Task complete, Blocked, Important | Long vibration |
| 3 | `default` | Informational | Normal sound |
| 2 | `low` | Status updates, Progress | Quiet |
| 1 | `min` | Debug, FYI | Silent |

---

## Tags (Emojis)

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

## Notification Workflow

### CORRECT Workflow:
1. Complete the task
2. **SEND NOTIFICATION IMMEDIATELY**
3. Write response to user

### WRONG Workflow:
1. Complete the task
2. Write response to user
3. ~~Forget to send notification~~

---

## Examples by Scenario

### Example 1: Task Completed

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

    Option 1: Redis
    - Best for distributed systems
    - Requires Redis server setup

    Option 2: In-Memory (LRU)
    - Simple, no dependencies
    - Only works for single instance

    Option 3: File-based
    - Persistent across restarts
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
    - test_auth_login: ConnectionError
    - test_order_total: ValueError""",
    suggestion="Check mock configuration in conftest.py"
)
```

### Example 4: Long Running Task

```python
from hooks import on_long_task

on_long_task(
    task_name="Processing Large Dataset",
    elapsed_seconds=180,
    progress_percent=45.5,
    estimated_remaining=220
)
```

---

## History & Analytics

### View History

```python
from notification_logger import get_history, get_statistics

# Get recent notifications
history = get_history(limit=20)

# Get statistics
stats = get_statistics()
print(f"Total sent: {stats['total_sent']}")
print(f"Success rate: {stats['success_rate']}%")
```

### Export History

```python
from notification_logger import export_to_markdown, export_to_csv

# Export to markdown
export_to_markdown("notification_report.md")

# Export to CSV
export_to_csv("notification_history.csv")
```

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

## Error Handling

Always handle notification failures gracefully:

```python
try:
    result = ensure_notification("Title", "Message")
    if not result.get('success'):
        print(f"Notification failed: {result.get('message')}")
except Exception as e:
    # Continue work - notification failure is non-critical
    print(f"Notification error: {e}")
```

---

## Rate Limiting & Deduplication

### Rate Limiting
- Maximum 10 notifications per minute
- 5-second cooldown between notifications
- Automatic queuing for excess notifications

### Deduplication
- Same title+message within 60 seconds = skipped
- Prevents spam from repeated calls
- Action Required (`urgent`) always sent regardless

---

## Setup Requirements

### User Setup (One-time)
1. Install **ntfy** app on phone (iOS/Android)
2. Create unique topic (e.g., `claude-username-abc123`)
3. Run `/ntfy-setup` in Claude Code
4. Test with `/ntfy-test`

### Self-Hosted Server (Optional)
```json
{
  "server": "https://your-ntfy-server.com",
  "topic": "your-topic"
}
```

---

## Interactive Two-Way Communication

### NEW: Ask User & Wait for Response

The plugin now supports **true two-way communication** - send notifications with action buttons and WAIT for the user's response.

### Import Pattern
```python
import sys
PLUGIN_PATH = r"{PLUGIN_DIR}/ntfy/scripts"
sys.path.insert(0, PLUGIN_PATH)
from interactive import ask_user, ask_yes_no, ask_choice, ask_confirm, ask_approval
```

### Primary Function: `ask_user()`

```python
from interactive import ask_user

# Send question with buttons, wait for response
response = ask_user(
    title="Database Selection",
    message="Which database should we use?",
    options=["PostgreSQL", "MySQL", "SQLite"],
    timeout=120  # seconds
)

if response == "PostgreSQL":
    setup_postgres()
elif response is None:
    print("User didn't respond, using default")
```

### Convenience Functions

```python
from interactive import ask_yes_no, ask_choice, ask_confirm, ask_approval

# Yes/No question
if ask_yes_no("Deploy?", "All tests passed.") == "YES":
    deploy()

# Multiple choice
db = ask_choice("Database", "Select:", ["PostgreSQL", "MySQL", "SQLite"])

# Confirmation (returns True/False)
if ask_confirm("Delete logs", "This cannot be undone"):
    delete_logs()

# Approval workflow
result = ask_approval("PR #123", "Adds auth feature")
if result == "APPROVE":
    merge_pr()
```

### How It Works

**Android:**
```
1. Claude sends notification with action buttons
   ↓
2. User sees notification with clickable buttons
   ↓
3. User taps a button (e.g., "PostgreSQL")
   ↓
4. Button sends response back to ntfy topic
   ↓
5. Claude polls topic and receives the response
   ↓
6. Claude continues execution based on user's choice
```

**iOS (Text-based replies):**
```
1. Claude sends notification with numbered options
   ↓
2. User sees notification: "Reply: 1=Yes, 2=No, 3=Maybe"
   ↓
3. User taps notification → opens ntfy app → types "1" or "Yes"
   ↓
4. Response is published to the topic
   ↓
5. Claude polls topic and receives the response
   ↓
6. Claude continues execution based on user's choice
```

### iOS vs Android Platform Support

**IMPORTANT**: ntfy action buttons are **NOT supported on iOS** (only Android + Web).

The plugin provides cross-platform support with different methods:

| Feature | Android | iOS |
|---------|---------|-----|
| Action Buttons | ✅ Native buttons | ❌ Not supported |
| Text Replies | ✅ Works | ✅ Works |
| Click to Open | ✅ Works | ✅ Works |

### Platform Configuration

Set your platform in config or per-call:

```python
from interactive import set_platform, ask_user

# Set default platform (persists in config)
set_platform("ios")       # iOS users
set_platform("android")   # Android users
set_platform("universal") # Both (default)

# Or specify per-call
response = ask_user(
    "Question",
    "Choose:",
    ["A", "B", "C"],
    platform="ios"  # Override for this call
)
```

### Platform Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `universal` | Shows buttons + numbered options | Mixed devices |
| `ios` | Numbered options only, tap-to-reply | iOS users |
| `android` | Action buttons only | Android users |

### iOS User Instructions

When using iOS, the notification will show:
```
Reply with number or text:
  1 = Yes
  2 = No
  3 = Maybe

Respond via: https://ntfy.sh/YOUR-TOPIC
```

**IMPORTANT**: The iOS ntfy app does NOT have an easy publish interface like Android.

**To respond on iOS:**
1. Open your web browser (Safari, Chrome, etc.)
2. Go to `https://ntfy.sh/YOUR-TOPIC` (replace with your actual topic)
3. Type your choice in the message box: "1" or "Yes"
4. Click "Publish" or press Enter
5. Claude receives your response

**Alternative**: You can also use:
- The ntfy web app at `https://ntfy.sh`
- Subscribe to your topic and use the publish feature
- Any HTTP client to POST to `https://ntfy.sh/YOUR-TOPIC`

### Interactive Examples

#### Example 1: Deployment Approval
```python
response = ask_user(
    title="Production Deployment",
    message="Ready to deploy v2.1.0 to production?\n\n"
            "Changes:\n"
            "- New user dashboard\n"
            "- Bug fixes\n"
            "- Performance improvements",
    options=["Deploy Now", "Deploy Later", "Cancel"],
    timeout=300  # 5 minutes
)

if response == "Deploy Now":
    run_deployment()
elif response == "Deploy Later":
    schedule_deployment()
else:
    print("Deployment cancelled")
```

#### Example 2: Error Recovery
```python
response = ask_user(
    title="Build Failed",
    message="npm install failed with error:\n"
            "ERESOLVE unable to resolve dependency tree\n\n"
            "How should I proceed?",
    options=["Retry", "Use --force", "Skip", "Abort"],
    timeout=120
)

if response == "Retry":
    retry_install()
elif response == "Use --force":
    force_install()
```

#### Example 3: Configuration Choice
```python
env = ask_choice(
    "Environment",
    "Which environment should I configure?",
    ["Development", "Staging", "Production"]
)

config = load_config(env.lower())
```

### Timeout Behavior

- Default timeout: 120 seconds (2 minutes)
- If user doesn't respond: returns `None`
- Always handle `None` case with a fallback

```python
response = ask_user("Question", "Choose:", ["A", "B"], timeout=60)

if response is None:
    print("No response, using default option A")
    response = "A"
```

---

## Best Practices

1. **Always notify on task completion** - Users are not watching the terminal
2. **Use appropriate priority** - Urgent for action required, high for completion
3. **Include actionable details** - What was done, what's needed
4. **Don't spam** - Deduplication prevents duplicate notifications
5. **Handle failures gracefully** - Continue work even if notification fails
6. **Use interactive for decisions** - When you need user input, use `ask_user()`
7. **Always handle timeout** - User may not respond, have a fallback plan

---

## Notification Templates

Use these pre-defined templates for consistent, actionable notifications:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from notify import send_notification

# Template dictionary — use instead of custom messages
TEMPLATES = {
    # Task lifecycle
    "task_complete": {
        "title": "✅ Task Complete",
        "body": "{task_name}",
        "priority": "default",
        "tags": ["white_check_mark"],
    },
    "task_complete_with_details": {
        "title": "✅ Done: {task_name}",
        "body": "{details}\n\nNext: {next_step}",
        "priority": "default",
        "tags": ["white_check_mark"],
    },
    # Action required
    "needs_input": {
        "title": "⏸️ Input Required",
        "body": "{question}",
        "priority": "high",
        "tags": ["pause_button"],
    },
    "needs_decision": {
        "title": "🤔 Decision Needed",
        "body": "{question}\n\nOptions: {options}",
        "priority": "high",
        "tags": ["thinking_face"],
    },
    # Errors
    "error": {
        "title": "❌ Error: {module}",
        "body": "{error_message}",
        "priority": "urgent",
        "tags": ["x", "warning"],
    },
    "warning": {
        "title": "⚠️ Warning",
        "body": "{message}",
        "priority": "high",
        "tags": ["warning"],
    },
    # Development workflow
    "server_ready": {
        "title": "🚀 Server Ready",
        "body": "Odoo running at http://localhost:{port}\nDatabase: {database}",
        "priority": "low",
        "tags": ["rocket"],
    },
    "module_updated": {
        "title": "🔄 Module Updated",
        "body": "{module} updated successfully on {database}",
        "priority": "low",
        "tags": ["arrows_counterclockwise"],
    },
    "tests_passed": {
        "title": "✅ Tests Passed",
        "body": "{module}: {count} tests passed",
        "priority": "default",
        "tags": ["white_check_mark", "test_tube"],
    },
    "tests_failed": {
        "title": "❌ Tests Failed",
        "body": "{module}: {failed} failed / {total} total\n{details}",
        "priority": "urgent",
        "tags": ["x", "test_tube"],
    },
    "deploy_complete": {
        "title": "🚀 Deployed",
        "body": "{module} deployed to {environment}",
        "priority": "default",
        "tags": ["rocket"],
    },
}

def notify_from_template(template_key: str, **kwargs) -> dict:
    """Send a notification using a pre-defined template."""
    template = TEMPLATES.get(template_key)
    if not template:
        raise ValueError(f"Unknown template: {template_key}. Available: {list(TEMPLATES.keys())}")

    title = template["title"].format(**kwargs)
    body = template["body"].format(**kwargs)

    return send_notification(
        title=title,
        message=body,
        priority=template.get("priority", "default"),
        tags=template.get("tags", []),
    )

# Usage examples:
# notify_from_template("task_complete", task_name="Build khairgate module")
# notify_from_template("error", module="disaster", error_message="Import failed: geopy not found")
# notify_from_template("server_ready", port=8069, database="khairgate19")
# notify_from_template("tests_passed", module="auth_otp", count=12)
```

---

## Notification Fallback (Windows Toast)

If ntfy.sh is unreachable (no internet, server down), fall back to Windows Toast notifications:

```python
import subprocess
import sys

def send_notification_with_fallback(title: str, message: str, priority: str = "default") -> dict:
    """Send notification via ntfy.sh with Windows Toast fallback."""
    # Try ntfy first
    try:
        sys.path.insert(0, str(Path(__file__).parent / "scripts"))
        from notify import send_notification
        result = send_notification(title=title, message=message, priority=priority)
        if result.get("success"):
            return result
    except Exception as e:
        pass  # Fall through to fallback

    # Fallback 1: Windows Toast Notification (PowerShell BurntToast)
    if sys.platform == "win32":
        try:
            ps_cmd = f'''
Add-Type -AssemblyName System.Windows.Forms
$notify = New-Object System.Windows.Forms.NotifyIcon
$notify.Icon = [System.Drawing.SystemIcons]::Information
$notify.Visible = $true
$notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep 1
$notify.Dispose()
'''
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return {"success": True, "method": "windows_toast"}
        except Exception:
            pass

    # Fallback 2: Terminal bell + print
    print(f"\a[NOTIFICATION] {title}: {message}", flush=True)
    return {"success": True, "method": "terminal"}
```

---

## CRITICAL REMINDER

**Sending notifications is MANDATORY, not optional.**

The user is NOT watching Claude Code. Without notifications, they won't know:
- When you're done
- When you need their input
- When something went wrong

Every significant event MUST trigger a notification.

---

*Part of TAQAT Techno Plugins v2.0*
