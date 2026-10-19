#!/usr/bin/env python3
"""0.9.0 safety behaviour, offline.

  * production gate: user-level `production_hosts` option; tracked config with
    inline credentials denies navigation; env-referenced config does not;
  * SessionStart: inline-credential warning, qa-evidence/ not ignored, pattern-
    ignored config is clean, CLAUDE_PROJECT_DIR is honoured;
  * click skiplist hook: selector / text / has-text matches ask, chrome-devtools
    uid clicks and missing config are silent, garbage fails open.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / "hooks" / "pre_navigate_prod_gate.py"
SESSION = ROOT / "hooks" / "session_start_target_check.py"
CLICK = ROOT / "hooks" / "pre_click_skiplist.py"
HOOKS_JSON = ROOT / "hooks" / "hooks.json"
CONFIG = ".qa-browser.local.json"
GIT = shutil.which("git")
PW = "mcp__plugin_playwright_playwright__"
CD = "mcp__plugin_chrome-devtools-mcp_chrome-devtools__"


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_PROJECT_DIR", "QA_BROWSER_ALLOW_PRODUCTION")
           and not k.upper().startswith("CLAUDE_PLUGIN_OPTION_")}
    env.update(extra)
    return env


def hook(script, cwd, payload, **env):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run([sys.executable, str(script)], input=raw.encode("utf-8"),
                          capture_output=True, cwd=str(cwd), env=clean_env(**env), timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def git(cwd, *args):
    subprocess.run([GIT, *args], cwd=str(cwd), check=True, capture_output=True, timeout=30)


def hso(out):
    return json.loads(out)["hookSpecificOutput"]


INLINE = {"targetUrl": "https://staging.example.com",
          "roles": {"admin": {"username": "qa@example.com", "password": "example-only"}}}
ENVREF = {"targetUrl": "https://staging.example.com",
          "roles": {"admin": {"username": "qa@example.com", "passwordEnv": "QA_ADMIN_PASSWORD"}}}
NAV = {"tool_name": PW + "browser_navigate", "tool_input": {"url": "https://staging.example.com/x"}}


class GateOption(unittest.TestCase):
    def test_user_level_production_hosts_block(self):
        with tempfile.TemporaryDirectory() as d:
            payload = {"tool_name": PW + "browser_navigate",
                       "tool_input": {"url": "https://shop.example.com/"}}
            self.assertEqual(hook(GATE, d, payload), (0, "", ""))
            code, _, err = hook(GATE, d, payload,
                                CLAUDE_PLUGIN_OPTION_PRODUCTION_HOSTS="www.example.org, shop.example.com")
        self.assertEqual(code, 2)
        self.assertIn("productionHosts", err)


@unittest.skipIf(GIT is None, "git not on PATH")
class GateTrackedConfig(unittest.TestCase):
    def _repo(self, d, cfg, track):
        git(d, "init", "-q")
        Path(d, CONFIG).write_text(json.dumps(cfg), encoding="utf-8")
        if track:
            git(d, "add", CONFIG)

    def test_tracked_inline_credentials_deny_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d, INLINE, track=True)
            code, out, err = hook(GATE, d, NAV)
        self.assertEqual(code, 0)
        h = hso(out)
        self.assertEqual(h["permissionDecision"], "deny")
        self.assertIn("tracked by git", h["permissionDecisionReason"])
        self.assertNotIn("example-only", out + err)

    def test_untracked_inline_credentials_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d, INLINE, track=False)
            self.assertEqual(hook(GATE, d, NAV), (0, "", ""))

    def test_tracked_env_reference_config_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            self._repo(d, ENVREF, track=True)
            self.assertEqual(hook(GATE, d, NAV), (0, "", ""))


@unittest.skipIf(GIT is None, "git not on PATH")
class SessionStartV09(unittest.TestCase):
    def _ctx(self, d, **env):
        code, out, err = hook(SESSION, d, {"hook_event_name": "SessionStart"}, **env)
        self.assertEqual((code, err), (0, ""))
        return hso(out)["additionalContext"] if out.strip() else ""

    def test_inline_credentials_warn_without_value(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            Path(d, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(d, CONFIG).write_text(json.dumps(INLINE), encoding="utf-8")
            ctx = self._ctx(d)
        self.assertIn("inline", ctx)
        self.assertIn("admin", ctx)
        self.assertNotIn("example-only", ctx)

    def test_env_reference_config_is_silent(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            Path(d, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(d, CONFIG).write_text(json.dumps(ENVREF), encoding="utf-8")
            self.assertEqual(self._ctx(d), "")

    def test_pattern_ignored_config_counts_as_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            Path(d, ".gitignore").write_text("*.local.json\n", encoding="utf-8")
            Path(d, CONFIG).write_text(json.dumps(ENVREF), encoding="utf-8")
            self.assertEqual(self._ctx(d), "")

    def test_unignored_evidence_dir_warns(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            Path(d, ".gitignore").write_text(CONFIG + "\n", encoding="utf-8")
            Path(d, CONFIG).write_text(json.dumps(ENVREF), encoding="utf-8")
            Path(d, "qa-evidence").mkdir()
            self.assertIn("qa-evidence/ is not git-ignored", self._ctx(d))
            Path(d, ".gitignore").write_text(CONFIG + "\nqa-evidence/\n", encoding="utf-8")
            self.assertEqual(self._ctx(d), "")

    def test_project_dir_env_is_used(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
            git(d, "init", "-q")
            Path(d, CONFIG).write_text(json.dumps(ENVREF), encoding="utf-8")
            self.assertIn("not in .gitignore", self._ctx(other, CLAUDE_PROJECT_DIR=d))


class ClickSkiplist(unittest.TestCase):
    CFG = {"doNotClick": ["button:has-text('Refund')", "#purge-all"],
           "doNotClickText": ["Delete account"]}

    def run_click(self, tool_input, tool=PW + "browser_click", cfg=CFG, raw=None):
        with tempfile.TemporaryDirectory() as d:
            if cfg is not None:
                Path(d, CONFIG).write_text(json.dumps(cfg), encoding="utf-8")
            payload = raw if raw is not None else {"tool_name": tool, "tool_input": tool_input}
            return hook(CLICK, d, payload)

    def assert_ask(self, result, needle):
        code, out, err = result
        self.assertEqual((code, err), (0, ""))
        h = hso(out)
        self.assertEqual(h["permissionDecision"], "ask")
        self.assertIn(needle, h["permissionDecisionReason"])

    def test_text_entry_matches_element_description(self):
        self.assert_ask(self.run_click({"element": "Delete account button", "target": "e14"}),
                        "Delete account")

    def test_has_text_selector_yields_text_pattern(self):
        self.assert_ask(self.run_click({"element": "Refund order #12", "target": "e3"}), "Refund")

    def test_selector_exact_match(self):
        self.assert_ask(self.run_click({"element": "red button", "target": "#PURGE-ALL"}),
                        "#purge-all")

    def test_harmless_click_silent(self):
        self.assertEqual(self.run_click({"element": "Next page", "target": "e9"}), (0, "", ""))

    def test_chrome_devtools_uid_click_silent(self):
        self.assertEqual(self.run_click({"uid": "1_23"}, tool=CD + "click"), (0, "", ""))

    def test_no_config_or_garbage_fails_open(self):
        self.assertEqual(self.run_click({"element": "Delete account"}, cfg=None), (0, "", ""))
        self.assertEqual(self.run_click(None, raw="not json"), (0, "", ""))
        self.assertEqual(self.run_click(None, raw='{"tool_input": "x"}'), (0, "", ""))

    def test_matcher_targets_click_tools_only(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        groups = [g for g in data["hooks"]["PreToolUse"]
                  if "pre_click_skiplist.py" in g["hooks"][0]["command"]]
        self.assertEqual(len(groups), 1)
        matcher = re.compile(groups[0]["matcher"])
        for name in (PW + "browser_click", CD + "click", "mcp__playwright__browser_click"):
            self.assertTrue(matcher.search(name), name)
        for name in (PW + "browser_navigate", PW + "browser_snapshot", CD + "navigate_page"):
            self.assertFalse(matcher.search(name), name)


if __name__ == "__main__":
    unittest.main()
