# /ntfy-test

Send a test notification to verify ntfy setup is working.

## What This Does

Sends a test push notification to your configured ntfy topic to verify:
1. Topic is configured correctly
2. Server is reachable
3. Notifications are being delivered

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}")
sys.path.insert(0, str(plugin_dir))

from notify import test_notification, get_config_status, check_connection

# First check configuration
status = get_config_status()

if not status['configured']:
    print("No topic configured!")
    print("Run /ntfy-setup first to configure notifications.")
else:
    print(f"Testing notifications...")
    print(f"  Server: {status['server']}")
    print(f"  Topic: {status['topic']}")
    print("")

    # Check connection first
    conn = check_connection()
    if conn['connected']:
        print(f"Server connection: OK ({conn['latency_ms']}ms)")
    else:
        print(f"Server connection: FAILED ({conn['status']})")
        print("Check your internet connection and try again.")

    # Send test notification
    result = test_notification()

    if result['success']:
        print("")
        print("Test notification sent!")
        print("Check your phone - you should see a notification within seconds.")
    else:
        print("")
        print(f"Failed to send: {result['message']}")
        print("")
        print("Troubleshooting:")
        print("1. Verify topic name matches exactly in ntfy app")
        print("2. Check you're subscribed to the topic")
        print("3. Ensure ntfy app has notification permissions")
        print("4. Try visiting https://ntfy.sh/YOUR_TOPIC in browser")
```

## Expected Success Output

```
Testing notifications...
  Server: https://ntfy.sh
  Topic: claude-john-x7k9m2

Server connection: OK (45.2ms)
[INFO] Sending test notification to topic: claude-john-x7k9m2
[OK] Notification sent: Test from Claude Code
[OK] Test notification sent successfully!
[INFO] Check your phone for the notification

Test notification sent!
Check your phone - you should see a notification within seconds.
```

## Expected Failure Outputs

### Not Configured
```
No topic configured!
Run /ntfy-setup first to configure notifications.
```

### Connection Failed
```
Server connection: FAILED (Connection refused)
Check your internet connection and try again.
```

### Send Failed
```
Failed to send: HTTP 404: topic not found

Troubleshooting:
1. Verify topic name matches exactly in ntfy app
2. Check you're subscribed to the topic
...
```

## Manual Browser Test

If the automated test fails, try manually:
1. Open browser to: `https://ntfy.sh/YOUR_TOPIC`
2. Type a message and click "Publish"
3. Check if you receive it on your phone
4. If yes, the issue is with the plugin configuration
5. If no, the issue is with your ntfy app subscription
