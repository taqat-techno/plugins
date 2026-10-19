#!/usr/bin/env python3
"""Offline check: every ${CLAUDE_PLUGIN_ROOT}/... path the plugin's markdown tells
Claude to use resolves to a real file, and the skill never runs a script by a bare
relative path (scripts are not copied into the user's project).

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "remotion" / "SKILL.md"
# Concrete references only: a placeholder such as scripts/<name>.py stops at "<"
# and leaves a trailing "/", which is skipped.
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
PIPELINE = ("setup_check.py", "generate_voice.py", "concat_audio.py", "measure_audio.py")


def md_files():
    # CHANGELOG.md is history: it legitimately quotes old, removed paths.
    return [p for p in ROOT.rglob("*.md") if "evals" not in p.parts and p.name != "CHANGELOG.md"]


def refs(path: Path) -> list[str]:
    found = (r.rstrip(".") for r in REF_RE.findall(path.read_text(encoding="utf-8")))
    return [r for r in found if not r.endswith("/")]


class PluginRootPaths(unittest.TestCase):
    def test_every_plugin_root_reference_exists(self):
        missing = [f"{md.relative_to(ROOT)} -> {rel}"
                   for md in md_files() for rel in refs(md) if not (ROOT / rel).is_file()]
        self.assertEqual(missing, [])

    def test_skill_references_every_pipeline_script(self):
        found = refs(SKILL)
        for script in PIPELINE:
            self.assertIn(f"scripts/{script}", found)

    def test_skill_has_no_bare_relative_script_invocation(self):
        bare = re.findall(r"python3? scripts/\S+", SKILL.read_text(encoding="utf-8"))
        self.assertEqual(bare, [])


if __name__ == "__main__":
    unittest.main()
