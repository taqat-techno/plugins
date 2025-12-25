#!/usr/bin/env python3
"""
Hybrid Release Notes Generator

Combines CLI queries for commits and PRs with work item analysis
to generate comprehensive release notes.

Author: TAQAT Techno
Version: 2.0.0
"""

import subprocess
import json
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Commit:
    """Represents a git commit."""
    id: str
    message: str
    author: str
    date: str
    work_item_ids: List[int] = field(default_factory=list)


@dataclass
class PullRequest:
    """Represents a pull request."""
    id: int
    title: str
    author: str
    source_branch: str
    target_branch: str
    merged_date: Optional[str]
    work_item_ids: List[int] = field(default_factory=list)


@dataclass
class WorkItem:
    """Represents a work item."""
    id: int
    title: str
    item_type: str
    state: str
    tags: List[str] = field(default_factory=list)


@dataclass
class ReleaseNotes:
    """Container for release notes data."""
    version: str
    date: str
    features: List[WorkItem] = field(default_factory=list)
    bugs: List[WorkItem] = field(default_factory=list)
    improvements: List[WorkItem] = field(default_factory=list)
    breaking_changes: List[str] = field(default_factory=list)
    commits: List[Commit] = field(default_factory=list)
    pull_requests: List[PullRequest] = field(default_factory=list)
    contributors: Set[str] = field(default_factory=set)


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


def extract_work_item_ids(text: str) -> List[int]:
    """Extract work item IDs from text (e.g., #123, AB#456)."""
    # Match patterns like #123, AB#456, Work Item 123
    patterns = [
        r'#(\d+)',
        r'AB#(\d+)',
        r'[Ww]ork [Ii]tem\s*#?(\d+)',
        r'\[(\d+)\]'
    ]

    ids = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        ids.update(int(m) for m in matches)

    return list(ids)


def get_merged_prs(project: str, repository: str, since_date: str) -> List[PullRequest]:
    """Get merged PRs since a date."""
    cmd = f'az repos pr list --project "{project}" --repository "{repository}" --status completed --top 100 -o json'
    result = run_cli(cmd)

    if not result:
        return []

    prs = []
    for pr in result:
        closed_date = pr.get('closedDate', '')
        if closed_date and closed_date >= since_date:
            # Extract work item IDs from title and description
            work_item_ids = extract_work_item_ids(pr.get('title', ''))
            work_item_ids.extend(extract_work_item_ids(pr.get('description', '')))

            # Also check linked work items
            if pr.get('workItemRefs'):
                work_item_ids.extend(int(wi['id']) for wi in pr['workItemRefs'])

            prs.append(PullRequest(
                id=pr['pullRequestId'],
                title=pr['title'],
                author=pr['createdBy']['displayName'],
                source_branch=pr['sourceRefName'].replace('refs/heads/', ''),
                target_branch=pr['targetRefName'].replace('refs/heads/', ''),
                merged_date=closed_date,
                work_item_ids=list(set(work_item_ids))
            ))

    return prs


def get_commits_since(project: str, repository: str, since_date: str, branch: str = 'main') -> List[Commit]:
    """Get commits since a date."""
    cmd = f'az repos ref list --repository "{repository}" --filter heads/{branch} -o json'
    ref_result = run_cli(cmd)

    if not ref_result or len(ref_result) == 0:
        return []

    # Get commit history (this is simplified - full implementation would paginate)
    # Note: Azure CLI doesn't have a direct commit list command, would use git log locally
    # For this script, we'll extract from PR commits

    return []  # Commits are better extracted from PRs


def get_work_items(project: str, ids: List[int]) -> List[WorkItem]:
    """Get work item details by IDs."""
    if not ids:
        return []

    # Batch query for work items
    ids_str = ','.join(str(id) for id in ids)
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.Tags]
    FROM WorkItems
    WHERE [System.Id] IN ({ids_str})
    """

    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    result = run_cli(cmd)
    if not result:
        return []

    items = []
    for item in result:
        fields = item.get('fields', {})
        tags = fields.get('System.Tags', '') or ''

        items.append(WorkItem(
            id=item['id'],
            title=fields.get('System.Title', 'No Title'),
            item_type=fields.get('System.WorkItemType', 'Item'),
            state=fields.get('System.State', 'Unknown'),
            tags=[t.strip() for t in tags.split(';') if t.strip()]
        ))

    return items


def get_completed_items_since(project: str, since_date: str) -> List[WorkItem]:
    """Get work items completed since a date."""
    wiql = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.Tags]
    FROM WorkItems
    WHERE [System.TeamProject] = '{project}'
      AND [System.State] IN ('Done', 'Closed', 'Resolved')
      AND [Microsoft.VSTS.Common.ClosedDate] >= '{since_date}'
    ORDER BY [System.WorkItemType], [Microsoft.VSTS.Common.Priority]
    """

    wiql_escaped = wiql.replace('\n', ' ').replace('"', '\\"')
    cmd = f'az boards query --wiql "{wiql_escaped}" --project "{project}" -o json'

    result = run_cli(cmd)
    if not result:
        return []

    items = []
    for item in result:
        fields = item.get('fields', {})
        tags = fields.get('System.Tags', '') or ''

        items.append(WorkItem(
            id=item['id'],
            title=fields.get('System.Title', 'No Title'),
            item_type=fields.get('System.WorkItemType', 'Item'),
            state=fields.get('System.State', 'Unknown'),
            tags=[t.strip() for t in tags.split(';') if t.strip()]
        ))

    return items


