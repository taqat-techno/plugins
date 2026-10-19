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

    def test_init_command_copies_every_template(self):
        found = refs(ROOT / "commands" / "init.md")
        for template in sorted((ROOT / "templates").iterdir()):
            self.assertIn(f"templates/{template.name}", found)

    def test_skill_links_every_memory_file(self):
        found = refs(SKILL)
        for memory in sorted((ROOT / "memories").glob("*.md")):
            self.assertIn(f"memories/{memory.name}", found)

    def test_no_command_repeats_the_plugin_name_except_the_deprecated_stub(self):
        stub = (ROOT / "commands" / "remotion.md").read_text(encoding="utf-8")
        self.assertIn("Deprecated", stub)
        for name in ("init", "status", "render", "voice"):
            self.assertTrue((ROOT / "commands" / f"{name}.md").is_file())

    def test_script_invocations_use_python3_consistently(self):
        # Stock macOS and Debian/Ubuntu ship only `python3`; the fallback to
        # `python` / `py -3` is documented once in the skill and README.
        bare = [f"{md.relative_to(ROOT)}: {m}" for md in md_files()
                for m in re.findall(r"\bpython \"?\$\{CLAUDE_PLUGIN_ROOT\}\S*",
                                    md.read_text(encoding="utf-8"))]
        self.assertEqual(bare, [])
        for doc in (SKILL, ROOT / "README.md"):
            self.assertIn("py -3", doc.read_text(encoding="utf-8"), doc.name)


if __name__ == "__main__":
    unittest.main()
