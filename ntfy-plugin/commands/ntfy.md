---
description: 'Push notifications to your phone — send, setup, test, status, history, config'
argument-hint: '<message> | setup | test | status | history [--export|--search=X] | config <key> <value>'
---

# /ntfy — Unified Notification Command

## Routing

Parse `$ARGUMENTS`:

- Starts with `setup` → **Section: Setup Wizard**
- Starts with `test` → **Section: Test Connection**
- Starts with `status` → **Section: Show Status**
- Starts with `history` → **Section: View History**
- Starts with `config` → **Section: Update Config**
- Anything else → **Section: Quick Send** (treat entire argument as message)
- No args → **Section: Quick Help**

---

## Section: Quick Help

When no arguments are provided, show:

```
ntfy — Push notifications to your phone

Usage:
  /ntfy <message>                  Send a quick notification
  /ntfy setup                      Interactive setup wizard
  /ntfy test                       Verify connection is working
  /ntfy status                     Show config, connection & stats
  /ntfy history                    View recent notification history
  /ntfy history --export           Export history to Markdown
  /ntfy history --search=<query>   Search notification history
  /ntfy config                     Show current configuration
  /ntfy config <key> <value>       Update a setting

Examples:
  /ntfy Build completed!
  /ntfy config priority default
  /ntfy history --search=deploy
```

---

## Section: Quick Send

Send a quick notification to the user's phone.

### Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notification_checker import ensure_notification

message = "${ARGS}"

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

Uses `high` priority by default. For other priorities use the Python API directly:
- `ensure_notification("Title", "Msg", priority="urgent")` — loud alert
- `ensure_notification("Title", "Msg", priority="low")` — quiet

---

## Section: Setup Wizard

Interactive setup wizard for ntfy push notifications.

### Step 1: Check Prerequisites

Ask the user:
> "Do you have the ntfy app installed on your phone?"

If NO, guide them:
1. **iOS**: App Store → search "ntfy" → install app by Philipp Heckel
2. **Android**: Play Store or F-Droid → search "ntfy" → install

### Step 2: Create Topic

Ask the user:
> "What topic name would you like to use?"

If they don't have one, suggest:
```
Recommended format: claude-[yourname]-[random]
Examples: claude-john-x7k9m2, claude-dev-alerts-abc123

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

topic_name = "USER_PROVIDED_TOPIC"
setup_topic(topic_name)
```

For self-hosted servers: `setup_topic("my-topic", server="https://ntfy.example.com")`

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

Expected: `[OK] Topic configured` → `[OK] Test notification sent successfully!`

---

## Section: Test Connection

Send a test notification to verify ntfy setup is working.

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
    print("Run /ntfy setup first to configure notifications.")
else:
    print(f"Testing notifications...")
    print(f"  Server: {status['server']}")
    print(f"  Topic: {status['topic']}")
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
    print("[OK] Test notification sent!")
    print("[INFO] Check your phone - you should see a notification within seconds.")
else:
    print(f"[ERROR] Failed to send: {result['message']}")
    print("Troubleshooting:")
    print("1. Verify topic name matches exactly in ntfy app")
    print("2. Check you're subscribed to the topic")
    print("3. Ensure ntfy app has notification permissions")
    print("4. Try visiting https://ntfy.sh/YOUR_TOPIC in browser")
```

### Manual Browser Test

If the automated test fails, try manually:
1. Open browser to `https://ntfy.sh/YOUR_TOPIC`
2. Type a message and click "Publish"
3. If phone receives it → issue is plugin config. If not → issue is app subscription.

---

## Section: Show Status

Check ntfy configuration, connection, and statistics.

### Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import get_config_status, check_connection, get_config
from notification_logger import get_statistics

print("ntfy Notification Status")
print("=" * 50)

# Configuration
status = get_config_status()
print("\nConfiguration:")
if status['configured']:
    print(f"  [OK] Topic: {status['topic']}")
    print(f"  [OK] Server: {status['server']}")
else:
    print("  [NOT CONFIGURED] - Run /ntfy setup")

# Connection
if status['configured']:
    print("\nConnection:")
    conn = check_connection()
    if conn['connected']:
        print(f"  [OK] Status: Connected ({conn.get('latency_ms', 'N/A')}ms)")
    else:
        print(f"  [ERROR] Status: DISCONNECTED - {conn.get('status', 'Unknown')}")

# Auto-notify settings
config = get_config()
auto = config.get('auto_notify', {})
print("\nAuto-Notify Settings:")
print(f"  Task Complete:    {'ON' if auto.get('on_task_complete', True) else 'OFF'}")
print(f"  Action Required:  {'ON' if auto.get('on_action_required', True) else 'OFF'}")
print(f"  Blocked/Error:    {'ON' if auto.get('on_blocked', True) else 'OFF'}")
print(f"  Long Tasks:       {'ON' if auto.get('on_long_task', True) else 'OFF'}")

# Rate limiting
rate = config.get('rate_limit', {})
print(f"\nRate Limiting:")
print(f"  Max per minute:   {rate.get('max_per_minute', 10)}")
print(f"  Cooldown:         {rate.get('cooldown_seconds', 5)}s")

