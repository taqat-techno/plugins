#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit|MultiEdit): refuse writes to core Odoo framework files and to the
MCP server's connection file.

1. Core framework files (odoo/addons/, odoo/*.py, a pip-installed site-packages/odoo,
   ...) must be changed by inheritance in a custom module, never in place. Patterns
   come from odoo-upgrade.config.json: the project's copy at $CLAUDE_PROJECT_DIR, then
   the plugin default (see config_loader.py).
2. `~/.odoo-mcp/profiles.json` (and its backups) holds every connection, key and access
   level. It is changed only through scripts/mcp/odoo_mcp.py, which validates, backs up
   and audits each change and needs the developer's yes to widen access.

Refusals go out as `permissionDecision: "deny"` with the reason. Fails open: bad
input, an exception or the 5 s watchdog all end in exit 0.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "_vendor"))
sys.path.insert(0, HERE)

import hooklib  # noqa: E402

try:  # hooklib writes JSON with non-ASCII text; a cp1252 console stdout would choke on it
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_GUARD_RE = re.compile(r"(^|/)\.odoo-mcp/(profiles\.json|backups/)", re.IGNORECASE)


def _core_patterns():
    try:
        from config_loader import load_config
        return load_config().get("core_path_patterns", [])
    except Exception:
        return []


def main() -> int:
    hooklib.watchdog(5.0)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    ti = hooklib.tool_input(payload)
    file_path = ti.get("file_path", "") or ti.get("path", "")
    if not isinstance(file_path, str) or not file_path:
        return 0
    normalized = file_path.replace("\\", "/")

    if _GUARD_RE.search(normalized):
        hooklib.deny(
            "BLOCKED: %s is the Odoo MCP connection file. Change it with python "
            "<plugin>/scripts/mcp/odoo_mcp.py (add / bind / remove / migrate), which validates, "
            "backs up and logs every change; widening access needs the developer's yes passed "
            "as --approved-by." % file_path)
        return 0

    for pattern in _core_patterns():
        try:
            if re.search(pattern, normalized):
                hooklib.deny(
                    "BLOCKED: Cannot modify core Odoo file: %s\n"
                    "Core framework files (odoo/addons/, odoo/*.py) must not be edited.\n"
                    "Use model/view inheritance in a custom module instead. A project can "
                    "change these patterns in its own odoo-upgrade.config.json." % file_path)
                return 0
        except re.error:
            continue  # Skip malformed user-provided patterns
    return 0


if __name__ == "__main__":
    hooklib.run(main)
