"""End-to-end tests for hooks/test_scope_guard.py.

Runs the hook exactly as Claude Code does: a subprocess fed a JSON payload on stdin.
Run with:  python -m pytest agent-safety-guards-plugin/tests  (or python -m unittest)
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "test_scope_guard.py")


def run_hook(mode, payload, data_dir, extra_env=None, raw=None):
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=data_dir)
    env.pop("TEST_SCOPE_GUARD", None)
    env.update(extra_env or {})
    stdin = raw if raw is not None else json.dumps(payload)
    proc = subprocess.run([sys.executable, HOOK, mode], input=stdin.encode("utf-8"),
                          capture_output=True, env=env, timeout=20)
    return proc


def bash(command, session="s1"):
    return {"session_id": session, "tool_name": "Bash", "tool_input": {"command": command}}


class TestScopeGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def decision(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.decode("utf-8").strip()
        return json.loads(out)["hookSpecificOutput"] if out else None

    def test_self_test_table_passes(self):
        proc = subprocess.run([sys.executable, HOOK, "--self-test"], capture_output=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())

    def test_full_suite_is_denied_with_changed_files_and_override(self):
        for path in ("app/orders/models.py", "app/orders/tests/test_orders.py"):
            track = run_hook("track", {"session_id": "s1", "tool_name": "Edit",
                                       "tool_input": {"file_path": path}}, self.data)
            self.assertEqual(track.returncode, 0)
        out = self.decision(run_hook("check", bash("pytest -q"), self.data))
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertEqual(out["permissionDecision"], "deny")
        reason = out["permissionDecisionReason"]
        self.assertIn("app/orders/models.py", reason)
        self.assertIn("pytest app/orders/tests/test_orders.py", reason)
        self.assertIn("FULL_SUITE=1", reason)

    def test_scoped_run_passes_silently(self):
        self.assertIsNone(self.decision(run_hook("check", bash("pytest tests/test_a.py::test_x"), self.data)))

    def test_override_passes(self):
        self.assertIsNone(self.decision(run_hook("check", bash("FULL_SUITE=1 python manage.py test"), self.data)))
        self.assertIsNone(self.decision(run_hook("check", bash("$env:FULL_SUITE=1; npm test"), self.data)))

    def test_non_test_commands_pass(self):
        for command in ("git status", "grep -r pytest .", "python manage.py migrate", "ls"):
            self.assertIsNone(self.decision(run_hook("check", bash(command), self.data)), command)

    def test_disabled_by_env(self):
        proc = run_hook("check", bash("pytest"), self.data, {"TEST_SCOPE_GUARD": "off"})
        self.assertIsNone(self.decision(proc))

    def test_advise_mode_lets_the_run_happen_and_steers_the_next(self):
        run_hook("track", {"session_id": "s1", "tool_input": {"file_path": "shop/cart.py"}}, self.data)
        out = self.decision(run_hook("check", bash("pytest"), self.data, {"TEST_SCOPE_GUARD": "advise"}))
        self.assertEqual(out["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", out, "advise mode must never deny")
        self.assertIn("shop/cart.py", out["additionalContext"])
        self.assertIn("advise mode", out["additionalContext"])
        with open(os.path.join(self.data, "test-scope", "decisions.jsonl"), encoding="utf-8") as fh:
            self.assertIn("\"advise\"", fh.read())

    def test_advise_mode_is_silent_for_scoped_runs(self):
        proc = run_hook("check", bash("pytest tests/test_a.py"), self.data, {"TEST_SCOPE_GUARD": "advise"})
        self.assertIsNone(self.decision(proc))

    def test_unknown_mode_value_means_enforce(self):
        out = self.decision(run_hook("check", bash("pytest"), self.data, {"TEST_SCOPE_GUARD": "banana"}))
        self.assertEqual(out["permissionDecision"], "deny")

    def test_fails_open_on_garbage(self):
        for raw in ("", "not json", "[1,2]", "{\"tool_input\": 5}"):
            proc = run_hook("check", None, self.data, raw=raw)
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), b"")

    def test_sessions_are_isolated(self):
        run_hook("track", {"session_id": "other", "tool_input": {"file_path": "x/secret_change.py"}}, self.data)
        out = self.decision(run_hook("check", bash("pytest", session="mine"), self.data))
        self.assertNotIn("secret_change.py", out["permissionDecisionReason"])

    def test_decision_log_has_no_command_text(self):
        run_hook("check", bash("pytest --token=abc123"), self.data)
        with open(os.path.join(self.data, "test-scope", "decisions.jsonl"), encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("\"deny\"", content)
        self.assertNotIn("abc123", content)

    def test_non_ascii_payload_on_windows(self):
        proc = run_hook("check", bash("pytest  # تجربة"), self.data)
        self.assertEqual(self.decision(proc)["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
