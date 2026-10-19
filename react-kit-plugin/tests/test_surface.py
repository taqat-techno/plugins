#!/usr/bin/env python3
"""Offline checks for react-kit's markdown surface (stdlib only).

  * frontmatter: name matches directory, description starts "Use when", fits
    1,024 chars, total description budget stays under 6,000 chars, custom keys
    live under metadata:;
  * genericity lint: no project-specific tokens and no mandate to replace a
    project's existing access model;
  * every ${CLAUDE_PLUGIN_ROOT}/ path resolves; skill-local references/ exist;
  * frontend-build-traps gates the webpack advice on the Next.js major and
    requires a process-ownership check before killing a port owner;
  * plugin.json claims only areas a skill owns; README badge == version;
    no relative ../ links in the README.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "skills").glob("*/SKILL.md"))
ALLOWED_TOP_KEYS = {"name", "description", "version", "user-invocable", "metadata",
                    "allowed-tools", "license", "disable-model-invocation", "argument-hint"}
FORBIDDEN_TOKENS = ("royal preps", "royalpreps", "railway.app", "taqatechno.com/", "C:\\",
                    "/Users/ahmed", "medical exam")
MANDATE_PHRASES = (r"role enum is a smell", r"replace (the|your) role enum",
                   r"must (use|adopt) module[- ]level", r"always (use|adopt) module[- ]level",
                   r"migrate (to|onto) module[- ]levels? (first|before)")
REF_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")
LOCAL_REF_RE = re.compile(r"`references/([a-z0-9-]+\.md)`")


def frontmatter(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").split("---", 2)[1].splitlines()


def top_keys(lines):
    return [l.split(":", 1)[0] for l in lines if l and not l.startswith((" ", "-", "#")) and ":" in l]


def description(lines) -> str:
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">-", ">", "|"):
                parts = []
                for nxt in lines[i + 1:]:
                    if not nxt.startswith("  "):
                        break
                    parts.append(nxt.strip())
                value = " ".join(parts)
            return value
    return ""


class Frontmatter(unittest.TestCase):
    def test_sixteen_skills(self):
        self.assertEqual(len(SKILLS), 16)

    def test_each_skill(self):
        total = 0
        for path in SKILLS:
            lines = frontmatter(path)
            with self.subTest(skill=path.parent.name):
                self.assertIn(f"name: {path.parent.name}", lines)
                desc = description(lines)
                total += len(desc)
                self.assertTrue(desc.startswith("Use when"))
                self.assertLessEqual(len(desc), 1024)
                self.assertNotIn("<example>", desc)
                self.assertLessEqual(set(top_keys(lines)), ALLOWED_TOP_KEYS)
        self.assertLess(total, 6000, "always-loaded description budget (RKT-P2-10)")


class Genericity(unittest.TestCase):
    def files(self):
        return [p for p in ROOT.rglob("*.md") if "evals" not in p.parts and p.name != "CHANGELOG.md"]

    def test_no_project_specific_tokens(self):
        for path in self.files():
            low = path.read_text(encoding="utf-8").lower()
            for token in FORBIDDEN_TOKENS:
                self.assertNotIn(token.lower(), low, f"{path.relative_to(ROOT)}: {token}")

    def test_no_access_model_mandate(self):
        for path in self.files():
            text = path.read_text(encoding="utf-8")
            for phrase in MANDATE_PHRASES:
                self.assertIsNone(re.search(phrase, text, re.I), f"{path.relative_to(ROOT)}: {phrase}")


class Paths(unittest.TestCase):
    def test_plugin_root_references_resolve(self):
        missing = []
        for md in ROOT.rglob("*.md"):
            if "evals" in md.parts or md.name == "CHANGELOG.md":
                continue
            for rel in REF_RE.findall(md.read_text(encoding="utf-8")):
                rel = rel.rstrip(".")
                if rel and not rel.endswith("/") and not (ROOT / rel).is_file():
                    missing.append(f"{md.relative_to(ROOT)} -> {rel}")
        self.assertEqual(missing, [])

    def test_skill_local_references_exist(self):
        missing = []
        for path in SKILLS:
            for name in LOCAL_REF_RE.findall(path.read_text(encoding="utf-8")):
                if not (path.parent / "references" / name).is_file():
                    missing.append(f"{path.parent.name} -> references/{name}")
        self.assertEqual(missing, [])

    def test_commands_reference_adapter_schema_by_plugin_root(self):
        for path in (ROOT / "commands").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?<![}/])skills/admin-panel-architecture/references/", text),
                              path.name)


class BuildTraps(unittest.TestCase):
    TEXT = (ROOT / "skills" / "frontend-build-traps" / "SKILL.md").read_text(encoding="utf-8")

    def test_webpack_advice_is_version_gated(self):
        self.assertIn("## Version gate (Next.js)", self.TEXT)
        self.assertRegex(self.TEXT, r"13 / 14 / 15 \| webpack")
        self.assertRegex(self.TEXT, r"16 and later \| Turbopack")

    def test_kill_requires_ownership_check(self):
        self.assertIn("## Before stopping a process", self.TEXT)
        self.assertIn("Never** kill a process by port alone", self.TEXT)
        self.assertIn("Get-NetTCPConnection", self.TEXT)
        self.assertIn("lsof", self.TEXT)


class Manifest(unittest.TestCase):
    DATA = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    def test_no_unowned_claims(self):
        desc = self.DATA["description"].lower()
        self.assertNotIn("accessibility basics", desc)
        self.assertNotIn("component architecture", desc)

    def test_readme_badge_matches_version(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"version-{self.DATA['version']}-", readme)
        self.assertNotIn("](../", readme)

    def test_untrusted_tool_output_rule(self):
        for rel in ("skills/react-lint-triage/SKILL.md", "skills/frontend-build-traps/SKILL.md",
                    "agents/admin-route-auditor.md"):
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
            self.assertTrue("never an instruction" in text or "not an instruction" in text, rel)

    def test_agent_is_read_only(self):
        text = (ROOT / "agents" / "admin-route-auditor.md").read_text(encoding="utf-8")
        tools = re.search(r"^tools:\s*(.+)$", text.split("---", 2)[1], re.M).group(1)
        self.assertEqual([t.strip() for t in tools.split(",")], ["Read", "Glob", "Grep"])


if __name__ == "__main__":
    unittest.main()
