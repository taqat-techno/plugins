"""
Behavioral tests for hooks/pre_write_validate.py.

The hook is invoked as a subprocess with a PreToolUse JSON payload on stdin,
exactly as Claude Code calls it. HOME/USERPROFILE point at a temp dir so the
role comes from a test profile, never the real ~/.claude/devops.md.

Contract under test:
  * role / naming rules apply only when the active process preset (profile
    `process:`) or a profile override defines them; stock presets define none
  * a violation returns permissionDecision "ask" by default; profile
    `enforcement: block` turns it into exit 2 + stderr; `advise` into context only
  * a target state the active preset does not define always asks
  * unresolved @mentions still exit 2 (correctness guard, not org policy)
  * soft reminders exit 0 with hookSpecificOutput JSON carrying BOTH
    hookEventName "PreToolUse" and additionalContext, and no permissionDecision

Run: pytest tests/test_hooks.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pre_write_validate.py"
PREFIX = "mcp__plugin_devops_azure-devops__"


def run_hook(payload, tmp_path, profile=None):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    if profile is not None:
        (home / ".claude" / "devops.md").write_text(profile, encoding="utf-8")
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home))
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=raw.encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=15,
    )
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def context_of(out):
    """Parse the advisory JSON and enforce the channel contract."""
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in hso
    return hso["additionalContext"]


def update(state, tool=PREFIX + "wit_update_work_item", path="/fields/System.State"):
    # The real @azure-devops/mcp 2.8.0 JSON-Patch shape.
    return {"tool_name": tool, "tool_input": {"id": 7, "updates": [
        {"op": "add", "path": path, "value": state}]}}


def create(wi_type):
    return {"tool_name": PREFIX + "wit_create_work_item",
            "tool_input": {"project": "P", "workItemType": wi_type, "fields": []}}


def ask_of(out):
    """Parse a permissionDecision 'ask' output and return its reason."""
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    return hso["permissionDecisionReason"]


def create_titled(wi_type, title):
    # @azure-devops/mcp 2.8.0 wit_create_work_item: fields = [{name, value}].
    return {"tool_name": PREFIX + "wit_create_work_item",
            "tool_input": {"project": "P", "workItemType": wi_type,
                           "fields": [{"name": "System.Title", "value": title}]}}


def profile(role, process=None, extra=""):
    lines = ["---", f"role: {role}"]
    if process:
        lines.append(f'process: "{process}"')
    if extra:
        lines.append(extra)
    return "\n".join(lines + ["---", ""])


YAML_DEV = "---\nrole: developer\n---\n"   # legacy profile: no process -> generic
YAML_PM = 'role: "pm"\n'
MD_DEV = "| Field | Value |\n|---|---|\n| **Primary Role** | developer |\n"
AGILE_DEV = profile("developer", "agile")
SCRUM_DEV = profile("developer", "scrum")
QC_DEV = profile("developer", "custom-scrum-qc")
QC_DEV_BLOCK = profile("developer", "custom-scrum-qc", "enforcement: block")
QC_DEV_ADVISE = profile("developer", "custom-scrum-qc", "enforcement: advise")
QC_PM = profile("pm", "custom-scrum-qc")


class TestStockPresets:
    """Stock Microsoft presets carry no role or naming rules."""

    def test_agile_developer_can_create_bug(self, tmp_path):
        code, out, _ = run_hook(create("Bug"), tmp_path, AGILE_DEV)
        assert code == 0
        assert "User Story/PBI" in context_of(out)

    @pytest.mark.parametrize("state", ["Closed", "Removed"])
    def test_agile_developer_can_close_and_remove(self, tmp_path, state):
        code, out, _ = run_hook(update(state), tmp_path, AGILE_DEV)
        assert code == 0
        assert f"State change to '{state}'" in context_of(out)

    def test_agile_no_prefix_requirement(self, tmp_path):
        code, out, _ = run_hook(create_titled("Task", "Write the API"), tmp_path, AGILE_DEV)
        assert code == 0
        assert "parent" in context_of(out)

    def test_scrum_developer_done_is_reminder(self, tmp_path):
        code, out, _ = run_hook(update("Done"), tmp_path, SCRUM_DEV)
        assert code == 0
        assert "process preset 'scrum'" in context_of(out)

    def test_state_outside_preset_asks(self, tmp_path):
        # 'Ready For QC' is a custom state; stock Agile does not define it.
        code, out, _ = run_hook(update("Ready For QC"), tmp_path, AGILE_DEV)
        assert code == 0
        reason = ask_of(out)
        assert "'Ready For QC' is not defined" in reason and "'agile'" in reason

    def test_state_outside_preset_asks_even_with_block(self, tmp_path):
        prof = profile("developer", "scrum", "enforcement: block")
        code, out, _ = run_hook(update("Active"), tmp_path, prof)
        assert code == 0
        assert "'Active' is not defined" in ask_of(out)


class TestCustomScrumQcPreset:
    """The opt-in custom preset: role and naming rules ask by default."""

    def test_developer_bug_asks(self, tmp_path):
        code, out, err = run_hook(create("Bug"), tmp_path, QC_DEV)
        assert code == 0 and err.strip() == ""
        reason = ask_of(out)
        assert "creating a Bug" in reason and "[Dev-Internal-fix]" in reason

    def test_developer_close_asks(self, tmp_path):
        code, out, _ = run_hook(update("Closed"), tmp_path, QC_DEV)
        assert code == 0
        assert "'Closed'" in ask_of(out)

    def test_developer_bug_blocks_with_enforcement_block(self, tmp_path):
        code, out, err = run_hook(create("Bug"), tmp_path, QC_DEV_BLOCK)
        assert code == 2 and out.strip() == ""
        assert "BLOCKED" in err and "creating a Bug" in err

    def test_developer_close_blocks_with_enforcement_block(self, tmp_path):
        code, _, err = run_hook(update("Closed"), tmp_path, QC_DEV_BLOCK)
        assert code == 2
        assert "BLOCKED" in err and "'developer'" in err and "'Closed'" in err

    def test_enforcement_advise_is_context_only(self, tmp_path):
        code, out, _ = run_hook(update("Removed"), tmp_path, QC_DEV_ADVISE)
        assert code == 0
        assert "Policy note" in context_of(out)

    def test_task_without_prefix_asks(self, tmp_path):
        code, out, _ = run_hook(create_titled("Task", "Write the API"), tmp_path, QC_DEV)
        assert code == 0
        assert "required prefix" in ask_of(out)

    def test_task_without_prefix_blocks_with_enforcement_block(self, tmp_path):
        code, _, err = run_hook(create_titled("Task", "Write the API"), tmp_path,
                                QC_DEV_BLOCK)
        assert code == 2 and "required prefix" in err

    @pytest.mark.parametrize("title", ["[Dev] Write the API", "[Dev-Internal-fix] Login - 500 - API"])
    def test_task_with_prefix_is_reminder(self, tmp_path, title):
        code, out, _ = run_hook(create_titled("Task", title), tmp_path, QC_DEV)
        assert code == 0
        assert "parent" in context_of(out)

    def test_pm_close_allowed(self, tmp_path):
        code, out, _ = run_hook(update("Closed"), tmp_path, QC_PM)
        assert code == 0
        assert "State change to 'Closed'" in context_of(out)

    def test_pm_creates_bug(self, tmp_path):
        code, out, _ = run_hook(create("Bug"), tmp_path, QC_PM)
        assert code == 0
        assert "User Story/PBI" in context_of(out)

    def test_custom_states_are_known(self, tmp_path):
        code, out, _ = run_hook(update("Ready For QC"), tmp_path, QC_DEV)
        assert code == 0
        assert "'Ready For QC'" in context_of(out)

    @pytest.mark.parametrize("profile_text", [
        'role: "PM"\nprocess: custom-scrum-qc\n',
        "role: Lead\nprocess: custom-scrum-qc\n",
        "process: custom-scrum-qc\n| Field | Value |\n|---|---|\n| **Primary Role** | Project Manager |\n",
        "process: custom-scrum-qc\n| Field | Value |\n|---|---|\n| **Primary Role** | Tech Lead |\n",
    ])
    def test_close_role_check_is_case_insensitive(self, tmp_path, profile_text):
        # Regression (F-DEV-10): role "PM" was flagged because the check was case-sensitive.
        code, out, _ = run_hook(update("Closed"), tmp_path, profile_text)
        assert code == 0
        assert "State change to 'Closed'" in context_of(out)

    def test_capitalized_developer_role_still_matches(self, tmp_path):
        code, out, _ = run_hook(create("Bug"), tmp_path,
                                "role: Frontend\nprocess: custom-scrum-qc\n")
        assert code == 0 and "creating a Bug" in ask_of(out)


class TestProfileOverrides:
    def test_role_rules_off_disables_preset_rules(self, tmp_path):
        prof = profile("developer", "custom-scrum-qc", "roleRules: off")
        code, out, _ = run_hook(update("Closed"), tmp_path, prof)
        assert code == 0
        assert "State change to 'Closed'" in context_of(out)

    def test_task_naming_off_disables_prefixes(self, tmp_path):
        prof = profile("developer", "custom-scrum-qc", "taskNaming: off")
        code, out, _ = run_hook(create_titled("Task", "Write the API"), tmp_path, prof)
        assert code == 0 and "parent" in context_of(out)

    def test_inline_role_rules_on_stock_preset(self, tmp_path):
        prof = profile("developer", "agile",
                       'roleRules: {"restrictedStates": {"Closed": {"allowedRoles": ["lead"]}}}')
        code, out, _ = run_hook(update("Closed"), tmp_path, prof)
        assert code == 0 and "'Closed'" in ask_of(out)

    def test_inline_task_naming_on_stock_preset(self, tmp_path):
        prof = profile("developer", "agile", 'taskNaming: {"prefixes": ["[BE]", "[FE]"]}')
        code, out, _ = run_hook(create_titled("Task", "Write the API"), tmp_path, prof)
        assert code == 0 and "[BE], [FE]" in ask_of(out)


class TestGenericFallback:
    """No profile, a legacy profile without `process`, or an unknown preset: never exit 2."""

    @pytest.mark.parametrize("prof", [None, YAML_DEV, MD_DEV, profile("developer", "no-such-preset"),
                                      "role: developer\nenforcement: block\n"])
    @pytest.mark.parametrize("payload", [update("Closed"), update("Removed"), create("Bug"),
                                         create_titled("Task", "untitled thing")])
    def test_no_role_or_naming_enforcement(self, tmp_path, prof, payload):
        code, out, _ = run_hook(payload, tmp_path, prof)
        assert code == 0
        context_of(out)  # reminder only, no permissionDecision

    def test_close_without_profile_is_reminder_only(self, tmp_path):
        code, out, _ = run_hook(update("Removed"), tmp_path)
        assert code == 0
        assert "state_machine.json" in context_of(out)

    def test_unknown_state_without_preset_is_reminder(self, tmp_path):
        code, out, _ = run_hook(update("Whatever"), tmp_path, YAML_DEV)
        assert code == 0 and "generic rules" in context_of(out)


class TestStateChange:
    def test_ordinary_state_change_reminds(self, tmp_path):
        code, out, _ = run_hook(update("In Progress"), tmp_path, YAML_DEV)
        assert code == 0
        assert "'In Progress'" in context_of(out)

    def test_legacy_tool_name_is_recognized(self, tmp_path):
        code, out, _ = run_hook(update("Closed", "mcp__azure-devops__wit_update_work_item"),
                                tmp_path, QC_DEV)
        assert code == 0 and "'Closed'" in ask_of(out)

    def test_bare_state_path_is_detected(self, tmp_path):
        code, out, _ = run_hook(update("Closed", path="System.State"), tmp_path, QC_DEV)
        assert code == 0 and "'Closed'" in ask_of(out)

    def test_state_is_read_from_its_own_update_not_the_first(self, tmp_path):
        # The bash hook took the first "value" in the payload: here "Closed" would
        # have been missed because the title update comes first.
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"id": 7,
                   "updates": [{"op": "add", "path": "/fields/System.Title", "value": "t"},
                               {"op": "add", "path": "/fields/System.State",
                                "value": "Closed"}]}}
        code, out, _ = run_hook(payload, tmp_path, QC_DEV)
        assert code == 0 and "'Closed'" in ask_of(out)

    def test_state_text_in_a_title_is_not_a_state_change(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"id": 7,
                   "updates": [{"op": "add", "path": "/fields/System.Title",
                                "value": "Document \"System.State\" handling"}]}}
        code, out, _ = run_hook(payload, tmp_path, QC_DEV)
        assert (code, out.strip()) == (0, "")

    def test_update_without_state_is_silent(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"updates": [
            {"op": "add", "path": "/fields/System.Title", "value": "x"}]}}
        code, out, err = run_hook(payload, tmp_path, QC_DEV)
        assert (code, out.strip(), err.strip()) == (0, "", "")


class TestCreate:
    @pytest.mark.parametrize("wi_type,parent", [
        ("Task", "User Story/PBI"),
        ("User Story", "Feature"),
        ("Requirement", "Feature"),
        ("Feature", "Epic"),
    ])
    def test_hierarchy_reminder(self, tmp_path, wi_type, parent):
        code, out, _ = run_hook(create(wi_type), tmp_path, YAML_DEV)
        assert code == 0
        assert f"parent {parent}" in context_of(out)

    def test_epic_is_silent(self, tmp_path):
        code, out, _ = run_hook(create("Epic"), tmp_path, YAML_DEV)
        assert (code, out.strip()) == (0, "")


class TestComment:
    def test_unresolved_mention_blocked(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_add_work_item_comment",
                   "tool_input": {"comment": "ping @alice please review"}}
        code, _, err = run_hook(payload, tmp_path)
        assert code == 2
        assert "Unresolved @mentions" in err

    def test_email_address_is_not_a_mention(self, tmp_path):
        # Regression (F-DEV-09): the "@" of an e-mail address hard-blocked the comment.
        payload = {"tool_name": PREFIX + "wit_add_work_item_comment",
                   "tool_input": {"comment": "Contact jane.doe@example.com for the logs"}}
        code, out, err = run_hook(payload, tmp_path)
        assert (code, out.strip(), err.strip()) == (0, "", "")

    def test_mention_next_to_email_still_blocked(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_add_work_item_comment",
                   "tool_input": {"comment": "@bob mail ops@example.com"}}
        code, _, err = run_hook(payload, tmp_path)
        assert code == 2 and "Unresolved @mentions" in err

    def test_at_sign_outside_comment_field_is_ignored(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_add_work_item_comment",
                   "tool_input": {"project": "@Team", "workItemId": 7,
                                  "comment": "plain note"}}
        code, out, _ = run_hook(payload, tmp_path)
        assert (code, out.strip()) == (0, "")

    def test_resolved_mention_allowed(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_add_work_item_comment", "tool_input": {
            "comment": '<a href="#" data-vss-mention="version:2.0,abc">@alice</a> hi'}}
        code, out, _ = run_hook(payload, tmp_path)
        assert (code, out.strip()) == (0, "")


class TestPullRequest:
    def test_repo_name_instead_of_guid_reminds(self, tmp_path):
        payload = {"tool_name": PREFIX + "repo_create_pull_request",
                   "tool_input": {"repositoryId": "my-repo"}}
        code, out, _ = run_hook(payload, tmp_path)
        assert code == 0
        assert "'my-repo' is not a GUID" in context_of(out)

    def test_repo_name_with_quotes_is_emitted_as_valid_json(self, tmp_path):
        # The bash hook spliced this value into a python -c string literal.
        payload = {"tool_name": PREFIX + "repo_create_pull_request",
                   "tool_input": {"repositoryId": "x''' + str(1/0) + '''"}}
        code, out, _ = run_hook(payload, tmp_path)
        assert code == 0
        assert "str(1/0)" in context_of(out)

    def test_guid_is_silent(self, tmp_path):
        payload = {"tool_name": PREFIX + "repo_create_pull_request",
                   "tool_input": {"repositoryId": "0a1b2c3d-0000-4000-8000-00000000abcd"}}
        code, out, _ = run_hook(payload, tmp_path)
        assert (code, out.strip()) == (0, "")


class TestFailOpen:
    def test_garbage_stdin(self, tmp_path):
        code, out, _ = run_hook("not json", tmp_path)
        assert (code, out.strip()) == (0, "")

    def test_unrelated_tool(self, tmp_path):
        code, out, _ = run_hook({"tool_name": PREFIX + "wit_work_items_link",
                                 "tool_input": {}}, tmp_path)
        assert (code, out.strip()) == (0, "")


SESSION_HOOK = HOOK.parent / "session_start_check.py"
MCP_JSON = HOOK.parent.parent / ".mcp.json"


def run_session_hook(tmp_path, **env_overrides):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items()
           if k not in ("ADO_ORGANIZATION", "ADO_MCP_AUTH_TOKEN", "ADO_MCP_PROJECT")}
    env.update(HOME=str(home), USERPROFILE=str(home), **env_overrides)
    proc = subprocess.run([sys.executable, str(SESSION_HOOK)], input=b"{}",
                          capture_output=True, env=env, timeout=15)
    assert proc.returncode == 0
    hso = json.loads(proc.stdout.decode("utf-8"))["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    return hso["additionalContext"]


class TestMcpEnvDefaults:
    def test_required_vars_use_empty_default(self):
        # An unset bare ${VAR} is forwarded literally; ${VAR:-} expands to empty.
        server = json.loads(MCP_JSON.read_text(encoding="utf-8"))["azure-devops"]
        assert "${ADO_ORGANIZATION:-}" in server["args"]
        assert server["env"]["ADO_MCP_AUTH_TOKEN"] == "${ADO_MCP_AUTH_TOKEN:-}"
        assert "@azure-devops/mcp@2.8.0" in server["args"]  # pin is deliberate
        blob = json.dumps(server)
        assert "${ADO_ORGANIZATION}" not in blob and "${ADO_MCP_AUTH_TOKEN}" not in blob

    def test_unset_vars_get_clear_session_warning(self, tmp_path):
        ctx = run_session_hook(tmp_path)
        assert "ADO_ORGANIZATION, ADO_MCP_AUTH_TOKEN is unset or empty" in ctx
        assert "/init" in ctx

    def test_empty_vars_get_clear_session_warning(self, tmp_path):
        ctx = run_session_hook(tmp_path, ADO_ORGANIZATION="", ADO_MCP_AUTH_TOKEN="  ")
        assert "ADO_ORGANIZATION, ADO_MCP_AUTH_TOKEN is unset or empty" in ctx

    def test_configured_vars_no_env_warning(self, tmp_path):
        ctx = run_session_hook(tmp_path, ADO_ORGANIZATION="Org", ADO_MCP_AUTH_TOKEN="x")
        assert "MCP is not configured" not in ctx
