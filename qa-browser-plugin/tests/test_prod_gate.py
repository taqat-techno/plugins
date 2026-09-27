#!/usr/bin/env python3
"""Behavior of hooks/pre_navigate_prod_gate.py, invoked exactly as Claude Code does.

Contract:
  * production URL, no override  -> exit 2, reason on stderr (Claude sees it)
  * production URL, override set -> exit 0, audit line as PreToolUse
    additionalContext JSON (exit-0 stderr reaches nobody), no permissionDecision
  * any other URL                -> exit 0, silent, override or not

    python tests/test_prod_gate.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pre_navigate_prod_gate.py"
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"


def run(url: str | None, override: bool = False, raw: str | None = None):
    env = {k: v for k, v in os.environ.items() if k != OVERRIDE_ENV}
    if override:
        env[OVERRIDE_ENV] = "1"
    payload = raw if raw is not None else json.dumps(
        {"tool_name": "mcp__plugin_playwright_playwright__browser_navigate",
         "tool_input": {"url": url} if url else {}})
    # Run from an empty dir so no .qa-browser.local.json changes the default markers.
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run([sys.executable, str(HOOK)], input=payload.encode("utf-8"),
                              capture_output=True, env=env, cwd=cwd, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


class ProdGate(unittest.TestCase):
    def test_production_url_blocked_without_override(self):
        code, out, err = run("https://app.production.example.com/login")
        self.assertEqual(code, 2)
        self.assertEqual(out.strip(), "")
        self.assertIn("BLOCKED", err)

    def test_production_url_with_override_notifies_claude(self):
        code, out, err = run("https://prod.example.com/", override=True)
        self.assertEqual(code, 0)
        self.assertEqual(err.strip(), "")
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", hso)
        self.assertIn("ALLOWED", hso["additionalContext"])
        self.assertIn("prod.example.com", hso["additionalContext"])

    def test_non_production_url_silent_with_override(self):
        self.assertEqual(run("http://localhost:3000/", override=True), (0, "", ""))

    def test_non_production_url_silent(self):
        self.assertEqual(run("http://localhost:3000/"), (0, "", ""))

    def test_no_url_and_garbage_fail_open(self):
        self.assertEqual(run(None), (0, "", ""))
        self.assertEqual(run(None, raw="not json"), (0, "", ""))
        self.assertEqual(run(None, raw="[1, 2]"), (0, "", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
