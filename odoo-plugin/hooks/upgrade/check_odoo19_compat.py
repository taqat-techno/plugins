#!/usr/bin/env python3
"""
PostToolUse hook: Check written/edited files for Odoo version compatibility issues.

Reads tool input JSON from stdin. Detects the target Odoo version from the file
path using configurable patterns, then runs version-appropriate compatibility checks.
Always exits 0 (advisory, never blocks).

Hardened: internal timeout, JSON hookSpecificOutput format, fail-open.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from pathlib import Path

# Internal timeout: fail-open after 5 seconds
_timer = threading.Timer(5.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config_loader import load_config, detect_target_version
except ImportError:
    def load_config():
        return {"target_version_path_patterns": {}, "default_target_version": 19}
    def detect_target_version(fp, cfg):
        return cfg.get("default_target_version")


def check_xml_compat(content: str, version: int) -> list[str]:
    issues = []
    if version >= 19:
        if re.search(r'<tree[\s>]', content):
            issues.append("<tree> tag detected - should be <list> in Odoo 19")
        if re.search(r't-name=["\']kanban-box["\']', content):
            issues.append("kanban-box template - should be 'card' in Odoo 19")
        if re.search(r'<group[^>]*expand', content) and '<search' in content:
            issues.append("<group expand> in search view - not allowed in Odoo 19")
        if re.search(r'<field\s+name=["\']numbercall', content):
            issues.append("numbercall field - removed in Odoo 19")
        if re.search(r'xpath[^>]*//tree', content):
            issues.append("XPath //tree - should be //list in Odoo 19")
        if re.search(r'format_(datetime|date|amount)\(env,', content):
            issues.append("format helper with env param - remove env in Odoo 19")
    if version >= 18:
        if re.search(r'attrs\s*=\s*["\']\{', content):
            issues.append("attrs={} syntax - should use inline expressions in Odoo 18+")
    return issues


def check_js_compat(content: str, version: int) -> list[str]:
    issues = []
    if version >= 19:
        if re.search(r'useService\(["\']rpc["\']\)', content):
            issues.append("useService('rpc') - RPC service not available in Odoo 19")
        if '@web/core/network/rpc_service' in content:
            issues.append("RPC service module - removed in Odoo 19")
    if version >= 18:
        if re.search(r'\bmounted\s*\(\s*\)', content) and 'Component' in content:
            issues.append("OWL 1.x mounted() - should be onMounted() in Odoo 18+")
        if re.search(r'\bwillStart\s*\(\s*\)', content) and 'Component' in content:
            issues.append("OWL 1.x willStart() - should be onWillStart() in Odoo 18+")
    return issues


def check_py_compat(content: str, version: int) -> list[str]:
    issues = []
    if version >= 19:
        if re.search(r"type\s*=\s*['\"]json['\"]", content) and '@http.route' in content:
            issues.append("type='json' in route - should be type='jsonrpc' in Odoo 19")
        if re.search(r"view_mode.*['\"]tree['\"]", content):
            issues.append("view_mode 'tree' - should be 'list' in Odoo 19")
    if version >= 15:
        if 'from openerp' in content:
            issues.append("'openerp' import - should be 'odoo' since Odoo 15+")
    return issues


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError, ValueError):
        sys.exit(0)

    tool_input = data.get('tool_input', {})
    file_path = tool_input.get('file_path', '') or tool_input.get('path', '')

    if not file_path:
        sys.exit(0)

    normalized = file_path.replace('\\', '/')

    try:
        config = load_config()
    except Exception:
        sys.exit(0)

    version = detect_target_version(normalized, config)
    if version is None:
        sys.exit(0)

    path = Path(file_path)
    if not path.exists():
        sys.exit(0)

    try:
        content = path.read_text(encoding='utf-8')
    except Exception:
        sys.exit(0)

    issues = []
    suffix = path.suffix.lower()

    if suffix == '.xml':
        issues = check_xml_compat(content, version)
    elif suffix in ('.js', '.ts'):
        issues = check_js_compat(content, version)
    elif suffix == '.py':
        issues = check_py_compat(content, version)

    if issues:
        msg = f"Odoo {version} compatibility:\n" + "\n".join(f"  - {i}" for i in issues)
        output = {"hookSpecificOutput": {"additionalContext": msg}}
        print(json.dumps(output))

    _timer.cancel()
    sys.exit(0)


if __name__ == '__main__':
    main()
