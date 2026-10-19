#!/usr/bin/env python3
"""edge-tts narration must never go through a shell.

The caption text is a command-line argument. With shell=True on Windows (the
old behaviour) cmd.exe parses it, so a caption such as `Save & calc` runs
`calc`. The fix resolves edge-tts with shutil.which and passes an argv list
with no shell; a missing binary, or a .bat/.cmd shim that Windows would hand to
cmd.exe anyway, is reported and narration is skipped.

Proven offline: subprocess.run is replaced by a double that records what
production code ASKED FOR.

    python tests/test_narration.py
"""
from __future__ import annotations

import ast
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_remotion  # noqa: E402

EXE = str(Path(tempfile.gettempdir()) / "bin" / "edge-tts.exe")


class _Result:
    returncode = 0


class Narration(unittest.TestCase):
    def setUp(self):
        self.project = Path(tempfile.mkdtemp(prefix="sr-narrate-"))
        self.calls = []
        self.warnings = []

    def tearDown(self):
        shutil.rmtree(self.project, ignore_errors=True)

    def _run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        Path(argv[argv.index("--write-media") + 1]).write_bytes(b"mp3")
        return _Result()

    def _narrate(self, which_result, scenes):
        with mock.patch.object(build_remotion.shutil, "which", return_value=which_result), \
             mock.patch.object(build_remotion.subprocess, "run", side_effect=self._run), \
             mock.patch.object(build_remotion, "warn", side_effect=self.warnings.append):
            build_remotion.narrate(scenes, self.project, "en-US-AriaNeural")

    def test_argv_list_without_shell(self):
        scenes = [{"type": "step", "caption": "Save & calc | whoami %PATH%"}]
        self._narrate(EXE, scenes)
        self.assertEqual(len(self.calls), 1)
        argv, kwargs = self.calls[0]
        self.assertIsInstance(argv, list)
        self.assertEqual(argv[0], EXE)
        self.assertIn("Save & calc | whoami %PATH%", argv)  # one intact argument
        self.assertFalse(kwargs.get("shell", False))
        self.assertTrue(scenes[0]["audio"].startswith("audio/"))

    def test_not_found_is_reported_and_skipped(self):
        scenes = [{"type": "step", "caption": "hello"}]
        self._narrate(None, scenes)
        self.assertEqual(self.calls, [])
        self.assertTrue(any("not on PATH" in w for w in self.warnings))
        self.assertNotIn("audio", scenes[0])

    def test_batch_shim_is_refused(self):
        for shim in ("C:\\tools\\edge-tts.cmd", "C:\\tools\\edge-tts.BAT"):
            self.calls.clear()
            self.warnings.clear()
            self._narrate(shim, [{"type": "step", "caption": "hello"}])
            self.assertEqual(self.calls, [])
            self.assertTrue(any("batch shim" in w for w in self.warnings))

    def test_source_has_no_shell_true_in_narration(self):
        tree = ast.parse((SCRIPTS / "build_remotion.py").read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "narrate")
        shell_kwargs = [kw for n in ast.walk(fn) if isinstance(n, ast.Call)
                        for kw in n.keywords if kw.arg == "shell"]
        self.assertEqual(shell_kwargs, [])


if __name__ == "__main__":
    unittest.main()
