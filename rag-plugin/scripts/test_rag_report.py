#!/usr/bin/env python3
"""Tests for rag-plugin report engine v0.13.1 patch.

Covers two regressions raised by external-user diagnostics on 2026-05-06:

 1. ``scale.level="over"`` (Qdrant past hard limit) was misclassified as
    healthy because the synthesizer only knew the
    ``approaching|warning|critical|near-limit`` bands.
 2. The session-scan classifier matched ordinary shell output
    (``Exit code 2``, ``ls -la`` listings, prose containing the word
    "port") as ``mcp-error`` / ``port-in-use`` / ``connect-refused``,
    inflating P-012 with false positives.

Stdlib-only (``unittest``). Run via:

    python rag-plugin/scripts/test_rag_report.py

Imports rag_report.py via importlib so we can drive the synthesizer with
synthetic ``State`` objects without touching the real ragtools service.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "rag_report.py"


def _load_rr():
    name = "rag_report_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return mod


# ----------------------------------------------------------------------------
# Helper: build a synthetic State with the minimal fields the synthesizer reads
# ----------------------------------------------------------------------------


def _state_with_scale(rr, level: str, points: int = 0,
                     hard_limit: int = 20000, soft_limit: int = 15000,
                     message: str = "") -> Any:
    state = rr.State()
    state.install_mode = "packaged-windows"
    state.service_mode = "UP"
    state.binary_path = ""
    state.version = "2.5.2"
    state.config_path = ""
    state.data_path = ""
    state.log_path = ""
    state.host = "127.0.0.1"
    state.port = 21420
    state.api_status = {
        "status": "ready",
        "collection": "markdown_kb",
        "points_count": points,
        "total_files": 0,
        "total_chunks": points,
        "scale": {
            "level": level,
            "points_count": points,
            "soft_limit": soft_limit,
            "hard_limit": hard_limit,
            "message": message,
        },
    }
    state.health = {"status": "ready", "collection": "markdown_kb"}
    state.watcher_status = {"running": True, "paths": []}
    # Seed a single project so the synthesizer doesn't emit A-008
    # ("no projects configured") which is unrelated to scale-band logic.
    state.api_projects = [{"project_id": "1", "name": "demo", "path": "/tmp/demo",
                           "files": 1, "chunks": 5, "enabled": True}]
    return state


def _empty_inspections(rr):
    plugin = rr.PluginInspection()
    cci = rr.ClaudeConfigInspection()
    cci.user_claude_md_exists = True
    cci.retrieval_rule_present = True
    cci.plugin_mcp_present = True
    cci.plugin_mcp_path = "/fake/plugin-level/.mcp.json"
    hook_stats = rr.HookLogStats()
    hook_stats.log_exists = True
    hook_stats.total_lines = 0
    hook_stats.actions = {}
    log_hits: list[dict[str, Any]] = []
    scan = rr.SessionScanResult()
    return plugin, cci, hook_stats, log_hits, scan


def _synth(rr, state):
    plugin, cci, hook_stats, log_hits, scan = _empty_inspections(rr)
    return rr.synthesize_findings(state, plugin, cci, hook_stats, log_hits, scan)


def _ids(findings) -> list[str]:
    return [f.id for f in findings]


def _by_id(findings, fid):
    for f in findings:
        if f.id == fid:
            return f
    return None


# ============================================================================
# Issue 1 — scale.level="over" must NOT produce A-OK only
# ============================================================================


class TestScaleBandOver(unittest.TestCase):

    def test_scale_level_over_emits_high_severity_finding(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="over", points=26242,
                                  hard_limit=20000, soft_limit=15000,
                                  message="Collection has 26,242 points...")
        app, plugin = _synth(rr, state)
        # The user's reported regression: the report engine emitted A-OK
        # while the user was 31% past the hard limit. After the patch,
        # there must be at least one application-side non-info finding.
        non_info = [f for f in app if f.severity in ("medium", "high", "critical")]
        self.assertTrue(non_info,
                        f"scale.level='over' must produce a non-info finding; got: {_ids(app)}")

    def test_scale_level_over_severity_is_high(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="over", points=26242,
                                  hard_limit=20000)
        app, _ = _synth(rr, state)
        # over (past hard limit) is more serious than approaching/warning
        # (forecast). Expect a high-severity finding for it specifically.
        high = [f for f in app if f.severity == "high"]
        self.assertTrue(high, f"expected at least one high-severity app finding; got: "
                              f"{[(f.id, f.severity) for f in app]}")

    def test_scale_level_over_recommendation_lists_remediation_order(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="over", points=26242,
                                  hard_limit=20000)
        app, _ = _synth(rr, state)
        # The recommendation for the over-band finding must mention all
        # three remediation steps the maintainer guidance recommends.
        non_info = [f for f in app if f.severity in ("medium", "high", "critical")]
        rec = " ".join(f.recommendation for f in non_info).lower()
        self.assertIn("ignore_patterns", rec)
        self.assertTrue("remove" in rec or "prune" in rec)
        self.assertTrue("server mode" in rec or "qdrant server" in rec)

    def test_scale_level_over_does_not_emit_only_a_ok(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="over", points=26242,
                                  hard_limit=20000)
        app, _ = _synth(rr, state)
        # Regression assertion for the original user complaint.
        info_only = all(f.severity == "info" for f in app)
        self.assertFalse(info_only,
                         "scale.level='over' must not be reported as A-OK only")

    # Regressions for existing bands (must keep working)

    def test_scale_level_approaching_still_emits_a012(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="approaching", points=14500,
                                  soft_limit=15000, hard_limit=20000)
        app, _ = _synth(rr, state)
        ids = _ids(app)
        self.assertIn("A-012", ids, f"expected A-012; got: {ids}")

    def test_scale_level_warning_still_emits_a013(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="warning", points=18500,
                                  hard_limit=20000)
        app, _ = _synth(rr, state)
        ids = _ids(app)
        self.assertIn("A-013", ids, f"expected A-013; got: {ids}")

    def test_scale_level_none_emits_a_ok(self):
        rr = _load_rr()
        state = _state_with_scale(rr, level="none", points=100,
                                  hard_limit=20000)
        app, _ = _synth(rr, state)
        # Healthy state — A-OK is the expected info-only summary.
        ids = _ids(app)
        self.assertIn("A-OK", ids)


# ============================================================================
# Issue 2 — session-scan classifier must not match generic shell output
# ============================================================================


# Real false-positive snippets from the 2026-05-06 user diagnostics, verbatim:

_FP_PORT_LEGACY_RE = (
    "{\"role\": \"user\", \"content\": [{\"tool_use_id\": \"toolu_01NGFBid6ggwEtrvB846gBv4\", "
    "\"type\": \"tool_result\", \"content\": \"493. **Legacy-RE deliverable: Decision Matrix > Prose, "
    "every time** — When the stakeholder's strategic intent is clear, prefer a Decision Matrix "
    "over Prose. The matrix import was in use of the wrong column set."
)

_FP_CONNECT_LS = (
    "{\"role\": \"user\", \"content\": [{\"tool_use_id\": \"toolu_01UffEtnbKaJNSc46ddxK5t3\", "
    "\"type\": \"tool_result\", \"content\": \"-rw-r--r-- 1 DELL 197121 19537 May 1 23:50 "
    "D:/Project Management/Project Management Office/Dashboards/PMO-Dashboard.md\""
)

_FP_CONNECT_LINENUM = (
    "{\"role\": \"user\", \"content\": [{\"tool_use_id\": \"toolu_01FDUxTUFgvLotgTNEnRvtg1\", "
    "\"type\": \"tool_result\", \"content\": \"1150\\t581. **Auto-reopen cap=2 prevents chronic "
    "loops — a closed-then-red-again entry must be capped at 2 reopens.\""
)

_FP_MCP_EXIT_CODE_2 = (
    "{\"role\": \"user\", \"content\": [{\"type\": \"tool_result\", \"content\": "
    "\"Exit code 2\\ntotal 12\\ndrwxr-xr-x 1 DELL 197121 0 Apr 20 09:36 .\\n"
    "drwxr-xr-x 1 DELL 197121 0 Apr 15 08:26 ..\\ndrwxr-xr-x 1 DELL 197121 0 Apr 19 08:32 0...."
)

_FP_MCP_DOC_PROSE = (
    "Documentation note: previously the rag-mcp launcher could fail. Has been resolved in v0.3.3."
)


class TestClassifierFalsePositives(unittest.TestCase):
    """The classifier must NOT match these generic-shell / prose strings."""

    def _patterns(self, rr):
        return dict(rr._SIGNAL_PATTERNS)

    def _matches_label(self, rr, text: str, label: str) -> bool:
        pat = self._patterns(rr).get(label)
        self.assertIsNotNone(pat, f"label {label!r} not present in _SIGNAL_PATTERNS")
        return bool(pat.search(text))

    def test_port_in_use_does_not_match_legacy_re_prose(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, _FP_PORT_LEGACY_RE, "port-in-use"),
                         "port-in-use must not match prose containing 'in use of'")

    def test_connect_refused_does_not_match_ls_listing(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, _FP_CONNECT_LS, "connect-refused"),
                         "connect-refused must not match an ls -la listing")

    def test_connect_refused_does_not_match_line_numbered_prose(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, _FP_CONNECT_LINENUM, "connect-refused"))

    def test_mcp_error_does_not_match_exit_code_2_listing(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, _FP_MCP_EXIT_CODE_2, "mcp-error"),
                         "mcp-error must not match a generic 'Exit code 2' shell error")

    def test_mcp_error_does_not_match_historical_doc_prose(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, _FP_MCP_DOC_PROSE, "mcp-error"),
                         "mcp-error must not match docs about a resolved past issue")

    def test_port_in_use_does_not_match_word_port_alone(self):
        rr = _load_rr()
        self.assertFalse(self._matches_label(rr, "import was in use of the wrong column", "port-in-use"))
        self.assertFalse(self._matches_label(rr, "port management is a key topic", "port-in-use"))


class TestClassifierPositiveStillMatches(unittest.TestCase):
    """Real failure markers must continue to classify correctly."""

    def _matches_label(self, rr, text: str, label: str) -> bool:
        pat = dict(rr._SIGNAL_PATTERNS).get(label)
        return bool(pat.search(text)) if pat else False

    def test_eaddrinuse_matches_port_in_use(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "Error: listen EADDRINUSE: address already in use :::21420", "port-in-use"))

    def test_address_already_in_use_matches_port_in_use(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "OSError: [Errno 98] Address already in use", "port-in-use"))

    def test_port_with_number_matches_port_in_use(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "port 21420 is already in use", "port-in-use"))

    def test_econnrefused_matches_connect_refused(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "fetch failed: connect ECONNREFUSED 127.0.0.1:21420", "connect-refused"))

    def test_connection_refused_matches_connect_refused(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "ConnectionError: HTTPConnectionPool(host='127.0.0.1', port=21420): Failed to establish a new connection: [Errno 111] Connection refused", "connect-refused"))

    def test_rag_error_service_unavailable_matches_rag_error_line(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "[RAG ERROR] Service unavailable. The RAG service may have stopped.", "rag-error-line"))

    def test_mcp_server_failed_matches_mcp_error(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "MCP server failed to start: stdio handshake timeout", "mcp-error"))

    def test_failed_to_reconnect_to_plugin_rag_matches_mcp_error(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "Failed to reconnect to plugin:rag:ragtools after 3 attempts", "mcp-error"))

    def test_tools_list_timeout_matches_mcp_error(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "MCP tools/list timeout after 60s for plugin:rag:ragtools", "mcp-error"))

    def test_mcp_startup_failed_matches_mcp_error(self):
        rr = _load_rr()
        self.assertTrue(self._matches_label(rr, "mcp_server.STARTUP_FAILED: encoder load failed", "mcp-error"))


# ============================================================================
# Existing self-test still passes (regression safety)
# ============================================================================


class TestSelfTestStillPasses(unittest.TestCase):
    def test_self_test_subprocess(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--self-test"],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(proc.returncode, 0,
                         f"--self-test returncode={proc.returncode}\n"
                         f"stdout: {proc.stdout}\nstderr: {proc.stderr}")


# ============================================================================
# GitHub issue filing (D-030): routing, cause-based re-route, fingerprint,
# duplicate prevention, create, and the never-create-during-generation guards.
# ============================================================================

import json as _json
import tempfile


def _finding(rr, fid, target, severity="high", title="x"):
    return rr.Finding(id=fid, title=title, severity=severity,
                      evidence="e", recommendation="r", target=target)


class _FakeGh:
    """Records gh calls and returns canned responses. Drop-in for rr._run_gh
    so no real GitHub API call is ever made in the test suite."""

    def __init__(self, authed=True, existing_body=None,
                 create_url="https://github.com/taqat-techno/rag/issues/1"):
        self.calls: list[list[str]] = []
        self.authed = authed
        self.existing_body = existing_body
        self.create_url = create_url

    def __call__(self, args, timeout=20.0):
        self.calls.append(list(args))
        if args[:1] == ["auth"]:
            return (0, "Logged in", "") if self.authed else (1, "", "not logged in")
        if args[:2] == ["issue", "list"]:
            items = []
            if self.existing_body is not None:
                items = [{"url": "https://github.com/taqat-techno/rag/issues/9",
                          "body": self.existing_body}]
            return 0, _json.dumps(items), ""
        if args[:2] == ["issue", "create"]:
            return 0, self.create_url, ""
        return 0, "", ""

    def created_count(self) -> int:
        return sum(1 for c in self.calls if c[:2] == ["issue", "create"])


def _write_plan_dir(tmp, fingerprint="abc123def456", repo="taqat-techno/rag",
                    target="rag", actionable=True):
    d = Path(tmp)
    body_file = f"_issue-body-{target}.md"
    (d / body_file).write_text(
        f"<!-- rag-plugin-report:fingerprint:{fingerprint} -->\nissue body\n",
        encoding="utf-8")
    plan = [{
        "repo": repo, "target": target, "title": f"[{target}] high: x",
        "labels": ["diagnostic"], "fingerprint": fingerprint,
        "actionable": actionable, "finding_count": 1,
        "body_file": body_file, "human_file": f"github-{target}-issue.md",
    }]
    (d / "issue-plan.json").write_text(_json.dumps(plan), encoding="utf-8")
    return d


class TestIssueRouting(unittest.TestCase):
    def setUp(self):
        self.rr = _load_rr()

    def test_rag_meta_targets_rag_repo(self):
        m = self.rr.build_issue_meta("rag", [_finding(self.rr, "A-003", "rag")],
                                     self.rr.State(), self.rr.PluginInspection())
        self.assertEqual(m["repo"], "taqat-techno/rag")

    def test_plugins_meta_targets_plugins_repo(self):
        m = self.rr.build_issue_meta("plugins", [_finding(self.rr, "P-005", "plugins")],
                                     self.rr.State(), self.rr.PluginInspection())
        self.assertEqual(m["repo"], "taqat-techno/plugins")

    def test_route_findings_merges_by_target(self):
        app = [_finding(self.rr, "A-003", "rag")]
        plg = [_finding(self.rr, "P-005", "plugins"),
               _finding(self.rr, "P-012", "rag")]  # re-targeted to rag
        rag, plugins, dropped = self.rr.route_findings(app, plg)
        self.assertEqual(sorted(f.id for f in rag), ["A-003", "P-012"])
        self.assertEqual([f.id for f in plugins], ["P-005"])
        self.assertEqual(dropped, [])

    def test_route_findings_surfaces_unroutable(self):
        rag, plugins, dropped = self.rr.route_findings(
            [_finding(self.rr, "X-1", "local")], [])
        self.assertEqual(dropped, ["X-1"])


class TestCauseBasedReroute(unittest.TestCase):
    """P-010 / P-012 must route to the application repo when the service was down."""

    def setUp(self):
        self.rr = _load_rr()

    def _scan_with(self, **counts):
        scan = self.rr.SessionScanResult()
        scan.sessions_scanned = 5
        scan.sessions_with_signal = 5
        scan.signal_counts = {"rag-mention": 10, "retrieval-skipped": 0,
                              "user-correct-search": 0, "mcp-error": 0,
                              "connect-refused": 0}
        scan.signal_counts.update(counts)
        return scan

    def _synth(self, service_mode, scan):
        state = self.rr.State()
        state.install_mode = "packaged-windows"
        state.service_mode = service_mode
        state.api_projects = [{"project_id": "1", "name": "d", "path": "/t",
                               "files": 1, "chunks": 5, "enabled": True}]
        return self.rr.synthesize_findings(
            state, self.rr.PluginInspection(), self.rr.ClaudeConfigInspection(),
            self.rr.HookLogStats(), [], scan)

    def test_mcp_error_routes_to_plugins_when_service_up(self):
        _, plg = self._synth("UP", self._scan_with(**{"mcp-error": 3}))
        self.assertEqual(_by_id(plg, "P-012").target, "plugins")

    def test_mcp_error_routes_to_rag_when_service_down(self):
        _, plg = self._synth("DOWN", self._scan_with(**{"mcp-error": 3}))
        self.assertEqual(_by_id(plg, "P-012").target, "rag")

    def test_skipped_retrieval_routes_to_rag_when_service_down(self):
        _, plg = self._synth("DOWN", self._scan_with(**{"retrieval-skipped": 9}))
        self.assertEqual(_by_id(plg, "P-010").target, "rag")

    def test_skipped_retrieval_blames_plugin_when_service_up(self):
        _, plg = self._synth("UP", self._scan_with(**{"retrieval-skipped": 9}))
        self.assertEqual(_by_id(plg, "P-010").target, "plugins")


class TestFingerprint(unittest.TestCase):
    def setUp(self):
        self.rr = _load_rr()

    def test_fingerprint_stable_and_order_independent(self):
        a = [_finding(self.rr, "A-003", "rag"), _finding(self.rr, "A-014", "rag")]
        b = [_finding(self.rr, "A-014", "rag"), _finding(self.rr, "A-003", "rag")]
        self.assertEqual(self.rr.issue_fingerprint(a), self.rr.issue_fingerprint(b))

    def test_fingerprint_differs_for_different_findings(self):
        self.assertNotEqual(
            self.rr.issue_fingerprint([_finding(self.rr, "A-003", "rag")]),
            self.rr.issue_fingerprint([_finding(self.rr, "A-014", "rag")]))


class TestDoCreate(unittest.TestCase):
    def setUp(self):
        self.rr = _load_rr()
        self._orig = self.rr._run_gh

    def tearDown(self):
        self.rr._run_gh = self._orig

    def test_gh_unavailable_falls_back_local_only(self):
        fake = _FakeGh(authed=False)
        self.rr._run_gh = fake
        with tempfile.TemporaryDirectory() as tmp:
            res = self.rr.do_create(_write_plan_dir(tmp))
        self.assertEqual(res.get("fallback"), "local-only")
        self.assertEqual(fake.created_count(), 0)

    def test_yes_creates_issue_when_gh_available(self):
        fake = _FakeGh(authed=True)
        self.rr._run_gh = fake
        with tempfile.TemporaryDirectory() as tmp:
            res = self.rr.do_create(_write_plan_dir(tmp, fingerprint="deadbeef0001"))
        self.assertIn("created", [r["status"] for r in res["results"]])
        self.assertEqual(fake.created_count(), 1)

    def test_duplicate_fingerprint_prevents_creation(self):
        fp = "cafe12345678"
        fake = _FakeGh(authed=True,
                       existing_body=f"x <!-- rag-plugin-report:fingerprint:{fp} --> y")
        self.rr._run_gh = fake
        with tempfile.TemporaryDirectory() as tmp:
            res = self.rr.do_create(_write_plan_dir(tmp, fingerprint=fp))
        self.assertEqual([r["status"] for r in res["results"]], ["duplicate"])
        self.assertEqual(fake.created_count(), 0)

    def test_no_plan_file_returns_no_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = self.rr.do_create(Path(tmp))
        self.assertEqual(res.get("reason"), "no-plan")


class TestGenerationNeverCreates(unittest.TestCase):
    """Default generation and --dry-run must NEVER call gh (no silent creation)."""

    def setUp(self):
        self.rr = _load_rr()
        self._orig = self.rr._run_gh
        self.fake = _FakeGh()
        self.rr._run_gh = self.fake

    def tearDown(self):
        self.rr._run_gh = self._orig

    def test_dry_run_makes_no_gh_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.rr.main(["--dry-run", "--no-sessions", "--quiet", "--out", tmp])
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.fake.calls), 0)

    def test_default_generation_makes_no_gh_call_and_writes_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = self.rr.main(["--no-sessions", "--quiet", "--out", tmp])
            self.assertEqual(rc, 0)
            self.assertEqual(len(self.fake.calls), 0)
            # main() writes to Path(--out).resolve(); check inside the context
            # manager so the dir still exists.
            self.assertTrue((Path(tmp).resolve() / "issue-plan.json").exists())


# ============================================================================
# D-031 / P-013: advisory UserPromptSubmit hook fail-open detection
# ============================================================================

import shutil


class TestHookSafetyAnalyzer(unittest.TestCase):
    """analyze_advisory_hook_safety must flag raw advisory script invocations and
    recognize the fail-open shapes (-c bootstrap, || exit guard) as safe."""

    def setUp(self):
        self.rr = _load_rr()

    def _plugin_with_hooks(self, hooks_obj):
        tmp = tempfile.mkdtemp(prefix="raghooks_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        hd = Path(tmp) / "hooks"
        hd.mkdir()
        (hd / "hooks.json").write_text(_json.dumps(hooks_obj), encoding="utf-8")
        return tmp

    def _ups(self, command):
        return {"hooks": {"UserPromptSubmit": [
            {"matcher": "*", "hooks": [{"type": "command", "command": command}]}]}}

    def test_flags_raw_advisory_command(self):
        tmp = self._plugin_with_hooks(
            self._ups("python3 ${CLAUDE_PLUGIN_ROOT}/hooks/prompt_retrieval_reminder.py"))
        unsafe = self.rr.analyze_advisory_hook_safety(tmp)
        self.assertEqual(len(unsafe), 1, unsafe)

    def test_inline_c_bootstrap_is_safe_even_with_fallback_var(self):
        # The real fixed shape: has ${CLAUDE_PLUGIN_ROOT}/...py as a FALLBACK arg
        # but is invoked via -c, so it is fail-open and must NOT be flagged.
        tmp = self._plugin_with_hooks(self._ups(
            "python3 -c \"import os\" retrieval-reminder "
            "${CLAUDE_PLUGIN_ROOT}/hooks/hook_launcher.py"))
        self.assertEqual(self.rr.analyze_advisory_hook_safety(tmp), [])

    def test_explicit_guard_is_safe(self):
        tmp = self._plugin_with_hooks(self._ups(
            "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/x.py || exit 0"))
        self.assertEqual(self.rr.analyze_advisory_hook_safety(tmp), [])

    def test_pretooluse_raw_is_not_flagged(self):
        # Only advisory (UserPromptSubmit) hooks are in scope; the intentionally
        # blocking PreToolUse lock hook must not be flagged.
        obj = {"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command",
             "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/lock_conflict_check.py"}]}]}}
        tmp = self._plugin_with_hooks(obj)
        self.assertEqual(self.rr.analyze_advisory_hook_safety(tmp), [])

    def test_missing_hooks_json_returns_empty(self):
        tmp = tempfile.mkdtemp(prefix="raghooks_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.assertEqual(self.rr.analyze_advisory_hook_safety(tmp), [])

    def test_real_plugin_hooks_are_failopen(self):
        # Regression guard: this plugin's own hooks.json must stay fail-open.
        plugin_root = str(HERE.parent)
        self.assertEqual(self.rr.analyze_advisory_hook_safety(plugin_root), [],
                         "rag-plugin's own advisory hooks must be fail-open")


class TestP013Finding(unittest.TestCase):
    """P-013 must fire on static unsafe-hook evidence, escalate with runtime
    evidence, and outrank P-012 in the generated plugins issue."""

    def setUp(self):
        self.rr = _load_rr()

    def _synth(self, unsafe, fatal=0):
        plugin = self.rr.PluginInspection()
        plugin.plugin_dir = "/fake/plugin"      # avoid P-001
        plugin.manifest_version = "0.15.1"
        plugin.unsafe_advisory_hooks = list(unsafe)
        cci = self.rr.ClaudeConfigInspection()
        cci.user_claude_md_exists = True        # avoid P-004
        cci.retrieval_rule_present = True        # avoid P-005
        cci.plugin_mcp_present = True            # avoid P-007
        hook_stats = self.rr.HookLogStats()
        scan = self.rr.SessionScanResult()
        if fatal:
            scan.signal_counts = {"hook-path-fatal": fatal}
        state = self.rr.State()
        state.install_mode = "packaged-windows"
        state.service_mode = "UP"
        state.api_projects = [{"project_id": "1", "name": "d", "path": "/t",
                               "files": 1, "chunks": 5, "enabled": True}]
        return self.rr.synthesize_findings(state, plugin, cci, hook_stats, [], scan)

    def test_p013_high_when_unsafe_present(self):
        _, plg = self._synth(["python3 ${CLAUDE_PLUGIN_ROOT}/hooks/x.py"])
        f = _by_id(plg, "P-013")
        self.assertIsNotNone(f, _ids(plg))
        self.assertEqual(f.severity, "high")
        self.assertEqual(f.target, "plugins")

    def test_p013_critical_with_runtime_signature(self):
        _, plg = self._synth(["python3 ${CLAUDE_PLUGIN_ROOT}/hooks/x.py"], fatal=3)
        f = _by_id(plg, "P-013")
        self.assertIsNotNone(f, _ids(plg))
        self.assertEqual(f.severity, "critical")

    def test_p013_absent_when_failopen(self):
        _, plg = self._synth([])
        self.assertIsNone(_by_id(plg, "P-013"), _ids(plg))

    def test_p013_outranks_p012_in_issue_title(self):
        rr = self.rr
        findings = [
            _finding(rr, "P-012", "plugins", severity="medium",
                     title="MCP error phrases detected in sessions"),
            _finding(rr, "P-013", "plugins", severity="high",
                     title="advisory UserPromptSubmit hook can block the prompt"),
        ]
        self.assertEqual(rr._sort_findings(findings)[0].id, "P-013")
        meta = rr.build_issue_meta("plugins", findings, rr.State(), rr.PluginInspection())
        self.assertIn("advisory UserPromptSubmit hook can block", meta["title"])


class TestHookPathFatalSignal(unittest.TestCase):
    """The hook-path-fatal session signal must match the real stderr signature
    but not the generic false-positive strings guarded elsewhere."""

    def setUp(self):
        self.rr = _load_rr()

    def _match(self, text):
        pat = dict(self.rr._SIGNAL_PATTERNS).get("hook-path-fatal")
        self.assertIsNotNone(pat)
        return bool(pat.search(text))

    def test_matches_real_cant_open_stderr(self):
        s = (r"python3.exe: can't open file "
             r"'C:\Users\me\rag-plugin\${CLAUDE_PLUGIN_ROOT}\hooks\prompt_retrieval_reminder.py': "
             r"[Errno 2] No such file or directory")
        self.assertTrue(self._match(s))

    def test_matches_posix_errno2_hooks(self):
        s = "python3: can't open file '/hooks/prompt_retrieval_reminder.py': [Errno 2] No such file or directory"
        self.assertTrue(self._match(s))

    def test_does_not_match_exit_code_2_listing(self):
        self.assertFalse(self._match(_FP_MCP_EXIT_CODE_2))

    def test_does_not_match_ls_listing(self):
        self.assertFalse(self._match(_FP_CONNECT_LS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
