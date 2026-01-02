---
title: 'ntfy Mode'
read_only: false
type: 'command'
description: 'Toggle notification mode for this session - auto-notify on task completion and actions'
---

# Notification Mode Control

Toggle automatic notifications for this Claude Code session.

## Usage

```
/ntfy-mode on [custom-topic]   Enable notification mode
/ntfy-mode off                  Disable notification mode
/ntfy-mode status               Check current status
/ntfy-mode                      Same as status
```

## Arguments

The user may provide:
- `on` - Enable notification mode (use default topic)
- `on <topic>` - Enable with custom topic for this session
- `off` - Disable notification mode
- `status` or no argument - Show current status

## What This Command Does

### When Enabled (`on`)

Claude will AUTOMATICALLY:

1. **On Task Completion**:
   - Send notification with task summary
   - Include optional next steps as choices
   - Wait for user to pick next action

2. **On Action Needed**:
   - Send interactive notification with options
   - Wait for user response via ntfy
   - Proceed based on user's choice

3. **On Error/Block**:
   - Notify user immediately
   - Provide options (Retry, Skip, Abort)
   - Wait for guidance

### When Disabled (`off`)

Claude returns to normal behavior:
- No automatic notifications
- User must explicitly request notifications
- Manual `/ntfy` commands still work

## Implementation

Run this Python code to handle the command:

```python
import sys
PLUGIN_PATH = r"C:\odoo\tmp\plugins\ntfy-plugin\ntfy\scripts"
sys.path.insert(0, PLUGIN_PATH)

from session import cli_handler

# Get the argument from user input (everything after /ntfy-mode)
args = "{ARGS}"  # This will be replaced with user's input

result = cli_handler(args)
```

## Examples

**Enable with default topic:**
```
/ntfy-mode on
```
Output:
```
NOTIFICATION MODE: ON
Topic: claude-alerts-nwo7r24v
Claude will now automatically notify on completions and actions.
```

**Enable with custom topic:**
```
/ntfy-mode on my-project-alerts
```
Output:
```
NOTIFICATION MODE: ON
Topic: my-project-alerts
(Custom topic for this session)
```

**Disable:**
```
/ntfy-mode off
```
Output:
```
NOTIFICATION MODE: OFF
Session stats: 5 tasks, 12 notifications
```

**Check status:**
```
/ntfy-mode status
```

## Session Behavior

When notification mode is ON, Claude MUST follow these rules:

### After Completing Any Task:
```python
from session import is_notification_mode_on, session_ask, increment_task_count

if is_notification_mode_on():
    increment_task_count()
    response = session_ask(
        title="Task Complete: <task_name>",
        message="<summary of what was done>",
        options=["<next_step_1>", "<next_step_2>", "Done"]
    )
    # Act on user's choice
```

### When Needing User Decision:
```python
from session import is_notification_mode_on, session_ask

if is_notification_mode_on():
    response = session_ask(
        title="Decision Needed: <topic>",
        message="<question>",
        options=["Option A", "Option B", "Option C"]
    )
    # Proceed with user's choice
```

### When Blocked or Error:
```python
from session import is_notification_mode_on, session_ask

if is_notification_mode_on():
    response = session_ask(
        title="Blocked: <issue>",
        message="<details>",
        options=["Retry", "Skip", "Abort"]
    )
    # Handle based on response
```

## Important Notes

- Session state persists until explicitly disabled or new session starts
- Custom topics only affect the current session
- Default topic from config is used when no custom topic specified
- All notifications include web URL for iOS users to respond
