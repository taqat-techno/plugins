"""Runs the offline Node suite and checks the properties that make the plugin usable by anyone:
no dependencies, no personal or company values baked in, wiring consistent across files."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def test_node_suite_passes():
    r = subprocess.run([NODE, "--test", str(PLUGIN / "tests" / "m365.test.mjs")], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]


def _rpc(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_server_speaks_mcp_over_stdio_with_no_install_step(tmp_path):
    env = {"PATH": __import__("os").environ["PATH"], "M365_HOME": str(tmp_path), "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    p = subprocess.Popen([NODE, str(PLUGIN / "server" / "index.mjs")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, encoding="utf-8")
    try:
        init = _rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
        assert init["result"]["serverInfo"]["name"] == "m365"
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        tools = _rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        names = {t["name"] for t in tools}
        assert {"m365_sign_in", "email_search", "calendar_find_free_slots", "people_resolve", "profile_remember_contact"} <= names
        status = _rpc(p, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "m365_auth_status", "arguments": {}}})
        body = json.loads(status["result"]["content"][0]["text"])
        assert body["configured"] is False and "APP_REGISTRATION" in body["hint"]
        mail = _rpc(p, {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "email_list_recent", "arguments": {}}})
        assert mail["result"]["isError"] is True
        assert json.loads(mail["result"]["content"][0]["text"])["error"] == "NOT_CONFIGURED"
    finally:
        p.kill()


def test_cli_status_runs_without_a_client_id(tmp_path):
    r = subprocess.run([NODE, str(PLUGIN / "server" / "cli.mjs"), "status"], capture_output=True, text=True, env={"PATH": __import__("os").environ["PATH"], "M365_HOME": str(tmp_path), "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}, timeout=30)
    assert r.returncode == 0 and json.loads(r.stdout)["configured"] is False


def test_no_dependencies_and_only_node_builtins():
    assert not (PLUGIN / "package.json").exists(), "the plugin must not need npm install"
    for f in (PLUGIN / "server").rglob("*.mjs"):
        for spec in re.findall(r'from\s+"([^"]+)"', f.read_text(encoding="utf-8")):
            assert spec.startswith(".") or spec.startswith("node:"), f"{f.name} imports {spec}"


def test_nothing_personal_or_company_specific_is_baked_in():
    pat = re.compile(r"ahmed|teqo|taqa|openclaw|cairo|khair|\.openclaw|contoso\.com/|@(?!x\.com|example\.com)\w+\.com", re.I)
    for f in list((PLUGIN / "server").rglob("*.mjs")) + [PLUGIN / "commands" / "init.md", PLUGIN / "commands" / "profile.md", PLUGIN / "skills" / "m365" / "SKILL.md"]:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = pat.search(line)
            # Africa/Cairo appears only as an example of an IANA zone name in help text.
            if m and not (m.group(0).lower() == "cairo" and "Africa/Cairo" in line):
                pytest.fail(f"{f.relative_to(PLUGIN)}:{i} has a hard-coded value: {m.group(0)}")


def test_manifest_settings_match_what_the_mcp_config_reads():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    used = set(re.findall(r"\$\{user_config\.(\w+)\}", json.dumps(mcp)))
    assert used == set(manifest["userConfig"]), (used, set(manifest["userConfig"]))
    for key in ("M365_CLIENT_ID", "M365_TENANT", "M365_HOME"):
        assert f"${{{key}:-}}" in json.dumps(mcp), f"{key} needs an empty default so an unset variable does not leak the literal"
    cfg = (PLUGIN / "server" / "config.mjs").read_text(encoding="utf-8")
    for name in mcp["m365"]["env"]:
        assert name in cfg, f"{name} is set in .mcp.json but never read"


def test_version_is_in_step_across_files():
    v = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    assert f'version: "{v}"' in (PLUGIN / "skills" / "m365" / "SKILL.md").read_text(encoding="utf-8")
    assert f"## [{v}]" in (PLUGIN / "CHANGELOG.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
