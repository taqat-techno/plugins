---
title: 'Test Notification'
read_only: true
type: 'command'
description: 'Send a test notification to verify ntfy setup is working'
---

# /ntfy-test

Send a test notification to verify ntfy setup is working.

## Instructions

### Step 1: Check Configuration

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import test_notification, get_config_status, check_connection

status = get_config_status()

if not status['configured']:
    print("[ERROR] No topic configured!")
    print("Run /ntfy-setup first to configure notifications.")
else:
    print(f"Testing notifications...")
    print(f"  Server: {status['server']}")
    print(f"  Topic: {status['topic']}")
    print("")
```

### Step 2: Test Connection

```python
conn = check_connection()
if conn['connected']:
    print(f"[OK] Server connection: OK ({conn.get('latency_ms', 'N/A')}ms)")
else:
    print(f"[ERROR] Server connection: FAILED ({conn.get('status', 'Unknown')})")
    print("Check your internet connection and try again.")
```

### Step 3: Send Test Notification

```python
result = test_notification()

if result['success']:
    print("")
    print("[OK] Test notification sent!")
    print("[INFO] Check your phone - you should see a notification within seconds.")
else:
    print("")
    print(f"[ERROR] Failed to send: {result['message']}")
    print("")
    print("Troubleshooting:")
    print("1. Verify topic name matches exactly in ntfy app")
    print("2. Check you're subscribed to the topic")
    print("3. Ensure ntfy app has notification permissions")
    print("4. Try visiting https://ntfy.sh/YOUR_TOPIC in browser")
```

## Expected Output

### Success
```
Testing notifications...
  Server: https://ntfy.sh
  Topic: claude-john-x7k9m2

[OK] Server connection: OK (45ms)
[OK] Test notification sent!
[INFO] Check your phone - you should see a notification within seconds.
```

### Not Configured
```
[ERROR] No topic configured!
Run /ntfy-setup first to configure notifications.
```

### Connection Failed
```
[ERROR] Server connection: FAILED (Connection refused)
Check your internet connection and try again.
```

## Manual Browser Test

If the automated test fails, try manually:
1. Open browser to: `https://ntfy.sh/YOUR_TOPIC`
2. Type a message and click "Publish"
3. Check if you receive it on your phone
4. If yes, the issue is with the plugin configuration
5. If no, the issue is with your ntfy app subscription

---

*Part of ntfy-notifications Plugin v2.0*