# Statistics
stats = get_statistics()
print(f"\nStatistics (All Time):")
print(f"  Total sent:       {stats.get('total_sent', 0)}")
print(f"  Successful:       {stats.get('successful', 0)}")
print(f"  Failed:           {stats.get('failed', 0)}")
print(f"  Success rate:     {stats.get('success_rate', 0):.1f}%")
```

### Recommendations

Based on status, suggest actions:
- **Not configured** → Run `/ntfy setup`
- **Connection failed** → Check internet, verify server URL
- **High failure rate** → Review failed notifications via `/ntfy history`

---

## Section: View History

View notification history and statistics.

### Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notification_logger import get_history, get_statistics

stats = get_statistics()

print("Notification Statistics")
print("=" * 50)
print(f"Total Sent:     {stats.get('total_sent', 0)}")
print(f"Successful:     {stats.get('successful', 0)}")
print(f"Failed:         {stats.get('failed', 0)}")
print(f"Success Rate:   {stats.get('success_rate', 0):.1f}%")
print(f"Deduplicated:   {stats.get('deduplicated', 0)}")

print("\nBy Priority:")
for priority, count in stats.get('by_priority', {}).items():
    print(f"  {priority}: {count}")

print("\nRecent Notifications (Last 10)")
print("-" * 50)

history = get_history(limit=10)

if not history:
    print("No notifications sent yet.")
else:
    for entry in history:
        status_icon = "[OK]" if entry.get('success') else "[FAIL]"
        timestamp = entry.get('timestamp', 'Unknown')[:19]
        title = entry.get('title', 'No title')[:35]
        print(f"{status_icon} {timestamp} - {title}")
```

### History Filters

Parse remaining arguments after `history`:

- `history today` — Show only today's notifications
- `history failed` — Show only failed notifications
- `history --search=<query>` — Search notification history by keyword
- `history --export` — Export full history to Markdown
- `history --export csv` — Export full history to CSV
- `history clear` — Clear all history (ask for confirmation first)

### Export

```python
from notification_logger import export_to_markdown, export_to_csv

export_to_markdown("notification_report.md")  # Markdown export
export_to_csv("notification_history.csv")      # CSV export
```

---

## Section: Update Config

Update ntfy notification settings.

### View Current Config (no key/value provided)

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import get_config, save_config

config = get_config()

print("Current Configuration")
print("=" * 50)
print(f"Server:           {config.get('server', 'https://ntfy.sh')}")
print(f"Topic:            {config.get('topic', '(not set)')}")
print(f"Default Priority: {config.get('default_priority', 'high')}")

auto = config.get('auto_notify', {})
print(f"\nAuto-Notify:")
print(f"  Task Complete:    {'ON' if auto.get('on_task_complete', True) else 'OFF'}")
print(f"  Action Required:  {'ON' if auto.get('on_action_required', True) else 'OFF'}")
print(f"  Blocked/Error:    {'ON' if auto.get('on_blocked', True) else 'OFF'}")
print(f"  Long Tasks:       {'ON' if auto.get('on_long_task', True) else 'OFF'}")

rate = config.get('rate_limit', {})
print(f"\nRate Limiting:")
print(f"  Max per minute:   {rate.get('max_per_minute', 10)}")
print(f"  Cooldown:         {rate.get('cooldown_seconds', 5)}s")
```

### Configurable Keys

When `config <key> <value>` is provided, apply the change:

| Key | Values | Example |
|-----|--------|---------|
| `topic` | Any string | `/ntfy config topic claude-new-topic` |
| `server` | URL | `/ntfy config server https://ntfy.example.com` |
| `priority` | min, low, default, high, urgent | `/ntfy config priority default` |
| `auto-notify` | on, off | `/ntfy config auto-notify off` |
| `rate-limit` | Integer (max/min) | `/ntfy config rate-limit 15` |
| `cooldown` | Integer (seconds) | `/ntfy config cooldown 3` |
| `reset` | *(no value)* | `/ntfy config reset` |

### Applying Changes

```python
# Change topic
from notify import setup_topic
setup_topic("new-topic-name")
# Self-hosted: setup_topic("my-topic", server="https://ntfy.example.com")

# Toggle auto-notify
config = get_config()
config['auto_notify']['on_task_complete'] = False  # or True
save_config(config)

# Update rate limiting
config['rate_limit']['max_per_minute'] = 15
config['rate_limit']['cooldown_seconds'] = 3
save_config(config)

# Update default priority (options: min, low, default, high, urgent)
config['default_priority'] = 'default'
save_config(config)

# Set up authentication (private servers)
config['authentication'] = {'enabled': True, 'token': 'tk_your_access_token_here'}
save_config(config)
```

### Full Config Reference

```json
{
  "server": "https://ntfy.sh",
  "topic": "your-topic",
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
  },
  "tags": {
    "success": ["white_check_mark"],
    "warning": ["warning"],
    "error": ["x"],
    "action": ["bell"],
    "blocked": ["stop_sign"]
  }
}
```

---

> Previously available as separate commands: /ntfy-setup, /ntfy-test, /ntfy-status,
> /ntfy-history, /ntfy-config, /ntfy-ask.
> Two-way Q&A (/ntfy-ask) is now handled via natural language by the skill.

---

*Part of ntfy-notifications Plugin v2.0*
