#!/usr/bin/env python3
"""SessionStart hook: a few cheap, read-only environment checks. Silent when all pass.

Checks (project directory only, no network, no subprocesses, well under a second):

  mcp-unset-var    the project's .mcp.json references ${NAME} without a default
                   (${NAME:-...}) and NAME is not set, so the literal text "${NAME}"
                   reaches the MCP server
  mcp-bad-json     the project's .mcp.json is not valid JSON, so none of its servers load
  sync-heavy-dir   the project sits inside a Syncthing folder (.stfolder found walking up)
                   and has node_modules / .venv / venv at its root that .stignore does not
                   ignore, which is the classic delete-deadlock and conflict source

Only when a check finds something does it print, as SessionStart additionalContext
JSON, one short line per finding pointing at /env-doctor:diagnose. It never prints
a variable's value, only names.

Silence it with the plugin option `session_checks` = false
(CLAUDE_PLUGIN_OPTION_SESSION_CHECKS) or ENV_DOCTOR_HINT=off. Never blocks; any
error exits 0 with no output.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

OFF = ("0", "false", "off", "no")
_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-[^}]*)?\}")
HEAVY_DIRS = ("node_modules", ".venv", "venv")
MAX_FILE = 512 * 1024


def silenced(env) -> bool:
    return any(str(env.get(k, "")).strip().lower() in OFF
               for k in ("ENV_DOCTOR_HINT", "CLAUDE_PLUGIN_OPTION_SESSION_CHECKS"))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def settings_env_names(root: str) -> set[str]:
    """Variable names that Claude Code settings files set through their `env` block."""
    names: set[str] = set()
    for path in (os.path.join(root, ".claude", "settings.json"), os.path.join(root, ".claude", "settings.local.json"),
                 os.path.join(os.path.expanduser("~"), ".claude", "settings.json")):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        env = data.get("env") if isinstance(data, dict) else None
        if isinstance(env, dict):
            names |= {k for k in env if isinstance(k, str)}
    return names


def check_mcp(root: str, env) -> list[str]:
    path = os.path.join(root, ".mcp.json")
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > MAX_FILE:
            return []
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
    except OSError:
        return []
    try:
        data = json.loads(text)
    except ValueError:
        return [".mcp.json in this project is not valid JSON, so none of its MCP servers will load."]
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        return []
    known = set(env) | settings_env_names(root)
    findings = []
    for name, cfg in servers.items():
        missing = sorted({m.group(1) for s in _strings(cfg) for m in _VAR.finditer(s)
                          if m.group(2) is None and m.group(1) not in known})
        if missing:
            findings.append(
                f"MCP server '{name}' in .mcp.json uses " + ", ".join("${" + v + "}" for v in missing)
                + " with no default and the variable is unset, so the literal text is passed. "
                "Set it, or write ${NAME:-} for an optional value.")
    return findings


def _find_stfolder(root: str) -> str | None:
    path = os.path.abspath(root)
    for _ in range(30):
        if os.path.isdir(os.path.join(path, ".stfolder")) or os.path.isfile(os.path.join(path, ".stfolder")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent
    return None


def _ignored(name: str, rel: str, patterns: list[str]) -> bool:
    for raw in patterns:
        p = raw.strip()
        if p.startswith("#include"):
            return True  # cannot evaluate includes cheaply; assume handled
        if not p or p.startswith("//") or p.startswith("#") or p.startswith("!"):
            continue
        p = re.sub(r"^\((?:\?[di])+\)", "", p).strip("/")
        if p in (name, rel, "**/" + name) or p.endswith("/" + name) or p in ("*", "**"):
            return True
    return False


def check_syncthing(root: str) -> list[str]:
    folder = _find_stfolder(root)
    if not folder:
        return []
    present = [d for d in HEAVY_DIRS if os.path.isdir(os.path.join(root, d))]
    if not present:
        return []
    try:
        with open(os.path.join(folder, ".stignore"), encoding="utf-8-sig") as fh:
            patterns = fh.read(MAX_FILE).splitlines()
    except OSError:
        patterns = []
    rel_root = os.path.relpath(root, folder).replace(os.sep, "/")
    rel_root = "" if rel_root == "." else rel_root + "/"
    unignored = [d for d in present if not _ignored(d, rel_root + d, patterns)]
    if not unignored:
        return []
    return ["This project is inside a Syncthing folder and " + ", ".join(unignored)
            + " is not in .stignore. Syncing it causes delete deadlocks and conflict files; add it as (?d)"
            + unignored[0] + "."]


def findings(root: str, env) -> list[str]:
    out: list[str] = []
    for check in (lambda: check_mcp(root, env), lambda: check_syncthing(root)):
        try:
            out.extend(check())
        except Exception:
            continue
    return out


def main() -> int:
    hooklib.watchdog(4)
    if silenced(os.environ):
        return 0
    payload = hooklib.read_payload() or {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd or os.getcwd()
    found = findings(root, os.environ)
    if not found:
        return 0
    text = "[env-doctor] " + " ".join(found[:3]) + " Run /env-doctor:diagnose for a read-only diagnosis."
    hooklib.context("SessionStart", text)
    return 0


if __name__ == "__main__":
    hooklib.run(main)
