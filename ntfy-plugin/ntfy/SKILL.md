---
name: ntfy
description: |
  Push notifications to your phone via ntfy.sh when Claude completes tasks, needs input, or encounters errors. Supports two-way phone Q&A — send interactive questions and wait for user responses. Sends real-time alerts for task completion, action required, blocking issues, and long-running tasks. Supports automatic retry, deduplication, rate limiting, and notification history. 100% FREE - No account required!


  <example>
  Context: User wants notifications when Claude finishes tasks
  user: "Set up notifications to my phone when Claude finishes a long task"
  assistant: "I will use the ntfy skill to configure a SessionEnd hook that sends a push notification via ntfy.sh to your subscribed topic when Claude completes a session."
  <commentary>Core trigger - automatic task completion notification setup.</commentary>
  </example>

  <example>
  Context: User wants to configure ntfy settings
  user: "Configure ntfy to send alerts to my custom topic on my self-hosted server"
  assistant: "I will use the ntfy skill to update the ntfy config with your server URL, topic name, and optional authentication credentials."
  <commentary>Configuration trigger - custom ntfy server setup.</commentary>
  </example>

  <example>
  Context: User wants to test the notification system
  user: "Test if ntfy notifications are working and send me a test message"
  assistant: "I will use the ntfy skill to send a test notification with priority 3 to your configured topic and verify the delivery response."
  <commentary>Testing trigger - verifying notification delivery.</commentary>
  </example>

  <example>
  Context: Claude needs user approval before proceeding
  user: "Ask me on my phone whether to deploy to production"
  assistant: "I'll send an interactive notification to your phone and wait for your response."
  <commentary>Two-way notification trigger — uses interactive.py for phone-based Q&A.</commentary>
  </example>

  <example>
  Context: Claude needs a choice from user who stepped away
  user: "Send a notification asking which database to use"
  assistant: "I'll send a choice notification to your phone with the options."
  <commentary>Interactive choice trigger — uses ask_choice() from interactive.py.</commentary>
  </example>
license: "MIT"
metadata:
  service: "ntfy.sh"
  platforms: "iOS, Android, Desktop, Web"
  requires-account: false
  self-hosted: true
  priority-levels: 5
  features: "retry, deduplication, rate-limiting, history, decorators"
---

# ntfy Notifications Skill

> For sending notifications, setup, and management, use the `/ntfy` command.
> For session auto-notify toggle, use `/ntfy-mode`.

## When to Send Notifications

| Event | Priority | When |
|-------|----------|------|
| **Task Completion** | `high` | After completing ANY significant task |
| **Action Required** | `urgent` | When user input, approval, or decision is needed |
| **Blocked/Error** | `high` | When progress is blocked or an error occurs |
| **Long-Running Task** | `low` | After 60+ seconds of continuous work |

## Import Pattern

```python
import sys
sys.path.insert(0, r"${PLUGIN_DIR}/ntfy/scripts")
from claude_actions import need_action, task_done, ask_proceed, ask_choice, get_user_input, blocked, error_occurred
```

## Core Functions (claude_actions)

### When Claude Needs User Input
```python
response = need_action(
    "Database Selection",
    "Which database should I use?",
    ["PostgreSQL", "MySQL", "SQLite"]
)
if response == "PostgreSQL":
    setup_postgres()
```

### When Task Completes
```python
result = task_done(
    "API Integration Complete",
    "Created 5 REST endpoints with authentication",
    next_steps=["Run tests", "Deploy to staging", "Update docs"]
)
if result == "Run tests":
    run_tests()
```

### When Claude Needs Approval
```python
if ask_proceed("Delete old log files", "This will remove 50 files older than 30 days"):
    delete_logs()
```

### When Claude is Blocked
```python
response = blocked(
    "Build Failed",
    "npm install failed with dependency errors",
    ["Retry", "Use --force", "Skip", "Abort"]
)
```

### Getting Free-Text Input
```python
module_name = get_user_input(
    "What should I name the new module?",
    "Creating module for inventory management"
)
```

---

## Notification Mode (Session Auto-Notifications)

Use `/ntfy-mode` to toggle automatic notifications:

```
/ntfy-mode on                  Enable with default topic
/ntfy-mode on my-custom-topic  Enable with custom topic
/ntfy-mode off                 Disable notification mode
/ntfy-mode status              Check current status
```

When **ON**, Claude automatically sends notifications on task completion,
decisions needed, and errors — and waits for user response via ntfy.

---

## Lower-Level API (notification_checker)

For direct notifications without session-awareness:

```python
import sys
sys.path.insert(0, r"${PLUGIN_DIR}/ntfy/scripts")
from notification_checker import ensure_notification, task_complete, action_required, blocked, error

ensure_notification(
    "Task Complete: API Integration",
    "Created REST API client with error handling",
    priority="high",
    tags=["white_check_mark"]
)
```

---

## Configuration

Config file: `${PLUGIN_DIR}/ntfy/config.json` (created from `config.default.json` on first setup)

```json
{
  "server": "https://ntfy.sh",
  "topic": "your-unique-topic",
  "default_priority": "default",
  "platform": "universal",
  "auto_notify": {
    "on_task_complete": true,
    "on_action_required": true,
    "on_error": true,
    "on_long_task": true
  },
  "rate_limit": {
    "max_per_minute": 10,
    "cooldown_seconds": 5
  }
}
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

## Task Helpers (Optional)

```python
from task_helpers import TaskContext, notify_on_complete, quick_notify

# Context manager
with TaskContext("Data Migration", notify_on_complete=True) as task:
    task.update_progress(50, "Halfway done")

# Decorator
@notify_on_complete("File Processing")
def process_files():
    pass

# Quick one-liner
quick_notify("Build completed!")
```

---

## Best Practices

1. **Always notify on task completion** — Users are not watching the terminal
2. **Use appropriate priority** — Urgent for action required, high for completion
3. **Include actionable details** — What was done, what's needed
4. **Use interactive for decisions** — `need_action()` when you need user input
5. **Always handle timeout** — User may not respond, have a fallback plan
6. **Don't spam** — Deduplication prevents duplicate notifications
7. **Handle failures gracefully** — Continue work even if notification fails

---

## Setup (One-Time)

1. Install **ntfy** app on phone (iOS/Android)
2. Create unique topic (e.g., `claude-username-abc123`)
3. Run `/ntfy setup` in Claude Code
4. Test with `/ntfy test`

---

## CRITICAL REMINDER

**Sending notifications is MANDATORY, not optional.**
The user is NOT watching Claude Code. Every significant event MUST trigger a notification.

---

*Part of TAQAT Techno Plugins v3.0*
