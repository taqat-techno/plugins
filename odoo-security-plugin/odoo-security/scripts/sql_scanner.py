#!/usr/bin/env python3
"""
Odoo SQL Injection Scanner
============================
Scans all Python files in an Odoo module for unsafe SQL patterns in
env.cr.execute() / self._cr.execute() calls.

Detection:
    CRITICAL - f-strings or .format() in cr.execute()
    HIGH     - String concatenation (+) or % operator in cr.execute()
    MEDIUM   - cr.execute(variable) where query is not a constant
    LOW      - _where_calc override without _apply_ir_rules

Safe patterns (no alert):
    - cr.execute("...", (param,))  — parameterized with tuple
    - cr.execute(CONSTANT_QUERY)   — module-level string constant

Usage:
    python sql_scanner.py <module_path> [options]

Options:
    --json     Output results as JSON
    --verbose  Show code context around each finding

Exit codes:
    0 = No issues found
    1 = Issues found
    2 = Usage error
"""

import sys
import re
import ast
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

try:
    from _common import (
        SEVERITY_ORDER, SEVERITY_WEIGHTS, find_python_files,
        count_by_severity, format_text_report, load_config, should_exclude_path,
    )
except ImportError:
    SEVERITY_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    SEVERITY_WEIGHTS = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

    def find_python_files(directory, exclude_tests=True):
        files = []
        for py_file in directory.rglob('*.py'):
            if exclude_tests and ('test' in py_file.parts or py_file.name.startswith('test_')):
                continue
            files.append(py_file)
        return sorted(files)

    def count_by_severity(issues):
        counts = {s: 0 for s in SEVERITY_ORDER}
        for issue in issues:
            sev = issue.get('severity', 'LOW')
            if sev in counts:
                counts[sev] += 1
        return counts

    def format_text_report(issues, title, module_name):
        lines = [f"\n{'=' * 60}", f"{title} — {module_name}", f"{'=' * 60}"]
        lines.append(f"Total issues: {len(issues)}")
        for issue in sorted(issues, key=lambda x: -(SEVERITY_WEIGHTS.get(x.get('severity', 'LOW'), 1))):
            loc = f"{issue.get('file', '')}:{issue.get('line', '')}" if issue.get('line') else issue.get('file', '')
            lines.append(f"[{issue.get('severity', 'LOW')}] {loc}")
            lines.append(f"  {issue.get('message', '')}")
            lines.append("")
        return '\n'.join(lines)

    def load_config(module_path):
        return {}

    def should_exclude_path(file_path, module_path, config=None):
        return False


# Patterns that match cr.execute calls
EXECUTE_PATTERNS = [
    r'\.cr\.execute\s*\(',
    r'self\._cr\.execute\s*\(',
    r'env\.cr\.execute\s*\(',
    r'request\.env\.cr\.execute\s*\(',
    r'request\.cr\.execute\s*\(',
]
EXECUTE_REGEX = re.compile('|'.join(EXECUTE_PATTERNS))


