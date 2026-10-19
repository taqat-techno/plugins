#!/usr/bin/env python3
"""Failure-mode tests for the rag-plugin hook wiring (D-031, PLUGIN_STANDARDS 1.1).

CRITICAL ACCEPTANCE CONDITION
-----------------------------
The advisory UserPromptSubmit hook must exit **0**, and never **2** (the Claude
Code blocking code that cancels the prompt), under every failure scenario:

  * unexpanded literal ``${CLAUDE_PLUGIN_ROOT}`` / unset root / missing directory
  * target script missing, raising, or calling ``sys.exit(2)``
  * malformed or empty payload
  * RAG service down (the default here: nothing listens on the test port)

The guarded PreToolUse lock hook passes an intentional exit code through, but
still fails open when it cannot be located or crashes.

Two layers are tested:

* ``TestLauncher*`` run ``hooks/hook_launcher.py`` directly, so they need no shell.
* ``TestShellLauncher`` runs the EXACT command strings from ``hooks/hooks.json``
  through bash, with a ``python3`` shim on PATH that points at ``sys.executable``.
  Skipped when no POSIX bash is available.

Every run points the plugin data directory at a temp dir, so no test writes into
the real ``~/.claude``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOKS = PLUGIN_ROOT / "hooks"
HOOKS_JSON = HOOKS / "hooks.json"
LAUNCHER = HOOKS / "hook_launcher.py"
BLOCKING_EXIT = 2
LITERAL_VAR = "${CLAUDE_PLUGIN_ROOT}"
GOOD_PAYLOAD = json.dumps({"hook_event_name": "UserPromptSubmit",
                           "user_prompt": "What is our deployment process?"})
STANDARD_PREFIX = 's="${CLAUDE_PLUGIN_ROOT}/hooks/hook_launcher.py"; [ -f "$s" ] || exit 0; '


def _base_env(data_dir: str) -> dict:
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    env["RAG_PLUGIN_DATA_DIR"] = data_dir
    env["RAG_PLUGIN_SERVICE_PORT"] = "9"   # discard port: nothing answers
    return env


def _temp_plugin(target_body=None, include_target=True,
                 target_filename="context_inject.py") -> str:
    tmp = tempfile.mkdtemp(prefix="raghook_")
    hooks = Path(tmp) / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(str(LAUNCHER), str(hooks / "hook_launcher.py"))
    if include_target:
        body = target_body if target_body is not None else "import sys\nsys.exit(0)\n"
        (hooks / target_filename).write_text(body, encoding="utf-8")
    return tmp


def _commands() -> dict:
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    out = {}
    for event, groups in data["hooks"].items():
        for group in groups:
            for h in group["hooks"]:
                out[event] = h
    return out


def _find_bash():
    if os.name == "nt":
        for cand in (r"C:\Program Files\Git\bin\bash.exe",
                     r"C:\Program Files\Git\usr\bin\bash.exe"):
            if os.path.isfile(cand):
                return cand
        found = shutil.which("bash")
        if found and "system32" not in found.lower():
            return found
        return None
    return shutil.which("bash")


class _DataDirMixin:
    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="ragdata_")
        self.addCleanup(shutil.rmtree, self.data, ignore_errors=True)

    def run_launcher(self, target, launcher=LAUNCHER, stdin=GOOD_PAYLOAD):
        return subprocess.run([sys.executable, str(launcher), target], input=stdin,
                              capture_output=True, text=True, timeout=30,
                              env=_base_env(self.data))


class TestLauncherNeverBlocks(_DataDirMixin, unittest.TestCase):

    def _ok(self, proc, ctx):
        self.assertNotEqual(proc.returncode, BLOCKING_EXIT, f"{ctx}: blocking exit 2")
        self.assertEqual(proc.returncode, 0, f"{ctx}: {proc.stderr}")

    def test_missing_target_script(self):
        tmp = _temp_plugin(include_target=False)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self._ok(self.run_launcher("context-inject", Path(tmp) / "hooks" / "hook_launcher.py"),
                 "missing target")

    def test_target_raises(self):
        tmp = _temp_plugin(target_body="raise RuntimeError('boom')\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self._ok(self.run_launcher("context-inject", Path(tmp) / "hooks" / "hook_launcher.py"),
                 "target raises")

    def test_target_exit_2_is_normalized(self):
        tmp = _temp_plugin(target_body="import sys\nsys.exit(2)\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self._ok(self.run_launcher("context-inject", Path(tmp) / "hooks" / "hook_launcher.py"),
                 "target exit 2")

    def test_malformed_and_empty_payload(self):
        for stdin in ("not json {{{", "", "[]"):
            self._ok(self.run_launcher("context-inject", stdin=stdin), f"payload {stdin!r}")

    def test_service_down_real_target(self):
        self._ok(self.run_launcher("context-inject"), "service down")

    def test_unknown_target_fails_open(self):
        # The pre-0.18 names retrieval-reminder / project-focus are no longer
        # mapped; an unknown name must still never block.
        for name in ("retrieval-reminder", "project-focus", "nope", ""):
            self._ok(self.run_launcher(name), f"unknown target {name!r}")

    def test_target_stdout_passes_through(self):
        marker = '{"hookSpecificOutput": {"x": 1}}'
        tmp = _temp_plugin(target_body="import sys\nsys.stdout.write(%r)\n" % marker)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = self.run_launcher("context-inject", Path(tmp) / "hooks" / "hook_launcher.py")
        self.assertEqual(proc.returncode, 0)
        self.assertIn(marker, proc.stdout)


class TestLauncherGuardedMode(_DataDirMixin, unittest.TestCase):

    def _run(self, body=None, include=True):
        tmp = _temp_plugin(target_body=body, include_target=include,
                           target_filename="lock_conflict_check.py")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return self.run_launcher("lock-conflict", Path(tmp) / "hooks" / "hook_launcher.py")

    def test_missing_target_fails_open(self):
        self.assertEqual(self._run(include=False).returncode, 0)

    def test_intentional_exit_2_passes_through(self):
        self.assertEqual(self._run("import sys\nsys.exit(2)\n").returncode, 2)

    def test_unexpected_exception_fails_open(self):
        self.assertEqual(self._run("raise RuntimeError('boom')\n").returncode, 0)

    def test_ask_stdout_passes_through(self):
        ask = '{"hookSpecificOutput": {"permissionDecision": "ask"}}'
        proc = self._run("import sys\nsys.stdout.write(%r)\n" % ask)
        self.assertEqual(proc.returncode, 0)
        self.assertIn(ask, proc.stdout)

    def test_real_lock_target_ignores_other_tools(self):
        payload = json.dumps({"tool_name": "Read", "tool_input": {}})
        proc = self.run_launcher("lock-conflict", stdin=payload)
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))


class TestHooksJsonShape(unittest.TestCase):

    def test_every_command_uses_the_standard_launcher(self):
        for event, hook in _commands().items():
            cmd = hook["command"]
            self.assertTrue(cmd.startswith(STANDARD_PREFIX), event)
            self.assertIn("for c in python3 python py; do command -v $c >/dev/null 2>&1 "
                          "|| continue; [ $c = py ] && c='py -3'; $c \"$s\" ", cmd)
            self.assertTrue(cmd.endswith("r=$?; [ $r -eq 49 ] || exit $r; done; exit 0"), event)

    def test_every_hook_has_a_timeout(self):
        for event, hook in _commands().items():
            self.assertIsInstance(hook.get("timeout"), int, event)
            self.assertLessEqual(hook["timeout"], 15, event)

    def test_lock_guard_covers_bash_and_powershell(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "Bash|PowerShell")

    def test_targets_are_registered(self):
        cmds = _commands()
        self.assertIn('"$s" lock-conflict;', cmds["PreToolUse"]["command"])
        self.assertIn('"$s" context-inject;', cmds["UserPromptSubmit"]["command"])

    def test_no_dead_hook_scripts(self):
        """Every .py directly under hooks/ is the launcher or a registered target."""
        launcher = LAUNCHER.read_text(encoding="utf-8")
        for script in HOOKS.glob("*.py"):
            if script.name == "hook_launcher.py":
                continue
            self.assertIn(f'("{script.name}"', launcher, f"{script.name} is not registered")


BASH = _find_bash()


@unittest.skipIf(BASH is None, "no POSIX bash available")
class TestShellLauncher(unittest.TestCase):
    """The hooks.json strings themselves, through bash."""

    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="ragdata_")
        self.bin = tempfile.mkdtemp(prefix="ragbin_")
        self.addCleanup(shutil.rmtree, self.data, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.bin, ignore_errors=True)
        shim = Path(self.bin) / "python3"
        shim.write_bytes(("#!/bin/sh\nexec \"%s\" \"$@\"\n"
                          % Path(sys.executable).as_posix()).encode("utf-8"))
        shim.chmod(0o755)

    def run_cmd(self, event, root, stdin=GOOD_PAYLOAD):
        env = _base_env(self.data)
        if root is not None:
            env["CLAUDE_PLUGIN_ROOT"] = root
        command = 'PATH="%s:$PATH"; %s' % (Path(self.bin).as_posix(),
                                           _commands()[event]["command"])
        return subprocess.run([BASH, "-c", command], input=stdin, capture_output=True,
                              text=True, timeout=60, env=env)

    def test_unset_root_exits_zero(self):
        self.assertEqual(self.run_cmd("UserPromptSubmit", None).returncode, 0)

    def test_literal_unexpanded_root_exits_zero(self):
        self.assertEqual(self.run_cmd("UserPromptSubmit", LITERAL_VAR).returncode, 0)

    def test_root_with_a_space_runs_the_target(self):
        tmp = tempfile.mkdtemp(prefix="rag plugin ")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        hooks = Path(tmp) / "hooks"
        hooks.mkdir()
        shutil.copy(str(LAUNCHER), str(hooks / "hook_launcher.py"))
        (hooks / "context_inject.py").write_text("print('RAN')\n", encoding="utf-8")
        proc = self.run_cmd("UserPromptSubmit", Path(tmp).as_posix())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("RAN", proc.stdout)

    def test_real_plugin_service_down_exits_zero(self):
        proc = self.run_cmd("UserPromptSubmit", PLUGIN_ROOT.as_posix())
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_lock_guard_passes_unrelated_command(self):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        proc = self.run_cmd("PreToolUse", PLUGIN_ROOT.as_posix(), stdin=payload)
        self.assertEqual((proc.returncode, proc.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
