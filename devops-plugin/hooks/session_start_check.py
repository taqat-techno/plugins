#!/usr/bin/env python3
"""
devops-plugin SessionStart hook - lightweight profile + data-file health check.

Single-process replacement for the legacy session-start.sh, which spawned 4+
separate python subprocesses (the latency the stabilization reports flagged).
This does every check in ONE process: at most three small JSON reads plus one
profile read. It emits the official hookSpecificOutput JSON contract.

NEVER blocks and NEVER breaks the session:
  - a threading.Timer watchdog fails open (empty additionalContext, exit 0),
  - a top-level try/except fails open,
  - exit 0 in all cases.

Invoked via an explicit `python` interpreter in hooks.json (Windows-safe).
"""
from __future__ import annotations

import json
import os
import sys
import threading
from datetime import date, datetime

DEFAULT_STALENESS_DAYS = 14

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PLUGIN_ROOT, "data")
PROFILE_PATH = os.path.join(os.path.expanduser("~"), ".claude", "devops.md")

_EMPTY = '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":""}}'


def _bail() -> None:
    """Watchdog: if anything hangs, emit empty context and exit without blocking."""
    try:
        sys.stdout.write(_EMPTY)
        sys.stdout.flush()
    finally:
        os._exit(0)


def _emit(messages) -> None:
    ctx = "\n".join(m for m in messages if m).strip()
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": ctx,
        }
    }))


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def _staleness_threshold() -> int:
    """Read workTracking.profileStalenessThresholdDays from project_defaults.json."""
    try:
        with open(os.path.join(DATA_DIR, "project_defaults.json"), encoding="utf-8") as fh:
            value = json.load(fh).get("workTracking", {}).get(
                "profileStalenessThresholdDays", DEFAULT_STALENESS_DAYS
            )
            return int(value)
    except Exception:
        return DEFAULT_STALENESS_DAYS


def _plugin_version() -> str:
    try:
        with open(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            return str(json.load(fh).get("version", ""))
    except Exception:
        return ""


def _profile_days_old(profile: str) -> "int | None":
    """Days since last refresh, from a lastRefresh/lastUpdated field, else file mtime."""
    for line in profile.splitlines():
        s = line.strip()
        for key in ("lastrefresh:", "lastupdated:"):
            if s.lower().startswith(key):
                raw = s.split(":", 1)[1].strip().strip('"').strip("'")[:10]
                try:
                    d = datetime.strptime(raw, "%Y-%m-%d").date()
                    return (date.today() - d).days
                except Exception:
                    pass
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(PROFILE_PATH)).date()
        return (date.today() - mtime).days
    except Exception:
        return None


def main() -> int:
    msgs = []

    # 1. Profile existence
    if not os.path.isfile(PROFILE_PATH):
        msgs.append(
            "[DevOps] Profile not configured. Run /init profile to set up identity, "
            "role, team members, and state permissions."
        )
    else:
        profile = _read_text(PROFILE_PATH)

        # 2. Staleness (threshold from config, default 14)
        threshold = _staleness_threshold()
        days_old = _profile_days_old(profile)
        if days_old is not None and days_old > threshold:
            msgs.append(
                f"[DevOps] Profile last refreshed {days_old} days ago "
                f"(threshold {threshold}d). Run /init profile --refresh."
            )

        # 3. Required profile fields (YAML key or Markdown table label)
        for key, label in (("role:", "Primary Role"), ("defaultProject:", "Default Project"), ("teamMembers:", "Team Members")):
            if key not in profile and label not in profile:
                msgs.append(f"[DevOps] Profile missing '{key.rstrip(':')}'. Run /init profile to complete setup.")

        # 4. Profile schema version
        if "schemaVersion" not in profile:
            msgs.append("[DevOps] Profile has no schemaVersion. Re-run /init profile to upgrade the profile format.")

        # 5. Plugin-version drift (profile created against an older plugin)
        cur_ver = _plugin_version()
        prof_ver = ""
        for line in profile.splitlines():
            s = line.strip()
            if s.lower().startswith("pluginversion:"):
                prof_ver = s.split(":", 1)[1].strip().strip('"').strip("'")
        if cur_ver and prof_ver and prof_ver != cur_ver:
            msgs.append(
                f"[DevOps] Profile was created for plugin v{prof_ver} but v{cur_ver} is installed. "
                "Re-run /init profile to refresh."
            )

    # 6. Core data files exist and parse as JSON
    for fname in ("state_machine.json", "hierarchy_rules.json", "project_defaults.json"):
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.isfile(fpath):
            msgs.append(f"[DevOps] data/{fname} is missing.")
            continue
        try:
            with open(fpath, encoding="utf-8") as fh:
                json.load(fh)
        except Exception:
            msgs.append(f"[DevOps] data/{fname} has invalid JSON.")

    _emit(msgs)
    return 0


if __name__ == "__main__":
    # Watchdog: daemon so it never blocks interpreter exit; cancelled on the fast path
    # so it does not fire a second (empty) emission or add latency.
    _watchdog = threading.Timer(5.0, _bail)
    _watchdog.daemon = True
    _watchdog.start()
    try:
        _rc = main()
    except Exception:
        _emit([])  # fail-open
        _rc = 0
    _watchdog.cancel()
    sys.exit(_rc)
