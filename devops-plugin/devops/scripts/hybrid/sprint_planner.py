#!/usr/bin/env python3
"""
Hybrid Sprint Planner

Combines CLI for speed with MCP data for rich sprint planning.
Analyzes capacity, work items, and generates sprint plan recommendations.

Author: TAQAT Techno
Version: 2.0.0
"""

import subprocess
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class TeamMember:
    """Represents a team member with capacity info."""
    name: str
    email: str
    capacity_per_day: float
    days_off: List[Tuple[str, str]]
    assigned_work: float = 0
    assigned_items: int = 0


@dataclass
class WorkItem:
    """Represents a work item for planning."""
    id: int
    title: str
    item_type: str
    state: str
    story_points: float
    remaining_work: float
    priority: int
    assigned_to: Optional[str]


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
            print(f"CLI Warning: {result.stderr}", file=sys.stderr)
            return None
        return json.loads(result.stdout) if result.stdout.strip() else None
    except (json.JSONDecodeError, Exception) as e:
        print(f"CLI Error: {e}", file=sys.stderr)
        return None


def get_current_iteration(project: str, team: str) -> Optional[Dict]:
    """Get current sprint/iteration info."""
    cmd = f'az boards iteration team list --project "{project}" --team "{team}" --timeframe current -o json'
    result = run_cli(cmd)
    return result[0] if result and len(result) > 0 else None


def get_backlog_items(project: str) -> List[WorkItem]:
    """Get backlog items available for planning."""
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
           [Microsoft.VSTS.Scheduling.StoryPoints], [Microsoft.VSTS.Scheduling.RemainingWork],
           [Microsoft.VSTS.Common.Priority], [System.AssignedTo]
    FROM WorkItems
    WHERE [System.TeamProject] = '{project}'
      AND [System.State] IN ('New', 'Approved', 'Committed')
      AND [System.WorkItemType] IN ('User Story', 'Product Backlog Item', 'Bug')
    ORDER BY [Microsoft.VSTS.Common.Priority], [Microsoft.VSTS.Common.StackRank]
    """

    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    items = run_cli(cmd)
    if not items:
        return []

    work_items = []
    for item in items:
        fields = item.get('fields', {})
        work_items.append(WorkItem(
            id=item.get('id', 0),
            title=fields.get('System.Title', 'No Title'),
            item_type=fields.get('System.WorkItemType', 'Item'),
            state=fields.get('System.State', 'Unknown'),
            story_points=fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0,
            remaining_work=fields.get('Microsoft.VSTS.Scheduling.RemainingWork', 0) or 0,
            priority=fields.get('Microsoft.VSTS.Common.Priority', 4),
            assigned_to=fields.get('System.AssignedTo', {}).get('displayName')
        ))

    return work_items


def get_sprint_items(project: str, iteration_path: str) -> List[WorkItem]:
    """Get items already in the sprint."""
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
           [Microsoft.VSTS.Scheduling.StoryPoints], [Microsoft.VSTS.Scheduling.RemainingWork],
           [Microsoft.VSTS.Common.Priority], [System.AssignedTo]
    FROM WorkItems
    WHERE [System.IterationPath] = '{iteration_path}'
      AND [System.State] <> 'Removed'
    ORDER BY [Microsoft.VSTS.Common.Priority]
    """

    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    items = run_cli(cmd)
    if not items:
        return []

    work_items = []
    for item in items:
        fields = item.get('fields', {})
        work_items.append(WorkItem(
            id=item.get('id', 0),
            title=fields.get('System.Title', 'No Title'),
            item_type=fields.get('System.WorkItemType', 'Item'),
            state=fields.get('System.State', 'Unknown'),
            story_points=fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0,
            remaining_work=fields.get('Microsoft.VSTS.Scheduling.RemainingWork', 0) or 0,
            priority=fields.get('Microsoft.VSTS.Common.Priority', 4),
            assigned_to=fields.get('System.AssignedTo', {}).get('displayName')
        ))

    return work_items


def calculate_sprint_metrics(iteration: Dict, sprint_items: List[WorkItem]) -> Dict:
    """Calculate sprint metrics and capacity."""
    start_date = datetime.fromisoformat(iteration['attributes']['startDate'].replace('Z', '+00:00'))
    finish_date = datetime.fromisoformat(iteration['attributes']['finishDate'].replace('Z', '+00:00'))

    # Calculate working days (exclude weekends)
    working_days = 0
    current = start_date
    while current <= finish_date:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            working_days += 1
        current += timedelta(days=1)

    # Calculate story points
    total_points = sum(item.story_points for item in sprint_items)
    completed_points = sum(item.story_points for item in sprint_items if item.state in ('Done', 'Closed'))
    remaining_points = total_points - completed_points

    # Calculate work hours
    total_work = sum(item.remaining_work for item in sprint_items)

    # Group by state
    by_state = {}
    for item in sprint_items:
        by_state[item.state] = by_state.get(item.state, 0) + 1

    # Group by type
    by_type = {}
    for item in sprint_items:
        by_type[item.item_type] = by_type.get(item.item_type, 0) + 1

    return {
        'sprint_name': iteration['name'],
        'start_date': start_date.strftime('%Y-%m-%d'),
        'finish_date': finish_date.strftime('%Y-%m-%d'),
        'working_days': working_days,
        'days_remaining': max(0, (finish_date - datetime.now(finish_date.tzinfo)).days),
        'total_items': len(sprint_items),
        'story_points': {
            'total': total_points,
            'completed': completed_points,
            'remaining': remaining_points
        },
        'remaining_work_hours': total_work,
        'by_state': by_state,
        'by_type': by_type,
        'progress_percent': round((completed_points / total_points * 100) if total_points > 0 else 0, 1)
    }


