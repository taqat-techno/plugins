#!/usr/bin/env python3
"""
Pull Request Analyzer for Azure DevOps

This script helps analyze pull requests by examining code changes,
linked work items, and review status.

Usage:
    python pr_analyzer.py --repo "MyRepo" --pr 45
    python pr_analyzer.py --repo "MyRepo" --list-open
"""

import argparse
from datetime import datetime
from collections import defaultdict


def analyze_pr(pr_data: dict, work_items: list = None, changes: list = None) -> str:
    """
    Analyze a pull request and generate a summary report.

    Args:
        pr_data: Pull request data from Azure DevOps
        work_items: List of linked work items
        changes: List of file changes

    Returns:
        Formatted markdown analysis
    """
    report = []

    # Header
    pr_id = pr_data.get('pullRequestId', 'N/A')
    title = pr_data.get('title', 'No title')
    report.append(f"## PR #{pr_id}: {title}")
    report.append("")

    # Basic info
    report.append("### Details")
    report.append("")
    report.append(f"| Field | Value |")
    report.append(f"|-------|-------|")
    report.append(f"| Author | {pr_data.get('createdBy', {}).get('displayName', 'Unknown')} |")
    report.append(f"| Status | {pr_data.get('status', 'Unknown')} |")
    report.append(f"| Source | {pr_data.get('sourceRefName', '').replace('refs/heads/', '')} |")
    report.append(f"| Target | {pr_data.get('targetRefName', '').replace('refs/heads/', '')} |")
    report.append(f"| Created | {pr_data.get('creationDate', 'Unknown')[:10]} |")
    report.append("")

    # Description
    description = pr_data.get('description', '')
    if description:
        report.append("### Description")
        report.append("")
        report.append(description[:500])  # Limit length
        if len(description) > 500:
            report.append("...")
        report.append("")

    # Reviewers
    reviewers = pr_data.get('reviewers', [])
    if reviewers:
        report.append("### Reviewers")
        report.append("")
        report.append("| Reviewer | Vote | Required |")
        report.append("|----------|------|----------|")

        vote_map = {
            10: 'Approved',
            5: 'Approved with suggestions',
            0: 'No vote',
            -5: 'Waiting for author',
            -10: 'Rejected'
        }

        for reviewer in reviewers:
            name = reviewer.get('displayName', 'Unknown')
            vote = vote_map.get(reviewer.get('vote', 0), 'Unknown')
            required = 'Yes' if reviewer.get('isRequired', False) else 'No'
            report.append(f"| {name} | {vote} | {required} |")

        report.append("")

    # Linked work items
    if work_items:
        report.append("### Linked Work Items")
        report.append("")
        report.append("| ID | Type | Title | State |")
        report.append("|----|------|-------|-------|")

        for item in work_items[:10]:  # Limit to 10
            item_id = item.get('System.Id', 'N/A')
            item_type = item.get('System.WorkItemType', 'Unknown')
            item_title = item.get('System.Title', 'No title')[:40]
            state = item.get('System.State', 'Unknown')
            report.append(f"| #{item_id} | {item_type} | {item_title} | {state} |")

        report.append("")

    # File changes
    if changes:
        report.append("### File Changes")
        report.append("")

        # Categorize changes
        by_type = defaultdict(list)
        for change in changes:
            change_type = change.get('changeType', 'edit')
            by_type[change_type].append(change)

        # Summary
        additions = len(by_type.get('add', []))
        edits = len(by_type.get('edit', []))
        deletes = len(by_type.get('delete', []))

        report.append(f"**Summary:** {additions} added, {edits} modified, {deletes} deleted")
        report.append("")

        # File list (limited)
        report.append("| File | Change | Lines |")
        report.append("|------|--------|-------|")

        for change in changes[:15]:  # Limit to 15 files
            path = change.get('item', {}).get('path', 'Unknown')
            if len(path) > 50:
                path = "..." + path[-47:]
            change_type = change.get('changeType', 'edit')
            # Note: Azure DevOps doesn't provide line counts in PR changes directly
            report.append(f"| {path} | {change_type} | - |")

        if len(changes) > 15:
            report.append(f"| ... and {len(changes) - 15} more files | | |")

        report.append("")

    # Review checklist
    report.append("### Review Checklist")
    report.append("")
    report.append("- [ ] Code follows project standards")
    report.append("- [ ] Tests added/updated")
    report.append("- [ ] Documentation updated")
    report.append("- [ ] No security issues")
    report.append("- [ ] Performance considered")
    report.append("")

    return "\n".join(report)


def calculate_pr_metrics(prs: list) -> dict:
    """
    Calculate metrics across multiple PRs.

    Args:
        prs: List of pull request data

    Returns:
        Dictionary with metrics
    """
    if not prs:
        return {}

    metrics = {
        'total': len(prs),
        'by_status': defaultdict(int),
        'by_author': defaultdict(int),
        'avg_reviewers': 0,
        'oldest_pr': None,
        'most_reviewers': 0
    }

    total_reviewers = 0
    oldest_date = None

    for pr in prs:
        # By status
        status = pr.get('status', 'unknown')
        metrics['by_status'][status] += 1

        # By author
        author = pr.get('createdBy', {}).get('displayName', 'Unknown')
        metrics['by_author'][author] += 1

        # Reviewers
        reviewers = len(pr.get('reviewers', []))
        total_reviewers += reviewers
        metrics['most_reviewers'] = max(metrics['most_reviewers'], reviewers)

        # Oldest PR
        created = pr.get('creationDate', '')
        if created:
            if oldest_date is None or created < oldest_date:
                oldest_date = created
                metrics['oldest_pr'] = pr

    metrics['avg_reviewers'] = total_reviewers / len(prs) if prs else 0

    return metrics


def main():
    parser = argparse.ArgumentParser(description='Analyze Pull Requests')
    parser.add_argument('--repo', required=True, help='Repository name')
    parser.add_argument('--pr', type=int, help='PR ID to analyze')
    parser.add_argument('--list-open', action='store_true', help='List open PRs')
    parser.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    print("PR Analyzer")
    print("=" * 40)
    print(f"Repository: {args.repo}")
    print("")

    if args.pr:
        print(f"To analyze PR #{args.pr}, use these MCP tools:")
        print("  1. mcp_ado_repos_get_pull_request - Get PR details")
        print("  2. mcp_ado_repos_get_pull_request_work_items - Get linked items")
        print("  3. mcp_ado_repos_get_pull_request_iterations - Get changes")
        print("")
        print("Then pass the data to analyze_pr() function")

    if args.list_open:
        print("To list open PRs, use:")
        print("  mcp_ado_repos_list_pull_requests with status='active'")
        print("")
        print("Then pass the results to calculate_pr_metrics()")


if __name__ == "__main__":
    main()
