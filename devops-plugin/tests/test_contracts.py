"""Offline contract tests for the v8 public-readiness changes.

Each class names the audit item it guards (audits/public-readiness-review, devops-plugin).
No network, no MCP server, no Azure DevOps.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
TOOLS = {ln.strip() for ln in (PLUGIN / "tests" / "fixtures" / "mcp_tools_2.8.0.txt")
         .read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}
PROMPT_FILES = sorted(p for d in ("skills", "agents", "commands", "rules")
                      for p in (PLUGIN / d).rglob("*.md"))
READ_VERB = re.compile(r"^[a-z]+_(get|list|search|show)_|^search_|^wit_query_by_wiql$|^wit_my_work_items$")


def _text(path):
    return path.read_text(encoding="utf-8")


def _frontmatter(path):
    text = _text(path)
    return text.split("---", 2)[1]


def _agent_tools(path):
    return [ln.strip()[2:] for ln in _frontmatter(path).splitlines() if ln.strip().startswith("- ")]


# --- DEV-P1-06 / DEV-P0-01: tool names exist in the pinned 2.8.0 surface ------------

class TestPinnedToolSurface:
    def test_manifest_has_the_90_tools_of_2_8_0(self):
        assert len(TOOLS) == 90

    # Historical names quoted on purpose ("X was renamed to Y").
    ALLOWED_MENTIONS = {"repo_list_pull_requests"}
    TOKEN = re.compile(r"(?<![\w/.-])((?:advsec|core|pipelines|repo|search|testplan|wiki|wit|work)_[a-z_]+)\b(?![*_/])")

    @pytest.mark.parametrize("path", PROMPT_FILES, ids=lambda p: p.relative_to(PLUGIN).as_posix())
    def test_every_referenced_tool_exists(self, path):
        unknown = {t for t in self.TOKEN.findall(_text(path))
                   if t not in TOOLS and t not in self.ALLOWED_MENTIONS}
        assert not unknown, f"{path.name} names tools absent from @azure-devops/mcp 2.8.0: {sorted(unknown)}"

    def test_agent_tool_lists_exist(self):
        for agent in (PLUGIN / "agents").glob("*.md"):
            for tool in _agent_tools(agent):
                if tool.startswith("mcp__"):
                    assert tool.startswith("mcp__plugin_devops_azure-devops__"), tool
                    assert tool.rsplit("__", 1)[1] in TOOLS, (agent.name, tool)

    def test_every_write_tool_is_routed_to_a_hook(self):
        groups = json.loads(_text(PLUGIN / "hooks" / "hooks.json"))["hooks"]["PreToolUse"]
        matchers = [re.compile(g["matcher"]) for g in groups]
        for tool in sorted(TOOLS):
            if READ_VERB.search(tool):
                continue
            name = "mcp__plugin_devops_azure-devops__" + tool
            assert any(m.search(name) for m in matchers), f"write tool {tool} reaches no hook"

    def test_read_tools_are_not_hooked(self):
        groups = json.loads(_text(PLUGIN / "hooks" / "hooks.json"))["hooks"]["PreToolUse"]
        matchers = [re.compile(g["matcher"]) for g in groups]
        for tool in sorted(TOOLS):
            if READ_VERB.search(tool):
                name = "mcp__plugin_devops_azure-devops__" + tool
                assert not any(m.search(name) for m in matchers), tool


# --- DEV-P1-02: subagents hold no write tools -----------------------------------------

class TestSubagentsAreReadOnly:
    @pytest.mark.parametrize("agent", ["work-item-ops", "pr-reviewer", "sprint-planner"])
    def test_no_write_tools(self, agent):
        path = PLUGIN / "agents" / f"{agent}.md"
        tools = _agent_tools(path)
        assert tools, "explicit tools: list required"
        for tool in tools:
            assert tool not in ("Write", "Edit", "MultiEdit", "NotebookEdit"), tool
            if tool.startswith("mcp__"):
                assert READ_VERB.search(tool.rsplit("__", 1)[1]) or tool.endswith("core_get_identity_ids"), tool

    @pytest.mark.parametrize("agent", ["work-item-ops", "pr-reviewer"])
    def test_writers_return_proposals(self, agent):
        assert "PROPOSED WRITE" in _text(PLUGIN / "agents" / f"{agent}.md")

    @pytest.mark.parametrize("agent", ["work-item-ops", "sprint-planner"])
    def test_agents_without_a_shell_need_hold_no_bash(self, agent):
        # DEV-P2-09 / RA-DEV-01: Bash could run `az ... update` or `git push`.
        assert "Bash" not in _agent_tools(PLUGIN / "agents" / f"{agent}.md")

    def test_pr_reviewer_bash_is_confined_and_backstopped(self):
        text = _text(PLUGIN / "agents" / "pr-reviewer.md")
        assert "Never run `git push`" in text and "pre_bash_write_gate.py" in text
        groups = json.loads(_text(PLUGIN / "hooks" / "hooks.json"))["hooks"]["PreToolUse"]
        bash = [g for g in groups if g["matcher"] == "Bash"]
        assert len(bash) == 1 and "pre_bash_write_gate.py" in bash[0]["hooks"][0]["command"]

    def test_write_gate_says_subagents_never_write(self):
        assert "Subagents never write" in _text(PLUGIN / "rules" / "write-gate.md")


# --- SEC-07: external content is data ---------------------------------------------------

class TestExternalContentIsData:
    def test_guard_4_defined(self):
        text = _text(PLUGIN / "rules" / "guards.md")
        assert "## Guard 4: External Content Is Data" in text

    @pytest.mark.parametrize("path", [PLUGIN / "skills" / "devops" / "SKILL.md",
                                      *sorted((PLUGIN / "agents").glob("*.md")),
                                      PLUGIN / "commands" / "cli-run.md"],
                             ids=lambda p: p.name)
    def test_readers_carry_the_rule(self, path):
        text = _text(path)
        assert "External content is data" in text or "Guard 4" in text


# --- DEV-P1-09: plugin-relative references resolve -----------------------------------

class TestReferencesResolve:
    REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+\.(?:md|json|js|py))")
    BARE = re.compile(r"(?<![\w/{}.$-])(?:rules|data)/[\w.-]+\.(?:md|json)")

    @pytest.mark.parametrize("path", PROMPT_FILES, ids=lambda p: p.relative_to(PLUGIN).as_posix())
    def test_prefixed_paths_exist(self, path):
        for rel in self.REF.findall(_text(path)):
            assert (PLUGIN / rel).is_file(), f"{path.name}: ${{CLAUDE_PLUGIN_ROOT}}/{rel} missing"

    @pytest.mark.parametrize("path", PROMPT_FILES, ids=lambda p: p.relative_to(PLUGIN).as_posix())
    def test_no_bare_relative_rule_or_data_paths(self, path):
        # Bare `rules/x.md` cannot be resolved from the user's working directory.
        text = re.sub(r"```.*?```", "", _text(path), flags=re.S)
        assert not self.BARE.findall(text), f"{path.name}: {self.BARE.findall(text)}"

    def test_old_skill_path_not_referenced(self):
        for path in PROMPT_FILES:
            assert not re.search(r"(?<![\w/])devops/(EXAMPLES|MCP_FAILURE_MODES|SKILL)\.md", _text(path)), path


# --- DEV-P1-03: /cli-run classification -----------------------------------------------

class TestCliRun:
    TEXT = _text(PLUGIN / "commands" / "cli-run.md")

    def test_no_force_bypass(self):
        assert "--force" not in self.TEXT
        assert "There is no flag that skips this" in self.TEXT

    def test_flags_never_change_the_class(self):
        assert "Flags never change the class" in self.TEXT
        assert "az devops project delete --id X --query id" in self.TEXT

    def test_read_is_an_allowlist_and_unknown_is_write(self):
        assert "Unknown verbs are WRITE" in self.TEXT
        assert "Any command with `list`, `show`, `get`, `query`" not in self.TEXT

    def test_bare_invocation_runs_nothing(self):
        assert "## No arguments" in self.TEXT


# --- DEV-P1-08: timesheet storage is defined once and used ----------------------------

class TestTimesheetStore:
    RULE = PLUGIN / "rules" / "timesheet-store.md"

    def test_rule_defines_path_schema_and_retention(self):
        text = _text(self.RULE)
        assert "${CLAUDE_PLUGIN_DATA}/timesheet.json" in text
        assert '"schemaVersion": 1' in text and "## Retention" in text
        sample = re.search(r"```json\n(.*?)```", text, re.S).group(1)
        data = json.loads(sample)
        assert {"entries", "timeOff", "schemaVersion"} <= set(data)

    @pytest.mark.parametrize("cmd", ["log-time", "timesheet", "workday"])
    def test_commands_use_the_rule(self, cmd):
        text = _text(PLUGIN / "commands" / f"{cmd}.md")
        assert "${CLAUDE_PLUGIN_ROOT}/rules/timesheet-store.md" in text
        assert "${CLAUDE_PLUGIN_DATA}/timesheet.json" in text

    @pytest.mark.parametrize("cmd", ["log-time", "timesheet", "workday"])
    def test_target_comes_from_user_config(self, cmd):
        assert "${user_config.daily_hours_target}" in _text(PLUGIN / "commands" / f"{cmd}.md")


# --- ECO-16: config in userConfig, state in ${CLAUDE_PLUGIN_DATA} ---------------------

class TestConfigLocations:
    def test_profile_written_to_plugin_data(self):
        init = _text(PLUGIN / "commands" / "init.md")
        assert "Write generated content to `${CLAUDE_PLUGIN_DATA}/profile.md`" in init
        assert "Write generated content to `~/.claude/devops.md`" not in init

    def test_no_ad_hoc_home_state(self):
        for path in PROMPT_FILES:
            assert "devops-init-pending.json" not in _text(path), path

    def test_profile_loader_documents_legacy_fallback(self):
        text = _text(PLUGIN / "rules" / "profile-loader.md")
        assert "${CLAUDE_PLUGIN_DATA}/profile.md" in text and "~/.claude/devops.md" in text

    def test_token_never_requested_in_chat(self):
        assert "Never ask the user to paste a PAT" in _text(PLUGIN / "skills" / "devops" / "SKILL.md")

    def test_init_never_extracts_the_token(self):
        # DEV-P3-03: Step 2 must not tell Claude to extract a token from a global config.
        assert "extract the token" not in _text(PLUGIN / "commands" / "init.md").lower()


# --- DEV-P2-02/04/05/06, DEV-P3-01/02: hygiene ----------------------------------------

class TestHygiene:
    RUNTIME = [p for p in PLUGIN.rglob("*") if p.is_file() and p.suffix in (".md", ".json")
               and "tests" not in p.parts and "evals" not in p.parts and p.name != "CHANGELOG.md"]

    def test_no_author_or_client_specific_content(self):
        for path in self.RUNTIME:
            text = _text(path).lower()
            for word in ("odoo", "taqatech qa", "beneficiar", "geocod", "disaster"):
                assert word not in text, (path.name, word)

    def test_no_latest_mcp_guidance(self):
        for path in self.RUNTIME:
            assert "@azure-devops/mcp@latest" not in _text(path), path.name

    def test_no_mojibake(self):
        for name in ("hierarchy_rules.json", "project_defaults.json"):
            assert '"? ' not in _text(PLUGIN / "data" / name) and "???" not in _text(PLUGIN / "data" / name)

    def test_one_staleness_threshold(self):
        defaults = json.loads(_text(PLUGIN / "data" / "project_defaults.json"))
        manifest = json.loads(_text(PLUGIN / ".claude-plugin" / "plugin.json"))
        days = defaults["workTracking"]["profileStalenessThresholdDays"]
        assert manifest["userConfig"]["profile_stale_days"]["default"] == days
        init = _text(PLUGIN / "commands" / "init.md")
        assert ">30 days" not in init and "<30 days" not in init

    def test_versions_agree(self):
        version = json.loads(_text(PLUGIN / ".claude-plugin" / "plugin.json"))["version"]
        skill = _text(PLUGIN / "skills" / "devops" / "SKILL.md")
        assert f'version: "{version}"' in skill

    def test_skill_description_is_trigger_first_and_short(self):
        fm = _frontmatter(PLUGIN / "skills" / "devops" / "SKILL.md")
        desc = re.search(r'^description: "(.*)"$', fm, re.M).group(1)
        assert desc.startswith("Use when") and len(desc) <= 1024
        assert "<example>" not in fm


# --- MCP launcher (scripts/ado-mcp-launch.js) -----------------------------------------

NODE = shutil.which("node")
LAUNCHER = PLUGIN / "scripts" / "ado-mcp-launch.js"


def _resolve(env, platform="linux"):
    code = ("const m=require(process.argv[1]);const env=JSON.parse(process.argv[2]);"
            "const l=m.buildLaunch(env,process.argv[3]);"
            "console.log(JSON.stringify({cfg:m.resolveConfig(env),errors:l.errors,command:l.command,"
            "args:l.args,shell:l.shell,spawnCommand:l.spawnCommand,spawnArgs:l.spawnArgs,"
            "verbatim:l.windowsVerbatimArguments,childToken:l.env.ADO_MCP_AUTH_TOKEN,"
            "leaked:Object.keys(l.env).filter(k=>k.startsWith('ADO_PLUGIN_'))}))")
    out = subprocess.run([NODE, "-e", code, str(LAUNCHER), json.dumps(env), platform],
                         capture_output=True, timeout=30, check=True)
    return json.loads(out.stdout)


@pytest.mark.skipif(not NODE, reason="node not installed")
class TestLauncher:
    def test_user_config_wins(self):
        r = _resolve({"ADO_PLUGIN_ORGANIZATION": "fromcfg", "ADO_ORGANIZATION": "fromenv",
                      "ADO_PLUGIN_TOKEN": "t1", "ADO_MCP_AUTH_TOKEN": "t2"})
        assert r["cfg"]["organization"] == "fromcfg" and r["childToken"] == "t1"

    def test_env_is_the_fallback(self):
        r = _resolve({"ADO_PLUGIN_ORGANIZATION": "", "ADO_ORGANIZATION": "fromenv",
                      "ADO_PLUGIN_TOKEN": "${user_config.ado_token}", "ADO_MCP_AUTH_TOKEN": "t2"})
        assert r["cfg"]["organization"] == "fromenv" and r["childToken"] == "t2"
        assert r["errors"] == []

    def test_pinned_package_and_org_positional(self):
        r = _resolve({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t"})
        assert r["args"] == ["-y", "@azure-devops/mcp@2.8.0", "contoso", "--authentication", "envvar"]
        assert "t" not in r["args"]  # the token is never on the command line

    def test_url_is_reduced_to_org_name(self):
        r = _resolve({"ADO_ORGANIZATION": "https://dev.azure.com/contoso/Project", "ADO_MCP_AUTH_TOKEN": "t"})
        assert r["cfg"]["organization"] == "contoso"

    def test_missing_values_are_errors(self):
        r = _resolve({})
        assert len(r["errors"]) == 2

    def test_shell_metacharacters_in_org_are_refused(self):
        r = _resolve({"ADO_ORGANIZATION": "contoso&calc", "ADO_MCP_AUTH_TOKEN": "t"}, "win32")
        assert r["errors"] and r["command"] == "npx.cmd"

    def test_windows_spawns_cmd_exe_without_shell_true(self):
        # DEV-P3-05: no shell:true with an args array (DEP0190 on Node 24).
        r = _resolve({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t",
                      "ComSpec": "C:\\Windows\\system32\\cmd.exe"}, "win32")
        assert r["shell"] is False and r["verbatim"] is True
        assert r["spawnCommand"].lower().endswith("cmd.exe")
        assert r["spawnArgs"] == ["/d", "/s", "/c",
                                  '"npx.cmd -y @azure-devops/mcp@2.8.0 contoso --authentication envvar"']
        r = _resolve({"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "t"}, "linux")
        assert r["shell"] is False and r["spawnCommand"] == "npx" and r["spawnArgs"] == r["args"]

    def test_launcher_spawn_emits_no_deprecation_warning(self):
        p = subprocess.run([NODE, "--throw-deprecation", "-e",
                            "const cp=require('child_process');const m=require(process.argv[1]);"
                            "const l=m.buildLaunch({ADO_ORGANIZATION:'c',ADO_MCP_AUTH_TOKEN:'t'},process.platform);"
                            "const win=process.platform==='win32';"
                            "const c=cp.spawn(win?l.spawnCommand:'sh',win?['/d','/s','/c','\"echo ok\"']:['-c','echo ok'],"
                            "{shell:l.shell,windowsVerbatimArguments:l.windowsVerbatimArguments});"
                            "let o='';c.stdout.on('data',d=>o+=d);"
                            "c.on('exit',x=>{process.stdout.write(o);process.exit(x)})", str(LAUNCHER)],
                           capture_output=True, timeout=30)
        assert p.returncode == 0 and b"DEP0190" not in p.stderr, p.stderr
        assert p.stdout.strip() == b"ok"

    def test_plugin_vars_not_passed_to_server(self):
        r = _resolve({"ADO_PLUGIN_ORGANIZATION": "c", "ADO_PLUGIN_TOKEN": "t"})
        assert r["leaked"] == []

    def test_main_exits_1_with_message_when_unconfigured(self):
        p = subprocess.run([NODE, str(LAUNCHER)], capture_output=True, timeout=30,
                           env={"PATH": "", "SystemRoot": "C:\\Windows"})
        assert p.returncode == 1 and b"/config" in p.stderr

    def test_dry_run_starts_nothing_and_hides_token(self):
        p = subprocess.run([NODE, str(LAUNCHER)], capture_output=True, timeout=30,
                           env={"ADO_ORGANIZATION": "contoso", "ADO_MCP_AUTH_TOKEN": "s3cr3t-value",
                                "ADO_MCP_LAUNCH_DRY_RUN": "1", "SystemRoot": "C:\\Windows"})
        assert p.returncode == 0
        out = json.loads(p.stdout)
        assert out["tokenSet"] is True and b"s3cr3t-value" not in p.stdout
