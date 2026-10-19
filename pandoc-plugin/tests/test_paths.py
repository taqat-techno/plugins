#!/usr/bin/env python3
"""Offline check: every ${CLAUDE_PLUGIN_ROOT}/... path the plugin's markdown tells
Claude to use resolves to a real file, and /pandoc setup points at the installers.

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
INSTALLERS = ("skills/pandoc/scripts/setup.ps1", "skills/pandoc/scripts/setup.sh")


def md_files():
    # CHANGELOG.md is history: it legitimately quotes old, removed paths.
    return [p for p in ROOT.rglob("*.md") if "evals" not in p.parts and p.name != "CHANGELOG.md"]


def refs(path: Path) -> list[str]:
    return [r.rstrip(".") for r in REF_RE.findall(path.read_text(encoding="utf-8"))]


class PluginRootPaths(unittest.TestCase):
    def test_every_plugin_root_reference_exists(self):
        missing = [f"{md.relative_to(ROOT)} -> {rel}"
                   for md in md_files() for rel in refs(md) if not (ROOT / rel).is_file()]
        self.assertEqual(missing, [])

    def test_references_were_found(self):
        self.assertTrue(any(refs(md) for md in md_files()), "no references scanned")

    def test_setup_command_and_skill_reference_both_installers(self):
        for md in (ROOT / "commands" / "pandoc.md", ROOT / "skills" / "pandoc" / "SKILL.md"):
            found = refs(md)
            for installer in INSTALLERS:
                self.assertIn(installer, found, f"{md.name} does not reference {installer}")


if __name__ == "__main__":
    unittest.main()
