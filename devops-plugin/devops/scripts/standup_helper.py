#!/usr/bin/env python3
"""
Daily Standup Helper for Azure DevOps

This script helps generate daily standup notes by analyzing recent work item
activity for the current user.

Usage:
    python standup_helper.py --user "Ahmed" --days 2
    python standup_helper.py --me --days 1
"""

import argparse
from datetime import datetime, timedelta
from collections import defaultdict


def categorize_work_items(work_items: list, cutoff_date: datetime) -> dict:
    """
    Categorize work items into completed, in progress, and blocked.

    Args:
        work_items: List of work item dictionaries
        cutoff_date: Date to consider for "yesterday" items

    Returns:
        Dictionary with categorized items
    """
    categories = {
        'completed': [],
        'in_progress': [],
        'blocked': [],
        'planned': []
    }

    for item in work_items:
        state = item.get('System.State', '')
        changed_date = item.get('System.ChangedDate', '')
        tags = item.get('System.Tags', '') or ''

        # Parse changed date if string
        if isinstance(changed_date, str) and changed_date:
            try:
                changed_dt = datetime.fromisoformat(changed_date.replace('Z', '+00:00'))
            except:
                changed_dt = datetime.now()
        else:
            changed_dt = datetime.now()

        # Categorize based on state and timing
        if state in ['Closed', 'Done', 'Resolved', 'Completed']:
            if changed_dt.date() >= cutoff_date.date():
                categories['completed'].append(item)
        elif 'blocked' in tags.lower() or 'impediment' in tags.lower():
            categories['blocked'].append(item)
        elif state in ['Active', 'In Progress', 'Committed']:
            categories['in_progress'].append(item)
        elif state in ['New', 'To Do', 'Approved']:
            categories['planned'].append(item)

    return categories


def format_standup_notes(categories: dict, user_name: str = None) -> str:
    """
    Format categorized work items as standup notes.

    Args:
        categories: Dictionary with categorized work items
        user_name: Name of the user

    Returns:
        Formatted markdown standup notes
    """
    today = datetime.now().strftime('%B %d, %Y')

    notes = []
    notes.append(f"## Daily Standup - {today}")
    if user_name:
        notes.append(f"**Team Member:** {user_name}")
    notes.append("")

    # Yesterday's completed work
    notes.append("### Completed (Yesterday)")
    if categories['completed']:
        for item in categories['completed'][:5]:  # Limit to 5
            item_id = item.get('System.Id', 'N/A')
            item_type = item.get('System.WorkItemType', 'Item')
            title = item.get('System.Title', 'No title')[:50]
            notes.append(f"- [{item_type}] #{item_id}: {title}")
    else:
        notes.append("- No items completed")
    notes.append("")

    # Today's work
    notes.append("### In Progress (Today)")
    if categories['in_progress']:
        for item in categories['in_progress'][:5]:
            item_id = item.get('System.Id', 'N/A')
            item_type = item.get('System.WorkItemType', 'Item')
            title = item.get('System.Title', 'No title')[:50]
            remaining = item.get('Microsoft.VSTS.Scheduling.RemainingWork', '')
            remaining_str = f" ({remaining}h remaining)" if remaining else ""
            notes.append(f"- [{item_type}] #{item_id}: {title}{remaining_str}")
    else:
        notes.append("- No items in progress")
    notes.append("")

    # Blockers
    notes.append("### Blockers")
    if categories['blocked']:
        for item in categories['blocked']:
            item_id = item.get('System.Id', 'N/A')
            title = item.get('System.Title', 'No title')[:50]
            notes.append(f"- #{item_id}: {title}")
    else:
        notes.append("- None")
    notes.append("")

    # Planned work
    if categories['planned']:
        notes.append("### Planned (Next)")
        for item in categories['planned'][:3]:
            item_id = item.get('System.Id', 'N/A')
            item_type = item.get('System.WorkItemType', 'Item')
            title = item.get('System.Title', 'No title')[:50]
            notes.append(f"- [{item_type}] #{item_id}: {title}")
        notes.append("")

    return "\n".join(notes)


def generate_wiql_query(user: str = "@Me", days: int = 2) -> str:
    """
    Generate WIQL query for standup items.

    Args:
        user: User identifier (@Me or display name)
        days: Number of days to look back

    Returns:
        WIQL query string
    """
    query = f"""SELECT [System.Id], [System.Title], [System.State],
       [System.WorkItemType], [System.ChangedDate], [System.Tags],
       [Microsoft.VSTS.Scheduling.RemainingWork]
FROM WorkItems
WHERE [System.AssignedTo] = {user}
  AND ([System.State] <> 'Closed'
       OR [System.ChangedDate] >= @Today - {days})
ORDER BY [System.State], [System.ChangedDate] DESC"""

    return query


def main():
    parser = argparse.ArgumentParser(description='Generate Standup Notes')
    parser.add_argument('--user', help='User display name')
    parser.add_argument('--me', action='store_true', help='Use current user (@Me)')
    parser.add_argument('--days', type=int, default=2, help='Days to look back')
    parser.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    user = "@Me" if args.me else (f"'{args.user}'" if args.user else "@Me")

    print("Standup Helper")
    print("=" * 40)
    print("")
    print("WIQL Query to fetch standup data:")
    print("-" * 40)
    print(generate_wiql_query(user, args.days))
    print("-" * 40)
    print("")
    print("Use this query with mcp_ado_workitems_query_workitems")
    print("Then pass the results to categorize_work_items() and format_standup_notes()")


if __name__ == "__main__":
    main()
