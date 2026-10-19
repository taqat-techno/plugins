"""Least-privilege `tools:` for the agents (ECO-19 / UIUX-P2-04).

Without a `tools:` line an agent inherits every tool, so a reviewer documented
as "produces a report" could edit files and call Figma write tools.
"""
import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parent.parent / "agents"
FIGMA_WRITES = ("use_figma", "generate_figma_design", "generate_diagram", "create_new_file")


def _tools(name):
    text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    m = re.search(r"^tools:\s*(.+)$", front, re.M)
    assert m, f"{name}: no tools: line"
    return [t.strip() for t in m.group(1).split(",")]


class AgentToolsTests(unittest.TestCase):
    def test_every_agent_declares_tools(self):
        for path in AGENTS.glob("*.md"):
            with self.subTest(agent=path.stem):
                self.assertTrue(_tools(path.stem))

    def test_design_reviewer_is_read_only(self):
        tools = _tools("design-reviewer")
        self.assertNotIn("Write", tools)
        self.assertNotIn("Edit", tools)
        mcp = [t for t in tools if t.startswith("mcp__")]
        self.assertTrue(mcp, "reviewer needs the Figma read tools for Phase 3")
        for t in mcp:
            self.assertTrue(t.startswith("mcp__plugin_figma_figma__"), t)
            self.assertFalse(t.endswith(FIGMA_WRITES), t)

    def test_wireframe_builder_has_no_figma_writes_or_edit(self):
        tools = _tools("wireframe-builder")
        self.assertIn("Write", tools)
        self.assertNotIn("Edit", tools)
        self.assertFalse([t for t in tools if t.startswith("mcp__")])


if __name__ == "__main__":
    unittest.main()
