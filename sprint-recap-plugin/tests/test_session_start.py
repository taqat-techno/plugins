#!/usr/bin/env python3
"""The SessionStart check must put its warnings where they are actually read.

Stderr from an exit-0 SessionStart hook is never shown, so the warnings the
hook exists for (an un-ignored password file, a tracked credentials page) were
silently dropped. They must arrive on stdout as hookSpecificOutput JSON with
hookEventName "SessionStart" and additionalContext, and the hook must still
exit 0.

    python tests/test_session_start.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "session_start_config_check.py"
GIT = shutil.which("git")


def run_in(cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, str(HOOK)], cwd=cwd, input=b"{}",
        capture_output=True, timeout=30,
    )
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


class SessionStartOutputContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sr-session-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_silent_when_project_does_not_use_sprint_recap(self):
        self.assertEqual(run_in(self.tmp), (0, "", ""))

    def test_missing_config_warning_is_additional_context_json(self):
        (self.tmp / ".sprint-recap").mkdir()
        code, out, err = run_in(self.tmp)
        self.assertEqual(code, 0)
        self.assertEqual(err.strip(), "")
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SessionStart")
        self.assertIn(".sprint-recap.local.json is missing", hso["additionalContext"])
        self.assertTrue(hso["additionalContext"].startswith("[sprint-recap]"))

    @unittest.skipUnless(GIT, "git not on PATH")
    def test_unignored_config_warning_reaches_stdout(self):
        subprocess.run([GIT, "init", "-q"], cwd=self.tmp, check=True)
        (self.tmp / ".sprint-recap.local.json").write_text("{}", encoding="utf-8")
        code, out, err = run_in(self.tmp)
        self.assertEqual(code, 0)
        self.assertEqual(err.strip(), "")
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("is not gitignored", ctx)


if __name__ == "__main__":
    unittest.main()
