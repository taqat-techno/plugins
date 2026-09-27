"""
Behavioral tests for hooks/pre_write_validate.py.

The hook is invoked as a subprocess with a PreToolUse JSON payload on stdin,
exactly as Claude Code calls it. HOME/USERPROFILE point at a temp dir so the
role comes from a test profile, never the real ~/.claude/devops.md.

Contract under test:
  * hard blocks exit 2 with the reason on stderr (Claude sees it as the denial)
  * soft reminders exit 0 with hookSpecificOutput JSON carrying BOTH
    hookEventName "PreToolUse" and additionalContext -- without hookEventName
    Claude Code rejects the output and the reminder never reaches the model
  * no permissionDecision is ever emitted (normal permission flow untouched)

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


YAML_DEV = "---\nrole: developer\n---\n"
YAML_PM = 'role: "pm"\n'
MD_DEV = "| Field | Value |\n|---|---|\n| **Primary Role** | developer |\n"


class TestStateChange:
    def test_close_blocked_for_developer(self, tmp_path):
        code, out, err = run_hook(update("Closed"), tmp_path, YAML_DEV)
        assert code == 2
        assert "BLOCKED" in err and "'developer'" in err and "'Closed'" in err
        assert out.strip() == ""

    def test_close_allowed_for_pm_with_reminder(self, tmp_path):
        code, out, _ = run_hook(update("Closed"), tmp_path, YAML_PM)
        assert code == 0
        assert "State change to 'Closed'" in context_of(out)

    def test_close_without_profile_is_reminder_only(self, tmp_path):
        code, out, _ = run_hook(update("Removed"), tmp_path)
        assert code == 0
        assert "state_machine.json" in context_of(out)

    def test_ordinary_state_change_reminds(self, tmp_path):
        code, out, _ = run_hook(update("In Progress"), tmp_path, YAML_DEV)
        assert code == 0
        assert "'In Progress'" in context_of(out)

    def test_legacy_tool_name_is_recognized(self, tmp_path):
        code, _, _ = run_hook(update("Closed", "mcp__azure-devops__wit_update_work_item"),
                              tmp_path, YAML_DEV)
        assert code == 2

    def test_bare_state_path_is_detected(self, tmp_path):
        code, _, _ = run_hook(update("Closed", path="System.State"), tmp_path, YAML_DEV)
        assert code == 2

    def test_state_is_read_from_its_own_update_not_the_first(self, tmp_path):
        # The bash hook took the first "value" in the payload: here "Closed" would
        # have been missed because the title update comes first.
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"id": 7,
                   "updates": [{"op": "add", "path": "/fields/System.Title", "value": "t"},
                               {"op": "add", "path": "/fields/System.State",
                                "value": "Closed"}]}}
        code, _, err = run_hook(payload, tmp_path, YAML_DEV)
        assert code == 2
        assert "'Closed'" in err

    def test_state_text_in_a_title_is_not_a_state_change(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"id": 7,
                   "updates": [{"op": "add", "path": "/fields/System.Title",
                                "value": "Document \"System.State\" handling"}]}}
        code, out, _ = run_hook(payload, tmp_path, YAML_DEV)
        assert (code, out.strip()) == (0, "")

    def test_update_without_state_is_silent(self, tmp_path):
        payload = {"tool_name": PREFIX + "wit_update_work_item", "tool_input": {"updates": [
            {"op": "add", "path": "/fields/System.Title", "value": "x"}]}}
        code, out, err = run_hook(payload, tmp_path, YAML_DEV)
        assert (code, out.strip(), err.strip()) == (0, "", "")


class TestCreate:
    def test_bug_blocked_for_developer_markdown_profile(self, tmp_path):
        code, _, err = run_hook(create("Bug"), tmp_path, MD_DEV)
        assert code == 2
        assert "cannot create Bugs" in err

    def test_bug_allowed_for_pm_with_hierarchy_reminder(self, tmp_path):
        code, out, _ = run_hook(create("Bug"), tmp_path, YAML_PM)
        assert code == 0
        assert "User Story/PBI" in context_of(out)

    @pytest.mark.parametrize("wi_type,parent", [
        ("Task", "User Story/PBI"),
        ("User Story", "Feature"),
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
