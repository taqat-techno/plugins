#!/usr/bin/env python3
"""devops-plugin SessionStart hook - lightweight configuration + profile health check.

One process, at most three small JSON reads plus one profile read. Findings go out
as hookSpecificOutput.additionalContext JSON on stdout; when there is nothing to
report the hook prints nothing.

Configuration is read the way the MCP launcher (scripts/ado-mcp-launch.js) reads it:
the plugin's userConfig first (exported to hooks as CLAUDE_PLUGIN_OPTION_<KEY>), then
the legacy environment variables ADO_ORGANIZATION / ADO_MCP_AUTH_TOKEN.

Profile: ${CLAUDE_PLUGIN_DATA}/profile.md, else the legacy ~/.claude/devops.md.

NEVER blocks and NEVER breaks the session: hooklib's watchdog and run() fail open,
and the exit code is always 0.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

DEFAULT_STALENESS_DAYS = 14

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PLUGIN_ROOT, "data")
LEGACY_PROFILE = os.path.join(os.path.expanduser("~"), ".claude", "devops.md")

# (userConfig option env var, legacy env var, label)
_REQUIRED = (
    ("CLAUDE_PLUGIN_OPTION_ADO_ORGANIZATION", "ADO_ORGANIZATION", "organization"),
    ("CLAUDE_PLUGIN_OPTION_ADO_TOKEN", "ADO_MCP_AUTH_TOKEN", "token"),
)


def _value(name: str) -> str:
    """An env value, treating empty, whitespace and unexpanded ${...} text as unset."""
    val = os.environ.get(name, "").strip()
    return "" if val.startswith("${") else val


def profile_path() -> str:
    data = os.environ.get("CLAUDE_PLUGIN_DATA", "").strip()
    if data:
        current = os.path.join(data, "profile.md")
        if os.path.isfile(current):
            return current
    return LEGACY_PROFILE


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def _staleness_threshold() -> int:
    """userConfig profile_stale_days, else project_defaults.json, else 14."""
    opt = _value("CLAUDE_PLUGIN_OPTION_PROFILE_STALE_DAYS")
    if opt:
        try:
            return max(1, int(float(opt)))
        except ValueError:
            pass
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


def _profile_days_old(profile: str, path: str) -> "int | None":
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
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).date()
        return (date.today() - mtime).days
    except Exception:
        return None


def _mcp_env_messages() -> list:
    """Check what the azure-devops MCP server needs: an organization and a PAT.

    Each comes from the plugin's userConfig (set when the plugin is enabled, or later
    in /config; the token is kept in the OS credential store) or, as a fallback, from
    the ADO_ORGANIZATION / ADO_MCP_AUTH_TOKEN environment variables. Without both the
    server cannot authenticate and every azure-devops tool call fails opaquely, so
    this is the clear error.
    """
    out = []
    missing = [label for opt, env, label in _REQUIRED if not (_value(opt) or _value(env))]
    if missing:
        out.append(
            "[DevOps] Azure DevOps MCP is not configured: no "
            + " or ".join(missing)
            + " is set. Every azure-devops tool call will fail until it is. Set it in "
            "/config (plugin options for devops: ado_organization, ado_token), or set the "
            "ADO_ORGANIZATION / ADO_MCP_AUTH_TOKEN environment variables. Run /init for "
            "guided setup."
        )
    for var in ("ADO_ORGANIZATION", "ADO_MCP_AUTH_TOKEN", "ADO_MCP_PROJECT", "ADO_MCP_TEAM"):
        val = os.environ.get(var, "").strip()
        if val.startswith("${") and val.endswith("}"):
            out.append(
                f"[DevOps] {var} contains an unexpanded placeholder. The variable it "
                "refers to is not defined - set it, or give it a ${VAR:-} default."
            )
    return out


def collect_messages() -> list:
    msgs = list(_mcp_env_messages())

    path = profile_path()
    if not os.path.isfile(path):
        msgs.append(
            "[DevOps] Profile not configured. Run /init profile to set up identity, "
            "role, process preset and team members."
        )
    else:
        profile = _read_text(path)
        if path == LEGACY_PROFILE and os.environ.get("CLAUDE_PLUGIN_DATA", "").strip():
            msgs.append(
                "[DevOps] Using the legacy profile ~/.claude/devops.md. Run /init profile "
                "--refresh to move it to the plugin data directory."
            )

        threshold = _staleness_threshold()
        days_old = _profile_days_old(profile, path)
        if days_old is not None and days_old > threshold:
            msgs.append(
                f"[DevOps] Profile last refreshed {days_old} days ago "
                f"(threshold {threshold}d). Run /init profile --refresh."
            )

        for key, label in (("role:", "Primary Role"), ("defaultProject:", "Default Project"),
                           ("teamMembers:", "Team Members")):
            if key not in profile and label not in profile:
                msgs.append(f"[DevOps] Profile missing '{key.rstrip(':')}'. Run /init profile to complete setup.")

        if "schemaVersion" not in profile:
            msgs.append("[DevOps] Profile has no schemaVersion. Re-run /init profile to upgrade the profile format.")

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
    return msgs


def main() -> int:
    hooklib.watchdog(5.0)
    msgs = collect_messages()
    if msgs:
        hooklib.context("SessionStart", "\n".join(msgs))
    return 0


if __name__ == "__main__":
    hooklib.run(main)
