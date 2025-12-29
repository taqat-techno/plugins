#!/usr/bin/env python3
"""
Notification Logger - Local History and Analytics
===================================================

This module provides local storage and analytics for notifications:
- JSON-based notification history
- Statistics and summaries
- Export to Markdown/CSV
- Search and filtering

Usage:
    from notification_logger import log_notification, get_history

    # Log a notification
    log_notification("Task Complete", "Details...", "high", ["check"])

    # Get recent notifications
    recent = get_recent(10)

    # Get statistics
    stats = get_statistics()

Author: TaqaTechno
License: MIT
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter


# =============================================================================
# CONFIGURATION
# =============================================================================

PLUGIN_DIR = Path(__file__).parent
LOG_FILE = PLUGIN_DIR / "notification_history.json"
EXPORT_DIR = PLUGIN_DIR / "exports"


# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

def log_notification(
    title: str,
    message: str,
    priority: str = "default",
    tags: List[str] = None,
    success: bool = True,
    error: str = None,
    metadata: Dict = None
) -> bool:
    """
    Log a notification to local history.

    Args:
        title: Notification title
        message: Notification message
        priority: Priority level
        tags: List of tags
        success: Whether the notification was sent successfully
        error: Error message if failed
        metadata: Additional metadata

    Returns:
        bool: True if logged successfully
    """
    try:
        # Load existing history
        history = _load_history()

        # Create entry
        entry = {
            'id': _generate_id(),
            'timestamp': datetime.now().isoformat(),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'weekday': datetime.now().strftime('%A'),
            'title': title,
            'message': message[:1000],  # Truncate for storage
            'priority': priority,
            'tags': tags or [],
            'success': success,
            'error': error,
            'metadata': metadata or {}
        }

        history.append(entry)

        # Trim to max size (keep last 1000)
        if len(history) > 1000:
            history = history[-1000:]

        # Save
        _save_history(history)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to log notification: {e}")
        return False


def _generate_id() -> str:
    """Generate unique notification ID."""
    import random
    import string
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))


def _load_history() -> List[Dict]:
    """Load history from file."""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def _save_history(history: List[Dict]) -> bool:
    """Save history to file."""
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save history: {e}")
        return False


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

def get_history(
    since_date: str = None,
    until_date: str = None,
    priority: str = None,
    success_only: bool = None,
    limit: int = None,
    search: str = None
) -> List[Dict]:
    """
    Get notification history with filters.

    Args:
        since_date: Get notifications since this date (YYYY-MM-DD)
        until_date: Get notifications until this date (YYYY-MM-DD)
        priority: Filter by priority level
        success_only: If True, only successful; if False, only failed
        limit: Maximum number to return
        search: Search text in title/message

    Returns:
        List of notification dictionaries (most recent first)
    """
    history = _load_history()

    # Apply filters
    if since_date:
        history = [n for n in history if n.get('date', '') >= since_date]

    if until_date:
        history = [n for n in history if n.get('date', '') <= until_date]

    if priority:
        history = [n for n in history if n.get('priority') == priority]

    if success_only is not None:
        history = [n for n in history if n.get('success') == success_only]

    if search:
        search_lower = search.lower()
        history = [
            n for n in history
            if search_lower in n.get('title', '').lower()
            or search_lower in n.get('message', '').lower()
        ]

    # Sort by timestamp (most recent first)
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    # Apply limit
    if limit:
        history = history[:limit]

    return history


def get_today() -> List[Dict]:
    """Get today's notifications."""
    today = datetime.now().strftime('%Y-%m-%d')
    return get_history(since_date=today)


def get_recent(count: int = 10) -> List[Dict]:
    """Get the most recent notifications."""
    return get_history(limit=count)


def get_failed() -> List[Dict]:
    """Get all failed notifications."""
    return get_history(success_only=False)


def get_by_priority(priority: str, limit: int = 50) -> List[Dict]:
    """Get notifications by priority level."""
    return get_history(priority=priority, limit=limit)


def search_notifications(query: str, limit: int = 50) -> List[Dict]:
    """Search notifications by title or message content."""
    return get_history(search=query, limit=limit)


# =============================================================================
# STATISTICS
# =============================================================================

def get_statistics(days: int = 7) -> Dict:
    """
    Get notification statistics for the last N days.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with statistics
    """
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    history = get_history(since_date=since)

    if not history:
        return {
            'period_days': days,
            'total': 0,
            'successful': 0,
            'failed': 0,
            'success_rate': 0,
            'by_priority': {},
            'by_day': {},
            'by_hour': {},
            'common_tags': []
        }

    # Calculate stats
    total = len(history)
    successful = sum(1 for n in history if n.get('success', True))
    failed = total - successful

    # By priority
    priority_counts = Counter(n.get('priority', 'default') for n in history)

    # By day
    day_counts = Counter(n.get('date', '') for n in history)

    # By hour
    hour_counts = Counter(
        n.get('time', '00:00:00')[:2] for n in history
    )

    # Common tags
    all_tags = []
    for n in history:
        all_tags.extend(n.get('tags', []))
    common_tags = Counter(all_tags).most_common(10)

    return {
        'period_days': days,
        'total': total,
        'successful': successful,
        'failed': failed,
        'success_rate': round(successful / total * 100, 1) if total > 0 else 0,
        'by_priority': dict(priority_counts),
        'by_day': dict(sorted(day_counts.items())),
        'by_hour': dict(sorted(hour_counts.items())),
        'common_tags': common_tags
    }


