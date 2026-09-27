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
  0 — allow (URL safe OR override active). With the override active, the audit
      line goes to Claude as PreToolUse additionalContext JSON: exit-0 stderr is
      never shown to the user or the model, and systemMessage is ignored on
      PreToolUse. No permissionDecision is set, so no extra prompt is added.
  2 — block (production URL without override) — Claude Code interprets non-zero as block
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


CONFIG_FILENAME = ".qa-browser.local.json"
DEFAULT_MARKERS = ["prod", "production"]
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"


def _advise(text: str) -> None:
    """Hand a note to Claude without blocking the tool call.

    On PreToolUse, stderr and plain stdout from an exit-0 hook never reach the
    model; only hookSpecificOutput.additionalContext does, and only with
    hookEventName set. Claude receives it next to the tool result. No
    permissionDecision is emitted, so the normal permission flow is untouched.
    """
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": text,
    }}))


def main() -> int:
    # Read tool-call payload from stdin (Claude Code convention). Decode as
    # UTF-8 explicitly: Windows defaults stdin to cp1252.
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        # If we cannot parse the payload, do not block. (Hook is best-effort.)
        return 0
    if not isinstance(payload, dict):
        return 0

    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    url = _extract_url(tool_input) if isinstance(tool_input, dict) else None

    if not url:
        return 0  # no URL → nothing to gate

    markers = _load_markers()
    matched = _matched_marker(url.lower(), [m.lower() for m in markers])

    if matched is None:
        return 0  # non-production URL — allow

    if os.environ.get(OVERRIDE_ENV) == "1":
        # Override active — allow, and put the production visit on record for
        # Claude (only for production URLs; other navigations stay silent).
        _advise(
            f"[qa-browser] navigation to production URL {url} (marker '{matched}') "
            f"ALLOWED because {OVERRIDE_ENV}=1 is set for this session."
        )
        return 0

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
