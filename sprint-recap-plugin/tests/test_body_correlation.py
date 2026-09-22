#!/usr/bin/env python3
"""Work-item references in the commit BODY must correlate.

A team whose subjects are prose ("[ADD] recovery: a queue whose resolutions
actually happen") and whose references live in the body ("Closes #33724
#33727") was invisible to subject-plus-refs matching: measured on a real
sprint, 0 commits carried an ID in the subject and 49 carried one only in the
body, hiding 111 distinct work items.

Body matching is deliberately EXPLICIT-ONLY. Branch-style bare numbers are
right for a ref like `feature/33724-recovery`, but in free prose a bare number
is a version, a count, a port or an HTTP status far more often than a work
item -- the same false-positive class that once turned "serve a favicon instead
of a 404" into work item 404.

    python tests/test_body_correlation.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import collect_evidence  # noqa: E402


class Args:
    since = "2026-09-14"
    until = "2026-09-25"
    author = None


def run(*cmd, cwd):
    subprocess.run(cmd, cwd=str(cwd), check=True,
                   capture_output=True, text=True)


class BodyCorrelationTests(unittest.TestCase):
    """Driven through collect_git against a real throwaway repo."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name) / "repo"
        cls.repo.mkdir()
        run("git", "init", "-q", "-b", "main", cwd=cls.repo)
        run("git", "config", "user.email", "t@example.test", cwd=cls.repo)
        run("git", "config", "user.name", "tester", cwd=cls.repo)

        def commit(fname, message):
            (cls.repo / fname).write_text("x\n", encoding="utf-8")
            run("git", "add", fname, cwd=cls.repo)
            run("git", "commit", "-q", "--date=2026-09-17T10:00:00",
                "-m", message, cwd=cls.repo)

        # the real-world shape: prose subject, references in the body
        commit("recovery.ts",
               "[ADD] recovery: a queue whose resolutions actually happen\n"
               "\n"
               "Long explanation over several lines, with a blank line in it.\n"
               "\n"
               "Closes #33724 #33727 #33730\n")
        # subject-only reference still works
        commit("export.ts", "[FIX] donors: export #23923")
        # a bare number in prose must NOT become a work item
        commit("favicon.ts",
               "[FIX] web: serve a favicon instead of a 404 on every page\n"
               "\n"
               "Ports 3000 and 8080 both showed it. Took 2 attempts.\n")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _commits(self):
        commits, notes = collect_evidence.collect_git([self.repo], Args())
        return {c["subject"].split(":")[0]: c for c in commits}, notes

    def test_body_references_are_collected(self):
        by, _ = self._commits()
        got = by["[ADD] recovery"]["work_items"]
        self.assertEqual(got, ["33724", "33727", "33730"])

    def test_subject_reference_still_works(self):
        by, _ = self._commits()
        self.assertIn("23923", by["[FIX] donors"]["work_items"])

    def test_bare_numbers_in_prose_are_not_work_items(self):
        """The 404 / port / count false-positive class."""
        by, _ = self._commits()
        got = by["[FIX] web"]["work_items"]
        for noise in ("404", "3000", "8080"):
            self.assertNotIn(noise, got, f"{noise} is not a work item")

    def test_note_reports_body_only_matches(self):
        """Per-source honesty: say how much came from a body reference."""
        _, notes = self._commits()
        self.assertTrue(
            any("body reference only" in n for n in notes),
            f"expected a body-only count in {notes}",
        )

    def test_files_still_parse_alongside_bodies(self):
        """The second log pass must not disturb --name-only parsing."""
        by, _ = self._commits()
        self.assertEqual(by["[ADD] recovery"]["files"], ["recovery.ts"])
        self.assertEqual(by["[ADD] recovery"]["file_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