def suggest_sprint_plan(backlog: List[WorkItem], capacity_hours: float, velocity: float) -> List[WorkItem]:
    """Suggest items to add to sprint based on capacity and velocity."""
    suggested = []
    used_capacity = 0
    used_points = 0

    # Sort by priority
    sorted_backlog = sorted(backlog, key=lambda x: (x.priority, -x.story_points))

    for item in sorted_backlog:
        # Estimate work based on story points if remaining_work not set
        estimated_work = item.remaining_work if item.remaining_work > 0 else item.story_points * 4

        if used_capacity + estimated_work <= capacity_hours and used_points + item.story_points <= velocity:
            suggested.append(item)
            used_capacity += estimated_work
            used_points += item.story_points

        if used_capacity >= capacity_hours * 0.9:  # 90% capacity
            break

    return suggested


def format_sprint_plan(metrics: Dict, backlog: List[WorkItem], suggestions: List[WorkItem]) -> str:
    """Format sprint planning report."""
    lines = [
        f"# Sprint Planning Report: {metrics['sprint_name']}",
        "",
        f"**Period:** {metrics['start_date']} to {metrics['finish_date']}",
        f"**Working Days:** {metrics['working_days']} ({metrics['days_remaining']} remaining)",
        "",
        "## Current Sprint Status",
        "",
        f"- **Total Items:** {metrics['total_items']}",
        f"- **Story Points:** {metrics['story_points']['completed']}/{metrics['story_points']['total']} completed",
        f"- **Progress:** {metrics['progress_percent']}%",
        f"- **Remaining Work:** {metrics['remaining_work_hours']} hours",
        "",
        "### By State",
        ""
    ]

    for state, count in sorted(metrics['by_state'].items()):
        lines.append(f"- {state}: {count}")

    lines.extend([
        "",
        "### By Type",
        ""
    ])

    for item_type, count in sorted(metrics['by_type'].items()):
        lines.append(f"- {item_type}: {count}")

    lines.extend([
        "",
        "## Backlog Available",
        "",
        f"**Items ready for planning:** {len(backlog)}",
        ""
    ])

    if backlog:
        lines.append("| ID | Type | Title | Points | Priority |")
        lines.append("|----|------|-------|--------|----------|")
        for item in backlog[:10]:
            lines.append(f"| #{item.id} | {item.item_type} | {item.title[:40]}... | {item.story_points} | P{item.priority} |")

        if len(backlog) > 10:
            lines.append(f"| ... | ... | *{len(backlog) - 10} more items* | ... | ... |")

    lines.extend([
        "",
        "## Suggested for Sprint",
        ""
    ])

    if suggestions:
        total_points = sum(item.story_points for item in suggestions)
        lines.append(f"**Recommended items:** {len(suggestions)} ({total_points} story points)")
        lines.append("")
        lines.append("| ID | Type | Title | Points | Priority |")
        lines.append("|----|------|-------|--------|----------|")
        for item in suggestions:
            lines.append(f"| #{item.id} | {item.item_type} | {item.title[:40]}... | {item.story_points} | P{item.priority} |")
    else:
        lines.append("No suggestions - sprint may be at capacity or backlog is empty")

    lines.extend([
        "",
        "---",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
    ])

    return "\n".join(lines)


def plan_sprint(project: str, team: str, capacity_hours: float = 160, velocity: float = 30) -> str:
    """Main function to generate sprint plan."""
    print(f"Planning sprint for {project} / {team}...", file=sys.stderr)

    # Get current iteration
    iteration = get_current_iteration(project, team)
    if not iteration:
        return "Error: Could not get current iteration"

    print(f"Sprint: {iteration['name']}", file=sys.stderr)

    # Get sprint items
    sprint_items = get_sprint_items(project, iteration['path'])
    print(f"Current sprint items: {len(sprint_items)}", file=sys.stderr)

    # Get backlog items
    backlog = get_backlog_items(project)
    print(f"Backlog items: {len(backlog)}", file=sys.stderr)

    # Calculate metrics
    metrics = calculate_sprint_metrics(iteration, sprint_items)

    # Calculate remaining capacity
    used_capacity = metrics['remaining_work_hours']
    remaining_capacity = max(0, capacity_hours - used_capacity)
    remaining_velocity = max(0, velocity - metrics['story_points']['total'])

    # Generate suggestions
    suggestions = suggest_sprint_plan(backlog, remaining_capacity, remaining_velocity)

    return format_sprint_plan(metrics, backlog, suggestions)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Sprint planning with capacity analysis')
    parser.add_argument('project', nargs='?', default='Relief Center',
                        help='Project name (default: Relief Center)')
    parser.add_argument('--team', '-t', default='',
                        help='Team name (default: {project} Team)')
    parser.add_argument('--capacity', '-c', type=float, default=160,
                        help='Total team capacity in hours (default: 160)')
    parser.add_argument('--velocity', '-v', type=float, default=30,
                        help='Target velocity in story points (default: 30)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    team = args.team if args.team else f"{args.project} Team"

    result = plan_sprint(args.project, team, args.capacity, args.velocity)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()
