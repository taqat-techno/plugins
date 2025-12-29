---
title: 'ntfy Setup'
read_only: false
type: 'command'
description: 'Interactive setup wizard for ntfy push notifications'
---

# /ntfy-setup

Interactive setup wizard for ntfy push notifications.

## Instructions

### Step 1: Check Prerequisites

Ask the user:
> "Do you have the ntfy app installed on your phone?"

If NO, guide them:
1. **iOS**: Open App Store, search "ntfy", install app by Philipp Heckel
2. **Android**: Open Play Store or F-Droid, search "ntfy", install

### Step 2: Create Topic

Ask the user:
> "What topic name would you like to use?"

If they don't have one, suggest:
```
Recommended format: claude-[yourname]-[random]
Examples:
  - claude-john-x7k9m2
  - claude-dev-alerts-abc123
  - my-claude-notifications-xyz789

IMPORTANT: Make it unique and hard to guess!
Topic names are like passwords - anyone who knows it can send you notifications.
```

### Step 3: Subscribe in App

Tell the user:
1. Open the ntfy app
2. Tap the **+** button
3. Enter the topic name exactly as provided
4. Tap **Subscribe**

### Step 4: Configure Plugin

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import setup_topic, test_notification

# After getting topic from user
topic_name = "USER_PROVIDED_TOPIC"
setup_topic(topic_name)
```

### Step 5: Test Notification

```python
result = test_notification()

if result['success']:
    print("Setup complete! Check your phone for the test notification.")
else:
    print(f"Test failed: {result['message']}")
    print("Please verify:")
    print("1. Topic name matches exactly")
    print("2. You're subscribed in the ntfy app")
    print("3. Internet connection is working")
```

## Advanced Options

For self-hosted servers:
```python
setup_topic("my-topic", server="https://ntfy.example.com")
```

## Expected Output

```
[OK] Topic configured: claude-john-x7k9m2
[OK] Server: https://ntfy.sh

Sending test notification...
[OK] Test notification sent successfully!
[INFO] Check your phone for the notification
```

---

*Part of ntfy-notifications Plugin v2.0*
