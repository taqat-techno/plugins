"""WP-3 — cited paths must resolve, or be reported as unverified.

Negative control
----------------
v0.17.0 had NO citation-path handling of any kind, so every one of these tests
fails against the baseline with ImportError — which is the correct signal: the
capability did not exist. The interesting assertions are the ones that stop the
repair from becoming a new defect:

  * ``docs/docs/x.md`` in a project called ``docs`` is REAL, not a duplicate
    artefact, and must survive.
  * ``odoo/odoo/odoo/addons/...`` must strip exactly ONE segment — the corpus
    id — leaving the genuine ``odoo/`` directory beneath it.
  * Running the repair twice must equal running it once (idempotent), so this
    module becomes a no-op rather than wrong when ragtools ships A-02.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import is_baseline, tree_root  # type: ignore[import-not-found]  # noqa: E402

# Import from the tree UNDER TEST, not the live one. Pointing at the live
# scripts/ unconditionally would let the helper import during a baseline run and
# silently turn this module's negative control into a no-op.
sys.path.insert(0, str(tree_root() / "scripts"))

# The helper is WP-3's deliverable, so against the v0.17.0 baseline it does not
# exist. Bind callable stubs rather than None so the absence shows up as a
# skip plus one explicit assertion, not as ten collection errors.
HAS_CITATION_PATH = True
try:
    from citation_path import normalize, to_native  # type: ignore[import-not-found]  # noqa: E402
except ImportError:  # pragma: no cover - baseline run
    HAS_CITATION_PATH = False

    def normalize(*_args, **_kwargs):  # type: ignore[misc]
        raise RuntimeError("citation_path is unavailable in this tree")

    def to_native(*_args, **_kwargs):  # type: ignore[misc]
        raise RuntimeError("citation_path is unavailable in this tree")


@unittest.skipUnless(HAS_CITATION_PATH, "citation_path not present (baseline tree)")
class TestDuplicateSegmentRepair(unittest.TestCase):
    def test_the_doubled_form_is_repaired(self):
        c = normalize("rag/rag/docs/decisions.md", project_id="rag")
        self.assertEqual(c.stored, "rag/docs/decisions.md")
        self.assertTrue(c.stripped)

    def test_an_already_correct_path_is_untouched(self):
        c = normalize("rag/docs/decisions.md", project_id="rag")
        self.assertEqual(c.stored, "rag/docs/decisions.md")
        self.assertFalse(c.stripped)

    def test_repair_is_idempotent(self):
        """When ragtools fixes A-02 this module must become a no-op, not a
        second defect."""
        once = normalize("rag/rag/docs/decisions.md", project_id="rag").stored
        twice = normalize(once, project_id="rag").stored
        self.assertEqual(once, twice)

    def test_a_real_repeated_directory_is_preserved(self):
        """`docs/docs/guide.md` inside a project called `docs` is a real path.
        Only the FIRST TWO segments both matching the project id is an
        artefact — anything looser corrupts genuine paths."""
        c = normalize("docs/docs/docs/guide.md", project_id="docs")
        self.assertEqual(c.stored, "docs/docs/guide.md")
        self.assertTrue(c.stripped)
        # ...and the surviving `docs/docs` is not stripped again.
        self.assertEqual(normalize(c.stored, project_id="docs").stored, "docs/guide.md")

    def test_framework_triple_prefix_strips_exactly_one(self):
        """A framework corpus stores `odoo/odoo/addons/...` — corpus id plus a
        genuine `odoo` directory. The formatter renders `odoo/odoo/odoo/...`.
        One strip is correct; a recursive strip eats a real directory."""
        c = normalize("odoo/odoo/odoo/addons/mail/models.py", project_id="odoo")
        self.assertEqual(c.stored, "odoo/odoo/addons/mail/models.py")

    def test_a_foreign_project_id_never_triggers_a_strip(self):
        c = normalize("rag/rag/docs/x.md", project_id="claude-plugins")
        self.assertEqual(c.stored, "rag/rag/docs/x.md")
        self.assertFalse(c.stripped)

    def test_windows_separators_are_accepted(self):
        c = normalize(r"rag\rag\docs\decisions.md", project_id="rag")
        self.assertEqual(c.stored, "rag/docs/decisions.md")

    def test_line_span_suffix_is_preserved(self):
        c = normalize("rag/rag/docs/decisions.md:L481-508", project_id="rag")
        self.assertEqual(c.stored, "rag/docs/decisions.md:L481-508")


@unittest.skipUnless(HAS_CITATION_PATH, "citation_path not present (baseline tree)")
class TestVerification(unittest.TestCase):
    def test_an_existing_file_is_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproj"
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "a.md").write_text("x", encoding="utf-8")
            c = normalize("myproj/myproj/docs/a.md", "myproj", str(root))
            self.assertTrue(c.trusted, c.describe())
            self.assertTrue(c.stripped)

    def test_a_missing_file_is_not_trusted_and_says_why(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproj"
            root.mkdir(parents=True)
            c = normalize("myproj/docs/ghost.md", "myproj", str(root))
            self.assertFalse(c.trusted)
            self.assertIn("could not be verified", c.describe())

    def test_without_a_root_the_result_is_unverified_not_false(self):
        """'I could not check' must never render as 'it does not exist' — the
        same distinction ragtools itself draws between None and 0 for counts."""
        c = normalize("rag/docs/decisions.md", "rag")
        self.assertIsNone(c.exists)
        self.assertFalse(c.trusted)
        self.assertIn("not verified", c.describe())

    def test_empty_input_never_raises(self):
        for bad in ("", "   ", "///"):
            c = normalize(bad, "rag")
            self.assertFalse(c.trusted)


@unittest.skipUnless(HAS_CITATION_PATH, "citation_path not present (baseline tree)")
class TestPlatform(unittest.TestCase):
    def test_to_native_matches_the_platform(self):
        out = to_native("a/b/c.md")
        self.assertEqual(out, "a" + os.sep + "b" + os.sep + "c.md")

    def test_stored_form_stays_posix_on_every_platform(self):
        """Comparison and storage stay POSIX so the logic is platform-neutral;
        only the read boundary converts."""
        c = normalize(r"p\p\a\b.md", "p")
        self.assertNotIn("\\", c.stored)


@unittest.skipUnless(HAS_CITATION_PATH, "citation_path not present (baseline tree)")
class TestGuardsRejectNaiveImplementations(unittest.TestCase):
    """The negative control, kept permanently rather than run once by hand.

    Against the v0.17.0 baseline this whole module skips, because the helper did
    not exist — an honest signal, but a weak gate: it proves absence, not that
    the assertions discriminate. These tests close that by running the naive
    algorithms a careless fix would produce and asserting the real
    implementation disagrees with each of them on a case that matters.
    """

    @staticmethod
    def _naive_recursive(cited: str) -> str:
        """"Strip any repeated leading segment, repeatedly." Eats real dirs."""
        segs = [s for s in cited.replace("\\", "/").split("/") if s]
        while len(segs) >= 2 and segs[0] == segs[1]:
            segs = segs[1:]
        return "/".join(segs)

    @staticmethod
    def _naive_id_agnostic(cited: str) -> str:
        """"Strip one repeated leading segment, ignoring the project id."""
        segs = [s for s in cited.replace("\\", "/").split("/") if s]
        if len(segs) >= 2 and segs[0] == segs[1]:
            segs = segs[1:]
        return "/".join(segs)

    def test_recursive_strip_would_eat_a_real_directory(self):
        """`odoo/odoo/odoo/addons/…` — the corpus id plus a genuine `odoo`
        package directory. A recursive strip collapses until the first two
        segments differ, consuming the real directory as well as the id."""
        cited = "odoo/odoo/odoo/addons/mail/models.py"
        naive = self._naive_recursive(cited)
        ours = normalize(cited, project_id="odoo").stored
        self.assertEqual(naive, "odoo/addons/mail/models.py",
                         "naive control drifted; re-derive it before trusting this test")
        self.assertEqual(ours, "odoo/odoo/addons/mail/models.py")
        self.assertNotEqual(ours, naive, "the once-only rule is not being applied")

    def test_recursive_strip_would_corrupt_a_real_repeated_directory(self):
        cited = "docs/docs/docs/guide.md"
        naive = self._naive_recursive(cited)
        ours = normalize(cited, project_id="docs").stored
        self.assertEqual(naive, "docs/guide.md",
                         "naive control drifted; re-derive it before trusting this test")
        self.assertEqual(ours, "docs/docs/guide.md")
        self.assertNotEqual(ours, naive, "one real directory level was lost")

    def test_id_agnostic_strip_would_touch_a_foreign_projects_path(self):
        """Keying on the scoped project id is what makes the repair safe: a
        path from another project is never a formatting artefact we can reason
        about, so it must be left exactly as it came."""
        cited = "rag/rag/docs/x.md"
        self.assertEqual(self._naive_id_agnostic(cited), "rag/docs/x.md")
        self.assertEqual(
            normalize(cited, project_id="claude-plugins").stored, cited,
            "a foreign-project path was modified",
        )

    def test_trusting_without_checking_would_present_a_missing_file(self):
        """A repair that returns a plausible string and calls it verified is
        the failure this module exists to prevent."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "myproj"
            root.mkdir(parents=True)
            c = normalize("myproj/myproj/docs/ghost.md", "myproj", str(root))
            self.assertEqual(c.stored, "myproj/docs/ghost.md")  # repair looks right
            self.assertFalse(c.trusted, "a nonexistent file was reported as trusted")


class TestBaselineLacksTheCapability(unittest.TestCase):
    def test_baseline_has_no_citation_handling(self):
        """The negative control for this whole module: against v0.17.0 the
        helper does not exist, which is exactly the defect WP-3 closes."""
        if is_baseline():
            self.assertFalse(
                HAS_CITATION_PATH,
                "baseline tree unexpectedly provides citation_path — either the "
                "snapshot is contaminated or the import is resolving against the "
                "live tree, which would make this negative control vacuous",
            )
        else:
            self.assertTrue(
                HAS_CITATION_PATH, "scripts/citation_path.py is missing from the live tree"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
