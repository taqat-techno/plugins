# /ntfy-status

Check ntfy configuration and connection status.

## What This Does

Shows the current state of ntfy notifications:
1. Configuration status (topic, server)
2. Connection status (reachable, latency)
3. Recent notification statistics
4. Any issues or warnings

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}")
sys.path.insert(0, str(plugin_dir))

from notify import get_config_status, check_connection, load_config
from notification_logger import get_statistics, get_storage_info

print("ntfy Notification Status")
print("=" * 50)
print("")

# Configuration
status = get_config_status()

print("Configuration:")
if status['configured']:
    print(f"  Topic: {status['topic']}")
    print(f"  Server: {status['server']}")
    print(f"  Auth: {'Enabled' if status['auth_enabled'] else 'Disabled'}")
else:
    print("  NOT CONFIGURED - Run /ntfy-setup")
print("")

# Connection
if status['configured']:
    print("Connection:")
    conn = check_connection()
    if conn['connected']:
        print(f"  Status: Connected")
        print(f"  Latency: {conn['latency_ms']}ms")
    else:
        print(f"  Status: DISCONNECTED")
        print(f"  Error: {conn['status']}")
    print("")

# Auto-notify settings
config = load_config()
auto = config.get('auto_notify', {})
print("Auto-Notify Settings:")
print(f"  On task complete: {'Yes' if auto.get('on_task_complete', True) else 'No'}")
print(f"  On action required: {'Yes' if auto.get('on_action_required', True) else 'No'}")
print(f"  On error: {'Yes' if auto.get('on_error', True) else 'No'}")
print(f"  Long task threshold: {auto.get('long_task_threshold_seconds', 60)}s")
print("")

# Statistics
stats = get_statistics(7)
print("Last 7 Days:")
print(f"  Total notifications: {stats['total']}")
print(f"  Successful: {stats['successful']}")
print(f"  Failed: {stats['failed']}")
print(f"  Success rate: {stats['success_rate']}%")
print("")

# Storage
storage = get_storage_info()
print("Storage:")
print(f"  History entries: {storage['count']}")
print(f"  File size: {storage['file_size_kb']} KB")
```

## Example Output

### Fully Configured
```
ntfy Notification Status
==================================================

Configuration:
  Topic: claude-john-x7k9m2
  Server: https://ntfy.sh
  Auth: Disabled

Connection:
  Status: Connected
  Latency: 42.5ms

Auto-Notify Settings:
  On task complete: Yes
  On action required: Yes
  On error: Yes
  Long task threshold: 60s

Last 7 Days:
  Total notifications: 47
  Successful: 45
  Failed: 2
  Success rate: 95.7%

Storage:
  History entries: 156
  File size: 28.4 KB
```

### Not Configured
```
ntfy Notification Status
==================================================

Configuration:
  NOT CONFIGURED - Run /ntfy-setup

Auto-Notify Settings:
  On task complete: Yes
  On action required: Yes
  On error: Yes
  Long task threshold: 60s

Last 7 Days:
  Total notifications: 0
  Successful: 0
  Failed: 0
  Success rate: 0%

Storage:
  History entries: 0
  File size: 0 KB
```

### Connection Issues
```
ntfy Notification Status
==================================================

Configuration:
  Topic: claude-john-x7k9m2
  Server: https://ntfy.example.com
  Auth: Enabled

Connection:
  Status: DISCONNECTED
  Error: Connection timed out

...
```

## Recommendations

Based on status, suggest actions:

- **Not configured**: Run `/ntfy-setup`
- **Connection failed**: Check internet, verify server URL
- **High failure rate**: Review failed notifications in `/ntfy-history`
- **Auth issues**: Verify token/credentials in config
