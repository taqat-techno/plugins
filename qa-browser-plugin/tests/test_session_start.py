#!/usr/bin/env python3
"""Behavior of hooks/session_start_target_check.py, invoked as Claude Code does.

Contract:
  * no .qa-browser.local.json         -> exit 0, no output at all
  * config tracked by git / unignored -> exit 0, SessionStart hook JSON on stdout
    (hookSpecificOutput.additionalContext + systemMessage), nothing on stderr
    (exit-0 stderr from SessionStart reaches only the debug log)
  * clean, ignored, untracked config  -> exit 0, no output

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

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "session_start_target_check.py"
CONFIG = ".qa-browser.local.json"
GIT = shutil.which("git")


def run(cwd: str):
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup"})
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload.encode("utf-8"),
                          capture_output=True, cwd=cwd, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def git(cwd: str, *args: str) -> None:
    subprocess.run([GIT, *args], cwd=cwd, check=True, capture_output=True, timeout=30)


class SessionStartHook(unittest.TestCase):
    def test_silent_without_config(self):
        with tempfile.TemporaryDirectory() as cwd:
            code, out, err = run(cwd)
        self.assertEqual((code, out, err), (0, "", ""))

    @unittest.skipIf(GIT is None, "git not on PATH")
    def test_tracked_config_warning_is_hook_json_on_stdout(self):
        with tempfile.TemporaryDirectory() as cwd:
            git(cwd, "init", "-q")
            Path(cwd, CONFIG).write_text(
                json.dumps({"targetUrl": "https://staging.example.test"}), encoding="utf-8")
            git(cwd, "add", CONFIG)
            code, out, err = run(cwd)
        self.assertEqual(code, 0)
        self.assertEqual(err, "", "warnings must not go to stderr")
        data = json.loads(out)
        hso = data["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "SessionStart")
        self.assertIn("DANGER", hso["additionalContext"])
        self.assertIn("tracked by git", hso["additionalContext"])
        self.assertIn("not in .gitignore", hso["additionalContext"])
        self.assertEqual(data["systemMessage"], hso["additionalContext"])

    @unittest.skipIf(GIT is None, "git not on PATH")
    def test_production_target_message_names_the_real_override(self):
        with tempfile.TemporaryDirectory() as cwd:
            git(cwd, "init", "-q")
            Path(cwd, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(cwd, CONFIG).write_text(
                json.dumps({"targetUrl": "https://app.production.example.com"}),
                encoding="utf-8")
            code, out, err = run(cwd)
        self.assertEqual((code, err), (0, ""))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("QA_BROWSER_ALLOW_PRODUCTION=1", ctx)
        self.assertNotIn("--allow-production", ctx)

    @unittest.skipIf(GIT is None, "git not on PATH")
    def test_clean_config_is_silent(self):
        with tempfile.TemporaryDirectory() as cwd:
            git(cwd, "init", "-q")
            Path(cwd, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(cwd, CONFIG).write_text(
                json.dumps({"targetUrl": "https://staging.example.test"}), encoding="utf-8")
            code, out, err = run(cwd)
        self.assertEqual((code, out, err), (0, "", ""))

    @unittest.skipIf(GIT is None, "git not on PATH")
    def test_products_path_is_not_a_production_marker(self):
        with tempfile.TemporaryDirectory() as cwd:
            git(cwd, "init", "-q")
            Path(cwd, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(cwd, CONFIG).write_text(
                json.dumps({"targetUrl": "https://shop.example.com/products"}),
                encoding="utf-8")
            code, out, err = run(cwd)
        self.assertEqual((code, out, err), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
