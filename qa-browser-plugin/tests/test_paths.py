#!/usr/bin/env python3
"""Static checks on the plugin's markdown surface (offline, no pyyaml).

  * every ${CLAUDE_PLUGIN_ROOT}/... path referenced in a .md file exists;
  * qa-evidence-collector's `tools:` grants namespaced browser MCP tools
    (mcp__plugin_<plugin>_<server>__<tool>) for both supported servers, and no
    script-evaluation / upload tool that would break its read-only contract.

    python tests/test_paths.py
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "agents" / "qa-evidence-collector.md"
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")


def md_files():
    # CHANGELOG.md is history: it legitimately quotes old, removed paths.
    return [p for p in ROOT.rglob("*.md") if "evals" not in p.parts and p.name != "CHANGELOG.md"]


def agent_tools(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    tools, in_tools = [], False
    for line in front.splitlines():
        if line.startswith("tools:"):
            in_tools = True
            inline = line[len("tools:"):].strip()
            if inline:
                return [t.strip() for t in inline.split(",") if t.strip()]
            continue
        if in_tools:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            if stripped.startswith("- "):
                tools.append(stripped[2:].strip())
            else:
                break
    return tools


class PluginRootPaths(unittest.TestCase):
    def test_every_plugin_root_reference_exists(self):
        missing = []
        for md in md_files():
            for rel in REF_RE.findall(md.read_text(encoding="utf-8")):
                rel = rel.rstrip(".")
                if not rel or rel.endswith("/"):
                    continue  # placeholder such as ${CLAUDE_PLUGIN_ROOT}/<x>
                if not (ROOT / rel).is_file():
                    missing.append(f"{md.relative_to(ROOT)} -> {rel}")
        self.assertEqual(missing, [])


class EvidenceCollectorTools(unittest.TestCase):
    def setUp(self):
        self.tools = agent_tools(AGENT)

    def test_has_namespaced_playwright_capture_tools(self):
        for t in ("browser_navigate", "browser_snapshot", "browser_take_screenshot",
                  "browser_console_messages", "browser_network_requests"):
            self.assertIn(f"mcp__plugin_playwright_playwright__{t}", self.tools)

    def test_has_namespaced_chrome_devtools_capture_tools(self):
        for t in ("navigate_page", "take_snapshot", "take_screenshot",
                  "list_console_messages", "list_network_requests"):
            self.assertIn(f"mcp__plugin_chrome-devtools-mcp_chrome-devtools__{t}", self.tools)

    def test_no_mutation_capable_tools(self):
        forbidden = ("evaluate", "run_code", "file_upload", "upload_file", "drag", "drop",
                     "handle_dialog", "select_option")
        bad = [t for t in self.tools if t.startswith("mcp__") and any(f in t for f in forbidden)]
        self.assertEqual(bad, [])

    def test_mcp_tool_names_are_well_formed(self):
        for t in self.tools:
            if t.startswith("mcp__"):
                self.assertRegex(t, r"^mcp__[A-Za-z0-9_-]+__[a-z_]+$")


if __name__ == "__main__":
    unittest.main()
