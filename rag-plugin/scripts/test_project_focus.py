#!/usr/bin/env python3
"""Tests for rag-plugin /project-focus v0.10.0 (per-workspace + explicit global).

Stdlib-only (unittest). Run via:

    python rag-plugin/scripts/test_project_focus.py

Covers the v2 schema, v1->v2 migration, workspace-keyed CRUD, the --global
flag, clear variants, and the project_focus_inject.py hook's effective-focus
resolution (workspace > global > none) plus the neutral other-workspace
notice.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from typing import Any, Optional


HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent
SCRIPT = HERE / "project_focus.py"
HOOK = PLUGIN_ROOT / "hooks" / "project_focus_inject.py"


def _load_pf():
    """Load project_focus.py as a module each time, to pick up STATE_FILE patches.

    Must register the module in sys.modules BEFORE exec_module() so that
    @dataclass can resolve the class's __module__ during type introspection.
    """
    name = "project_focus_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


@contextmanager
def temp_state_dir():
    """Run the test with project_focus.py STATE_DIR/STATE_FILE pointed at a temp dir.

    Returns the temp Path.
    """
    pf = _load_pf()
    saved_dir, saved_file = pf.STATE_DIR, pf.STATE_FILE
    with tempfile.TemporaryDirectory() as td:
        new_dir = Path(td) / "state"
        new_dir.mkdir(parents=True, exist_ok=True)
        pf.STATE_DIR = new_dir
        pf.STATE_FILE = new_dir / "project-focus.json"
        try:
            yield pf, new_dir
        finally:
            pf.STATE_DIR, pf.STATE_FILE = saved_dir, saved_file


def _write_v1(state_file: Path, **fields: Any) -> dict[str, Any]:
    record = {
        "enabled": True,
        "mode": "strict",
        "project_id": "alpha",
        "project_name": "alpha",
        "project_path": str(Path.cwd()),
        "project_paths": [str(Path.cwd())],
        "match_method": "exact-path",
        "cwd_at_set": str(Path.cwd()),
        "git_root_at_set": str(Path.cwd()),
        "service_reachable": True,
        "created_at": "2026-04-30T00:00:00Z",
        "source": "/project-focus (auto)",
        "engine_version": "0.9.0",
    }
    record.update(fields)
    state_file.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


# ============================================================================
# Schema migration
# ============================================================================


class TestMigration(unittest.TestCase):

    def test_v1_with_git_root_at_set_migrates_to_workspaces(self):
        with temp_state_dir() as (pf, sdir):
            with tempfile.TemporaryDirectory() as ws:
                ws_path = Path(ws).resolve()
                _write_v1(pf.STATE_FILE,
                          git_root_at_set=str(ws_path),
                          cwd_at_set=str(ws_path))
                bundle = pf.read_state()
                self.assertEqual(bundle.get("schema_version"), 2)
                key = pf._norm(str(ws_path))
                self.assertIn(key, bundle["workspaces"])
                self.assertEqual(bundle["workspaces"][key]["scope"], "workspace")
                self.assertEqual(bundle["workspaces"][key]["workspace_key"], key)
                self.assertIsNone(bundle["global"])

    def test_v1_falls_back_to_cwd_at_set_when_git_empty(self):
        with temp_state_dir() as (pf, sdir):
            with tempfile.TemporaryDirectory() as ws:
                ws_path = Path(ws).resolve()
                _write_v1(pf.STATE_FILE,
                          git_root_at_set="",
                          cwd_at_set=str(ws_path))
                bundle = pf.read_state()
                key = pf._norm(str(ws_path))
                self.assertIn(key, bundle["workspaces"])

    def test_v1_unsafe_no_paths_disables_focus(self):
        with temp_state_dir() as (pf, sdir):
            _write_v1(pf.STATE_FILE, git_root_at_set="", cwd_at_set="")
            bundle = pf.read_state()
            self.assertEqual(bundle.get("schema_version"), 2)
            self.assertEqual(bundle["workspaces"], {})
            self.assertIsNone(bundle["global"])
            self.assertTrue(any("disabled" in line.lower()
                                for line in bundle.get("migration_log", [])))

    def test_v1_unsafe_path_does_not_exist_disables_focus(self):
        with temp_state_dir() as (pf, sdir):
            bogus = "/no/such/dir/at/all/here"
            _write_v1(pf.STATE_FILE,
                      git_root_at_set=bogus, cwd_at_set=bogus)
            bundle = pf.read_state()
            self.assertEqual(bundle["workspaces"], {})
            self.assertIsNone(bundle["global"])

    def test_v1_to_v2_creates_backup_once(self):
        with temp_state_dir() as (pf, sdir):
            with tempfile.TemporaryDirectory() as ws:
                _write_v1(pf.STATE_FILE,
                          git_root_at_set=str(Path(ws).resolve()),
                          cwd_at_set=str(Path(ws).resolve()))
                pf.read_state()  # triggers migration
                bak = sdir / "project-focus.v1.bak.json"
                self.assertTrue(bak.exists())
                first_bytes = bak.read_bytes()
                # Trigger a second migration by re-creating a v1 file with
                # different content; backup must NOT be overwritten.
                _write_v1(pf.STATE_FILE,
                          project_name="DIFFERENT",
                          git_root_at_set=str(Path(ws).resolve()),
                          cwd_at_set=str(Path(ws).resolve()))
                pf.read_state()
                self.assertEqual(bak.read_bytes(), first_bytes,
                                 "v1 backup must not be overwritten on a second migration")

    def test_v2_passthrough_no_remigration(self):
        with temp_state_dir() as (pf, sdir):
            v2 = {"schema_version": 2, "engine_version": "0.10.0",
                  "workspaces": {}, "global": None}
            pf.STATE_FILE.write_text(json.dumps(v2), encoding="utf-8")
            bundle = pf.read_state()
            self.assertEqual(bundle, v2)

    def test_no_state_file_returns_none(self):
        with temp_state_dir() as (pf, sdir):
            self.assertIsNone(pf.read_state())


# ============================================================================
# Workspace key normalization
# ============================================================================


class TestWorkspaceKey(unittest.TestCase):

    def test_norm_strips_trailing_slash(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            self.assertEqual(pf._norm(str(base) + "/"), pf._norm(str(base)))
            self.assertEqual(pf._norm(str(base) + "\\"), pf._norm(str(base)))

    def test_norm_lowercases_on_windows(self):
        pf = _load_pf()
        if os.name != "nt":
            self.skipTest("windows-only path normalization rule")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            up = pf._norm(str(base).upper())
            lo = pf._norm(str(base).lower())
            self.assertEqual(up, lo)

    def test_resolve_workspace_key_uses_git_root_when_present(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            (root / ".git").mkdir()
            sub = root / "deep" / "nested"
            sub.mkdir(parents=True)
            key = pf.resolve_workspace_key(sub)
            self.assertEqual(key, pf._norm(str(root)))

    def test_resolve_workspace_key_falls_back_to_cwd_when_no_git(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td).resolve()
            sub = root / "no_git_here"
            sub.mkdir()
            key = pf.resolve_workspace_key(sub)
            self.assertEqual(key, pf._norm(str(sub)))


# ============================================================================
# State CRUD: workspaces and global both writable independently
# ============================================================================


class TestSetGetClear(unittest.TestCase):

    def _empty_v2(self, pf):
        pf.write_state({
            "schema_version": 2,
            "engine_version": "0.10.0",
            "workspaces": {},
            "global": None,
        })

    def test_set_workspace_focus(self):
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            ws_key = pf._norm("/some/workspace/A")
            record = {"enabled": True, "scope": "workspace",
                      "workspace_key": ws_key, "project_name": "alpha"}
            bundle = pf.read_state()
            bundle["workspaces"][ws_key] = record
            pf.write_state(bundle)
            re_read = pf.read_state()
            self.assertIn(ws_key, re_read["workspaces"])
            self.assertEqual(re_read["workspaces"][ws_key]["project_name"], "alpha")

    def test_set_global_focus_does_not_touch_workspaces(self):
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            bundle = pf.read_state()
            ws_key = pf._norm("/some/workspace/A")
            bundle["workspaces"][ws_key] = {"enabled": True,
                                            "scope": "workspace",
                                            "project_name": "alpha"}
            bundle["global"] = {"enabled": True, "scope": "global",
                                "workspace_key": "",
                                "project_name": "royal-preps"}
            pf.write_state(bundle)
            re_read = pf.read_state()
            self.assertEqual(re_read["workspaces"][ws_key]["project_name"], "alpha")
            self.assertEqual(re_read["global"]["project_name"], "royal-preps")
            self.assertEqual(re_read["global"]["scope"], "global")

    def test_set_in_workspace_a_does_not_affect_workspace_b(self):
        # The regression test for the leak: the whole point of v0.10.0.
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            bundle = pf.read_state()
            key_a = pf._norm("/ws/a")
            key_b = pf._norm("/ws/b")
            bundle["workspaces"][key_a] = {"enabled": True,
                                           "scope": "workspace",
                                           "workspace_key": key_a,
                                           "project_name": "alpha"}
            pf.write_state(bundle)

            # Resolving for B must NOT return alpha.
            re_read = pf.read_state()
            self.assertIn(key_a, re_read["workspaces"])
            self.assertNotIn(key_b, re_read["workspaces"])

            # Effective focus resolver for B must yield NO effective focus
            # (this is the regression assertion — B does not inherit A's
            # focus). The source tag becomes "other-workspace-only" because
            # an enabled record exists for a different workspace; that tag
            # tells the hook to emit a neutral notice without leaking A's
            # project name.
            effective, source = pf.resolve_effective_focus(re_read, key_b)
            self.assertIsNone(effective)
            self.assertEqual(source, "other-workspace-only")

            # Effective focus resolver for A returns alpha as workspace.
            effective_a, source_a = pf.resolve_effective_focus(re_read, key_a)
            self.assertEqual(effective_a["project_name"], "alpha")
            self.assertEqual(source_a, "workspace")

    def test_clear_workspace_only(self):
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            bundle = pf.read_state()
            key = pf._norm("/ws/a")
            bundle["workspaces"][key] = {"enabled": True, "project_name": "x"}
            bundle["global"] = {"enabled": True, "project_name": "g"}
            pf.write_state(bundle)
            cleared = pf.clear_workspace(key)
            self.assertTrue(cleared)
            re_read = pf.read_state()
            self.assertNotIn(key, re_read["workspaces"])
            self.assertIsNotNone(re_read["global"])

    def test_clear_global_only(self):
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            bundle = pf.read_state()
            key = pf._norm("/ws/a")
            bundle["workspaces"][key] = {"enabled": True, "project_name": "x"}
            bundle["global"] = {"enabled": True, "project_name": "g"}
            pf.write_state(bundle)
            cleared = pf.clear_global()
            self.assertTrue(cleared)
            re_read = pf.read_state()
            self.assertIn(key, re_read["workspaces"])
            self.assertIsNone(re_read["global"])

    def test_clear_all_empties_both(self):
        with temp_state_dir() as (pf, sdir):
            self._empty_v2(pf)
            bundle = pf.read_state()
            key = pf._norm("/ws/a")
            bundle["workspaces"][key] = {"enabled": True, "project_name": "x"}
            bundle["global"] = {"enabled": True, "project_name": "g"}
            pf.write_state(bundle)
            pf.clear_all()
            re_read = pf.read_state()
            self.assertEqual(re_read["workspaces"], {})
            self.assertIsNone(re_read["global"])


# ============================================================================
# Effective focus resolver (workspace > global > none, with labeling)
# ============================================================================


class TestResolveEffectiveFocus(unittest.TestCase):

    def _bundle(self, workspaces=None, glob=None):
        return {"schema_version": 2, "engine_version": "0.10.0",
                "workspaces": workspaces or {}, "global": glob}

    def test_workspace_match_returns_workspace_source(self):
        pf = _load_pf()
        key = pf._norm("/ws/a")
        bundle = self._bundle(
            workspaces={key: {"enabled": True, "scope": "workspace",
                              "project_name": "alpha"}},
            glob={"enabled": True, "scope": "global", "project_name": "g"},
        )
        effective, source = pf.resolve_effective_focus(bundle, key)
        self.assertEqual(effective["project_name"], "alpha")
        self.assertEqual(source, "workspace")

    def test_no_workspace_falls_back_to_global(self):
        pf = _load_pf()
        bundle = self._bundle(
            workspaces={pf._norm("/ws/other"): {"enabled": True,
                                                 "project_name": "alpha"}},
            glob={"enabled": True, "scope": "global", "project_name": "g"},
        )
        effective, source = pf.resolve_effective_focus(bundle, pf._norm("/ws/here"))
        self.assertEqual(effective["project_name"], "g")
        self.assertEqual(source, "global")

    def test_no_workspace_no_global_returns_none(self):
        pf = _load_pf()
        bundle = self._bundle(
            workspaces={pf._norm("/ws/other"): {"enabled": True,
                                                 "project_name": "alpha"}},
        )
        effective, source = pf.resolve_effective_focus(bundle, pf._norm("/ws/here"))
        self.assertIsNone(effective)
        # Should signal that focus exists for OTHER workspaces, so the hook
        # can emit the neutral notice.
        self.assertEqual(source, "other-workspace-only")

    def test_disabled_workspace_record_treated_as_none(self):
        pf = _load_pf()
        key = pf._norm("/ws/a")
        bundle = self._bundle(
            workspaces={key: {"enabled": False, "project_name": "alpha"}},
        )
        effective, source = pf.resolve_effective_focus(bundle, key)
        self.assertIsNone(effective)
        self.assertEqual(source, "none")

    def test_disabled_global_treated_as_none(self):
        pf = _load_pf()
        bundle = self._bundle(
            glob={"enabled": False, "scope": "global", "project_name": "g"},
        )
        effective, source = pf.resolve_effective_focus(bundle, pf._norm("/ws/x"))
        self.assertIsNone(effective)
        self.assertEqual(source, "none")


# ============================================================================
# Hook: project_focus_inject.py reads v2 state, labels global, neutral notice
# ============================================================================


def _run_hook(state_file: Path, cwd: Path) -> dict[str, Any]:
    """Run the hook script as a subprocess. Return parsed JSON output (or {})."""
    env = os.environ.copy()
    env["RAG_PLUGIN_FOCUS_STATE_FILE"] = str(state_file)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input="{}",
        capture_output=True, text=True,
        timeout=10, cwd=str(cwd),
        env=env,
    )
    out = proc.stdout.strip()
    if not out:
        return {}
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"_raw": out, "_stderr": proc.stderr}


class TestHook(unittest.TestCase):

    def _empty_v2(self, state_file: Path):
        state_file.write_text(json.dumps({
            "schema_version": 2, "engine_version": "0.10.0",
            "workspaces": {}, "global": None}), encoding="utf-8")

    def test_silent_pass_when_no_state_file(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "no-such-file.json"
            cwd = Path(td)
            out = _run_hook(state, cwd)
            self.assertEqual(out, {})

    def test_silent_pass_when_empty_v2(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            self._empty_v2(state)
            out = _run_hook(state, Path(td))
            self.assertEqual(out, {})

    def test_workspace_focus_injected_when_cwd_matches(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td).resolve()
            state = ws / "state.json"
            key = pf._norm(str(ws))
            state.write_text(json.dumps({
                "schema_version": 2, "engine_version": "0.10.0",
                "workspaces": {key: {"enabled": True, "scope": "workspace",
                                     "workspace_key": key,
                                     "project_name": "alpha",
                                     "project_path": str(ws),
                                     "match_method": "exact-path"}},
                "global": None,
            }), encoding="utf-8")
            out = _run_hook(state, ws)
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("alpha", ctx)
            self.assertIn("project-focus", ctx.lower())
            # workspace focus should NOT carry the explicit-global label
            self.assertNotIn("EXPLICIT GLOBAL FOCUS", ctx)

    def test_global_focus_labeled_explicitly_when_used_as_fallback(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td).resolve()
            state = ws / "state.json"
            # No workspace focus for this cwd, only a global.
            state.write_text(json.dumps({
                "schema_version": 2, "engine_version": "0.10.0",
                "workspaces": {},
                "global": {"enabled": True, "scope": "global",
                           "workspace_key": "",
                           "project_name": "royal-preps",
                           "project_path": "",
                           "match_method": "manual"},
            }), encoding="utf-8")
            out = _run_hook(state, ws)
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            self.assertIn("royal-preps", ctx)
            # The injected text must clearly tell Claude this is global because
            # the user explicitly used --global, NOT because it matches cwd.
            self.assertIn("EXPLICIT GLOBAL FOCUS", ctx)
            self.assertIn("--global", ctx)

    def test_neutral_notice_when_other_workspace_has_focus_and_no_global(self):
        pf = _load_pf()
        with tempfile.TemporaryDirectory() as td:
            here = Path(td) / "here_ws"
            other = Path(td) / "other_ws"
            here.mkdir(); other.mkdir()
            here, other = here.resolve(), other.resolve()
            state = Path(td) / "state.json"
            state.write_text(json.dumps({
                "schema_version": 2, "engine_version": "0.10.0",
                "workspaces": {pf._norm(str(other)): {
                    "enabled": True, "scope": "workspace",
                    "workspace_key": pf._norm(str(other)),
                    "project_name": "secret-other",
                    "project_path": str(other)}},
                "global": None,
            }), encoding="utf-8")
            out = _run_hook(state, here)
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            # Must surface that focus exists for other workspaces.
            self.assertIn("another workspace", ctx.lower())
            # Must NOT leak the other project's name (could cause Claude to
            # use it as a project= filter).
            self.assertNotIn("secret-other", ctx)
            # Must explicitly tell the model not to apply foreign focus.
            self.assertIn("not applied here", ctx.lower())

    def test_silent_pass_on_malformed_state(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            state.write_text("not-json{", encoding="utf-8")
            out = _run_hook(state, Path(td))
            self.assertEqual(out, {})

    def test_v1_state_is_migrated_then_resolved(self):
        # Hook should tolerate old v1 file by triggering migration via the
        # script's read_state(). End result: it injects (or doesn't) based
        # on the migrated v2 contents.
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td).resolve()
            state = ws / "state.json"
            _write_v1(state,
                      git_root_at_set=str(ws),
                      cwd_at_set=str(ws))
            out = _run_hook(state, ws)
            ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
            # Migrated focus key matches our cwd, so it should inject.
            self.assertIn("alpha", ctx)


# ============================================================================
# Existing self-test still passes (regression safety)
# ============================================================================


class TestSelfTestStillPasses(unittest.TestCase):
    def test_self_test_subprocess(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "self-test"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(proc.returncode, 0,
                         f"self-test returncode={proc.returncode}\n"
                         f"stdout: {proc.stdout}\nstderr: {proc.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
