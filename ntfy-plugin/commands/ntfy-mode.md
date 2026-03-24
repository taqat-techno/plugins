---
description: 'Toggle notification mode for this session - auto-notify on task completion and actions'
argument-hint: '[on|off|status]'
---

# /ntfy-mode - Toggle Notification Mode

Parse `$ARGUMENTS`:

| Input | Action |
|-------|--------|
| `on` | Enable auto-notifications for this session |
| `off` | Disable auto-notifications |
| `status` | Show current mode |
| *(no args)* | Toggle current mode |

Use the ntfy skill for notification formatting, priority configuration, and delivery patterns.

When enabled, automatically send push notifications on:
- Task completion (Stop hook)
- Actions requiring user input
- Errors or blocking issues
- Long-running task milestones
