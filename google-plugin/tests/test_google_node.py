"""Runs the offline Node suite and checks the properties that make the plugin usable by anyone:
no dependencies, no personal or host-specific values baked in, wiring consistent across files."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def clean_env(**extra):
    """The real environment minus any GOOGLE_* the developer has set, so tests never see a real setup."""
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GOOGLE_")}, **extra}


def test_node_suite_passes():
    files = sorted(str(f) for f in (PLUGIN / "tests").glob("*.test.mjs"))
    assert files
    r = subprocess.run([NODE, "--test", *files], capture_output=True, text=True, timeout=300, env=clean_env(), cwd=str(PLUGIN / "tests"))
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1500:]


def _rpc(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_server_speaks_mcp_over_stdio_with_no_install_step(tmp_path):
    p = subprocess.Popen([NODE, str(PLUGIN / "server" / "index.mjs")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env=clean_env(GOOGLE_PLUGIN_HOME=str(tmp_path)), encoding="utf-8", cwd=str(tmp_path))
    try:
        init = _rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}})
        assert init["result"]["serverInfo"]["name"] == "google"
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        tools = _rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        classes = json.loads((PLUGIN / "data" / "tools.json").read_text(encoding="utf-8"))
        assert {t["name"] for t in tools} == set(classes["local"] + classes["read"] + classes["write"] + classes["confirm"]) - set(classes["rest_tools"]) - set(classes.get("option_tools", [])), "REST tools are off by default"
        assert all(len(t["description"]) <= 1024 for t in tools)
        status = _rpc(p, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "google_auth_status", "arguments": {}}})
        body = json.loads(status["result"]["content"][0]["text"])
        assert body["ok"] is True and body["configured"] is False and "GOOGLE_CLOUD_SETUP" in body["hint"]
        sign = _rpc(p, {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "google_sign_in", "arguments": {}}})
        assert sign["result"]["isError"] is True
        assert [b["type"] for b in sign["result"]["content"]] == ["text"]
        assert json.loads(sign["result"]["content"][0]["text"]) ["error"]["code"] == "NOT_CONFIGURED"
    finally:
        p.kill()


def test_cli_status_runs_without_a_client_and_exits_3(tmp_path):
    r = subprocess.run([NODE, str(PLUGIN / "server" / "cli.mjs"), "status"], capture_output=True, text=True, env=clean_env(GOOGLE_PLUGIN_HOME=str(tmp_path)), cwd=str(tmp_path), timeout=30)
    assert r.returncode == 3, r.stdout + r.stderr
    assert json.loads(r.stdout)["configured"] is False


def test_no_dependencies_and_only_node_builtins():
    assert not (PLUGIN / "package.json").exists(), "the plugin must not need npm install"
    for f in (PLUGIN / "server").rglob("*.mjs"):
        for spec in re.findall(r'from\s+"([^"]+)"', f.read_text(encoding="utf-8")):
            assert spec.startswith(".") or spec.startswith("node:"), f"{f.name} imports {spec}"


def test_nothing_personal_or_host_specific_is_baked_in():
    pat = re.compile(r"ahmed|lakosha|nino|teqo|taqa|openclaw|dolivu|royal.?preps|@(?!example\.com)[\w-]+\.(com|net|org)", re.I)
    files = list((PLUGIN / "server").rglob("*.mjs")) + [PLUGIN / "skills" / "google" / "SKILL.md", PLUGIN / "docs" / "GOOGLE_CLOUD_SETUP.md"]
    for f in files:
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            m = pat.search(line)
            if m:
                pytest.fail(f"{f.relative_to(PLUGIN)}:{i} has a hard-coded value: {m.group(0)}")


def test_manifest_settings_match_what_the_mcp_config_reads():
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    mcp = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
    used = set(re.findall(r"\$\{user_config\.(\w+)\}", json.dumps(mcp)))
    assert used == set(manifest["userConfig"]), (used, set(manifest["userConfig"]))
    for value in mcp["google"]["env"].values():
        if "user_config" not in value:
            assert value.endswith(":-}"), f"{value} needs an empty default so an unset variable does not leak the literal"
    cfg = (PLUGIN / "server" / "config.mjs").read_text(encoding="utf-8")
    for name in mcp["google"]["env"]:
        assert f'"{name}"' in cfg, f"{name} is set in .mcp.json but never read"


def test_version_is_in_step_across_files():
    v = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    assert f'version: "{v}"' in (PLUGIN / "skills" / "google" / "SKILL.md").read_text(encoding="utf-8")
    assert f"## [{v}]" in (PLUGIN / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f'version: "{v}"' in (PLUGIN / "server" / "index.mjs").read_text(encoding="utf-8")


def test_plugin_folder_holds_only_expected_top_level_entries():
    expected = {".claude-plugin", ".mcp.json", "CHANGELOG.md", "LICENSE", "README.md", "data", "docs", "hooks", "scripts", "server", "skills", "tests",
                ".pytest_cache", "__pycache__"}
    extra = {p.name for p in PLUGIN.iterdir()} - expected
    assert not extra, f"unexpected entries in the plugin folder: {sorted(extra)}"


def _build(out):
    r = subprocess.run([sys.executable, str(PLUGIN / "scripts" / "build_agent_plugin.py"), "--out", str(out)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


def test_agent_package_holds_exactly_the_runtime_files_and_no_backups(tmp_path):
    out = tmp_path / "pkg"
    files = _build(out)
    servers = {"server/" + p.relative_to(PLUGIN / "server").as_posix() for p in (PLUGIN / "server").rglob("*.mjs")}
    assert files == {"plugin.json", "mcp.json", "README.md", "LICENSE", "skills/google/SKILL.md", "data/tools.json",
                     "data/google_mcp_snapshot.json", "docs/GOOGLE_CLOUD_SETUP.md"} | servers
    assert not any(".bak" in f or f.startswith("hooks/") or f.startswith("tests/") for f in files)
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert json.loads((out / "plugin.json").read_text(encoding="utf-8"))["version"] == manifest["version"]
    mcp = json.loads((out / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]["google"]
    assert mcp["args"] == ["${PLUGIN_ROOT}/server/index.mjs"] and "env" not in mcp, "the package must not force read-only (it would need a new sign-in)"
    skill = (out / "skills" / "google" / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: google\ndescription: ")
    for b in [p for p in out.rglob("*") if p.is_file()]:
        assert b"\r\n" not in b.read_bytes(), b
    # Rebuilding over a previous build works; a non-empty foreign folder and the plugin folder itself are refused.
    _build(out)
    foreign = tmp_path / "foreign"; foreign.mkdir(); (foreign / "x.txt").write_text("x")
    for bad in (foreign, PLUGIN / "pkg"):
        r = subprocess.run([sys.executable, str(PLUGIN / "scripts" / "build_agent_plugin.py"), "--out", str(bad)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 2


def test_agent_package_server_starts_from_the_package_and_lists_every_classified_tool(tmp_path):
    out = tmp_path / "pkg"
    _build(out)
    home = tmp_path / "home"; home.mkdir()
    p = subprocess.Popen([NODE, str(out / "server" / "index.mjs")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env=clean_env(GOOGLE_PLUGIN_HOME=str(home)), encoding="utf-8", cwd=str(tmp_path))
    try:
        _rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}}})
        tools = _rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
        classes = json.loads((out / "data" / "tools.json").read_text(encoding="utf-8"))
        assert {t["name"] for t in tools} == set(classes["read"] + classes["local"] + classes["write"] + classes["confirm"]) - set(classes["rest_tools"]) - set(classes.get("option_tools", []))
        call = _rpc(p, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "gmail_list_labels", "arguments": {}}})
        assert json.loads(call["result"]["content"][0]["text"])["error"]["code"] == "NOT_CONFIGURED"
    finally:
        p.kill()




def test_deny_list_removes_local_tools_over_stdio(tmp_path):
    p = subprocess.Popen([NODE, str(PLUGIN / "server" / "index.mjs")], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, env=clean_env(GOOGLE_PLUGIN_HOME=str(tmp_path), GOOGLE_TOOLS_DENY="google_sign_in,google_sign_out"), encoding="utf-8", cwd=str(tmp_path))
    try:
        _rpc(p, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}})
        names = {t["name"] for t in _rpc(p, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]}
        assert "google_sign_in" not in names and "google_sign_out" not in names and "google_auth_status" in names
        call = _rpc(p, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "google_sign_out", "arguments": {}}})
        assert call["result"]["isError"] is True
        assert json.loads(call["result"]["content"][0]["text"])["error"]["code"] == "UNKNOWN_TOOL"
    finally:
        p.kill()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
