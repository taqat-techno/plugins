"""WP-1 — every retrieval call the plugin teaches must carry an explicit scope.

Why this is a gate, not decoration
----------------------------------
ragtools made retrieval fail-closed in v3.0.0: ``owner.search`` calls
``resolve_scope(..., allow_unscoped=False)``, so ``GET /api/search`` with no
``project`` returns **HTTP 422 SCOPE_UNRESOLVED** and zero results.

v0.17.0 taught the unscoped call in two places that reach Claude on every
session:

  * ``rules/claude-md-retrieval-rule.md:40`` — "call ``search_knowledge_base(query=...)`` first"
  * ``hooks/prompt_retrieval_reminder.py:343`` — the injected reminder body

Both are in ``tests/baseline_v0.17.0/``. Run this module against that snapshot
and it must FAIL; run it against the live tree and it must pass.

Documenting the anti-pattern is still allowed: put ``unscoped-example-ok`` on
the same line or the line before, which is how the retrieval skill shows what
NOT to do without tripping this gate.
"""

from __future__ import annotations

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import is_baseline, read, scan_files  # noqa: E402

# `search_knowledge_base(` / `search_project_context(` plus everything up to the
# closing paren on that line.
_CALL = re.compile(
    r"(search_knowledge_base|search_project_context)\s*\(([^)\n]*)\)?",
)
_OPT_OUT = "unscoped-example-ok"

# A block example may legitimately spread its arguments over several lines:
#
#     search_knowledge_base(
#       query="...",
#       projects=["docs", "notes"],
#     )
#
# Reading only the opening line would flag that as unscoped. When the call is
# left open at end-of-line, the window extends to the closing paren (bounded,
# so an unterminated example cannot swallow the rest of the file).
_MULTILINE_LOOKAHEAD = 8

# Tools whose scope argument is mandatory server-side. `find_definition` and
# `secret_audit` are deliberately absent: ragtools does NOT call resolve_scope
# for them, so an unscoped call is legal there (report A-03).
SCOPE_REQUIRED = {"search_knowledge_base", "search_project_context"}


def _arg_window(lines, i: int, match) -> str:
    """The argument text of a call starting on line ``i``.

    Same-line when the call closes there; otherwise the following lines up to
    the closing paren, bounded by ``_MULTILINE_LOOKAHEAD``.
    """
    line = lines[i]
    tail = line[match.end(1):]
    if ")" in tail:
        return match.group(2)
    parts = [match.group(2)]
    for j in range(i + 1, min(i + 1 + _MULTILINE_LOOKAHEAD, len(lines))):
        parts.append(lines[j])
        if ")" in lines[j]:
            break
    return "\n".join(parts)


def _unscoped_calls():
    """(file, lineno, tool, args) for every scope-required call lacking scope."""
    out = []
    for rel, text in scan_files():
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if _OPT_OUT in line:
                continue
            if i > 0 and _OPT_OUT in lines[i - 1]:
                continue
            for match in _CALL.finditer(line):
                tool = match.group(1)
                if tool not in SCOPE_REQUIRED:
                    continue
                args = _arg_window(lines, i, match)
                if "project" in args:
                    continue
                out.append((rel, i + 1, tool, args.strip().replace("\n", " ⏎ ")))
    return out


class TestNoUnscopedRetrievalCall(unittest.TestCase):
    def test_no_artefact_teaches_an_unscoped_retrieval_call(self):
        offenders = _unscoped_calls()
        detail = "\n".join(
            f"  {rel}:{ln}  {tool}({args})" for rel, ln, tool, args in offenders
        )
        self.assertEqual(
            offenders, [],
            "These call examples omit project=/projects= and return HTTP 422 "
            "SCOPE_UNRESOLVED against ragtools >=3.0.0:\n" + detail,
        )

    def test_the_gate_can_actually_see_the_baseline_defect(self):
        """Negative control for the detector itself.

        A scanner that matches nothing passes every tree, including a broken
        one. Against the baseline this asserts the defect IS found; against the
        live tree it asserts the opt-out marker still works, so the detector is
        never silently disabled.
        """
        if is_baseline():
            self.assertTrue(
                _unscoped_calls(),
                "Running against the v0.17.0 baseline but found no unscoped "
                "call — the detector has stopped working.",
            )
        else:
            sample = "search_knowledge_base(query=x)"
            self.assertIsNotNone(
                _CALL.search(sample), "the call regex no longer matches a bare call"
            )


