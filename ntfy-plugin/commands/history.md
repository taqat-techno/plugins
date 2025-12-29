---
title: 'Notification History'
read_only: true
type: 'command'
description: 'View notification history and statistics'
---

# /ntfy-history

View notification history and statistics.

## Instructions

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}/ntfy/scripts")
sys.path.insert(0, str(plugin_dir))

from notification_logger import get_history, get_statistics

# Get statistics
stats = get_statistics()

print("Notification Statistics")
print("=" * 50)
print(f"Total Sent:     {stats.get('total_sent', 0)}")
print(f"Successful:     {stats.get('successful', 0)}")
print(f"Failed:         {stats.get('failed', 0)}")
print(f"Success Rate:   {stats.get('success_rate', 0):.1f}%")
print(f"Deduplicated:   {stats.get('deduplicated', 0)}")
print("")

# By priority
print("By Priority:")
for priority, count in stats.get('by_priority', {}).items():
    print(f"  {priority}: {count}")
print("")

# Recent history
print("Recent Notifications (Last 10)")
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

## Expected Output

```
Notification Statistics
==================================================
Total Sent:     47
Successful:     45
Failed:         2
Success Rate:   95.7%
Deduplicated:   12

By Priority:
  urgent: 5
  high: 32
  default: 8
  low: 2

Recent Notifications (Last 10)
--------------------------------------------------
[OK] 2024-01-15 14:30:22 - Task Complete: API Integration
[OK] 2024-01-15 14:25:10 - Action Required: Choose DB
[OK] 2024-01-15 14:20:05 - Task Complete: Unit Tests
[OK] 2024-01-15 14:15:33 - Blocked: Missing Dependency
[FAIL] 2024-01-15 14:10:00 - Test Notification
[OK] 2024-01-15 14:05:45 - Task Complete: Refactoring
...
```

## Subcommands

- `/ntfy-history today` - Show only today's notifications
- `/ntfy-history failed` - Show only failed notifications
- `/ntfy-history search <query>` - Search history
- `/ntfy-history export` - Export to Markdown
- `/ntfy-history export csv` - Export to CSV
- `/ntfy-history clear` - Clear all history (requires confirmation)

## Export Options

```python
from notification_logger import export_to_markdown, export_to_csv

# Export to Markdown
export_to_markdown("notification_report.md")

# Export to CSV
export_to_csv("notification_history.csv")
```

---

*Part of ntfy-notifications Plugin v2.0*
