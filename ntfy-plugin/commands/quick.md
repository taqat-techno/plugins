# /ntfy

Quick send a notification message.

## Usage

```
/ntfy <message>
/ntfy "Title" <message>
```

## What This Does

Sends a quick notification without specifying all parameters.
Perfect for quick updates during work.

## Examples

```
/ntfy Build completed successfully
/ntfy "Reminder" Check the logs in 10 minutes
/ntfy Code review is ready for your approval
```

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}")
sys.path.insert(0, str(plugin_dir))

from notification_checker import ensure_notification
from notify import get_config_status

# Check if configured
status = get_config_status()
if not status['configured']:
    print("ntfy not configured. Run /ntfy-setup first.")
else:
    # Parse arguments
    # If args starts with quoted string, use as title
    # Otherwise, use "Claude Code" as default title

    message = "USER_PROVIDED_MESSAGE"
    title = "Claude Code"

    # Example parsing:
    # /ntfy "Build Done" All tests passed
    # title = "Build Done", message = "All tests passed"

    # /ntfy All tests passed
    # title = "Claude Code", message = "All tests passed"

    result = ensure_notification(
        title=title,
        message=message,
        silent=True
    )

    if result['success']:
        print(f"Sent: {title}")
    else:
        print(f"Failed: {result['message']}")
```

## Quick Patterns

| Input | Result |
|-------|--------|
| `/ntfy Hello` | Title: "Claude Code", Message: "Hello" |
| `/ntfy "Alert" Server down` | Title: "Alert", Message: "Server down" |
| `/ntfy Task finished!` | Title: "Claude Code", Message: "Task finished!" |

## Options

For more control, use the full notification functions:

```python
from notification_checker import task_complete, action_required

# Task completion with details
task_complete("Migration", "500 records moved", duration="2m 30s")

# Action required with options
action_required("Choose DB", "Which database?", options=["PostgreSQL", "MySQL"])
```

## Related Commands

- `/ntfy-setup` - Configure notifications
- `/ntfy-test` - Test notification delivery
- `/ntfy-status` - Check configuration
- `/ntfy-history` - View past notifications
