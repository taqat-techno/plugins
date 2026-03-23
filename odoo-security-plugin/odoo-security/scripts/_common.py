#!/usr/bin/env python3
"""
Shared utilities for Odoo security auditor scripts.
====================================================
Contains constants, helpers, and configuration loading used by all sub-auditors.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

SEVERITY_WEIGHTS = {
    'CRITICAL': 4,
    'HIGH': 3,
    'MEDIUM': 2,
    'LOW': 1,
}

# Unified sensitive models list — used by route_auditor and sudo_finder
SENSITIVE_MODELS = {
    'res.partner', 'res.users', 'hr.employee', 'hr.payslip',
    'account.move', 'account.payment', 'sale.order', 'purchase.order',
    'stock.picking', 'stock.move', 'ir.config_parameter',
    'ir.attachment', 'base.automation', 'ir.rule', 'ir.model.access',
    'mail.message', 'mail.thread', 'res.bank', 'res.partner.bank',
}

# Config file name looked up in module root and project root
CONFIG_FILENAME = '.odoo-security.json'


def find_python_files(directory: Path, exclude_tests: bool = True) -> List[Path]:
    """Find all Python files in a directory, optionally excluding tests."""
    files = []
    for py_file in directory.rglob('*.py'):
        if exclude_tests:
            if 'test' in py_file.parts:
                continue
            if py_file.name.startswith('test_'):
                continue
        files.append(py_file)
    return sorted(files)


def count_by_severity(issues: List[Dict]) -> Dict[str, int]:
    """Count issues grouped by severity level."""
    counts = {s: 0 for s in SEVERITY_ORDER}
    for issue in issues:
        sev = issue.get('severity', 'LOW')
        if sev in counts:
            counts[sev] += 1
    return counts


def format_text_report(issues: List[Dict], title: str, module_name: str) -> str:
    """Standard text report formatting with severity counting and sorting."""
    lines = []
    counts = count_by_severity(issues)

    lines.append(f"\n{'=' * 60}")
    lines.append(f"{title} — {module_name}")
    lines.append(f"{'=' * 60}")
    lines.append(f"Total issues: {len(issues)}")
    for sev, count in counts.items():
        if count:
            lines.append(f"  {sev}: {count}")
    lines.append("")

    for issue in sorted(issues, key=lambda x: -(
        SEVERITY_WEIGHTS.get(x.get('severity', 'LOW'), 1)
    )):
        severity = issue.get('severity', 'LOW')
        file_info = issue.get('file', '')
        line = issue.get('line', '')
        loc = f"{file_info}:{line}" if line else file_info
        lines.append(f"[{severity}] {loc}")
        lines.append(f"  {issue.get('message', '')}")
        if issue.get('suggestion'):
            lines.append(f"  FIX: {issue['suggestion']}")
        lines.append("")

    return '\n'.join(lines)


def load_config(module_path: Path) -> Dict:
    """
    Load .odoo-security.json configuration if present.

    Looks in module root first, then parent (project root).
    Returns empty dict if no config found — all fields are optional.

    Schema:
        sensitive_models_add: list[str]    - models to add to the sensitive set
        sensitive_models_remove: list[str]  - models to remove from the sensitive set
        exclude_paths: list[str]           - glob patterns for paths to skip
        default_severity: str              - minimum severity (CRITICAL/HIGH/MEDIUM/LOW)
        custom_safe_groups: list[str]      - groups to treat as known/valid
    """
    for search_dir in [module_path, module_path.parent]:
        config_path = search_dir / CONFIG_FILENAME
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                return {}
    return {}


def get_sensitive_models(config: Optional[Dict] = None) -> set:
    """Get the effective sensitive models set, applying config overrides."""
    models = set(SENSITIVE_MODELS)
    if config:
        for m in config.get('sensitive_models_add', []):
            models.add(m)
        for m in config.get('sensitive_models_remove', []):
            models.discard(m)
    return models


def should_exclude_path(file_path: Path, module_path: Path, config: Optional[Dict] = None) -> bool:
    """Check if a file path should be excluded based on config."""
    if not config or 'exclude_paths' not in config:
        return False
    try:
        rel = file_path.relative_to(module_path)
    except ValueError:
        return False
    rel_str = str(rel).replace('\\', '/')
    for pattern in config.get('exclude_paths', []):
        if rel_str.startswith(pattern.rstrip('/')):
            return True
    return False
