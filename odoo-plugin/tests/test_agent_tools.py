"""The read-only analyzer agents must declare a least-privilege tool list.

Without a `tools:` line an agent inherits every tool in the session - including
the odoo MCP write tools (odoo_write, odoo_unlink, odoo_call). The analyzers
only read code and return a report in their reply, so they need no Write/Edit
and no MCP access.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

AGENTS = Path(__file__).resolve().parent.parent / "agents"
ANALYZERS = ("security-auditor", "test-analyzer", "upgrade-analyzer")
EXPECTED = ["Read", "Glob", "Grep", "Bash"]


def _frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "%s has no YAML frontmatter" % path.name
    return m.group(1)


@pytest.mark.parametrize("name", ANALYZERS)
def test_analyzer_declares_least_privilege_tools(name):
    fm = _frontmatter(AGENTS / ("%s.md" % name))
    lines = [ln for ln in fm.splitlines() if ln.startswith("tools:")]
    assert len(lines) == 1, "%s must have exactly one tools: line" % name
    tools = [t.strip() for t in lines[0].split(":", 1)[1].split(",") if t.strip()]
    assert tools == EXPECTED, "%s tools are %r" % (name, tools)
    for forbidden in ("Write", "Edit", "mcp__", "odoo_"):
        assert not any(forbidden in t for t in tools), (name, forbidden)