def _is_execute_call(node: ast.Call) -> bool:
    """Check if an AST Call node is a cr.execute() call."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == 'execute':
        # Walk the attribute chain looking for 'cr' or '_cr'
        current = func.value
        while isinstance(current, ast.Attribute):
            if current.attr in ('cr', '_cr'):
                return True
            current = current.value
        if isinstance(current, ast.Name) and current.id in ('cr', '_cr'):
            return True
    return False


def _classify_query_arg(node: ast.expr) -> Optional[str]:
    """
    Classify the first argument to cr.execute() by safety.

    Returns severity string or None if safe.
    """
    # f-string → CRITICAL
    if isinstance(node, ast.JoinedStr):
        return 'CRITICAL'

    # "...".format(...) → CRITICAL
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'format':
            return 'CRITICAL'

    # string % value → HIGH (but not the %s parameterized form — that uses 2nd arg to execute)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        return 'HIGH'

    # string + something → HIGH
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return 'HIGH'

    # Variable reference (not a constant string) → MEDIUM
    if isinstance(node, ast.Name):
        return 'MEDIUM'

    # Constant string is safe
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return None

    return None


def _has_parameterized_second_arg(node: ast.Call) -> bool:
    """Check if cr.execute() has a tuple/list as second argument (parameterized)."""
    if len(node.args) >= 2:
        second = node.args[1]
        if isinstance(second, (ast.Tuple, ast.List)):
            return True
        # Check for tuple() call
        if isinstance(second, ast.Call) and isinstance(second.func, ast.Name) and second.func.id == 'tuple':
            return True
    return False


def analyze_file_ast(source: str, file_path: Path, module_path: Path) -> List[Dict]:
    """Analyze a Python file using AST for SQL injection patterns."""
    issues = []
    try:
        rel_path = file_path.relative_to(module_path)
    except ValueError:
        rel_path = file_path

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return analyze_file_regex(source, file_path, module_path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_execute_call(node):
            continue
        if not node.args:
            continue

        query_arg = node.args[0]
        severity = _classify_query_arg(query_arg)

        if severity is None:
            continue

        # If it has a parameterized second arg and the issue is just a variable name, skip
        if severity == 'MEDIUM' and _has_parameterized_second_arg(node):
            continue

        line = node.lineno
        source_lines = source.split('\n')
        code_line = source_lines[line - 1].strip() if line <= len(source_lines) else ''

        if severity == 'CRITICAL':
            if isinstance(query_arg, ast.JoinedStr):
                msg = (
                    f"SQL injection: f-string used in cr.execute() at line {line}. "
                    f"Use parameterized query: cr.execute('...%s...', (value,))"
                )
                issue_type = 'sql_fstring'
            else:
                msg = (
                    f"SQL injection: .format() used in cr.execute() at line {line}. "
                    f"Use parameterized query: cr.execute('...%s...', (value,))"
                )
                issue_type = 'sql_format'
        elif severity == 'HIGH':
            if isinstance(query_arg, ast.BinOp) and isinstance(query_arg.op, ast.Add):
                msg = (
                    f"Potential SQL injection: string concatenation (+) in cr.execute() at line {line}. "
                    f"Use parameterized query or psycopg2.sql.Identifier for dynamic names."
                )
                issue_type = 'sql_concat'
            else:
                msg = (
                    f"Potential SQL injection: % operator in cr.execute() at line {line}. "
                    f"Use parameterized query: cr.execute('...%s...', (value,)) — note the tuple."
                )
                issue_type = 'sql_percent'
        else:
            msg = (
                f"cr.execute() with variable query at line {line}. "
                f"Verify the query string is a constant or properly parameterized."
            )
            issue_type = 'sql_variable_query'

        issues.append({
            'severity': severity,
            'type': issue_type,
            'file': str(rel_path),
            'line': line,
            'message': msg,
            'code_snippet': code_line,
        })

    # Check for _where_calc override without _apply_ir_rules
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '_where_calc':
            func_source = '\n'.join(source.split('\n')[node.lineno - 1:getattr(node, 'end_lineno', node.lineno + 20)])
            if '_apply_ir_rules' not in func_source:
                issues.append({
                    'severity': 'LOW',
                    'type': 'sql_where_calc_no_rules',
                    'file': str(rel_path),
                    'line': node.lineno,
                    'message': (
                        f"_where_calc override without _apply_ir_rules call. "
                        f"This may bypass record-level security rules."
                    ),
                })

    return issues


def analyze_file_regex(source: str, file_path: Path, module_path: Path) -> List[Dict]:
    """Regex-based fallback for files that can't be AST-parsed."""
    issues = []
    try:
        rel_path = file_path.relative_to(module_path)
    except ValueError:
        rel_path = file_path

    lines = source.split('\n')

    for i, line in enumerate(lines, 1):
        if not EXECUTE_REGEX.search(line):
            continue

        stripped = line.strip()
        if stripped.startswith('#'):
            continue

        # f-string detection
        if re.search(r'execute\s*\(\s*f[\'"]', stripped):
            issues.append({
                'severity': 'CRITICAL',
                'type': 'sql_fstring',
                'file': str(rel_path),
                'line': i,
                'message': "SQL injection: f-string in cr.execute(). Use parameterized query.",
                'code_snippet': stripped,
            })
        # .format() detection
        elif re.search(r'execute\s*\(.*\.format\(', stripped):
            issues.append({
                'severity': 'CRITICAL',
                'type': 'sql_format',
                'file': str(rel_path),
                'line': i,
                'message': "SQL injection: .format() in cr.execute(). Use parameterized query.",
                'code_snippet': stripped,
            })
        # % operator (but not %s parameterized)
        elif re.search(r'execute\s*\([^,]*%\s*(?!\s*s\b)', stripped):
            issues.append({
                'severity': 'HIGH',
                'type': 'sql_percent',
                'file': str(rel_path),
                'line': i,
                'message': "Potential SQL injection: % operator in cr.execute(). Use parameterized query.",
                'code_snippet': stripped,
            })
        # String concatenation
        elif re.search(r'execute\s*\([^,]*\+', stripped):
            issues.append({
                'severity': 'HIGH',
                'type': 'sql_concat',
                'file': str(rel_path),
                'line': i,
                'message': "Potential SQL injection: string concatenation in cr.execute().",
                'code_snippet': stripped,
            })

    return issues


def scan_for_sql_injection(module_path: Path, config: Optional[Dict] = None) -> List[Dict]:
    """Main analysis function. Returns list of SQL injection issues."""
    all_issues = []
    module_path = Path(module_path)

    py_files = find_python_files(module_path)

    for py_file in py_files:
        if should_exclude_path(py_file, module_path, config):
            continue

        try:
            source = py_file.read_text(encoding='utf-8', errors='replace')
        except (OSError, IOError):
            continue

        # Quick pre-check — skip files without execute calls
        if 'execute' not in source:
            continue

        file_issues = analyze_file_ast(source, py_file, module_path)
        all_issues.extend(file_issues)

    return all_issues


def main():
    parser = argparse.ArgumentParser(
        description='Scan Odoo module for SQL injection vulnerabilities'
    )
    parser.add_argument('module_path', help='Path to the Odoo module')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', action='store_true', help='Show code context')

    args = parser.parse_args()
    module_path = Path(args.module_path).resolve()

    if not module_path.exists():
        print(json.dumps({'error': f'Path not found: {module_path}', 'issues': []}))
        sys.exit(2)

    config = load_config(module_path)
    issues = scan_for_sql_injection(module_path, config)

    counts = count_by_severity(issues)

    if args.json:
        output = {
            'auditor': 'sql_scanner',
            'module': module_path.name,
            'module_path': str(module_path),
            'summary': {'total': len(issues), 'by_severity': counts},
            'issues': issues,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(format_text_report(issues, 'SQL SCANNER REPORT', module_path.name))

    has_real_issues = any(
        i.get('severity', 'LOW') in ('CRITICAL', 'HIGH')
        for i in issues
    )
    sys.exit(1 if has_real_issues else 0)


if __name__ == '__main__':
    main()
