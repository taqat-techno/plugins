"""Shared utilities for PM Guidelines hooks."""

import os
from pathlib import Path

# Directories where PM deliverables live (hooks only fire on these)
PM_DIRECTORIES = [
    'researches',
    'tasks',
    'reports',
    'deliverables',
    'dashboards',
    'proposals',
    'presentations',
]

# File extensions for PM deliverables
PM_EXTENSIONS = {'.html', '.md', '.htm'}


def is_pm_deliverable(file_path):
    """Check if a file is in a PM deliverable directory."""
    if not file_path:
        return False

    normalized = file_path.replace('\\', '/').lower()

    # Check extension
    ext = os.path.splitext(normalized)[1]
    if ext not in PM_EXTENSIONS:
        return False

    # Check if any PM directory is in the path
    parts = normalized.split('/')
    for part in parts:
        if part in PM_DIRECTORIES:
            return True

    return False


def is_html_file(file_path):
    """Check if file is an HTML file."""
    if not file_path:
        return False
    ext = os.path.splitext(file_path)[1].lower()
    return ext in {'.html', '.htm'}


def is_dashboard_file(file_path):
    """Check if file appears to be a dashboard or report HTML."""
    if not is_html_file(file_path):
        return False

    normalized = file_path.replace('\\', '/').lower()
    dashboard_keywords = ['dashboard', 'report', 'kpi', 'okr', 'metrics', 'analytics']
    return any(kw in normalized for kw in dashboard_keywords)


def read_file_safe(file_path, max_size=500_000):
    """Safely read a file, returning empty string on failure."""
    try:
        path = Path(file_path)
        if not path.exists():
            return ''
        if path.stat().st_size > max_size:
            return ''
        return path.read_text(encoding='utf-8', errors='replace')
    except (IOError, OSError):
        return ''
