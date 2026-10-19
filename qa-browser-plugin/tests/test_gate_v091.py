#!/usr/bin/env python3
"""0.9.1 gate hardening (re-audit RA-QAB-01..04), offline.

  * RA-QAB-01 browser-style URL normalisation; undeterminable host -> ask
  * RA-QAB-02 browser_batch (nested actions) and preview_start are gated
  * RA-QAB-03 fetch / XHR / sendBeacon gated; run-time URLs ask when production
    hosts are configured; Bash curl / wget / httpie to production hosts blocked
  * RA-QAB-04 credential env names allow-listed (QA_* or the option)

    python -m pytest -q -p no:cacheprovider tests/test_gate_v091.py
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
SESSION = PLUGIN_ROOT / "hooks" / "session_start_target_check.py"
TOTP = PLUGIN_ROOT / "scripts" / "totp.py"
HOOKS_JSON = PLUGIN_ROOT / "hooks" / "hooks.json"
CONFIG = ".qa-browser.local.json"
OVERRIDE_ENV = "QA_BROWSER_ALLOW_PRODUCTION"

PW = "mcp__plugin_playwright_playwright__"
CB = "mcp__Claude_Browser__"
CIC = "mcp__claude-in-chrome__"

PROD = {"targetUrl": "https://shop.example.com", "productionHosts": ["app.example.com"]}

sys.dont_write_bytecode = True


def _env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in (OVERRIDE_ENV, "CLAUDE_PROJECT_DIR")
           and not k.upper().startswith("CLAUDE_PLUGIN_OPTION_")}
    env.update(extra or {})
    return env


def run(tool_input, tool=PW + "browser_navigate", config=None, env=None, files=None):
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    with tempfile.TemporaryDirectory() as root:
        if config is not None:
            Path(root, CONFIG).write_text(json.dumps(config), encoding="utf-8")
        for rel, text in (files or {}).items():
            p = Path(root, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(HOOK)], input=payload.encode("utf-8"),
                              capture_output=True, env=_env(env), cwd=root, timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def decision(out: str):
    return json.loads(out)["hookSpecificOutput"].get("permissionDecision") if out.strip() else None


def verdict(result) -> str:
    code, out, _ = result
    if code == 2:
        return "block"
    return decision(out) or "allow"


class UrlNormalisation(unittest.TestCase):
    """RA-QAB-01: every browser-equivalent spelling of a production URL is blocked."""

    def test_browser_equivalent_forms_blocked(self):
        for url in ("https:\\\\app.example.com/x", "https:/app.example.com/x",
                    "https:app.example.com", "https:///app.example.com",
                    "//app.example.com/x", "\\\\app.example.com/x",
                    "  https://app.example.com/x \n", "https://app.exa\tmple.com",
                    "https://qa:pw@app.example.com/", "https://shop.example.com@app.example.com",
                    "HTTPS://APP.EXAMPLE.COM/", "https://app.example.com./",
                    "https://app.example.com:8443/", "https://%61pp.example.com/",
                    "https://app．example。com/", "view-source:https://app.example.com",
                    "blob:https://app.example.com/uuid",
                    "javascript:location='https://app.example.com'"):
            with self.subTest(url=url):
                self.assertEqual(verdict(run({"url": url}, config=PROD)), "block")

    def test_idn_hosts_compared_as_punycode(self):
        cfg = dict(PROD, productionHosts=["bücher.example"])
        self.assertEqual(verdict(run({"url": "https://xn--bcher-kva.example/"}, config=cfg)), "block")
        self.assertEqual(verdict(run({"url": "https://BÜCHER.example/"}, config=cfg)), "block")
        # a homograph (Cyrillic a) is a different host: not production, but unknown -> ask
        self.assertEqual(verdict(run({"url": "https://аpp.example.com/"}, config=PROD)), "ask")

    def test_entries_normalised_like_urls(self):
        cfg = dict(PROD, productionHosts=["APP.Example.com."])
        self.assertEqual(verdict(run({"url": "https://app.example.com"}, config=cfg)), "block")

    def test_undeterminable_host_asks(self):
        for url in ("https://", "https:///", "http://[bad", "https://a b.example.com",
                    "https://exa..mple.com"):
            with self.subTest(url=url):
                self.assertEqual(verdict(run({"url": url})), "ask")

    def test_hostless_and_safe_urls_still_allowed(self):
        for url in ("about:blank", "data:text/html,hi", "/relative", "?q=1", "#top",
                    "back", "forward", "http://localhost:3000", "localhost:3000/x",
                    "http://0x7f.0.0.1/", "http://2130706433/", "https://shop.example.com/x"):
            with self.subTest(url=url):
                self.assertEqual(verdict(run({"url": url}, config=PROD)), "allow")

    def test_unknown_host_still_asks_not_blocks(self):
        self.assertEqual(verdict(run({"url": "https:\\\\other.example.org"}, config=PROD)), "ask")


class BatchAndPreview(unittest.TestCase):
    """RA-QAB-02."""

    def test_matcher_covers_batch_and_preview(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        matcher = re.compile(data["hooks"]["PreToolUse"][0]["matcher"])
        for name in (CB + "browser_batch", CIC + "browser_batch", CB + "preview_start",
                     CB + "navigate", CIC + "navigate", CB + "javascript_tool"):
            with self.subTest(name=name):
                self.assertTrue(matcher.search(name))
        self.assertFalse(matcher.search(CB + "computer"))

    def test_bash_matcher_registered(self):
        data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        groups = data["hooks"]["PreToolUse"]
        bash = [g for g in groups if re.compile(g["matcher"]).search("Bash")]
        self.assertEqual(len(bash), 1)
        self.assertTrue(re.compile(bash[0]["matcher"]).search("PowerShell"))
        self.assertIn("pre_navigate_prod_gate.py", bash[0]["hooks"][0]["command"])
        self.assertFalse(re.compile(bash[0]["matcher"]).search("mcp__x__Bash_tool"))

    def batch(self, *actions):
        return {"actions": [{"name": n, "input": i} for n, i in actions]}

    def test_nested_navigate_blocked(self):
        b = self.batch(("computer", {"action": "screenshot"}),
                       ("navigate", {"url": "https:/app.example.com/admin"}))
        self.assertEqual(verdict(run(b, tool=CB + "browser_batch", config=PROD)), "block")
        self.assertEqual(verdict(run(b, tool=CIC + "browser_batch", config=PROD)), "block")

    def test_nested_script_blocked_and_unknown_asks(self):
        b = self.batch(("javascript_tool", {"text": "fetch('https://app.example.com/api')"}))
        self.assertEqual(verdict(run(b, tool=CB + "browser_batch", config=PROD)), "block")
        b = self.batch(("navigate", {"url": "https://other.example.org"}))
        self.assertEqual(verdict(run(b, tool=CB + "browser_batch", config=PROD)), "ask")

    def test_benign_batch_allowed(self):
        b = self.batch(("navigate", {"url": "https://shop.example.com/cart"}),
                       ("computer", {"action": "left_click", "coordinate": [1, 2]}),
                       ("find", {"query": "https://app.example.com"}),
                       ("navigate", {"url": "back"}))
        self.assertEqual(run(b, tool=CB + "browser_batch", config=PROD), (0, "", ""))

    def test_preview_start_url_and_launch_json(self):
        self.assertEqual(verdict(run({"url": "https://app.example.com"}, tool=CB + "preview_start",
                                     config=PROD)), "block")
        launch = json.dumps({"version": "0.0.1", "configurations": [
            {"name": "prod-attach", "url": "https://app.example.com"},
            {"name": "web", "runtimeExecutable": "npm", "port": 3000}]})
        files = {".claude/launch.json": launch}
        self.assertEqual(verdict(run({"name": "prod-attach"}, tool=CB + "preview_start",
                                     config=PROD, files=files)), "block")
        self.assertEqual(run({"name": "web"}, tool=CB + "preview_start", config=PROD,
                             files=files), (0, "", ""))
        self.assertEqual(run({"name": "missing"}, tool=CB + "preview_start", config=PROD,
                             files=files), (0, "", ""))


class ScriptRequests(unittest.TestCase):
    """RA-QAB-03: network constructs and run-time URLs in page scripts."""

    def ev(self, js, config=PROD):
        return verdict(run({"function": js}, tool=PW + "browser_evaluate", config=config))

    def test_network_constructs_to_production_blocked(self):
        for js in ("() => fetch('https://app.example.com/api', {method: 'DELETE'})",
                   "() => { const x = new XMLHttpRequest(); x.open('POST', 'https://app.example.com/u'); x.send(); }",
                   "() => navigator.sendBeacon('https://app.example.com/b', 'x')",
                   "() => new WebSocket('wss://app.example.com/ws')",
                   "() => fetch(`https://app.example.com/users/${id}`)",
                   "() => { location.href = 'https://' + 'app.example.com'; }",
                   "() => fetch('https:\\\\\\\\app.example.com/x')"):
            with self.subTest(js=js):
                self.assertEqual(self.ev(js), "block")

    def test_playwright_request_context_blocked(self):
        code = "await page.request.delete('https://app.example.com/api/1');"
        self.assertEqual(verdict(run({"code": code}, tool=PW + "browser_run_code_unsafe",
                                     config=PROD)), "block")

    def test_runtime_built_url_asks_when_production_configured(self):
        for js in ("() => fetch(base + '/api')",
                   "() => { location.href = 'https://' + host; }",
                   "() => navigator.sendBeacon(`https://${h}/x`)",
                   "() => window.open(url)"):
            with self.subTest(js=js):
                self.assertEqual(self.ev(js), "ask")
                self.assertEqual(self.ev(js, config={"targetUrl": "https://shop.example.com"}),
                                 "allow")
                self.assertEqual(self.ev(js, config={}), "allow")

    def test_option_production_hosts_make_runtime_urls_ask(self):
        r = run({"function": "() => fetch(api)"}, tool=PW + "browser_evaluate", config={},
                env={"CLAUDE_PLUGIN_OPTION_PRODUCTION_HOSTS": "app.example.com"})
        self.assertEqual(verdict(r), "ask")

    def test_benign_scripts_allowed(self):
        for js in ("() => fetch('/api/me').then(r => r.status)",
                   "() => fetch('https://shop.example.com/api')",
                   "() => fetch(`/api/users/${id}`)",
                   "() => location.href === 'https://app.example.com'",
                   "() => document.querySelectorAll('a').length"):
            with self.subTest(js=js):
                self.assertEqual(self.ev(js), "allow")


class BashGate(unittest.TestCase):
    """RA-QAB-03 (shell) and RA-QAB-04 (credential env reads)."""

    def bash(self, command, config=PROD, env=None):
        return run({"command": command}, tool="Bash", config=config, env=env)

    def test_http_clients_to_production_blocked(self):
        for cmd in ("curl -s https://app.example.com/api",
                    "curl app.example.com/health",
                    "curl -X DELETE -H 'Authorization: Bearer x' 'https:\\\\app.example.com/u/1'",
                    "wget -qO- HTTPS://APP.EXAMPLE.COM./",
                    "http DELETE app.example.com/u/1",
                    "cd x && /usr/bin/curl --url=https://app.example.com/",
                    "Invoke-WebRequest -Uri https://app.example.com/ -Method Post",
                    "curl https://api.prod.example.net/"):
            with self.subTest(cmd=cmd):
                code, _, err = self.bash(cmd)
                self.assertEqual(code, 2)
                self.assertIn("BLOCKED", err)

    def test_powershell_tool_gated(self):
        r = run({"command": "Invoke-RestMethod -Uri https://app.example.com/api -Method Delete"},
                tool="PowerShell", config=PROD)
        self.assertEqual(r[0], 2)

    def test_override_allows_with_audit(self):
        code, out, _ = self.bash("curl https://app.example.com/", env={OVERRIDE_ENV: "1"})
        self.assertEqual(code, 0)
        self.assertIn("ALLOWED", json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_non_production_and_non_http_commands_allowed(self):
        for cmd in ("curl https://shop.example.com/api", "curl https://other.example.org/",
                    "git clone https://app.example.com/repo.git", "python -m http.server 8000",
                    "echo app.example.com", "ls -la"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.bash(cmd), (0, "", ""))

    def test_no_config_means_no_bash_gate(self):
        self.assertEqual(self.bash("curl https://app.prod.example.com/", config=None), (0, "", ""))

    def test_disallowed_credential_env_read_denied(self):
        cfg = dict(PROD, roles={"admin": {"username": "u", "passwordEnv": "GITHUB_TOKEN"}})
        code, out, _ = self.bash("printenv GITHUB_TOKEN", config=cfg)
        self.assertEqual((code, decision(out)), (0, "deny"))
        # an allow-listed or QA_ name is read normally
        cfg_ok = dict(PROD, roles={"admin": {"username": "u", "passwordEnv": "QA_ADMIN_PASSWORD",
                                             "totpEnv": "STAGING_TOTP"}})
        self.assertEqual(self.bash("printenv QA_ADMIN_PASSWORD", config=cfg_ok), (0, "", ""))
        code, out, _ = self.bash("printenv STAGING_TOTP", config=cfg_ok)
        self.assertEqual(decision(out), "deny")
        self.assertEqual(self.bash("printenv STAGING_TOTP", config=cfg_ok,
                                   env={"CLAUDE_PLUGIN_OPTION_CREDENTIAL_ENV_ALLOWLIST": "STAGING_TOTP"}),
                         (0, "", ""))


class CredentialAllowList(unittest.TestCase):
    """RA-QAB-04: totp.py and the SessionStart hook apply the gate's allow-list."""

    SEED = "JBSWY3DPEHPK3PXP"

    def totp(self, name, extra=None):
        env = _env({name: self.SEED})
        env.update(extra or {})
        return subprocess.run([sys.executable, str(TOTP), name], capture_output=True,
                              env=env, timeout=30)

    def test_totp_refuses_names_outside_allow_list(self):
        p = self.totp("GITHUB_TOKEN")
        self.assertEqual(p.returncode, 2)
        self.assertIn("allow", p.stderr.decode("utf-8"))
        self.assertEqual(p.stdout.strip(), b"")
        self.assertEqual(self.totp("qa_lower_case").returncode, 2)

    def test_totp_accepts_qa_and_allow_listed_names(self):
        self.assertEqual(self.totp("QA_ADMIN_TOTP").returncode, 0)
        p = self.totp("STAGING_TOTP", {"CLAUDE_PLUGIN_OPTION_CREDENTIAL_ENV_ALLOWLIST": "X, STAGING_TOTP"})
        self.assertEqual(p.returncode, 0)
        self.assertRegex(p.stdout.decode("ascii").strip(), r"^\d{6}$")

    def session(self, config):
        with tempfile.TemporaryDirectory() as root:
            Path(root, CONFIG).write_text(json.dumps(config), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SESSION)], input=b"{}", capture_output=True,
                                  env=_env({"CLAUDE_PROJECT_DIR": root}), cwd=root, timeout=30)
        return proc.stdout.decode("utf-8")

    def test_session_start_warns_on_disallowed_names(self):
        out = self.session({"roles": {"a": {"passwordEnv": "AWS_SECRET_ACCESS_KEY"}}})
        self.assertIn("AWS_SECRET_ACCESS_KEY", out)
        self.assertIn("allow-list", out)
        self.assertNotIn("allow-list", self.session({"roles": {"a": {"passwordEnv": "QA_A_PASSWORD"}}}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
