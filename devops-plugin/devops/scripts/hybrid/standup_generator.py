#!/usr/bin/env python3
"""
Hybrid Standup Generator

Uses CLI for speed and MCP for rich details.
Generates formatted standup notes from Azure DevOps work items.

Author: TAQAT Techno
Version: 2.0.0
"""

import subprocess
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


def run_cli(command: str) -> Optional[Any]:
    """Execute CLI command and return JSON result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout) if result.stdout.strip() else None
    except (json.JSONDecodeError, Exception) as e:
        print(f"CLI Error: {e}", file=sys.stderr)
        return None


def get_my_work_items(project: str) -> List[Dict]:
    """Query work items assigned to current user."""
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.State],
           [System.ChangedDate], [System.WorkItemType],
           [Microsoft.VSTS.Common.Priority]
    FROM WorkItems
    WHERE [System.AssignedTo] = @Me
      AND [System.TeamProject] = '{project}'
      AND [System.State] <> 'Removed'
      AND [System.State] <> 'Closed'
    ORDER BY [System.ChangedDate] DESC
    """

    # Escape the WIQL for command line
    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    result = run_cli(cmd)
    return result if result else []


def get_completed_items(project: str, since_date: str) -> List[Dict]:
    """Get items completed since a specific date."""
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.State],
           [System.ChangedDate], [System.WorkItemType]
    FROM WorkItems
    WHERE [System.AssignedTo] = @Me
      AND [System.TeamProject] = '{project}'
      AND [System.State] IN ('Done', 'Closed', 'Resolved')
      AND [System.ChangedDate] >= '{since_date}'
    ORDER BY [System.ChangedDate] DESC
    """

    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    result = run_cli(cmd)
    return result if result else []


def categorize_items(items: List[Dict], completed: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize items into yesterday, today, and blockers."""
    categories = {
        'yesterday': [],
        'today': [],
        'blockers': [],
        'in_progress': []
    }

    # Completed items go to yesterday
    for item in completed:
        categories['yesterday'].append({
            'id': item.get('id'),
            'title': item.get('fields', {}).get('System.Title', 'No Title'),
            'type': item.get('fields', {}).get('System.WorkItemType', 'Item'),
            'state': item.get('fields', {}).get('System.State', 'Unknown')
        })

    # Active items
    for item in items:
        state = item.get('fields', {}).get('System.State', '')
        priority = item.get('fields', {}).get('Microsoft.VSTS.Common.Priority', 4)

        item_data = {
            'id': item.get('id'),
            'title': item.get('fields', {}).get('System.Title', 'No Title'),
            'type': item.get('fields', {}).get('System.WorkItemType', 'Item'),
            'state': state,
            'priority': priority
        }

        if state == 'Blocked':
            categories['blockers'].append(item_data)
        elif state in ('Active', 'In Progress', 'New'):
            categories['today'].append(item_data)
            if state == 'Active':
                categories['in_progress'].append(item_data)

    # Sort by priority
    for key in categories:
        categories[key] = sorted(categories[key], key=lambda x: x.get('priority', 4))

    return categories


def format_standup(categories: Dict[str, List], project: str, format_type: str = 'markdown') -> str:
    """Format standup notes."""
    today = datetime.now().strftime("%Y-%m-%d")

    if format_type == 'markdown':
        lines = [
            f"# Daily Standup - {today}",
            f"**Project:** {project}",
            "",
            "## Yesterday",
            ""
        ]

        if categories['yesterday']:
            for item in categories['yesterday'][:5]:
                lines.append(f"- [#{item['id']}] {item['title']} ✅")
        else:
            lines.append("- No items completed")

        lines.extend(["", "## Today", ""])

        if categories['today']:
            for item in categories['today'][:5]:
                status = "🔄" if item['state'] == 'Active' else "📋"
                lines.append(f"- [#{item['id']}] {item['title']} {status}")
        else:
            lines.append("- Planning work items")

        lines.extend(["", "## Blockers", ""])

        if categories['blockers']:
            for item in categories['blockers']:
                lines.append(f"- ⛔ [#{item['id']}] {item['title']}")
        else:
            lines.append("- None")

        lines.extend(["", "---", f"*Generated: {datetime.now().strftime('%H:%M')}*"])

        return "\n".join(lines)

    else:  # Plain text
        lines = [
            f"Daily Standup - {today}",
            f"Project: {project}",
            "",
            "YESTERDAY:",
        ]

        if categories['yesterday']:
            for item in categories['yesterday'][:5]:
                lines.append(f"  - [#{item['id']}] {item['title']}")
        else:
            lines.append("  - No items completed")

        lines.extend(["", "TODAY:"])

        if categories['today']:
            for item in categories['today'][:5]:
                lines.append(f"  - [#{item['id']}] {item['title']}")
        else:
            lines.append("  - Planning work items")

        lines.extend(["", "BLOCKERS:"])

        if categories['blockers']:
            for item in categories['blockers']:
                lines.append(f"  - [#{item['id']}] {item['title']}")
        else:
            lines.append("  - None")

        return "\n".join(lines)


def generate_standup(project: str, format_type: str = 'markdown') -> str:
    """Main function to generate standup notes."""
    print(f"Generating standup for {project}...", file=sys.stderr)

    # Calculate yesterday's date
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Get work items using CLI (fast)
    active_items = get_my_work_items(project)
    completed_items = get_completed_items(project, yesterday)

    print(f"Found {len(active_items)} active items, {len(completed_items)} completed", file=sys.stderr)

    # Categorize items
    categories = categorize_items(active_items, completed_items)

    # Format output
    return format_standup(categories, project, format_type)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate daily standup notes from Azure DevOps')
    parser.add_argument('project', nargs='?', default='Relief Center',
                        help='Project name (default: Relief Center)')
    parser.add_argument('--format', '-f', choices=['markdown', 'text'], default='markdown',
                        help='Output format (default: markdown)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--copy', '-c', action='store_true',
                        help='Copy to clipboard (Windows)')

    args = parser.parse_args()

    result = generate_standup(args.project, args.format)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)

    if args.copy and sys.platform == 'win32':
        import subprocess
        subprocess.run(['clip'], input=result.encode('utf-8'), check=True)
        print("Copied to clipboard!", file=sys.stderr)


if __name__ == '__main__':
    main()