def print_summary(days: int = 7):
    """Print a formatted summary of notification statistics."""
    stats = get_statistics(days)

    print(f"\nNotification Summary (Last {days} days)")
    print("=" * 50)
    print(f"Total notifications: {stats['total']}")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Success rate: {stats['success_rate']}%")

    if stats['by_priority']:
        print("\nBy Priority:")
        for priority, count in sorted(stats['by_priority'].items()):
            print(f"  {priority}: {count}")

    if stats['by_day']:
        print("\nBy Day:")
        for day, count in list(stats['by_day'].items())[-7:]:
            print(f"  {day}: {count}")

    if stats['common_tags']:
        print("\nTop Tags:")
        for tag, count in stats['common_tags'][:5]:
            print(f"  {tag}: {count}")

    # Recent notifications
    recent = get_recent(5)
    if recent:
        print("\nMost Recent:")
        for n in recent:
            status = "[OK]" if n.get('success', True) else "[FAIL]"
            print(f"  {status} [{n.get('time', '')}] {n.get('title', '')[:40]}")


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def export_to_markdown(
    output_path: str = None,
    since_date: str = None,
    limit: int = 100
) -> Optional[str]:
    """
    Export notification history to Markdown file.

    Args:
        output_path: Path for output file
        since_date: Export notifications since this date
        limit: Maximum notifications to export

    Returns:
        str: Path to exported file, or None if failed
    """
    try:
        history = get_history(since_date=since_date, limit=limit)

        if not history:
            print("[INFO] No notifications to export")
            return None

        if not output_path:
            EXPORT_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = EXPORT_DIR / f"notifications_{timestamp}.md"

        lines = [
            "# Notification History",
            "",
            f"**Exported:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total:** {len(history)} notifications",
            "",
            "---",
            ""
        ]

        for notif in history:
            status = "SUCCESS" if notif.get('success', True) else "FAILED"
            tags = ', '.join(notif.get('tags', []))

            lines.extend([
                f"## {notif.get('title', 'Untitled')}",
                "",
                f"- **Date:** {notif.get('date', '')} {notif.get('time', '')}",
                f"- **Priority:** {notif.get('priority', 'default')}",
                f"- **Status:** {status}",
                f"- **Tags:** {tags or 'None'}",
                "",
                notif.get('message', ''),
                "",
                "---",
                ""
            ])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"[OK] Exported {len(history)} notifications to: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"[ERROR] Failed to export: {e}")
        return None


def export_to_csv(
    output_path: str = None,
    since_date: str = None,
    limit: int = 1000
) -> Optional[str]:
    """
    Export notification history to CSV file.

    Args:
        output_path: Path for output file
        since_date: Export notifications since this date
        limit: Maximum notifications to export

    Returns:
        str: Path to exported file, or None if failed
    """
    try:
        import csv

        history = get_history(since_date=since_date, limit=limit)

        if not history:
            print("[INFO] No notifications to export")
            return None

        if not output_path:
            EXPORT_DIR.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = EXPORT_DIR / f"notifications_{timestamp}.csv"

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'time', 'title', 'message', 'priority', 'tags', 'success', 'error'
            ])
            writer.writeheader()

            for notif in history:
                writer.writerow({
                    'date': notif.get('date', ''),
                    'time': notif.get('time', ''),
                    'title': notif.get('title', ''),
                    'message': notif.get('message', '').replace('\n', ' '),
                    'priority': notif.get('priority', ''),
                    'tags': ','.join(notif.get('tags', [])),
                    'success': notif.get('success', True),
                    'error': notif.get('error', '')
                })

        print(f"[OK] Exported {len(history)} notifications to: {output_path}")
        return str(output_path)

    except Exception as e:
        print(f"[ERROR] Failed to export: {e}")
        return None


# =============================================================================
# MANAGEMENT
# =============================================================================

def clear_history(confirm: bool = False) -> bool:
    """
    Clear all notification history.

    Args:
        confirm: Must be True to actually clear

    Returns:
        bool: True if cleared successfully
    """
    if not confirm:
        print("[WARNING] This will delete all notification history!")
        print("[INFO] Call clear_history(confirm=True) to proceed")
        return False

    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        print("[OK] Notification history cleared")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to clear history: {e}")
        return False


def prune_old_entries(days: int = 30) -> int:
    """
    Remove entries older than specified days.

    Args:
        days: Keep entries from last N days

    Returns:
        int: Number of entries removed
    """
    history = _load_history()
    original_count = len(history)

    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    history = [n for n in history if n.get('date', '') >= cutoff]

    _save_history(history)

    removed = original_count - len(history)
    print(f"[OK] Removed {removed} entries older than {days} days")
    return removed


def get_storage_info() -> Dict:
    """Get information about notification storage."""
    history = _load_history()

    if not history:
        return {
            'count': 0,
            'file_size_kb': 0,
            'oldest': None,
            'newest': None
        }

    file_size = LOG_FILE.stat().st_size if LOG_FILE.exists() else 0

    dates = [n.get('timestamp', '') for n in history if n.get('timestamp')]
    dates.sort()

    return {
        'count': len(history),
        'file_size_kb': round(file_size / 1024, 2),
        'oldest': dates[0] if dates else None,
        'newest': dates[-1] if dates else None
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Notification History")
    print("=" * 60)
    print("")

    # Show storage info
    info = get_storage_info()
    print(f"Total entries: {info['count']}")
    print(f"File size: {info['file_size_kb']} KB")

    if info['oldest']:
        print(f"Oldest: {info['oldest'][:19]}")
        print(f"Newest: {info['newest'][:19]}")

    print("")

    # Show summary
    print_summary()
