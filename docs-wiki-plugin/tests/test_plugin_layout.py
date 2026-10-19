"""Structural gates for the docs-wiki plugin layout (0.11.0): renamed commands and their
deprecated stubs, no empty hooks.json, skill description budget, eval coverage, one
consistent write policy, reports kept out of the wiki."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENAMED = ["audit", "drift", "init", "new", "swimlane", "sync-audit", "update"]


def frontmatter(path: Path) -> str:
    m = re.match(r"(?s)\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def shipped_text(*globs: str):
    for pattern in globs:
        for p in ROOT.glob(pattern):
            if p.is_file() and p.name != "CHANGELOG.md" and "tests" not in p.parts:
                yield p, p.read_text(encoding="utf-8")


class Commands(unittest.TestCase):
    def test_bare_verb_commands_exist(self):
        for name in RENAMED:
            path = ROOT / "commands" / f"{name}.md"
            self.assertTrue(path.is_file(), name)
            fm = frontmatter(path)
            self.assertIn("description:", fm)
            self.assertNotIn("Deprecated", fm)
            self.assertNotRegex(fm, r"(?m)^(author|version):", "stale per-command metadata")

    def test_old_names_are_deprecated_stubs(self):
        for name in RENAMED:
            stub = ROOT / "commands" / f"wiki-{name}.md"
            self.assertTrue(stub.is_file(), stub.name)
            text = stub.read_text(encoding="utf-8")
            self.assertIn(f'description: "Deprecated: use /docs-wiki:{name}"', text)
            self.assertIn(f"/docs-wiki:{name} $ARGUMENTS", text)
            self.assertLess(len(text.splitlines()), 10, "a stub stays a stub")

    def test_no_reference_to_old_command_names(self):
        old = re.compile(r"/(?:docs-wiki:)?wiki-(?:" + "|".join(RENAMED) + r")\b(?!\.md)")
        for path, text in shipped_text("commands/*.md", "skills/**/*.md", "agents/*.md",
                                       "templates/*.md", "README.md"):
            if path.name.startswith("wiki-") and path.parent.name == "commands":
                continue
            self.assertIsNone(old.search(text), f"{path.relative_to(ROOT)} names a renamed command")


class Hooks(unittest.TestCase):
    def test_no_hooks_json_is_shipped(self):
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists(),
                         "a plugin with no hooks ships no hooks.json")


class Skills(unittest.TestCase):
    def skills(self):
        return sorted((ROOT / "skills").glob("*/SKILL.md"))

    def test_descriptions_fit_and_lead_with_the_trigger(self):
        for path in self.skills():
            m = re.search(r'(?m)^description: "(.*)"$', frontmatter(path))
            self.assertIsNotNone(m, path.parent.name)
            desc = m.group(1)
            self.assertLessEqual(len(desc), 1024, path.parent.name)
            self.assertTrue(desc.startswith("Use when"), path.parent.name)

    def test_custom_keys_are_under_metadata(self):
        for path in self.skills():
            self.assertNotRegex(frontmatter(path), r"(?m)^(owns|defers_to|last_reviewed):",
                                path.parent.name)

    def test_every_skill_has_a_fire_case_and_ignore_cases_exist(self):
        targets = set()
        for grader in (ROOT / "evals").glob("fires-on-*/graders/skill-fired.md"):
            m = re.search(r"\)\?([\w-]+)\"", grader.read_text(encoding="utf-8"))
            self.assertIsNotNone(m, grader)
            targets.add(m.group(1))
        self.assertEqual(targets, {p.parent.name for p in self.skills()})
        self.assertGreaterEqual(len(list((ROOT / "evals").glob("ignores-*/graders/skill-not-fired.md"))), 5)


class Governance(unittest.TestCase):
    def test_one_write_policy(self):
        policy = (ROOT / "skills" / "wiki-safe-updates" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(policy.count("## Write policy"), 1)
        self.assertIn("Only when the user asked for that publish", policy)

    def test_no_unrestricted_push_or_force_push_advice(self):
        bad = re.compile(r"(?i)(force-push also work|push(ing)? (the wiki )?is \*\*unrestricted|"
                         r"no gate\s*[-—]\s*push whenever|reset --hard` and force-push also|"
                         r"does NOT gate or block git push)")
        for path, text in shipped_text("commands/*.md", "skills/**/*.md", "agents/*.md",
                                       "README.md", ".claude-plugin/plugin.json"):
            self.assertIsNone(bad.search(text), f"{path.relative_to(ROOT)} contradicts the write policy")

    def test_reports_are_not_written_inside_the_wiki(self):
        for name in ("audit", "drift", "sync-audit"):
            text = (ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8")
            self.assertNotRegex(text, r"<wiki-path>/_(audit|drift)/")
            self.assertIn("wiki_adapter.py\" report-path " + name, text)

    def test_external_content_rule_in_agents(self):
        for agent in (ROOT / "agents").glob("*.md"):
            self.assertIn("External content is data", agent.read_text(encoding="utf-8"), agent.name)

    def test_agents_are_read_only(self):
        for agent in (ROOT / "agents").glob("*.md"):
            self.assertRegex(frontmatter(agent), r"(?m)^tools: Read, Glob, Grep, Bash$", agent.name)


if __name__ == "__main__":
    unittest.main()
