---
title: 'Quick Notification'
read_only: false
type: 'command'
description: 'Quick send a notification to your phone'
---

# /ntfy <message>

Send a quick notification to your phone.

## Usage

```
/ntfy Your message here
```

## Examples

```
/ntfy Build completed successfully!
/ntfy Deployment to production finished
/ntfy Tests passing - ready for review
```

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notification_checker import ensure_notification

# Get the message from command argument
message = "${ARGS}"  # User's message

if not message or message.strip() == "":
    print("Usage: /ntfy <message>")
    print("Example: /ntfy Build completed!")
else:
    result = ensure_notification(
        "Claude Code Notification",
        message,
        priority="high",
        tags=["bell"]
    )

    if result.get('success'):
        print(f"[OK] Notification sent: {message[:50]}...")
    else:
        print(f"[ERROR] Failed to send: {result.get('message')}")
```

## Priority Options

The quick notification uses `high` priority by default. For other priorities, use the Python API:

```python
from notification_checker import ensure_notification

# Urgent (loud alert)
ensure_notification("Title", "Message", priority="urgent")

# Low (quiet)
ensure_notification("Title", "Message", priority="low")
```

---

*Part of ntfy-notifications Plugin v2.0*