def categorize_work_items(items: List[WorkItem]) -> ReleaseNotes:
    """Categorize work items into release note sections."""
    notes = ReleaseNotes(
        version='',
        date=datetime.now().strftime('%Y-%m-%d')
    )

    for item in items:
        # Check for breaking changes tag
        if 'breaking-change' in [t.lower() for t in item.tags]:
            notes.breaking_changes.append(f"[#{item.id}] {item.title}")

        # Categorize by type
        if item.item_type in ('User Story', 'Product Backlog Item', 'Feature'):
            notes.features.append(item)
        elif item.item_type == 'Bug':
            notes.bugs.append(item)
        else:
            notes.improvements.append(item)

    return notes


def format_release_notes(notes: ReleaseNotes, format_type: str = 'markdown') -> str:
    """Format release notes."""
    lines = []

    if format_type == 'markdown':
        lines.extend([
            f"# Release Notes - {notes.version or 'Unreleased'}",
            "",
            f"**Release Date:** {notes.date}",
            ""
        ])

        # Breaking changes (most important)
        if notes.breaking_changes:
            lines.extend([
                "## ⚠️ Breaking Changes",
                ""
            ])
            for change in notes.breaking_changes:
                lines.append(f"- {change}")
            lines.append("")

        # New Features
        if notes.features:
            lines.extend([
                "## ✨ New Features",
                ""
            ])
            for item in notes.features:
                lines.append(f"- **[#{item.id}]** {item.title}")
            lines.append("")

        # Bug Fixes
        if notes.bugs:
            lines.extend([
                "## 🐛 Bug Fixes",
                ""
            ])
            for item in notes.bugs:
                lines.append(f"- **[#{item.id}]** {item.title}")
            lines.append("")

        # Improvements
        if notes.improvements:
            lines.extend([
                "## 🔧 Improvements",
                ""
            ])
            for item in notes.improvements:
                lines.append(f"- **[#{item.id}]** {item.title}")
            lines.append("")

        # PRs
        if notes.pull_requests:
            lines.extend([
                "## 📥 Pull Requests Merged",
                ""
            ])
            for pr in notes.pull_requests[:10]:
                lines.append(f"- PR #{pr.id}: {pr.title} (@{pr.author})")
            if len(notes.pull_requests) > 10:
                lines.append(f"- ... and {len(notes.pull_requests) - 10} more")
            lines.append("")

        # Contributors
        if notes.contributors:
            lines.extend([
                "## 👥 Contributors",
                ""
            ])
            for contributor in sorted(notes.contributors):
                lines.append(f"- {contributor}")
            lines.append("")

        lines.extend([
            "---",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"
        ])

    else:  # Plain text
        lines.extend([
            f"RELEASE NOTES - {notes.version or 'Unreleased'}",
            f"Release Date: {notes.date}",
            "=" * 50,
            ""
        ])

        if notes.breaking_changes:
            lines.extend(["BREAKING CHANGES:", ""])
            for change in notes.breaking_changes:
                lines.append(f"  * {change}")
            lines.append("")

        if notes.features:
            lines.extend(["NEW FEATURES:", ""])
            for item in notes.features:
                lines.append(f"  * [#{item.id}] {item.title}")
            lines.append("")

        if notes.bugs:
            lines.extend(["BUG FIXES:", ""])
            for item in notes.bugs:
                lines.append(f"  * [#{item.id}] {item.title}")
            lines.append("")

    return "\n".join(lines)


def generate_release_notes(
    project: str,
    repository: str = '',
    since_date: str = '',
    version: str = ''
) -> str:
    """Main function to generate release notes."""
    print(f"Generating release notes for {project}...", file=sys.stderr)

    # Default to 2 weeks ago if not specified
    if not since_date:
        since_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')

    print(f"Since: {since_date}", file=sys.stderr)

    # Get completed work items
    completed_items = get_completed_items_since(project, since_date)
    print(f"Completed items: {len(completed_items)}", file=sys.stderr)

    # Categorize items
    notes = categorize_work_items(completed_items)
    notes.version = version
    notes.date = datetime.now().strftime('%Y-%m-%d')

    # Get merged PRs if repository specified
    if repository:
        prs = get_merged_prs(project, repository, since_date)
        notes.pull_requests = prs
        notes.contributors = set(pr.author for pr in prs)
        print(f"Merged PRs: {len(prs)}", file=sys.stderr)

    return format_release_notes(notes)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate release notes from Azure DevOps')
    parser.add_argument('project', nargs='?', default='Relief Center',
                        help='Project name (default: Relief Center)')
    parser.add_argument('--repository', '-r', default='',
                        help='Repository name for PR analysis')
    parser.add_argument('--since', '-s', default='',
                        help='Start date (YYYY-MM-DD, default: 14 days ago)')
    parser.add_argument('--version', '-v', default='',
                        help='Version number for release')
    parser.add_argument('--format', '-f', choices=['markdown', 'text'], default='markdown',
                        help='Output format (default: markdown)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    args = parser.parse_args()

    result = generate_release_notes(
        args.project,
        args.repository,
        args.since,
        args.version
    )

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()
