# /ntfy-history

View notification history and statistics.

## What This Does

Shows recent notifications sent by Claude and provides options to:
1. View recent notifications
2. See statistics and trends
3. Search history
4. Export to file

## Implementation

```python
import sys
from pathlib import Path

plugin_dir = Path(r"${PLUGIN_DIR}")
sys.path.insert(0, str(plugin_dir))

from notification_logger import (
    get_recent,
    get_today,
    get_failed,
    get_statistics,
    print_summary,
    export_to_markdown,
    export_to_csv
)

print("Notification History")
print("=" * 50)
print("")

# Show summary first
print_summary()

print("")
print("=" * 50)
print("")

# Recent notifications
print("Recent Notifications:")
print("-" * 50)

recent = get_recent(10)
for n in recent:
    status = "[OK]" if n.get('success', True) else "[FAIL]"
    priority = n.get('priority', 'default')
    title = n.get('title', 'Untitled')[:45]

    print(f"{status} [{n.get('date')} {n.get('time')}] {title}")
    if not n.get('success'):
        print(f"     Error: {n.get('error', 'Unknown')[:50]}")
```

## Interactive Options

### View Today's Notifications
```python
today = get_today()
print(f"Today: {len(today)} notifications")
for n in today:
    print(f"  [{n['time']}] {n['title']}")
```

### View Failed Only
```python
failed = get_failed()
print(f"Failed notifications: {len(failed)}")
for n in failed:
    print(f"  [{n['date']} {n['time']}] {n['title']}")
    print(f"    Error: {n['error']}")
```

### Search History
```python
from notification_logger import search_notifications

results = search_notifications("database")
print(f"Found {len(results)} notifications mentioning 'database'")
```

### Export Options
```python
# Export to Markdown
path = export_to_markdown()
print(f"Exported to: {path}")

# Export to CSV
path = export_to_csv()
print(f"Exported to: {path}")
```

## Example Output

```
Notification History
==================================================

Notification Summary (Last 7 days)
==================================================
Total notifications: 47
  Successful: 45
  Failed: 2
  Success rate: 95.7%

By Priority:
  urgent: 5
  high: 28
  default: 12
  low: 2

By Day:
  2025-12-28: 8
  2025-12-27: 12
  2025-12-26: 9
  2025-12-25: 6
  2025-12-24: 7
  2025-12-23: 5

Top Tags:
  white_check_mark: 28
  computer: 45
  warning: 12
  bell: 5

Most Recent:
  [OK] [15:30:22] Task Complete: API Integration
  [OK] [15:28:45] Task Complete: Database Migration
  [OK] [14:55:12] ACTION REQUIRED: Choose Framework
  [FAIL] [14:30:01] Task Complete: Build Process
  [OK] [14:15:33] BLOCKED: Missing Dependency

==================================================

Recent Notifications:
--------------------------------------------------
[OK] [2025-12-28 15:30:22] Task Complete: API Integration
[OK] [2025-12-28 15:28:45] Task Complete: Database Migration
[OK] [2025-12-28 14:55:12] ACTION REQUIRED: Choose Framework
[FAIL] [2025-12-28 14:30:01] Task Complete: Build Process
     Error: Connection timeout
[OK] [2025-12-28 14:15:33] BLOCKED: Missing Dependency
```

## Commands Subprompts

- `/ntfy-history today` - Show only today's notifications
- `/ntfy-history failed` - Show only failed notifications
- `/ntfy-history search <query>` - Search history
- `/ntfy-history export` - Export to Markdown file
- `/ntfy-history export csv` - Export to CSV file
- `/ntfy-history clear` - Clear all history (requires confirmation)
