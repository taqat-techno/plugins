#!/usr/bin/env python3
"""Static contract of the plugin's markdown surface (offline, stdlib only).

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")


def description(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").split("---", 2)[1].splitlines()
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">-", ">", "|"):
                value = " ".join(_block(lines[i + 1:]))
            return value.strip('"\'')
    return ""


def _block(lines):
    for line in lines:
        if not line.startswith("  "):
            return
        yield line.strip()


def md_files():
    return [p for p in ROOT.rglob("*.md") if "evals" not in p.parts and p.name != "CHANGELOG.md"]


class Surface(unittest.TestCase):
    def test_no_empty_hooks_file(self):
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists())

    def test_plugin_root_references_resolve(self):
        missing = []
        for md in md_files():
            for rel in REF_RE.findall(md.read_text(encoding="utf-8")):
                rel = rel.rstrip(".")
                if rel and not rel.endswith("/") and not (ROOT / rel).is_file():
                    missing.append(f"{md.name} -> {rel}")
        self.assertEqual(missing, [])

    def test_skills_and_agents_use_plugin_root_for_reference_docs(self):
        for path in list((ROOT / "skills").rglob("SKILL.md")) + list((ROOT / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?<![/\w])reference/[a-z-]+\.md", text), path.name)

    def test_descriptions_fit_budget_and_lead_with_trigger(self):
        for path in (ROOT / "skills").glob("*/SKILL.md"):
            desc = description(path)
            self.assertTrue(desc.startswith("Use when"), path.parent.name)
            self.assertLessEqual(len(desc), 1024, path.parent.name)
            self.assertNotIn("<example>", desc)

    def test_figma_write_approval_gate(self):
        mech = (ROOT / "skills" / "figma-mcp-mechanics" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## User approval before any write", mech)
        gate = mech.split("## User approval before any write", 1)[1].split("\n## ", 1)[0]
        self.assertIn("probe", gate)
        self.assertLess(mech.index("## User approval before any write"),
                        mech.index("## The fifteen mechanics"))
        wf = (ROOT / "skills" / "figma-workflow" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Every Write row needs the user's approval first", wf)
        cmd = (ROOT / "commands" / "toolkit.md").read_text(encoding="utf-8")
        self.assertIn("User approval before any write", cmd)

    def test_figma_content_is_data(self):
        for rel in ("skills/figma-mcp-mechanics/SKILL.md", "skills/figma-workflow/SKILL.md",
                    "agents/design-reviewer.md"):
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertTrue("never instructions" in text or "never an instruction" in text
                            or "not instructions" in text, rel)

    def test_core_reference_is_framework_neutral(self):
        for name in ("color-theory.md", "typography-scale.md", "layout-patterns.md",
                     "platform-guidelines.md", "accessibility-checklist.md"):
            text = (ROOT / "reference" / name).read_text(encoding="utf-8")
            self.assertNotIn("o-color-", text, name)
            self.assertNotIn("## Odoo", text, name)

    def test_platform_guidelines_cite_sources(self):
        text = (ROOT / "reference" / "platform-guidelines.md").read_text(encoding="utf-8")
        for url in ("developer.apple.com/design/human-interface-guidelines",
                    "m3.material.io", "fluent2.microsoft.design"):
            self.assertIn(url, text)

    def test_wcag_22_criteria_listed(self):
        text = (ROOT / "reference" / "accessibility-checklist.md").read_text(encoding="utf-8")
        for sc in ("2.4.11", "2.5.7", "2.5.8", "3.2.6", "3.3.7", "3.3.8"):
            self.assertIn(sc, text)

    def test_command_rename_and_stub(self):
        self.assertTrue((ROOT / "commands" / "toolkit.md").is_file())
        stub = ROOT / "commands" / "ui-ux-mechanics.md"
        self.assertEqual(description(stub), "Deprecated: use /ui-ux-mechanics:toolkit")

    def test_readme_badge_matches_manifest(self):
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn(f"version-{version}-", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_readme_has_no_manual_copy_install(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("/plugin install ui-ux-mechanics@taqat-techno-plugins", text)
        self.assertNotIn("cp -r", text)
        self.assertNotIn("skills` array", text)


if __name__ == "__main__":
    unittest.main()
