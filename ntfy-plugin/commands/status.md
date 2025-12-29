---
title: 'ntfy Status'
read_only: true
type: 'command'
description: 'Check ntfy configuration and connection status'
---

# /ntfy-status

Check ntfy configuration and connection status.

## Instructions

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notify import get_config_status, check_connection, get_config
from notification_logger import get_statistics

print("ntfy Notification Status")
print("=" * 50)
print("")

# Configuration
status = get_config_status()

print("Configuration:")
if status['configured']:
    print(f"  [OK] Topic: {status['topic']}")
    print(f"  [OK] Server: {status['server']}")
else:
    print("  [NOT CONFIGURED] - Run /ntfy-setup")
print("")

# Connection
if status['configured']:
    print("Connection:")
    conn = check_connection()
    if conn['connected']:
        print(f"  [OK] Status: Connected")
        print(f"  [OK] Latency: {conn.get('latency_ms', 'N/A')}ms")
    else:
        print(f"  [ERROR] Status: DISCONNECTED")
        print(f"  [ERROR] Error: {conn.get('status', 'Unknown')}")
    print("")

# Auto-notify settings
config = get_config()
auto = config.get('auto_notify', {})
print("Auto-Notify Settings:")
print(f"  Task Complete:    {'ON' if auto.get('on_task_complete', True) else 'OFF'}")
print(f"  Action Required:  {'ON' if auto.get('on_action_required', True) else 'OFF'}")
print(f"  Blocked/Error:    {'ON' if auto.get('on_blocked', True) else 'OFF'}")
print(f"  Long Tasks:       {'ON' if auto.get('on_long_task', True) else 'OFF'}")
print("")

# Rate limiting
rate = config.get('rate_limit', {})
print("Rate Limiting:")
print(f"  Max per minute:   {rate.get('max_per_minute', 10)}")
print(f"  Cooldown:         {rate.get('cooldown_seconds', 5)}s")
print("")

# Statistics
stats = get_statistics()
print("Statistics (All Time):")
print(f"  Total sent:       {stats.get('total_sent', 0)}")
print(f"  Successful:       {stats.get('successful', 0)}")
print(f"  Failed:           {stats.get('failed', 0)}")
print(f"  Success rate:     {stats.get('success_rate', 0):.1f}%")
```

## Expected Output

### Configured
```
ntfy Notification Status
==================================================

Configuration:
  [OK] Topic: claude-john-x7k9m2
  [OK] Server: https://ntfy.sh

Connection:
  [OK] Status: Connected
  [OK] Latency: 42ms

Auto-Notify Settings:
  Task Complete:    ON
  Action Required:  ON
  Blocked/Error:    ON
  Long Tasks:       ON

Rate Limiting:
  Max per minute:   10
  Cooldown:         5s

Statistics (All Time):
  Total sent:       47
  Successful:       45
  Failed:           2
  Success rate:     95.7%
```

### Not Configured
```
ntfy Notification Status
==================================================

Configuration:
  [NOT CONFIGURED] - Run /ntfy-setup
```

## Recommendations

Based on status, suggest actions:

- **Not configured**: Run `/ntfy-setup`
- **Connection failed**: Check internet, verify server URL
- **High failure rate**: Review failed notifications in `/ntfy-history`

---

*Part of ntfy-notifications Plugin v2.0*
