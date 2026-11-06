"""Sign-in modes, PAT token file, the read-only proxy, and the agent package.

These cover scripts/ado-mcp-launch.js (auth mode resolution and the stdio read-only proxy),
data/write_tools.json (the single read/write classification) and agent-plugin/ (generated).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
LAUNCHER = PLUGIN / "scripts" / "ado-mcp-launch.js"
WRITE_TOOLS = PLUGIN / "data" / "write_tools.json"

pytestmark = pytest.mark.skipif(not NODE, reason="node not installed")


def _launch(env, platform="linux"):
    code = ("const m=require(process.argv[1]);const l=m.buildLaunch(JSON.parse(process.argv[2]),process.argv[3]);"
            "console.log(JSON.stringify({errors:l.errors,mode:l.mode,args:l.args,readOnly:l.readOnly,"
            "token:l.env.ADO_MCP_AUTH_TOKEN===undefined?null:l.env.ADO_MCP_AUTH_TOKEN,"
            "leaked:Object.keys(l.env).filter(k=>/^ADO_PLUGIN_|TOKEN_FILE$/.test(k))}))")
    out = subprocess.run([NODE, "-e", code, str(LAUNCHER), json.dumps(env), platform],
                         capture_output=True, timeout=30, check=True)
    return json.loads(out.stdout)


class TestSignInModes:
    def test_auto_without_token_is_interactive_and_needs_no_token(self):
        r = _launch({"ADO_ORGANIZATION": "contoso"})
        assert r["errors"] == [] and r["mode"] == "interactive"
        assert r["args"][-2:] == ["--authentication", "interactive"] and r["token"] is None

    def test_auto_with_token_is_pat(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t"})
        assert r["mode"] == "pat" and r["token"] == "t"
        assert r["args"][-2:] == ["--authentication", "envvar"]

    def test_stale_token_never_reaches_a_non_pat_mode(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t", "ADO_PLUGIN_AUTH_MODE": "azcli"})
        assert r["mode"] == "azcli" and r["token"] is None
        assert r["args"][-2:] == ["--authentication", "azcli"]

    def test_pat_mode_without_token_is_an_error(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_AUTH_MODE": "pat"})
        assert any("Personal Access Token" in e for e in r["errors"])

    def test_unknown_mode_is_an_error(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_AUTH_MODE": "magic"})
        assert any("authentication mode" in e for e in r["errors"])

    def test_unexpanded_placeholder_mode_counts_as_auto(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_AUTH_MODE": "${user_config.ado_auth_mode}"})
        assert r["errors"] == [] and r["mode"] == "interactive"

    def test_tenant_is_passed_for_browser_sign_in_only(self):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_TENANT": "contoso.onmicrosoft.com"})
        assert r["args"][-2:] == ["--tenant", "contoso.onmicrosoft.com"]
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t", "ADO_PLUGIN_TENANT": "x"})
        assert "--tenant" not in r["args"]

    def test_bad_tenant_is_refused(self):
        assert _launch({"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_TENANT": "a&calc"})["errors"]

    def test_token_file_is_read_and_its_variable_not_leaked(self, tmp_path):
        f = tmp_path / "pat.txt"
        f.write_text("\n  file-token-value  \nsecond line\n", encoding="utf-8")
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN_FILE": str(f)})
        assert r["mode"] == "pat" and r["token"] == "file-token-value" and r["leaked"] == []

    def test_explicit_token_wins_over_token_file(self, tmp_path):
        f = tmp_path / "pat.txt"
        f.write_text("from-file", encoding="utf-8")
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "explicit",
                     "ADO_MCP_AUTH_TOKEN_FILE": str(f)})
        assert r["token"] == "explicit"

    def test_missing_token_file_names_the_path_not_content(self, tmp_path):
        r = _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN_FILE": str(tmp_path / "nope.txt")})
        assert r["errors"] and "nope.txt" in r["errors"][0]

    def test_empty_token_file_is_an_error(self, tmp_path):
        f = tmp_path / "pat.txt"
        f.write_text("  \n", encoding="utf-8")
        assert _launch({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN_FILE": str(f)})["errors"]

    def test_read_only_flag_from_either_source(self):
        assert _launch({"ADO_ORGANIZATION": "c", "ADO_PLUGIN_READONLY": "true"})["readOnly"] is True
        assert _launch({"ADO_ORGANIZATION": "c", "ADO_MCP_READONLY": "1"})["readOnly"] is True
        assert _launch({"ADO_ORGANIZATION": "c", "ADO_PLUGIN_READONLY": "false"})["readOnly"] is False
        assert _launch({"ADO_ORGANIZATION": "c",
                        "ADO_PLUGIN_READONLY": "${user_config.ado_read_only}"})["readOnly"] is False

    def test_main_prints_the_mode_but_never_the_token(self):
        p = subprocess.run([NODE, str(LAUNCHER)], capture_output=True, timeout=30,
                           env={"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "s3cr3t-value",
                                "ADO_MCP_LAUNCH_DRY_RUN": "1", "SystemRoot": "C:\\Windows"})
        out = json.loads(p.stdout)
        assert out["mode"] == "pat" and out["readOnly"] is False and b"s3cr3t-value" not in p.stdout + p.stderr


FAKE_SERVER = r"""
const rl = require('readline').createInterface({input: process.stdin});
const TOOLS = ['wit_get_work_item','wit_create_work_item','repo_create_branch','wit_my_work_items','brand_new_tool'];
const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');
rl.on('line', (l) => {
  const parsed = JSON.parse(l);
  (Array.isArray(parsed) ? parsed : [parsed]).forEach(handle);
});
function handle(m) {
  if (m.method === 'tools/list') out({jsonrpc:'2.0', id:m.id, result:{tools:TOOLS.map(name => ({name}))}});
  else if (m.method === 'tools/call') out({jsonrpc:'2.0', id:m.id, result:{content:[{type:'text', text:'CALLED ' + m.params.name}]}});
  else if (m.id !== undefined) out({jsonrpc:'2.0', id:m.id, result:{}});
}
"""

HOST = (
    "const {spawn}=require('child_process');const m=require(process.argv[2]);"
    "const allowed=m.loadAllowedTools(process.argv[3]);"
    "const c=spawn(process.execPath,[process.argv[4]],{stdio:['pipe','pipe','inherit']});"
    "m.proxy(process.stdin,process.stdout,c.stdin,c.stdout,allowed);"
    "c.on('exit',()=>setTimeout(()=>process.exit(0),50));"
)


def _through_proxy(messages, tmp_path):
    """Sends messages through launcher.proxy() to a fake server; returns what the host sees."""
    srv = tmp_path / "fake_server.js"
    srv.write_text(FAKE_SERVER, encoding="utf-8")
    host = tmp_path / "host.js"
    host.write_text(HOST, encoding="utf-8")
    stdin = "".join(json.dumps(m) + "\n" for m in messages)
    p = subprocess.run([NODE, str(host), str(LAUNCHER), str(WRITE_TOOLS), str(srv)],
                       input=stdin.encode(), capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr
    return [json.loads(line) for line in p.stdout.decode().splitlines() if line.strip()]


def _flat(out):
    return [m for o in out for m in (o if isinstance(o, list) else [o])]


class TestReadOnlyProxy:
    def test_tools_list_hides_write_and_unknown_tools(self, tmp_path):
        out = _through_proxy([{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}], tmp_path)
        names = [t["name"] for t in out[0]["result"]["tools"]]
        assert names == ["wit_get_work_item", "wit_my_work_items"]

    def test_write_call_is_refused_and_never_reaches_the_server(self, tmp_path):
        out = _through_proxy([
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "wit_create_work_item", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "wit_get_work_item", "arguments": {}}},
        ], tmp_path)
        by_id = {m["id"]: m for m in out}
        assert by_id[2]["result"]["isError"] is True
        assert "read-only" in by_id[2]["result"]["content"][0]["text"]
        assert "CALLED" not in json.dumps(by_id[2])
        assert by_id[3]["result"]["content"][0]["text"] == "CALLED wit_get_work_item"

    def test_unlisted_tool_is_blocked_fail_closed(self, tmp_path):
        out = _through_proxy([{"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                               "params": {"name": "brand_new_tool"}}], tmp_path)
        assert out[0]["result"]["isError"] is True

    def test_batched_call_cannot_smuggle_a_write(self, tmp_path):
        out = _flat(_through_proxy([[
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "repo_create_branch"}},
            {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "wit_my_work_items"}},
        ]], tmp_path))
        assert not any("CALLED repo_create_branch" in json.dumps(m) for m in out)
        assert any(m.get("id") == 6 and "CALLED wit_my_work_items" in json.dumps(m) for m in out)

    def test_other_messages_pass_through(self, tmp_path):
        out = _through_proxy([{"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {}}], tmp_path)
        assert out[0]["id"] == 7 and out[0]["result"] == {}

    def test_read_only_refuses_to_start_without_the_allowlist(self, tmp_path):
        # The launcher alone, with data/write_tools.json missing next to it.
        lone = tmp_path / "scripts"
        lone.mkdir()
        (lone / "ado-mcp-launch.js").write_bytes(LAUNCHER.read_bytes())
        p = subprocess.run([NODE, str(lone / "ado-mcp-launch.js")], capture_output=True, timeout=30,
                           env={"ADO_ORGANIZATION": "contoso", "ADO_PLUGIN_READONLY": "true",
                                "SystemRoot": "C:\\Windows"})
        assert p.returncode == 1 and b"write_tools.json" in p.stderr


def _hook_write_tools():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    found = set()
    for entry in hooks:
        m = re.search(r"azure-devops__\((.*)\)\$$", entry["matcher"])
        if not m:
            continue
        depth, cur, parts = 0, "", []
        for ch in m.group(1):
            depth += ch == "("
            depth -= ch == ")"
            if ch == "|" and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        for part in parts:
            g = re.match(r"(\w+_)\((.*)\)$", part)
            found.update([g.group(1) + x for x in g.group(2).split("|")] if g else [part])
    return found


class TestWriteToolsClassification:
    def _data(self):
        return json.loads(WRITE_TOOLS.read_text(encoding="utf-8"))

    def test_write_list_equals_the_hook_gated_tools(self):
        assert set(self._data()["write"]) == _hook_write_tools()

    def test_read_plus_write_is_exactly_the_server_surface(self):
        lines = (PLUGIN / "tests" / "fixtures" / "mcp_tools_2.8.0.txt").read_text(encoding="utf-8").splitlines()
        surface = {l.strip() for l in lines if l.strip() and not l.startswith("#")}
        d = self._data()
        assert not set(d["read"]) & set(d["write"])
        assert set(d["read"]) | set(d["write"]) == surface

    def test_pin_matches_the_classification(self):
        assert self._data()["serverVersion"] == "2.8.0"
        assert "@azure-devops/mcp@2.8.0" in LAUNCHER.read_text(encoding="utf-8")


BUILDER = PLUGIN / "scripts" / "build_agent_plugin.py"


@pytest.fixture(scope="module")
def pkg(tmp_path_factory):
    out = tmp_path_factory.mktemp("agent") / "azure-devops"
    p = subprocess.run([sys.executable, str(BUILDER), "--out", str(out)], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode()
    return out


class TestAgentPackage:
    def test_package_is_not_committed_inside_the_plugin(self):
        # A SKILL.md outside skills/ trips validate_marketplace.py and a copy would drift.
        assert not (PLUGIN / "agent-plugin").exists()

    def test_builder_refuses_to_write_inside_the_plugin(self):
        p = subprocess.run([sys.executable, str(BUILDER), "--out", str(PLUGIN / "agent-plugin")],
                           capture_output=True, timeout=60)
        assert p.returncode == 2 and not (PLUGIN / "agent-plugin").exists()

    def test_builder_refuses_a_foreign_non_empty_directory(self, tmp_path):
        (tmp_path / "important.txt").write_text("keep", encoding="utf-8")
        p = subprocess.run([sys.executable, str(BUILDER), "--out", str(tmp_path)], capture_output=True, timeout=60)
        assert p.returncode == 2 and (tmp_path / "important.txt").read_text(encoding="utf-8") == "keep"

    def test_package_starts_read_only_with_no_claude_only_parts(self, pkg):
        mcp = json.loads((pkg / "mcp.json").read_text(encoding="utf-8"))
        assert set(mcp) == {"$schema", "mcpServers"} and "${CLAUDE_PLUGIN_ROOT}" not in json.dumps(mcp)
        server = mcp["mcpServers"]["azure-devops"]
        assert server["command"] == "node" and server["env"] == {"ADO_PLUGIN_READONLY": "true"}
        assert server["args"] == ["${PLUGIN_ROOT}/scripts/ado-mcp-launch.js"]
        for gone in ("hooks", "commands", "agents", ".mcp.json", ".claude-plugin"):
            assert not (pkg / gone).exists(), gone
        manifest = json.loads((pkg / "plugin.json").read_text(encoding="utf-8"))
        plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        assert manifest["version"] == plugin["version"]

    def test_package_launcher_matches_source_and_finds_its_allowlist(self, pkg):
        src = LAUNCHER.read_bytes().replace(b"\r\n", b"\n")
        assert (pkg / "scripts" / "ado-mcp-launch.js").read_bytes() == src
        assert (pkg / "data" / "write_tools.json").is_file()  # read-only mode needs it next to the launcher
        # the poller requires the launcher from the same folder, so both must ship together
        assert (pkg / "scripts" / "ado-events.js").read_bytes() == (PLUGIN / "scripts" / "ado-events.js").read_bytes().replace(b"\r\n", b"\n")

    def test_skill_names_only_read_tools(self, pkg):
        skill = (pkg / "skills" / "azure-devops" / "SKILL.md").read_text(encoding="utf-8")
        assert skill.startswith("---\nname: azure-devops\n")
        read = set(json.loads(WRITE_TOOLS.read_text(encoding="utf-8"))["read"])
        names = set(re.findall(r"`((?:wit|repo|work|pipelines|search|core|wiki|testplan|advsec)_\w+)`", skill))
        assert names, "the skill should name tools"
        assert names <= read, names - read
