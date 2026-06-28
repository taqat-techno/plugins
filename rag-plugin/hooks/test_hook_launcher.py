#!/usr/bin/env python3
"""Failure-mode tests for the rag-plugin fail-open hook launcher (D-031).

CRITICAL ACCEPTANCE CONDITION
-----------------------------
The advisory UserPromptSubmit hook invocation must return exit code **0** — and
must NEVER return **2** (the Claude Code "blocking error" code that cancels the
prompt) — under every failure scenario:

  * unresolved literal ``${CLAUDE_PLUGIN_ROOT}``  (host did not expand it)
  * unset plugin root                              (env var missing)
  * plugin root points at a non-existent directory
  * target script missing
  * target script raises an exception
  * target script ``sys.exit(2)`` (worst case — must be normalized to 0)
  * malformed / empty hook payload on stdin
  * RAG service down / unreachable (the default in CI — no service running)
  * Windows-style paths (backslashes, the runner's real plugin dir)

Plus the success path: a normal target still runs and its stdout passes through.

These tests run the EXACT bootstrap string from ``hooks/hooks.json`` (so a
regression in the wiring is caught), executed without a shell by splitting the
``python3 -c "<payload>" <name> "<fallback>"`` form into argv. The payload is
deliberately free of any double-quote, so the split is unambiguous. A separate
``shell=True`` smoke test proves the full command string also parses through the
host shell on this platform.

The interpreter under test is ``sys.executable`` (not the literal ``python3``)
so the suite never depends on a ``python3`` alias resolving on the runner — the
fail-open *logic* is what we are proving, independent of interpreter discovery.

Stdlib-only (unittest). Run:  python rag-plugin/hooks/test_hook_launcher.py
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

HERE = Path(__file__).resolve().parent            # <plugin>/hooks
PLUGIN_ROOT = HERE.parent                          # <plugin>
HOOKS_JSON = HERE / "hooks.json"
LAUNCHER = HERE / "hook_launcher.py"

BLOCKING_EXIT = 2  # Claude Code hook spec: exit 2 == blocking error.
LITERAL_VAR = "${CLAUDE_PLUGIN_ROOT}"


# --------------------------------------------------------------------------- #
# Helpers: pull the real bootstrap out of hooks.json and run it in isolation. #
# --------------------------------------------------------------------------- #


def _bootstrap_command(target_name: str) -> str:
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    for _event, groups in data["hooks"].items():
        for group in groups:
            for h in group["hooks"]:
                cmd = h["command"]
                if (" " + target_name + " ") in cmd:
                    return cmd
    raise AssertionError("no hook command for " + target_name)


def _split_bootstrap(command: str) -> tuple[str, list[str]]:
    """Extract the FIRST `python3 -c "<payload>" <name> "<fallback>"` segment of
    a (possibly `|| python -c ... || py -3 -c ...` chained) command.
    Returns (payload, [name, fallback]). The payload contains no double-quote by
    design, so the first closing `"` ends it."""
    marker = ' -c "'
    assert marker in command, command
    after = command.split(marker, 1)[1]
    payload, rest = after.split('"', 1)            # payload has no internal "
    rest = rest.strip()
    name, _, tail = rest.partition(" ")
    tail = tail.strip()
    # fallback is the first double-quoted token after the name (ignore any
    # trailing `|| python -c ...` interpreter-fallback segments).
    if tail.startswith('"'):
        fallback = tail[1:].split('"', 1)[0]
    else:
        fallback = tail.split(" ", 1)[0]
    return payload, [name, fallback]


def _run_bootstrap(target_name="retrieval-reminder", *, env_root=None,
                   fallback=None, stdin="", timeout=30):
    """Run the real bootstrap argv under a controlled environment."""
    payload, args = _split_bootstrap(_bootstrap_command(target_name))
    if fallback is not None:
        args[1] = fallback
    env = dict(os.environ)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    if env_root is not None:
        env["CLAUDE_PLUGIN_ROOT"] = env_root
    return subprocess.run(
        [sys.executable, "-c", payload] + args,
        input=stdin, capture_output=True, text=True, timeout=timeout, env=env,
    )


def _temp_plugin(target_body=None, include_target=True,
                 target_filename="prompt_retrieval_reminder.py"):
    """Build a throwaway <tmp>/hooks/ with the real launcher and a controllable
    target. Returns (tmp_root, launcher_path)."""
    tmp = tempfile.mkdtemp(prefix="raghook_")
    hooks = Path(tmp) / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy(str(LAUNCHER), str(hooks / "hook_launcher.py"))
    if include_target:
        body = target_body if target_body is not None else "import sys\nsys.exit(0)\n"
        (hooks / target_filename).write_text(body, encoding="utf-8")
    return tmp, str(hooks / "hook_launcher.py")


# A realistic UserPromptSubmit payload (a question likely to pass the shape gate).
_GOOD_PAYLOAD = json.dumps({"hook_event_name": "UserPromptSubmit",
                            "user_prompt": "What is our deployment process?"})


# --------------------------------------------------------------------------- #
# The headline guarantee: NEVER exit 2, always exit 0, on every failure path. #
# --------------------------------------------------------------------------- #


class TestNeverBlocks(unittest.TestCase):

    def _assert_failopen(self, proc, ctx):
        self.assertNotEqual(proc.returncode, BLOCKING_EXIT,
                            f"{ctx}: returned BLOCKING exit 2\nstderr: {proc.stderr}")
        self.assertEqual(proc.returncode, 0,
                         f"{ctx}: expected exit 0, got {proc.returncode}\nstderr: {proc.stderr}")

    def test_unset_plugin_root(self):
        # env var missing AND fallback left as the literal ${...} (unexpanded).
        proc = _run_bootstrap(env_root=None, fallback=LITERAL_VAR + "/hooks/hook_launcher.py",
                              stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "unset CLAUDE_PLUGIN_ROOT")

    def test_literal_unexpanded_var(self):
        # Simulates a host that passed ${CLAUDE_PLUGIN_ROOT} through literally.
        proc = _run_bootstrap(env_root=LITERAL_VAR,
                              fallback=LITERAL_VAR + "/hooks/hook_launcher.py",
                              stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "literal ${CLAUDE_PLUGIN_ROOT}")

    def test_nonexistent_plugin_root(self):
        proc = _run_bootstrap(env_root=str(Path(tempfile.gettempdir()) / "no_such_rag_plugin_xyz"),
                              fallback=LITERAL_VAR + "/hooks/hook_launcher.py",
                              stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "nonexistent plugin root")

    def test_missing_target_script(self):
        tmp, launcher = _temp_plugin(include_target=False)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(env_root=tmp, fallback=launcher, stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "missing target script")

    def test_target_raises_exception(self):
        tmp, launcher = _temp_plugin(target_body="raise RuntimeError('boom')\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(env_root=tmp, fallback=launcher, stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "target raises")

    def test_target_sys_exit_2_is_normalized(self):
        # The worst case: a target that itself exits 2. The launcher MUST swallow
        # it and exit 0 so the prompt is never blocked.
        tmp, launcher = _temp_plugin(target_body="import sys\nsys.exit(2)\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(env_root=tmp, fallback=launcher, stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "target sys.exit(2)")

    def test_malformed_payload(self):
        proc = _run_bootstrap(env_root=str(PLUGIN_ROOT), stdin="not json at all {{{")
        self._assert_failopen(proc, "malformed payload")

    def test_empty_payload(self):
        proc = _run_bootstrap(env_root=str(PLUGIN_ROOT), stdin="")
        self._assert_failopen(proc, "empty payload")

    def test_service_down_real_target(self):
        # No ragtools service runs in CI; the real target must silent-pass -> 0.
        proc = _run_bootstrap(env_root=str(PLUGIN_ROOT), stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "service down (real target)")

    def test_windows_style_root(self):
        # PLUGIN_ROOT on Windows contains backslashes; ensure path joins survive.
        proc = _run_bootstrap(env_root=str(PLUGIN_ROOT), stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "windows-style root")

    def test_project_focus_target(self):
        proc = _run_bootstrap(target_name="project-focus",
                              env_root=str(PLUGIN_ROOT), stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "project-focus target")

    def test_fallback_arg_recovers_when_env_missing(self):
        # env var missing, but the host-expanded fallback path is valid -> still
        # runs (and still exits 0).
        proc = _run_bootstrap(env_root=None, fallback=str(LAUNCHER), stdin=_GOOD_PAYLOAD)
        self._assert_failopen(proc, "fallback recovery")


# --------------------------------------------------------------------------- #
# Success path: the launcher must NOT swallow the target's stdout.            #
# --------------------------------------------------------------------------- #


class TestSuccessPathPreserved(unittest.TestCase):

    def test_target_stdout_passes_through(self):
        marker = '{"hookSpecificOutput": {"x": 1}}'
        body = "import sys\nsys.stdout.write(%r)\nsys.exit(0)\n" % marker
        tmp, launcher = _temp_plugin(target_body=body)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(env_root=tmp, fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(marker, proc.stdout,
                      "launcher must pass the target's stdout (additionalContext) through")


# --------------------------------------------------------------------------- #
# Guarded mode (the PreToolUse lock hook): intentional exit code passes through;#
# path-resolution failure + unexpected exceptions still fail open.            #
# --------------------------------------------------------------------------- #


class TestGuardedLockHook(unittest.TestCase):

    def test_path_resolution_failure_fails_open(self):
        # Launcher unreachable -> exit 0 (no false block of the Bash tool call).
        proc = _run_bootstrap(target_name="lock-conflict", env_root=None,
                              fallback=LITERAL_VAR + "/hooks/hook_launcher.py",
                              stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_target_fails_open(self):
        tmp, launcher = _temp_plugin(include_target=False)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(target_name="lock-conflict", env_root=tmp,
                              fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_intentional_block_exit_2_passes_through(self):
        # A guarded target that deliberately exits 2 (a hard block) MUST survive —
        # guarded mode preserves the hook's ability to influence the tool call.
        tmp, launcher = _temp_plugin(target_filename="lock_conflict_check.py",
                                     target_body="import sys\nsys.exit(2)\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(target_name="lock-conflict", env_root=tmp,
                              fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 2,
                         "guarded mode must pass an intentional block (exit 2) through")

    def test_silent_pass_exit_0(self):
        tmp, launcher = _temp_plugin(target_filename="lock_conflict_check.py",
                                     target_body="import sys\nsys.exit(0)\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(target_name="lock-conflict", env_root=tmp,
                              fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_unexpected_exception_fails_open(self):
        # Even guarded mode fails open on an UNEXPECTED crash — never a false block.
        tmp, launcher = _temp_plugin(target_filename="lock_conflict_check.py",
                                     target_body="raise RuntimeError('boom')\n")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(target_name="lock-conflict", env_root=tmp,
                              fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_ask_decision_stdout_passes_through(self):
        ask = '{"hookSpecificOutput": {"permissionDecision": "ask"}}'
        body = "import sys\nsys.stdout.write(%r)\nsys.exit(0)\n" % ask
        tmp, launcher = _temp_plugin(target_filename="lock_conflict_check.py",
                                     target_body=body)
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        proc = _run_bootstrap(target_name="lock-conflict", env_root=tmp,
                              fallback=launcher, stdin=_GOOD_PAYLOAD)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(ask, proc.stdout, "guarded mode must pass the ask decision through")

    def test_real_lock_target_silent_passes(self):
        # Real lock_conflict_check.py with a non-Bash payload -> silent pass -> 0.
        payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Read",
                              "tool_input": {}})
        proc = _run_bootstrap(target_name="lock-conflict", env_root=str(PLUGIN_ROOT),
                              stdin=payload)
        self.assertEqual(proc.returncode, 0, proc.stderr)


# --------------------------------------------------------------------------- #
# Wiring guards: hooks.json must stay fail-open; full string must parse in the #
# host shell on this platform.                                                #
# --------------------------------------------------------------------------- #


class TestWiringStaysFailOpen(unittest.TestCase):

    def _all_commands(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        return [h["command"] for groups in data["hooks"].values()
                for g in groups for h in g["hooks"]]

    def test_no_command_invokes_a_raw_script_path(self):
        # The dangerous raw form (python ${ROOT}/hooks/<script>.py with no -c)
        # must NOT be how ANY hook script is invoked — every command goes through
        # the -c bootstrap + launcher.
        for cmd in self._all_commands():
            self.assertIn(" -c ", cmd, "every hook must use the -c inline bootstrap")
            self.assertNotRegex(
                cmd, r"python\d?\s+\$\{CLAUDE_PLUGIN_ROOT\}/hooks/\w+\.py",
                "no hook may invoke a raw script file path")

    def test_every_command_has_interpreter_fallback(self):
        # python3 -> python -> py-3 chain so the hook runs where python3 is not
        # the interpreter name (a missing interpreter is non-blocking by spec).
        for cmd in self._all_commands():
            self.assertIn("python3 -c ", cmd)
            self.assertIn("|| python -c ", cmd)
            self.assertIn("|| py -3 -c ", cmd)

    def test_pretooluse_lock_hook_is_guarded_bootstrap(self):
        # The lock hook is now routed through the bootstrap (guarded mode): it
        # uses -c + the lock-conflict target, and is NOT the raw script form, so
        # a path-resolution failure can no longer falsely block a Bash tool call.
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        cmd = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        self.assertIn(" -c ", cmd)
        self.assertIn(" lock-conflict ", cmd)
        self.assertIn("hook_launcher.py", cmd)
        self.assertNotRegex(cmd, r"python\d?\s+\$\{CLAUDE_PLUGIN_ROOT\}/hooks/lock_conflict_check\.py")

    def test_full_command_string_parses_in_host_shell(self):
        # Prove the entire command string (as the host shell receives it) parses
        # and exits non-blocking. Substitute the leading interpreter token so the
        # test does not depend on a 'python3' alias.
        #
        # NOTE: shell=True is intentional here and is the whole point — this test
        # validates how the HOST SHELL parses the command string (the failure
        # surface of D-031). The command is sourced from our own in-repo
        # hooks.json plus sys.executable; there is no untrusted/user input, so
        # there is no command-injection exposure.
        cmd = _bootstrap_command("retrieval-reminder")
        assert cmd.startswith("python3 ")
        shell_cmd = '"%s" %s' % (sys.executable, cmd[len("python3 "):])
        env = dict(os.environ)
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
        proc = subprocess.run(shell_cmd, shell=True, input=_GOOD_PAYLOAD,
                              capture_output=True, text=True, timeout=30, env=env)
        self.assertNotEqual(proc.returncode, BLOCKING_EXIT,
                            f"shell parse exit 2\nstderr: {proc.stderr}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
