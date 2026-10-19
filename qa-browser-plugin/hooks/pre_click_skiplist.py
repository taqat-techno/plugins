#!/usr/bin/env python3
"""
qa-browser PreToolUse hook - do-not-click skiplist.

Matcher (hooks/hooks.json): browser click tools (`browser_click`, `click`).

A click is put to the user (permissionDecision "ask") when the click target
matches the project's skiplist in `.qa-browser.local.json`:

  doNotClick      CSS / Playwright selectors. A hit is an exact,
                  case-insensitive match against the tool's `target` /
                  `selector` field. Text inside `:has-text('...')` or a
                  `text=...` selector is also matched as a text pattern.
  doNotClickText  Plain text (e.g. "Refund", "Delete account"). A hit is a
                  case-insensitive substring of the tool's `element`
                  description or `target`.

What the hook can see depends on the browser server: Playwright MCP's
`browser_click` carries a human-readable `element` description and a `target`
(snapshot ref or selector), so both lists apply. chrome-devtools-mcp's `click`
carries only an element `uid`, which says nothing about the button, so the
hook cannot match it; the `safe-destructive-testing` skill is the only guard
there.

No config, or no skiplist, means no output. Any error fails open (exit 0).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

CONFIG_FILENAME = ".qa-browser.local.json"
SELECTOR_KEYS = ("target", "selector")
TEXT_KEYS = ("element", "target", "selector")
HAS_TEXT_RE = re.compile(r"""(?:has-text\(\s*['"](.+?)['"]\s*\)|^text\s*=\s*['"]?(.+?)['"]?$)""")


def find_config() -> Path | None:
    candidates: list[Path] = []
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        candidates.append(Path(project))
    cwd = Path.cwd()
    candidates.append(cwd)
    candidates.extend(cwd.parents)
    for d in candidates:
        p = d / CONFIG_FILENAME
        if p.is_file():
            return p
    return None


def _strings(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if isinstance(v, str) and v.strip()]


def match(tool_input: dict, config: dict) -> str | None:
    """Return the skiplist entry the click hits, else None."""
    selectors = _strings(config.get("doNotClick"))
    texts = _strings(config.get("doNotClickText"))
    for sel in selectors:
        m = HAS_TEXT_RE.search(sel)
        if m:
            texts.append(m.group(1) or m.group(2))
    fields = {k: tool_input.get(k) for k in set(SELECTOR_KEYS + TEXT_KEYS)}
    for key in SELECTOR_KEYS:
        value = fields.get(key)
        if isinstance(value, str):
            for sel in selectors:
                if value.strip().lower() == sel.lower():
                    return f"doNotClick selector '{sel}'"
    for key in TEXT_KEYS:
        value = fields.get(key)
        if isinstance(value, str):
            low = value.lower()
            for text in texts:
                if text.lower() in low:
                    return f"do-not-click text '{text}'"
    return None


def main() -> int:
    hooklib.watchdog(4.5)
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    tool_input = hooklib.tool_input(payload)
    if not tool_input:
        return 0
    path = find_config()
    if path is None:
        return 0
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    if not isinstance(config, dict):
        return 0
    hit = match(tool_input, config)
    if hit:
        what = tool_input.get("element") or tool_input.get("target") or "this element"
        hooklib.ask(f"[qa-browser] The click on '{what}' matches the {hit} in "
                    f"{CONFIG_FILENAME}. Approve only if this record is disposable "
                    f"test data.")
    return 0


if __name__ == "__main__":
    hooklib.run(main)
