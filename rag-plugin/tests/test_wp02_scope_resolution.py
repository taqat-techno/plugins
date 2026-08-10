"""WP-2 — scope resolution must be deterministic, and ambiguity must surface.

The regression this module exists for
-------------------------------------
The v0.17.0 engine scored every descendant match ``200 + len(path)``. Measured
live from a ``claude_plugins`` workspace root, that ranked:

    my-plugins      …/claude_plugins/my_plugins   score 241   <- selected
    claude-plugins  …/claude_plugins/plugins      score 238

so the plugin's own repository resolved to the wrong project, decided by three
characters of path string. Its tie-break needed ``abs(len0-len1) < 3``; the
difference was exactly 3, so the guard never fired.

``TestRV4Regression`` reproduces that fixture exactly. It is written against
synthetic paths rather than the live service so it keeps failing for the right
reason after someone renames a project.

The deeper point is not the off-by-one: ranking descendants by path length is
meaningless. When the cwd is a parent of several project roots, none of them is
"more correct". ``TestRelationPrecedence`` pins that separation.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _tree import PLUGIN_ROOT  # type: ignore[import-not-found]  # noqa: E402

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from scope_resolve import (  # type: ignore[import-not-found]  # noqa: E402
    ANCESTOR,
    DESCENDANT,
    EXACT,
    ProjectMatch,
    ScopeDecision,
    invalidate_cache,
    norm,
    read_cache,
    resolve,
    write_cache,
)


def proj(pid: str, path: str, mode: str = "docs", state: str = "indexed",
         enabled: bool = True) -> dict:
    return {"id": pid, "path": path, "mode": mode, "state": state, "enabled": enabled}


class TestRV4Regression(unittest.TestCase):
    """The exact live case that exposed the defect."""

    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.root = Path(tmp).resolve()
        # Recreate for real so norm()'s resolve() has something to resolve.
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        self.workspace = self.root / "claude_plugins"
        (self.workspace / "plugins").mkdir(parents=True)
        (self.workspace / "my_plugins").mkdir(parents=True)
        self.projects = [
            proj("claude-plugins", str(self.workspace / "plugins")),
            proj("my-plugins", str(self.workspace / "my_plugins")),
        ]

    def tearDown(self):
        self._tmp.cleanup()

    def test_two_descendants_are_ambiguous_not_silently_ranked(self):
        d = resolve(self.workspace, self.projects)
        self.assertTrue(
            d.ambiguous,
            f"expected ambiguity, got {d.project_id!r} — the old engine picked "
            "the longer path name and was wrong",
        )
        self.assertIsNone(d.project)
        self.assertEqual(sorted(d.union_ids), ["claude-plugins", "my-plugins"])

    def test_the_three_character_path_difference_is_not_a_tie_break(self):
        """`my_plugins` is exactly 3 characters longer than `plugins`; the old
        guard required a difference of *less than* 3 to call it ambiguous."""
        a = len(str(self.workspace / "my_plugins"))
        b = len(str(self.workspace / "plugins"))
        self.assertEqual(a - b, 3, "fixture drifted; re-derive before trusting")
        self.assertTrue(resolve(self.workspace, self.projects).ambiguous)

    def test_descendants_carry_equal_scores(self):
        """Positively pin that length no longer enters descendant scoring."""
        d = resolve(self.workspace, self.projects)
        scores = {c.score for c in d.candidates}
        self.assertEqual(len(scores), 1, f"descendant scores differ: {scores}")

    def test_a_union_search_is_offered_as_the_honest_answer(self):
        """ragtools supports projects=[a,b] natively, so 'both' beats guessing."""
        d = resolve(self.workspace, self.projects)
        self.assertEqual(len(d.union_ids), 2)
        self.assertIn("union", d.describe())


class TestTheOldEngineActuallyGetsThisWrong(unittest.TestCase):
    """Negative control against the real pre-fix code, kept permanently.

    Loads ``tests/baseline_v0.17.0/scripts/project_focus.py`` — the shipped
    v0.17.0 engine — and runs the same fixture through it. If this ever stops
    demonstrating the defect, either the snapshot has been contaminated or the
    fixture no longer reproduces the case, and the WP-2 tests above stop being
    evidence of anything.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.workspace = root / "claude_plugins"
        (self.workspace / "plugins").mkdir(parents=True)
        (self.workspace / "my_plugins").mkdir(parents=True)
        self.projects = [
            proj("claude-plugins", str(self.workspace / "plugins")),
            proj("my-plugins", str(self.workspace / "my_plugins")),
        ]

    def tearDown(self):
        self._tmp.cleanup()
        sys.modules.pop("baseline_project_focus", None)

    def _load_old_engine(self):
        import importlib.util

        path = PLUGIN_ROOT / "tests" / "baseline_v0.17.0" / "scripts" / "project_focus.py"
        if not path.is_file():
            self.skipTest("baseline snapshot missing")
        spec = importlib.util.spec_from_file_location("baseline_project_focus", path)
        if spec is None or spec.loader is None:
            self.skipTest("could not load the baseline engine")
        module = importlib.util.module_from_spec(spec)
        sys.modules["baseline_project_focus"] = module
        spec.loader.exec_module(module)
        return module

    def test_v0_17_0_silently_selects_the_wrong_project(self):
        old = self._load_old_engine()
        best, ranked = old.match_project(self.workspace, self.projects)
        self.assertIsNotNone(
            best,
            "the old engine was expected to pick something (wrongly); it "
            "returned ambiguous, so this fixture no longer reproduces the bug",
        )
        picked = old._project_name(best.project)
        self.assertEqual(
            picked, "my-plugins",
            f"old engine picked {picked!r}; the recorded defect selected "
            "'my-plugins' purely because its path string is longer",
        )
        self.assertEqual(len(ranked), 2, "both projects should have been candidates")

    def test_the_new_engine_refuses_the_same_input(self):
        """Same fixture, opposite outcome — which is the whole point."""
        self.assertTrue(resolve(self.workspace, self.projects).ambiguous)


