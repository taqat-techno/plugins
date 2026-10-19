"""Offline checks for the portable hook launcher in hooks/hooks.json.

Every python hook is launched through one POSIX-sh snippet:

    s="${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"; [ -f "$s" ] || exit 0;
    for c in python3 python py; do command -v $c ... ; $c "$s" ...;
    r=$?; [ $r -eq 49 ] || exit $r; done; exit 0

These tests prove the properties the launcher exists for:
  * the plugin root is quoted, so a path containing a space still runs the hook
    (unquoted, python got a truncated path and exited 2 -> every call blocked);
  * an unresolved root / missing script exits 0, never 2 (2 is the blocking code);
  * the hook's own exit code (e.g. a deliberate 2) is propagated unchanged;
  * no python on PATH exits 0 instead of erroring.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
SH = shutil.which("sh")
SCRIPT_RE = re.compile(r'"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/([^"]+\.py)"')


def _command_hooks():
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    for event, groups in data.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("type") == "command":
                    yield event, hook["command"]


def _run(command, root, path=None):
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(root))
    if path is not None:
        env["PATH"] = path
    return subprocess.run([SH, "-c", command], input=b'{"prompt": "\xd8\xb9"}',
                          env=env, capture_output=True, timeout=60)


class HookLauncherTests(unittest.TestCase):
    def test_hooks_exist(self):
        self.assertTrue(list(_command_hooks()), "no command hooks found")

    def test_root_always_quoted_and_launcher_used(self):
        for event, cmd in _command_hooks():
            with self.subTest(event=event):
                for m in re.finditer(r"\$\{CLAUDE_PLUGIN_ROOT\}", cmd):
                    self.assertEqual(cmd[m.start() - 1], '"', f"unquoted root: {cmd}")
                self.assertIn("for c in python3 python py", cmd)

    def test_referenced_scripts_exist(self):
        for event, cmd in _command_hooks():
            with self.subTest(event=event):
                m = SCRIPT_RE.search(cmd)
                self.assertIsNotNone(m, cmd)
                self.assertTrue((PLUGIN_ROOT / "hooks" / m.group(1)).is_file(), m.group(1))

    @unittest.skipUnless(SH, "sh not available")
    def test_unresolved_root_exits_zero(self):
        for event, cmd in _command_hooks():
            with self.subTest(event=event):
                self.assertEqual(_run(cmd, "/nonexistent/plugin root").returncode, 0)

    @unittest.skipUnless(SH, "sh not available")
    def test_space_in_root_runs_hook_and_propagates_exit_code(self):
        for event, cmd in _command_hooks():
            rel = SCRIPT_RE.search(cmd).group(1)
            with self.subTest(event=event), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp) / "plugin root with space"
                stub = root / "hooks" / rel
                stub.parent.mkdir(parents=True)
                stub.write_text("import sys\nsys.stdin.buffer.read()\nsys.exit(2)\n", encoding="utf-8")
                self.assertEqual(_run(cmd, root).returncode, 2)

    @unittest.skipUnless(SH, "sh not available")
    def test_no_python_on_path_exits_zero(self):
        with tempfile.TemporaryDirectory() as empty:
            for event, cmd in _command_hooks():
                with self.subTest(event=event):
                    self.assertEqual(_run(cmd, PLUGIN_ROOT, path=empty).returncode, 0)


if __name__ == "__main__":
    unittest.main()
