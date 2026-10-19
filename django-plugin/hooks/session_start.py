#!/usr/bin/env python3
"""SessionStart hook: detect a Django project and hand Claude one context line.

Looks for `manage.py` in the session directory, then up to two levels below it
(monorepos keep it in `backend/` or `src/`). When found, it reports the Django
version and DRF presence from the dependency files and the settings layout.

Outputs SessionStart additionalContext JSON only when a Django project is found;
otherwise it prints nothing. Read-only, no imports of the project, no subprocess.
Fails open: any error ends in exit 0 with no output.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

_SKIP = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "site-packages",
         "dist", "build", ".tox"}
_DEP_FILES = ("requirements.txt", "requirements/base.txt", "pyproject.toml", "Pipfile")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(500_000)
    except (OSError, UnicodeError):
        return ""


def find_manage_py(root, depth=2):
    """Directory holding manage.py: `root` itself, else the shallowest match below it."""
    level = [root]
    for _ in range(depth + 1):
        nxt = []
        for d in level:
            if os.path.isfile(os.path.join(d, "manage.py")):
                return d
            try:
                nxt += sorted(e.path for e in os.scandir(d) if e.is_dir()
                              and e.name not in _SKIP and not e.name.startswith("."))
            except OSError:
                continue
        level = nxt
    return ""


def detect(cwd):
    proj = find_manage_py(cwd)
    if not proj:
        return ""
    rel = os.path.relpath(proj, cwd).replace("\\", "/")
    where = "manage.py" if rel == "." else f"{rel}/manage.py"
    parts = [f"Django project detected ({where})."]

    blob = " ".join(_read(os.path.join(d, f)) for d in dict.fromkeys((proj, cwd))
                    for f in _DEP_FILES)
    m = re.search(r"[Dd]jango[>=~ \"']+(\d+\.\d+(?:\.\d+)?)", blob)
    if m:
        parts.append(f"Django ~{m.group(1)}.")
    if re.search(r"djangorestframework|rest_framework", blob, re.IGNORECASE):
        parts.append("DRF present.")

    layout = ""
    for root, dirs, files in os.walk(proj):
        depth = root[len(proj):].count(os.sep)
        dirs[:] = [d for d in dirs if d not in _SKIP]
        if depth > 3:
            dirs[:] = []
            continue
        if os.path.basename(root) == "settings" and "__init__.py" in files:
            layout = "settings/ package"
            break
        if "settings.py" in files and not layout:
            layout = "single settings.py"
    if layout:
        parts.append(f"Settings: {layout}.")

    parts.append("Skills: orm/migrations/views-drf/settings/security/testing/performance. "
                 "Commands: /django:migrate, /django:test, /django:security, /django:scaffold.")
    return "[Django] " + " ".join(parts)


def main():
    hooklib.watchdog(8.0)
    payload = hooklib.read_payload() or {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else ""
    text = detect(cwd if cwd and os.path.isdir(cwd) else os.getcwd())
    if text:
        hooklib.context("SessionStart", text)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
