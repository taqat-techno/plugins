#!/usr/bin/env python3
"""
SessionStart hook: Detect Django / DRF presence, version, and project layout,
and inject a short context line.

Outputs JSON in the official hookSpecificOutput format. Exit 0 always.
Read-only and fail-open: never blocks a session.
"""

import json
import os
import re
import sys
import threading

# Internal timeout guard — fail-open after 8 seconds.
_timer = threading.Timer(8.0, lambda: os._exit(0))
_timer.daemon = True
_timer.start()

# Read stdin (required by hook protocol).
try:
    sys.stdin.read()
except Exception:
    pass


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except (OSError, UnicodeError):
        return ""


def detect():
    cwd = os.getcwd()

    # A Django project is identified by a manage.py at the root.
    if not os.path.isfile(os.path.join(cwd, "manage.py")):
        return ""

    parts = ["Django project detected (manage.py)."]

    # Version from dependency declarations (no imports / no subprocess).
    version = ""
    for dep_file in ("requirements.txt", "requirements/base.txt", "pyproject.toml", "Pipfile"):
        text = _read(os.path.join(cwd, dep_file))
        if not text:
            continue
        m = re.search(r"[Dd]jango[>=~ \"']+(\d+\.\d+(?:\.\d+)?)", text)
        if m:
            version = m.group(1)
            break
    if version:
        parts.append(f"Django ~{version}.")

    # DRF presence.
    blob = " ".join(
        _read(os.path.join(cwd, f))
        for f in ("requirements.txt", "requirements/base.txt", "pyproject.toml", "Pipfile")
    )
    if re.search(r"djangorestframework|rest_framework", blob, re.IGNORECASE):
        parts.append("DRF present.")

    # Settings layout: package vs single module.
    settings_layout = ""
    for root, dirs, files in os.walk(cwd):
        # Stay shallow and skip noise dirs.
        depth = root[len(cwd):].count(os.sep)
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__", "site-packages")]
        if depth > 3:
            dirs[:] = []
            continue
        base = os.path.basename(root)
        if base == "settings" and "__init__.py" in files:
            settings_layout = "settings/ package"
            break
        if "settings.py" in files and not settings_layout:
            settings_layout = "single settings.py"
    if settings_layout:
        parts.append(f"Settings: {settings_layout}.")

    parts.append("Skills: orm/migrations/views-drf/settings/security/testing/performance. "
                 "Commands: /django-init, /django-migrate, /django-test, /django-security, /django-scaffold.")

    return "[Django] " + " ".join(parts)


try:
    ctx = detect()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }
    print(json.dumps(output))
except Exception:
    print('{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}')

_timer.cancel()
sys.exit(0)
