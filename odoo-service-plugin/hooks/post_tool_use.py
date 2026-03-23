#!/usr/bin/env python3
"""
PostToolUse hook for odoo-service-plugin.

Reads tool invocation JSON from stdin, checks if the edited file matches
Odoo-relevant patterns, and returns context-aware suggestions via stdout.

Only fires for Write|Edit tools (filtered by hooks.json matcher).
"""

import json
import os
import sys
from pathlib import PurePosixPath, PureWindowsPath


def get_file_path(data: dict) -> str:
    """Extract file_path from the hook input."""
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            return ""
    return tool_input.get("file_path", "")


def normalize_path(file_path: str) -> str:
    """Normalize path separators to forward slashes for matching."""
    return file_path.replace("\\", "/")


def match_pattern(path: str, tool_name: str) -> str | None:
    """Match a file path against Odoo-relevant patterns. Returns suggestion or None."""
    parts = path.lower().split("/")
    basename = parts[-1] if parts else ""

    # requirements.txt modified
    if basename.startswith("requirements") and basename.endswith(".txt"):
        return (
            "requirements.txt was modified. Install updated dependencies:\n"
            "```bash\npip install -r requirements.txt\n```"
        )

    # Odoo .conf file modified
    if basename.endswith(".conf") and any(p in ("conf", "config") for p in parts):
        return (
            "Odoo config file was modified. Restart the server to apply:\n"
            "```bash\n/odoo-service stop\n/odoo-service start\n```"
        )

    # docker-compose file modified
    if basename.startswith("docker-compose") and basename.endswith((".yml", ".yaml")):
        return (
            "docker-compose file was modified. Recreate containers:\n"
            "```bash\ndocker-compose up -d\n```"
        )

    # Dockerfile modified
    if basename.startswith("dockerfile"):
        return (
            "Dockerfile was modified. Rebuild the image:\n"
            "```bash\ndocker-compose up -d --build\n```"
        )

    # __manifest__.py modified
    if basename == "__manifest__.py":
        return (
            "__manifest__.py was modified. Update the module:\n"
            "```bash\n"
            "python -m odoo -c conf/<CONFIG>.conf -d <DB> -u <MODULE> --stop-after-init\n"
            "```\n"
            "Remember to bump the version field."
        )

    # New model file created (Write only, inside models/ directory)
    if tool_name == "Write" and "models" in parts and basename.endswith(".py") and basename != "__init__.py":
        return (
            "New model file created. Ensure:\n"
            "1. The class is imported in `models/__init__.py`\n"
            "2. Access rules exist in `security/ir.model.access.csv`\n"
            "3. Update the module:\n"
            "```bash\n"
            "python -m odoo -c conf/<CONFIG>.conf -d <DB> -u <MODULE> --stop-after-init\n"
            "```"
        )

    return None


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, IOError):
        data = {}

    file_path = get_file_path(data)
    if not file_path:
        return

    tool_name = data.get("tool_name", "")
    normalized = normalize_path(file_path)
    suggestion = match_pattern(normalized, tool_name)

    if suggestion:
        print(json.dumps({"additionalContext": suggestion}))


if __name__ == "__main__":
    main()
