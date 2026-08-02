"""WP-6/8/9 — the retrieval skill guides; it never invokes.

Why this test exists
--------------------
D-001 forbids the plugin from wrapping ``search_knowledge_base``; D-032 §1
extends that to ``search_project_context`` and ``find_definition``. WP-7 adds a
skill whose entire subject is those tools, which is exactly the kind of change
that erodes a boundary by accident rather than by decision.

The distinction the new decision (D-034) records: **guidance is not
invocation.** Telling Claude how to choose and read a tool is what the CLAUDE.md
retrieval rule has done since D-016. Performing the call on the user's behalf —
intercepting, reformatting, or proxying the result — is the line.

So this module asserts the mechanical consequences of that line rather than
trying to police prose:

  * no command grants a retrieval tool in ``allowed-tools``;
  * the skill states its own boundary, so a future editor meets it;
  * ``secret_audit`` remains the documented carve-out (D-032 §2), so the
    boundary is not accidentally widened to every tool with "search" in it.
"""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT  # type: ignore[import-not-found]  # noqa: E402

#: Tools the plugin may never call itself (D-001 + D-032 §1).
CLAUDE_ONLY = ("search_knowledge_base", "search_project_context", "find_definition")

#: The carve-out: an ops/audit tool the plugin MAY call (D-032 §2).
PLUGIN_CALLABLE = "secret_audit"

SKILL = PLUGIN_ROOT / "skills" / "ragtools-retrieval" / "SKILL.md"


class TestNoCommandGrantsARetrievalTool(unittest.TestCase):
    """`allowed-tools` is the mechanical grant. If a retrieval tool is not in
    it, the command cannot call one however its prose is worded."""

    def test_allowed_tools_never_lists_a_claude_only_tool(self):
        offenders = []
        for path in sorted((PLUGIN_ROOT / "commands").glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.startswith("allowed-tools:"):
                    continue
                for tool in CLAUDE_ONLY:
                    if tool in line:
                        offenders.append(f"{path.name} grants {tool}")
                break
        self.assertEqual(
            offenders, [],
            "D-001/D-032 §1: the plugin never calls these; Claude does.\n"
            + "\n".join(offenders),
        )

    def test_the_carve_out_is_still_expressible(self):
        """A guard that also blocked `secret_audit` would be over-broad —
        D-022/D-032 §2 deliberately permit it."""
        self.assertNotIn(PLUGIN_CALLABLE, CLAUDE_ONLY)


class TestTheSkillDeclaresItsBoundary(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8") if SKILL.is_file() else ""

    def test_the_skill_exists(self):
        self.assertTrue(self.text, "skills/ragtools-retrieval/SKILL.md is missing")

    @staticmethod
    def _plain(text: str) -> str:
        """Strip markdown emphasis so an assertion pins the sentence, not its
        formatting. Without this, adding italics to a word silently breaks a
        boundary test — and the failure output is the entire file."""
        return (text.replace("*", "").replace("`", "")
                .replace("’", "'").replace("—", "-").lower())

    def test_it_states_that_it_never_calls_a_retrieval_tool(self):
        self.assertIn(
            "never calls a retrieval tool", self._plain(self.text),
            "the skill must say, in its own text, that it does not invoke",
        )

    def test_it_cites_the_governing_decisions(self):
        for decision in ("D-001", "D-032", "D-034"):
            self.assertIn(decision, self.text, f"{decision} is not referenced")

    def test_it_names_the_line_concretely(self):
        """A boundary stated abstractly is a boundary nobody can apply."""
        self.assertIn(
            "performs a search on the user's behalf", self._plain(self.text),
            "the skill states the boundary but not where the line falls",
        )


class TestSkillDescriptionTriggersOnRetrievalIntent(unittest.TestCase):
    """A skill that never loads is guidance nobody reads."""

    def setUp(self):
        text = SKILL.read_text(encoding="utf-8") if SKILL.is_file() else ""
        m = re.search(r"^description:\s*(.+?)$", text, re.M)
        self.description = m.group(1) if m else ""

    def test_description_exists_and_is_substantial(self):
        self.assertGreater(len(self.description), 120,
                           "the description is what decides whether the skill loads")

    def test_it_covers_the_phrasings_users_actually_type(self):
        lowered = self.description.lower()
        for phrase in ("where is", "what did we decide", "find the definition",
                       "search my notes"):
            self.assertIn(phrase, lowered,
                          f"description does not trigger on {phrase!r}")

    def test_it_covers_the_failure_modes_too(self):
        """The skill is most valuable when a search has already gone wrong."""
        lowered = self.description.lower()
        for phrase in ("low-confidence", "stale", "conflicting"):
            self.assertIn(phrase, lowered, f"description omits {phrase!r}")


class TestReferencesAreReachable(unittest.TestCase):
    def test_every_reference_named_by_the_skill_exists(self):
        text = SKILL.read_text(encoding="utf-8") if SKILL.is_file() else ""
        named = set(re.findall(r"`references/([a-z-]+\.md)`", text))
        self.assertTrue(named, "the skill routes to no reference files")
        missing = [n for n in sorted(named)
                   if not (SKILL.parent / "references" / n).is_file()]
        self.assertEqual(missing, [], f"referenced but absent: {missing}")

    def test_the_trust_model_rule_exists(self):
        self.assertTrue((PLUGIN_ROOT / "rules" / "trust-model.md").is_file(),
                        "rules/trust-model.md is referenced by the skill and "
                        "by state-detection but does not exist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