class TestManagedBlockContract(unittest.TestCase):
    """The CLAUDE.md block is spliced by marker; its version and shape are the
    contract that lets `/config claude-md install` upgrade an existing user."""

    def _rule(self) -> str:
        return read("rules/claude-md-retrieval-rule.md")

    def test_marker_version_is_at_least_0_6_0(self):
        text = self._rule()
        m = re.search(r"<!-- rag-plugin:retrieval-rule:begin v=(\d+)\.(\d+)\.(\d+) -->", text)
        if m is None:
            self.fail("no begin marker with a parseable version")
        version = tuple(int(g) for g in m.groups())
        self.assertGreaterEqual(
            version, (0, 6, 0),
            f"managed block is v{'.'.join(map(str, version))}; WP-1 ships v0.6.0 "
            "so /config claude-md install upgrades existing users",
        )

    def test_block_states_that_scope_is_mandatory(self):
        text = self._rule()
        self.assertIn(
            "SCOPE_UNRESOLVED", text,
            "the block must name the error Claude will actually receive",
        )

    @staticmethod
    def _managed_block(text: str) -> str:
        """The block that actually gets injected.

        The rule file contains TWO begin/end pairs: a one-line illustration in
        the "How it is managed" section, and the real block under "## The block
        (verbatim…)". A non-greedy match finds the illustration first and
        reports a 1-line body — which made an earlier version of the
        line-budget assertion pass against anything. Take the longest pair.
        """
        bodies = re.findall(
            r"<!-- rag-plugin:retrieval-rule:begin[^>]*-->\n(.*?)\n<!-- rag-plugin:retrieval-rule:end -->",
            text, re.DOTALL,
        )
        return max(bodies, key=len) if bodies else ""

    def test_block_extraction_finds_the_real_block_not_the_illustration(self):
        """Guard for the assertion below. Without it, a 1-line match makes
        every budget check vacuous."""
        body = self._managed_block(self._rule())
        self.assertGreater(
            len(body.splitlines()), 10,
            "extracted block is implausibly short — the extractor is matching "
            "the illustrative marker pair, not the injected block",
        )
        self.assertIn("### 0.", body, "extracted block is not Section 0")

    def test_block_is_shorter_than_the_block_it_replaces(self):
        """Context budget. The v0.4.0 block installed on disk is 54 lines of
        content; the shipped v0.5.0 asset is 66. Depth belongs in the skill.
        """
        body_lines = self._managed_block(self._rule()).splitlines()
        self.assertLessEqual(
            len(body_lines), 52,
            f"managed block is {len(body_lines)} lines; it loads on every prompt "
            "in every session — move depth into the ragtools-retrieval skill",
        )

    def test_operational_override_is_preserved(self):
        """Section 0a is D-027's fix for the hook's inability to tell a
        knowledge question from 'what is listening on port X'. It must survive
        every rewrite of Section 0."""
        text = self._rule()
        self.assertIn("0a.", text, "Section 0a was dropped")
        for phrase in (
            "How do I start / stop / restart X?",
            "What's running / listening / scheduled?",
            "the question is about the user's own machine state",
        ):
            self.assertIn(
                phrase, text,
                f"Section 0a lost a load-bearing line: {phrase!r}",
            )


class TestHookReminderText(unittest.TestCase):
    def test_injected_reminder_shows_a_scoped_call(self):
        """The hook's reminder is injected verbatim into Claude's context. If
        it shows an unscoped call, it teaches the failing call at the exact
        moment Claude is deciding what to do."""
        for rel in ("hooks/context_inject.py", "hooks/prompt_retrieval_reminder.py"):
            text = read(rel)
            if not text:
                continue
            if "search_knowledge_base(" not in text:
                continue
            for line in text.splitlines():
                if "search_knowledge_base(" in line and _OPT_OUT not in line:
                    self.assertIn(
                        "project", line,
                        f"{rel}: injected reminder shows an unscoped call: {line.strip()!r}",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
