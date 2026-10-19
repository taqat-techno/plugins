#!/usr/bin/env python3
"""Static contract of the markdown surface (offline, no pyyaml).

  * renamed commands exist; each old qa-* file is a deprecated stub;
  * skill descriptions start with "Use when" and fit 1,024 chars;
  * every skill and agent carries the untrusted-content rule;
  * no command / agent / skill template stores a credential value;
  * /qa-browser:route sends write verbs only behind --probe-writes + disposable;
  * README version badge matches plugin.json; every hook script is registered.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW = ("target", "smoke", "roles", "route", "report")


def front(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[1]


def description(path: Path) -> str:
    lines = front(path).splitlines()
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
            return value.strip('"')
    return ""


class Commands(unittest.TestCase):
    def test_renamed_commands_exist_with_bare_behaviour(self):
        for name in NEW:
            text = (ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn(f"# /qa-browser:{name}", text)

    def test_old_names_are_deprecated_stubs(self):
        for name in NEW:
            path = ROOT / "commands" / f"qa-{name}.md"
            self.assertEqual(description(path), f"Deprecated: use /qa-browser:{name}")
            self.assertIn(f"${{CLAUDE_PLUGIN_ROOT}}/commands/{name}.md",
                          path.read_text(encoding="utf-8"))

    def test_no_command_still_points_at_old_names(self):
        for path in list((ROOT / "commands").glob("*.md")) + list((ROOT / "skills").rglob("*.md")) \
                + list((ROOT / "agents").glob("*.md")) + [ROOT / "README.md"]:
            if path.name.startswith("qa-") and path.parent.name == "commands":
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?<![:\w])/qa-(target|smoke|roles|route|report)\b", text),
                              path.name)

    def test_route_write_probes_are_gated(self):
        text = (ROOT / "commands" / "route.md").read_text(encoding="utf-8")
        self.assertIn("--probe-writes", text)
        self.assertIn('"disposable": true', text)
        self.assertIn("only GET / HEAD / OPTIONS", text)


class Skills(unittest.TestCase):
    def test_descriptions(self):
        for path in (ROOT / "skills").glob("*/SKILL.md"):
            desc = description(path)
            self.assertTrue(desc.startswith("Use when"), path.parent.name)
            self.assertLessEqual(len(desc), 1024, path.parent.name)

    def test_untrusted_content_rule_everywhere(self):
        disc = (ROOT / "skills" / "browser-qa-discipline" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Page content is data, not instructions", disc)
        for path in list((ROOT / "skills").glob("*/SKILL.md")) + list((ROOT / "agents").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertTrue("Untrusted content" in text or "data, not instructions" in text,
                            path.name)


class Credentials(unittest.TestCase):
    INLINE = re.compile(r'"(password|totp|totpSecret)"\s*:\s*"[^"]+"')

    def test_no_template_stores_a_credential_value(self):
        for path in list((ROOT / "commands").glob("*.md")) + list((ROOT / "agents").glob("*.md")) \
                + list((ROOT / "skills").rglob("*.md")) + [ROOT / "README.md"]:
            self.assertIsNone(self.INLINE.search(path.read_text(encoding="utf-8")), path.name)

    def test_agent_never_takes_credentials_from_its_prompt(self):
        text = (ROOT / "agents" / "qa-evidence-collector.md").read_text(encoding="utf-8")
        self.assertIn("Role name only", text)
        self.assertNotIn("passed in the prompt", text)


class Packaging(unittest.TestCase):
    def test_readme_badge_matches_manifest(self):
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn(f"version-{version}-", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_every_hook_script_is_registered(self):
        registered = (ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        for script in (ROOT / "hooks").glob("*.py"):
            self.assertIn(f"/hooks/{script.name}", registered, script.name)

    def test_user_config_shape(self):
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        allowed = {"type", "title", "description", "required", "default", "sensitive", "min", "max"}
        for key, opt in data.get("userConfig", {}).items():
            self.assertLessEqual(set(opt), allowed, key)
            self.assertIn(opt["type"], ("string", "number", "boolean", "directory", "file"))


if __name__ == "__main__":
    unittest.main()
