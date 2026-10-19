#!/usr/bin/env python3
"""Behavior of hooks/pre_navigate_prod_gate.py, invoked exactly as Claude Code does.

Contract (decision rules are owned by the hook's docstring):
  * production host, no override  -> exit 2, reason on stderr (Claude sees it)
  * production host, override set -> exit 0, audit line as PreToolUse
    additionalContext JSON, no permissionDecision
  * unknown host with a QA target configured -> exit 0, permissionDecision "ask"
  * target / allow-listed / local host, or no config -> exit 0, silent
  * matching is on the hostname only: "/products" paths are not production

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "pre_navigate_prod_gate.py"
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"
CONFIG = ".qa-browser.local.json"

PW = "mcp__plugin_playwright_playwright__"
CD = "mcp__plugin_chrome-devtools-mcp_chrome-devtools__"
CIC = "mcp__claude-in-chrome__"

TARGET = {"targetUrl": "https://shop.example.com",
          "productionHosts": ["www.example.com"]}


def run(tool_input=None, tool=PW + "browser_navigate", config=None,
        override=False, raw=None, subdir=False):
    env = {k: v for k, v in os.environ.items()
           if k not in (OVERRIDE_ENV, "CLAUDE_PROJECT_DIR")}
    if override:
        env[OVERRIDE_ENV] = "1"
    payload = raw if raw is not None else json.dumps(
        {"tool_name": tool, "tool_input": tool_input or {}})
    with tempfile.TemporaryDirectory() as root:
        if config is not None:
            Path(root, CONFIG).write_text(json.dumps(config), encoding="utf-8")
        cwd = Path(root)
        if subdir:
            cwd = cwd / "a" / "b"
            cwd.mkdir(parents=True)
        proc = subprocess.run([sys.executable, str(HOOK)], input=payload.encode("utf-8"),
                              capture_output=True, env=env, cwd=str(cwd), timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def decision(out: str):
    return json.loads(out)["hookSpecificOutput"].get("permissionDecision") if out.strip() else None


class ProdGate(unittest.TestCase):
    # --- legacy contract -------------------------------------------------
    def test_production_url_blocked_without_override(self):
        code, out, err = run({"url": "https://app.production.example.com/login"})
        self.assertEqual(code, 2)
        self.assertEqual(out.strip(), "")
        self.assertIn("BLOCKED", err)
        self.assertNotIn("--allow-production", err)
        self.assertIn("relaunch", err)

    def test_production_url_with_override_notifies_claude(self):
        code, out, err = run({"url": "https://prod.example.com/"}, override=True)
        self.assertEqual(code, 0)
        self.assertEqual(err.strip(), "")
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", hso)
        self.assertIn("ALLOWED", hso["additionalContext"])
        self.assertIn("prod.example.com", hso["additionalContext"])

    def test_non_production_url_silent(self):
        self.assertEqual(run({"url": "http://localhost:3000/"}), (0, "", ""))
        self.assertEqual(run({"url": "http://localhost:3000/"}, override=True), (0, "", ""))

    def test_no_url_and_garbage_fail_open(self):
        self.assertEqual(run(None), (0, "", ""))
        self.assertEqual(run(None, raw="not json"), (0, "", ""))
        self.assertEqual(run(None, raw="[1, 2]"), (0, "", ""))
        self.assertEqual(run(None, raw='{"tool_input": "x"}'), (0, "", ""))

    # --- host-based decisions --------------------------------------------
    def test_products_path_on_target_host_allowed(self):
        self.assertEqual(run({"url": "https://shop.example.com/products"}, config=TARGET),
                         (0, "", ""))

    def test_products_path_without_config_allowed(self):
        self.assertEqual(run({"url": "https://staging.example.com/products"}), (0, "", ""))

    def test_prod_label_blocked(self):
        code, _, err = run({"url": "https://app.prod.example.com"}, config=TARGET)
        self.assertEqual(code, 2)
        self.assertIn("production marker 'prod'", err)

    def test_prod_hyphen_part_blocked(self):
        self.assertEqual(run({"url": "https://app-prod.example.com"})[0], 2)

    def test_configured_production_host_blocked(self):
        code, _, err = run({"url": "https://www.example.com"}, config=TARGET)
        self.assertEqual(code, 2)
        self.assertIn("productionHosts", err)

    def test_production_host_beats_allowlist(self):
        cfg = dict(TARGET, allowedHosts=["www.example.com"])
        self.assertEqual(run({"url": "https://www.example.com/"}, config=cfg)[0], 2)

    def test_unknown_host_with_config_asks(self):
        code, out, err = run({"url": "https://other.example.org/"}, config=TARGET)
        self.assertEqual((code, err), (0, ""))
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "ask")
        self.assertIn("other.example.org", hso["permissionDecisionReason"])

    def test_allowed_hosts_and_local_hosts_allowed(self):
        cfg = dict(TARGET, allowedHosts=["*.staging.example.net", "auth.example.org"])
        for url in ("https://a.staging.example.net/x", "https://auth.example.org/login",
                    "http://127.0.0.1:8000", "http://[::1]:3000/", "http://app.localhost",
                    "http://shop.test/", "about:blank", "/relative/path"):
            with self.subTest(url=url):
                self.assertEqual(run({"url": url}, config=cfg), (0, "", ""))

    def test_vanity_marker_with_dot_matches_host(self):
        cfg = {"productionMarkers": ["app.example.com"]}
        self.assertEqual(run({"url": "https://app.example.com/"}, config=cfg)[0], 2)
        self.assertEqual(run({"url": "https://staging.example.com/app.example.com"},
                             config=cfg), (0, "", ""))

    def test_config_found_from_subdirectory(self):
        self.assertEqual(run({"url": "https://www.example.com"}, config=TARGET,
                             subdir=True)[0], 2)

    # --- widened tool coverage --------------------------------------------
    def test_new_page_gated(self):
        self.assertEqual(run({"url": "https://app.prod.example.com"}, tool=CD + "new_page")[0], 2)

    def test_browser_tabs_new_gated(self):
        self.assertEqual(run({"action": "new", "url": "https://www.example.com"},
                             tool=PW + "browser_tabs", config=TARGET)[0], 2)
        self.assertEqual(run({"action": "list"}, tool=PW + "browser_tabs"), (0, "", ""))

    def test_claude_in_chrome_navigate_gated(self):
        self.assertEqual(run({"url": "https://prod.example.com", "tabId": 1},
                             tool=CIC + "navigate")[0], 2)

    def test_evaluate_with_location_assignment_gated(self):
        js = "() => { window.location='https://prod.example.com/admin'; }"
        self.assertEqual(run({"function": js}, tool=PW + "browser_evaluate")[0], 2)
        self.assertEqual(run({"function": js}, tool=CD + "evaluate_script")[0], 2)
        self.assertEqual(run({"text": "location.href = 'https://prod.example.com'"},
                             tool=CIC + "javascript_tool")[0], 2)
        self.assertEqual(run({"code": "await page.goto('https://prod.example.com');"},
                             tool=PW + "browser_run_code_unsafe")[0], 2)
        self.assertEqual(run({"function": "() => window.open('https://other.example.org')"},
                             tool=PW + "browser_evaluate", config=TARGET)[0:1], (0,))
        self.assertEqual(decision(run({"function": "() => window.open('https://other.example.org')"},
                                      tool=PW + "browser_evaluate", config=TARGET)[1]), "ask")

    def test_evaluate_without_navigation_allowed(self):
        js = "() => fetch('https://prod.example.com/api').then(r => r.status)"
        self.assertEqual(run({"function": js}, tool=PW + "browser_evaluate"), (0, "", ""))
        self.assertEqual(run({"function": "() => location.href === 'https://prod.example.com'"},
                             tool=PW + "browser_evaluate"), (0, "", ""))

    def test_matcher_covers_gated_tools(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        matcher = re.compile(data["hooks"]["PreToolUse"][0]["matcher"])
        for name in (CD + "navigate_page", CD + "new_page", CD + "evaluate_script",
                     PW + "browser_navigate", PW + "browser_tabs", PW + "browser_evaluate",
                     PW + "browser_run_code_unsafe", CIC + "navigate", CIC + "javascript_tool",
                     "mcp__Claude_Browser__navigate", "mcp__playwright__browser_navigate"):
            with self.subTest(name=name):
                self.assertTrue(matcher.search(name))
        for name in (PW + "browser_click", PW + "browser_snapshot", CD + "take_screenshot"):
            with self.subTest(name=name):
                self.assertFalse(matcher.search(name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
