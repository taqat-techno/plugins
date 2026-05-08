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


if __name__ == "__main__":
    unittest.main(verbosity=2)
