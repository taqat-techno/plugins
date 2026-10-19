"""0.20.0: plugin data directory, service-down cache, bounded decision log,
plugin options, and the command-aware lock guard (audit RAG-P1-05, F-RAG-06,
RAG-P3-12, PLUGIN_STANDARDS 1.6-1.7 and 4.2).

Every subprocess gets its own HOME and data directory, and the service port is
pointed at the discard port, so nothing here touches the real ~/.claude or a
running ragtools.
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
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "context_inject.py"
QUESTION = "What is our documented process for handling release approvals here?"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Sandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="rag_wp15_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = self.root / "home"
        self.data = self.root / "data"
        self.work = self.root / "work"
        for d in (self.home, self.data, self.work):
            d.mkdir()

    def env(self, **extra) -> dict:
        env = dict(os.environ)
        for var in ("CLAUDE_PLUGIN_DATA", "RAG_PLUGIN_DATA_DIR",
                    "CLAUDE_PLUGIN_OPTION_HOOK_DECISION_LOG",
                    "CLAUDE_PLUGIN_OPTION_SERVICE_PORT", "RAG_SERVICE_PORT"):
            env.pop(var, None)
        env.update(HOME=str(self.home), USERPROFILE=str(self.home),
                   CLAUDE_PLUGIN_DATA=str(self.data), RAG_PLUGIN_SERVICE_PORT="9")
        env.update(extra)
        return env

    def run_hook(self, prompt=QUESTION, **extra):
        payload = json.dumps({"hook_event_name": "UserPromptSubmit",
                              "user_prompt": prompt, "cwd": str(self.work)})
        proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                              capture_output=True, text=True, timeout=30,
                              env=self.env(**extra), cwd=str(self.work))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc

    def log_lines(self, base=None):
        log = (base or self.data) / "hook-decisions.log"
        if not log.is_file():
            return []
        return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x]


class TestPluginDataDir(_Sandbox):
    def _pd(self):
        return _load("pd_under_test", PLUGIN_ROOT / "scripts" / "plugin_data.py")

    def test_precedence(self):
        pd = self._pd()
        with mock.patch.dict(os.environ, {"RAG_PLUGIN_DATA_DIR": str(self.root / "x"),
                                          "CLAUDE_PLUGIN_DATA": str(self.data)}):
            self.assertEqual(pd.data_dir(), self.root / "x")
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": str(self.data)}):
            os.environ.pop("RAG_PLUGIN_DATA_DIR", None)
            self.assertEqual(pd.data_dir(), self.data)

    def test_unsubstituted_variable_falls_back_to_legacy(self):
        pd = self._pd()
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": "${CLAUDE_PLUGIN_DATA}"}):
            os.environ.pop("RAG_PLUGIN_DATA_DIR", None)
            self.assertEqual(pd.data_dir(), pd.legacy_dir())

    def test_legacy_file_is_copied_forward_once(self):
        pd = self._pd()
        legacy = self.home / ".claude" / "rag-plugin" / "state"
        legacy.mkdir(parents=True)
        (legacy / "project-focus.json").write_text('{"v": 1}', encoding="utf-8")
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": str(self.data),
                                          "HOME": str(self.home),
                                          "USERPROFILE": str(self.home)}):
            os.environ.pop("RAG_PLUGIN_DATA_DIR", None)
            target = pd.path("state/project-focus.json")
            self.assertEqual(target, self.data / "state" / "project-focus.json")
            self.assertEqual(target.read_text(encoding="utf-8"), '{"v": 1}')
            target.write_text('{"v": 2}', encoding="utf-8")
            pd.path("state/project-focus.json")  # no second copy over newer data
            self.assertEqual(target.read_text(encoding="utf-8"), '{"v": 2}')
            self.assertTrue((legacy / "project-focus.json").is_file(), "legacy kept")

    def test_marker_in_either_location_counts(self):
        pd = self._pd()
        legacy = self.home / ".claude" / "rag-plugin"
        legacy.mkdir(parents=True)
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_DATA": str(self.data),
                                          "HOME": str(self.home),
                                          "USERPROFILE": str(self.home)}):
            os.environ.pop("RAG_PLUGIN_DATA_DIR", None)
            self.assertFalse(pd.marker_present(".m"))
            (legacy / ".m").write_text("", encoding="utf-8")
            self.assertTrue(pd.marker_present(".m"))


class TestServiceDownCache(_Sandbox):
    def test_second_prompt_skips_the_health_probes(self):
        self.run_hook()
        self.run_hook()
        lines = self.log_lines()
        self.assertEqual(len(lines), 2, lines)
        self.assertGreaterEqual(lines[0]["http_calls"], 1,
                                "the first prompt probes /health and must count it")
        self.assertEqual(lines[1]["http_calls"], 0,
                         "a cached 'down' verdict must skip the probes")
        self.assertTrue((self.data / "state" / "service-down.json").is_file())

    def test_ttl_zero_disables_the_cache(self):
        self.run_hook(RAG_PLUGIN_HOOK_DOWN_TTL="0")
        self.run_hook(RAG_PLUGIN_HOOK_DOWN_TTL="0")
        self.assertTrue(all(x["http_calls"] >= 1 for x in self.log_lines()))

    def test_stale_verdict_is_ignored(self):
        state = self.data / "state"
        state.mkdir()
        (state / "service-down.json").write_text(
            json.dumps({"ts": 0, "ports": [9]}), encoding="utf-8")
        self.run_hook()
        self.assertGreaterEqual(self.log_lines()[0]["http_calls"], 1)


class TestDecisionLog(_Sandbox):
    def test_log_lives_in_the_plugin_data_dir(self):
        self.run_hook("Please rewrite this email to sound more polite.")
        self.assertTrue((self.data / "hook-decisions.log").is_file())
        self.assertFalse((self.home / ".claude" / "rag-plugin" / "hook-decisions.log").exists())

    def test_log_rotates_at_the_size_cap(self):
        log = self.data / "hook-decisions.log"
        log.write_text("x" * 500 + "\n", encoding="utf-8")
        self.run_hook("Please rewrite this email.", RAG_PLUGIN_HOOK_LOG_MAX_BYTES="200")
        self.assertTrue((self.data / "hook-decisions.log.1").is_file())
        self.assertLess(log.stat().st_size, 400)
        self.assertEqual(len(self.log_lines()), 1)

    def test_default_cap_is_one_megabyte(self):
        src = HOOK.read_text(encoding="utf-8")
        self.assertIn('"RAG_PLUGIN_HOOK_LOG_MAX_BYTES", str(1024 * 1024)', src)

    def test_plugin_option_turns_the_log_off(self):
        self.run_hook("Please rewrite this email.",
                      CLAUDE_PLUGIN_OPTION_HOOK_DECISION_LOG="false")
        self.assertEqual(self.log_lines(), [])

    def test_legacy_disable_marker_is_honoured(self):
        legacy = self.home / ".claude" / "rag-plugin"
        legacy.mkdir(parents=True)
        (legacy / ".hook-observability-disabled").write_text("", encoding="utf-8")
        self.run_hook("Please rewrite this email.")
        self.assertEqual(self.log_lines(), [])

    def test_no_prompt_text_is_logged(self):
        self.run_hook("Please rewrite this email about the Acme invoice.")
        raw = (self.data / "hook-decisions.log").read_text(encoding="utf-8")
        self.assertNotIn("Acme", raw)


class TestPortOption(unittest.TestCase):
    def test_service_port_option_wins(self):
        for module_path in (PLUGIN_ROOT / "hooks" / "context_inject.py",
                            PLUGIN_ROOT / "hooks" / "lock_conflict_check.py"):
            with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_SERVICE_PORT": "23456",
                                              "RAG_PLUGIN_SERVICE_PORT": "21420"}):
                mod = _load("port_" + module_path.stem, module_path)
            self.assertEqual(mod._ENV_PORT, "23456", module_path.name)

    def test_zero_means_auto(self):
        with mock.patch.dict(os.environ, {"CLAUDE_PLUGIN_OPTION_SERVICE_PORT": "0"}):
            os.environ.pop("RAG_PLUGIN_SERVICE_PORT", None)
            os.environ.pop("RAG_SERVICE_PORT", None)
            mod = _load("port_auto", PLUGIN_ROOT / "hooks" / "context_inject.py")
        self.assertEqual(mod.CANDIDATE_PORTS, [21420, 21421])


class TestLockGuardMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lc = _load("lock_under_test", PLUGIN_ROOT / "hooks" / "lock_conflict_check.py")

    def test_commands_that_run_match(self):
        for cmd in ("rag index", "  rag rebuild --full", "FOO=1 rag watch",
                    "cd repo && rag index .", "cat list | rag index",
                    'echo "starting"; rag rebuild', "rag-mcp",
                    "rag.exe index C:/docs",
                    '& "C:\\Tools\\RAGTools\\rag.exe" index',
                    'python -c "from qdrant_client import QdrantClient"',
                    "python3 -c \"c = QdrantClient(path='data/qdrant')\""):
            with self.subTest(cmd=cmd):
                self.assertIsNotNone(self.lc.matches_lock_conflict(cmd))

    def test_text_that_mentions_the_command_does_not(self):
        for cmd in ("echo rag index", 'grep -n "rag rebuild" notes.md',
                    "rg 'rag watch' docs", 'git commit -m "document rag index"',
                    "ls  # then rag index", 'Write-Host "run rag index later"',
                    'Select-String -Pattern "rag index" -Path *.md',
                    "curl -X POST http://127.0.0.1:21420/api/rebuild",
                    "rag indexer", "fragrag index", "rag search 'index'",
                    'node -e "QdrantClient(path=1)"'):
            with self.subTest(cmd=cmd):
                self.assertIsNone(self.lc.matches_lock_conflict(cmd))

    def _decide(self, payload, up=True):
        out = io.StringIO()
        with mock.patch.object(self.lc, "service_is_up", return_value=up), \
                mock.patch.object(self.lc.hooklib, "read_payload", return_value=payload), \
                mock.patch.object(self.lc.hooklib, "watchdog"), redirect_stdout(out):
            self.assertEqual(self.lc.main(), 0)
        return out.getvalue()

    def test_powershell_tool_is_guarded(self):
        out = self._decide({"tool_name": "PowerShell",
                            "tool_input": {"command": "rag index C:\\docs"}})
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "ask")

    def test_ask_carries_no_override_token(self):
        out = self._decide({"tool_name": "Bash", "tool_input": {"command": "rag rebuild"}})
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        for token in ("RAG_ALLOW", "--force", "override", "bypass"):
            self.assertNotIn(token, reason)

    def test_service_down_stays_silent(self):
        self.assertEqual(self._decide({"tool_name": "Bash",
                                       "tool_input": {"command": "rag index"}}, up=False), "")

    def test_other_tools_are_ignored(self):
        self.assertEqual(self._decide({"tool_name": "Write",
                                       "tool_input": {"command": "rag index"}}), "")


if __name__ == "__main__":
    unittest.main()
