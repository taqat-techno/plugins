#!/usr/bin/env python3
"""
qa-browser PreToolUse hook — production URL gate.

Intercepts browser MCP navigation calls (chrome-devtools-mcp `navigate_page`,
playwright-mcp `browser_navigate`). Extracts the target URL from tool input.
If the URL matches any production marker AND the per-session override is NOT
set, BLOCKS the navigation with a clear message.

Production markers are read from `.qa-browser.local.json` if present, else
fall back to defaults: ["prod", "production"].

Per-session override: an environment variable QA_BROWSER_ALLOW_PRODUCTION=1
disables the gate for the current session. The user must set it deliberately
(typically by running a /qa-target opt-in flow that exports the var in this
session's scope, OR by setting it manually in the shell).

Exit codes:
  0 — allow (URL safe OR override active)
  2 — block (production URL without override) — Claude Code interprets non-zero as block
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


CONFIG_FILENAME = ".qa-browser.local.json"
DEFAULT_MARKERS = ["prod", "production"]
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"


def main() -> int:
    # Read tool-call payload from stdin (Claude Code convention).
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # If we cannot parse the payload, do not block. (Hook is best-effort.)
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    url = _extract_url(tool_input)

    if not url:
        return 0  # no URL → nothing to gate

    if os.environ.get(OVERRIDE_ENV) == "1":
        # Override active — allow, but log to stderr so the user sees the audit trail.
        print(
            f"[qa-browser] navigation to {url} ALLOWED — "
            f"{OVERRIDE_ENV}=1 is set for this session.",
            file=sys.stderr,
        )
        return 0

    markers = _load_markers()
    matched = _matched_marker(url.lower(), [m.lower() for m in markers])

    if matched is None:
        return 0  # non-production URL — allow

    # Production URL detected, no override → block.
    print(
        f"[qa-browser] BLOCKED navigation to {url}\n"
        f"  Reason: URL matches production marker '{matched}'.\n"
        f"  To override for this session, set the environment variable:\n"
        f"      Windows PowerShell:  $env:{OVERRIDE_ENV} = '1'\n"
        f"      bash / zsh:          export {OVERRIDE_ENV}=1\n"
        f"  Then re-run the navigation. The override lasts only for the current shell session.\n"
        f"  Configure custom markers in {CONFIG_FILENAME} under productionMarkers.",
        file=sys.stderr,
    )
    return 2  # non-zero → block


def _extract_url(tool_input: dict) -> str | None:
    """
    Try common URL field names across browser MCP servers.

    chrome-devtools-mcp uses `url`.
    playwright-mcp uses `url`.
    Both accept the URL as a string.
    """
    for key in ("url", "URL", "href", "address"):
        v = tool_input.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _load_markers() -> list[str]:
    cwd = Path.cwd()
    config = cwd / CONFIG_FILENAME
    if not config.exists():
        return DEFAULT_MARKERS
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        markers = data.get("productionMarkers")
        if isinstance(markers, list) and markers:
            return [str(m) for m in markers]
        return DEFAULT_MARKERS
    except Exception:
        return DEFAULT_MARKERS


def _matched_marker(url_lower: str, markers_lower: list[str]) -> str | None:
    for m in markers_lower:
        if m and m in url_lower:
            return m
    return None


if __name__ == "__main__":
    sys.exit(main())
