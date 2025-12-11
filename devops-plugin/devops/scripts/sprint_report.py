#!/usr/bin/env python3
"""
Sprint Report Generator for Azure DevOps

This script generates comprehensive sprint progress reports by analyzing
work items in the current or specified iteration.

Usage:
    python sprint_report.py --project "ProjectName" --sprint "Sprint 15"
    python sprint_report.py --project "ProjectName" --current
"""

import argparse
import json
from datetime import datetime
from collections import defaultdict


def generate_sprint_report(work_items: list, sprint_info: dict) -> str:
    """
    Generate a formatted sprint report from work items data.

    Args:
        work_items: List of work item dictionaries
        sprint_info: Sprint/iteration information

    Returns:
        Formatted markdown report string
    """
    # Categorize work items
    by_type = defaultdict(list)
    by_state = defaultdict(list)
    by_assignee = defaultdict(list)

    total_points = 0
    completed_points = 0

    for item in work_items:
        item_type = item.get('System.WorkItemType', 'Unknown')
        state = item.get('System.State', 'Unknown')
        assignee = item.get('System.AssignedTo', {}).get('displayName', 'Unassigned')
        points = item.get('Microsoft.VSTS.Scheduling.StoryPoints', 0) or 0

        by_type[item_type].append(item)
        by_state[state].append(item)
        by_assignee[assignee].append(item)

        total_points += points
        if state in ['Closed', 'Done', 'Completed']:
            completed_points += points

    # Calculate progress
    total_items = len(work_items)
    completed_items = len(by_state.get('Closed', [])) + len(by_state.get('Done', []))
    in_progress = len(by_state.get('Active', [])) + len(by_state.get('In Progress', []))
    not_started = total_items - completed_items - in_progress

    completion_pct = (completed_items / total_items * 100) if total_items > 0 else 0
    points_pct = (completed_points / total_points * 100) if total_points > 0 else 0

    # Generate report
    report = []
    report.append(f"## Sprint Report - {sprint_info.get('name', 'Current Sprint')}")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append(f"**Start Date:** {sprint_info.get('startDate', 'N/A')}")
    report.append(f"**End Date:** {sprint_info.get('finishDate', 'N/A')}")
    report.append("")

    # Progress section
    report.append("### Progress Overview")
    report.append("")
    report.append(f"| Metric | Value |")
    report.append(f"|--------|-------|")
    report.append(f"| Total Items | {total_items} |")
    report.append(f"| Completed | {completed_items} ({completion_pct:.0f}%) |")
    report.append(f"| In Progress | {in_progress} |")
    report.append(f"| Not Started | {not_started} |")
    report.append(f"| Story Points (Total) | {total_points} |")
    report.append(f"| Story Points (Done) | {completed_points} ({points_pct:.0f}%) |")
    report.append("")

    # By type breakdown
    report.append("### By Work Item Type")
    report.append("")
    report.append("| Type | Total | Done | In Progress | Not Started |")
    report.append("|------|-------|------|-------------|-------------|")

    for item_type, items in sorted(by_type.items()):
        done = sum(1 for i in items if i.get('System.State') in ['Closed', 'Done'])
        active = sum(1 for i in items if i.get('System.State') in ['Active', 'In Progress'])
        new = len(items) - done - active
        report.append(f"| {item_type} | {len(items)} | {done} | {active} | {new} |")

    report.append("")

    # By assignee breakdown
    report.append("### By Team Member")
    report.append("")
    report.append("| Member | Assigned | Completed | In Progress |")
    report.append("|--------|----------|-----------|-------------|")

    for assignee, items in sorted(by_assignee.items()):
        done = sum(1 for i in items if i.get('System.State') in ['Closed', 'Done'])
        active = sum(1 for i in items if i.get('System.State') in ['Active', 'In Progress'])
        report.append(f"| {assignee} | {len(items)} | {done} | {active} |")

    report.append("")

    # At risk items (not started with high priority)
    at_risk = [
        i for i in work_items
        if i.get('System.State') in ['New', 'To Do']
        and i.get('Microsoft.VSTS.Common.Priority', 4) <= 2
    ]

    if at_risk:
        report.append("### At Risk Items")
        report.append("")
        report.append("| ID | Type | Title | Priority | Assignee |")
        report.append("|----|------|-------|----------|----------|")

        for item in at_risk[:10]:  # Limit to 10
            item_id = item.get('System.Id', 'N/A')
            item_type = item.get('System.WorkItemType', 'Unknown')
            title = item.get('System.Title', 'No title')[:40]
            priority = item.get('Microsoft.VSTS.Common.Priority', 'N/A')
            assignee = item.get('System.AssignedTo', {}).get('displayName', 'Unassigned')
            report.append(f"| #{item_id} | {item_type} | {title} | P{priority} | {assignee} |")

        report.append("")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Generate Sprint Report')
    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--sprint', help='Sprint name')
    parser.add_argument('--current', action='store_true', help='Use current sprint')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--format', choices=['md', 'json'], default='md', help='Output format')

    args = parser.parse_args()

    print(f"Sprint Report Generator")
    print(f"Project: {args.project}")
    print(f"Sprint: {args.sprint or 'Current'}")
    print("")
    print("Note: This script provides the report generation logic.")
    print("The actual Azure DevOps data should be fetched via MCP tools:")
    print("  1. mcp_ado_work_get_current_iteration")
    print("  2. mcp_ado_workitems_query_workitems with WIQL query")
    print("")
    print("Example WIQL query:")
    print("SELECT [System.Id], [System.Title], [System.State],")
    print("       [System.WorkItemType], [System.AssignedTo],")
    print("       [Microsoft.VSTS.Scheduling.StoryPoints]")
    print("FROM WorkItems")
    print("WHERE [System.IterationPath] UNDER @CurrentIteration")


if __name__ == "__main__":
    main()