class TestRelationPrecedence(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.mono = root / "mono"
        self.inner = self.mono / "svc"
        self.deep = self.inner / "api"
        self.deep.mkdir(parents=True)
        self.root = root

    def tearDown(self):
        self._tmp.cleanup()

    def test_exact_match_wins_over_everything(self):
        projects = [
            proj("outer", str(self.mono)),
            proj("inner", str(self.inner)),
        ]
        d = resolve(self.inner, projects)
        self.assertEqual(d.project_id, "inner")
        self.assertEqual(d.project.method, EXACT)  # type: ignore[union-attr]

    def test_ancestor_beats_descendant(self):
        """cwd inside `outer`, and `deep` inside cwd. Containment wins:
        the project you are working *in* beats one that merely lives below."""
        projects = [
            proj("outer", str(self.mono)),
            proj("deep", str(self.deep)),
        ]
        d = resolve(self.inner, projects)
        self.assertEqual(d.project_id, "outer")
        self.assertEqual(d.project.method, ANCESTOR)  # type: ignore[union-attr]

    def test_deepest_ancestor_wins(self):
        """Here length IS meaningful — a deeper containing project is more
        specific about the directory you are actually in."""
        projects = [
            proj("outer", str(self.mono)),
            proj("mid", str(self.inner)),
        ]
        d = resolve(self.deep, projects)
        self.assertEqual(d.project_id, "mid")

    def test_single_descendant_resolves_cleanly(self):
        projects = [proj("only", str(self.inner))]
        d = resolve(self.mono, projects)
        self.assertFalse(d.ambiguous)
        self.assertEqual(d.project_id, "only")
        self.assertEqual(d.project.method, DESCENDANT)  # type: ignore[union-attr]

    def test_no_match_is_reported_not_guessed(self):
        projects = [proj("elsewhere", str(self.root / "unrelated"))]
        d = resolve(self.mono, projects)
        self.assertIsNone(d.project)
        self.assertFalse(d.ambiguous)
        self.assertIn("no configured project", d.reason)


class TestModeAndStateArePropagated(unittest.TestCase):
    """The two fields the pre-WP-2 fetch path never retrieved at all."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        (self.root / "p").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_docs_mode_is_visible_to_the_caller(self):
        d = resolve(self.root / "p", [proj("p", str(self.root / "p"), mode="docs")])
        self.assertIsNotNone(d.project)
        self.assertFalse(d.project.indexes_code)  # type: ignore[union-attr]

    def test_general_mode_indexes_code(self):
        d = resolve(self.root / "p", [proj("p", str(self.root / "p"), mode="general")])
        self.assertTrue(d.project.indexes_code)  # type: ignore[union-attr]

    def test_stale_state_is_visible(self):
        d = resolve(self.root / "p",
                    [proj("p", str(self.root / "p"), state="indexed_stale")])
        self.assertTrue(d.project.stale)  # type: ignore[union-attr]

    def test_describe_mentions_mode(self):
        d = resolve(self.root / "p", [proj("p", str(self.root / "p"))])
        self.assertIn("mode=docs", d.describe())


class TestNameOverride(unittest.TestCase):
    PROJECTS = [proj("alpha", "/nowhere/a"), proj("alpha-beta", "/nowhere/b")]

    def test_exact_name_wins_over_partial(self):
        d = resolve(Path("/tmp"), self.PROJECTS, manual_name="alpha")
        self.assertEqual(d.project_id, "alpha")
        self.assertEqual(d.source, "override")

    def test_ambiguous_partial_name_is_surfaced(self):
        d = resolve(Path("/tmp"), self.PROJECTS, manual_name="alph")
        self.assertTrue(d.ambiguous)
        self.assertEqual(len(d.union_ids), 2)

    def test_unknown_name_resolves_to_nothing(self):
        d = resolve(Path("/tmp"), self.PROJECTS, manual_name="nope")
        self.assertIsNone(d.project)


class TestPathNormalisation(unittest.TestCase):
    def test_separators_are_unified(self):
        self.assertEqual(norm(r"C:\a\b"), norm("C:/a/b"))

    def test_trailing_slash_is_irrelevant(self):
        self.assertEqual(norm("/a/b/"), norm("/a/b"))

    def test_case_folding_is_windows_only(self):
        folded = norm("/A/B") == norm("/a/b")
        self.assertEqual(
            folded, os.name == "nt",
            "case folding must follow the platform: merging distinct paths on "
            "POSIX is as wrong as failing to merge them on Windows",
        )

    def test_empty_input_is_safe(self):
        self.assertEqual(norm(""), "")


class TestCache(unittest.TestCase):
    KEY = "unit-test-workspace-key"

    def tearDown(self):
        invalidate_cache(self.KEY)

    def test_roundtrip(self):
        d = ScopeDecision(
            project=ProjectMatch("p", "/x", EXACT, 1000, "general", "indexed"),
            candidates=[], source="resolved", reason="test",
        )
        self.assertTrue(write_cache(self.KEY, d, service={"bound_port": 21420}))
        entry = read_cache(self.KEY)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["project"]["project_id"], "p")  # type: ignore[index]
        self.assertEqual(entry["service"]["bound_port"], 21420)  # type: ignore[index]

    def test_expiry(self):
        d = ScopeDecision(project=ProjectMatch("p", "/x", EXACT, 1000))
        write_cache(self.KEY, d, now=1000.0)
        self.assertIsNone(read_cache(self.KEY, ttl=60, now=2000.0))
        self.assertIsNotNone(read_cache(self.KEY, ttl=5000, now=2000.0))

    def test_unknown_workspace_is_a_miss_not_an_error(self):
        self.assertIsNone(read_cache("never-written-" + self.KEY))

    def test_reads_never_raise(self):
        """A hook that dies on a corrupt cache is worse than one that
        re-resolves."""
        import scope_resolve as sr  # type: ignore[import-not-found]

        original = sr.CACHE_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                bad = Path(tmp) / "corrupt.json"
                bad.write_text("{not json", encoding="utf-8")
                sr.CACHE_FILE = bad
                self.assertIsNone(sr.read_cache(self.KEY))
        finally:
            sr.CACHE_FILE = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
