"""
Cross-file consistency tests for the DevOps plugin.

Validates that references between files are correct, no stale paths exist,
and naming conventions are consistent across the plugin.
"""

import json
import re
import pytest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).parent.parent
DATA_DIR = PLUGIN_ROOT / "data"
RULES_DIR = PLUGIN_ROOT / "rules"
DEVOPS_DIR = PLUGIN_ROOT / "devops"
AGENTS_DIR = PLUGIN_ROOT / "agents"
HOOKS_DIR = PLUGIN_ROOT / "hooks"
COMMANDS_DIR = PLUGIN_ROOT / "commands"


# ─── File Existence ──────────────────────────────────────────────


class TestFileExistence:
    """Verify all expected files exist."""

    @pytest.mark.parametrize("path", [
        "data/state_machine.json",
        "data/hierarchy_rules.json",
        "data/project_defaults.json",
        "data/profile_template.md",
        "data/bug_report_template.md",
        "devops/SKILL.md",
        "devops/EXAMPLES.md",
        "devops/MCP_FAILURE_MODES.md",
        "rules/write-gate.md",
        "rules/guards.md",
        "rules/profile-loader.md",
        "agents/work-item-ops.md",
        "agents/sprint-planner.md",
        "agents/pr-reviewer.md",
        "hooks/hooks.json",
        "hooks/session-start.sh",
        "hooks/pre-write-validate.sh",
        "hooks/pre-bash-check.sh",
        "hooks/post-bash-suggest.sh",
        "hooks/error-recovery.sh",
        ".claude-plugin/plugin.json",
    ])
    def test_expected_file_exists(self, path):
        assert (PLUGIN_ROOT / path).exists(), f"Expected file missing: {path}"


class TestDeletedFilesGone:
    """Verify obsolete files from pre-v6 are deleted."""

    @pytest.mark.parametrize("path", [
        "middleware",
        "references",
        "devops/workflows.md",
        "devops/profile_generator.md",
        "data/state_permissions.json",
        "data/required_fields.json",
        "data/repository_cache.json",
        "data/team_members.json",
        "hooks/check-profile.sh",
        "MIGRATION.md",
        "data/work_tracker_defaults.json",
        "data/error_patterns.json",
    ])
    def test_deleted_file_absent(self, path):
        full = PLUGIN_ROOT / path
        assert not full.exists(), f"Obsolete file/dir should be deleted: {path}"


# ─── SKILL.md References ────────────────────────────────────────


class TestSkillReferences:
    """Verify SKILL.md only references existing files."""

    @pytest.fixture(scope="class")
    def skill_content(self):
        return (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")

    def test_no_middleware_references(self, skill_content):
        assert "middleware/" not in skill_content, "SKILL.md should not reference middleware/"

    def test_no_references_dir(self, skill_content):
        assert "references/" not in skill_content, "SKILL.md should not reference references/"

    def test_no_workflows_md(self, skill_content):
        assert "workflows.md" not in skill_content, "SKILL.md should not reference workflows.md"

    def test_no_profile_generator(self, skill_content):
        assert "profile_generator.md" not in skill_content, "SKILL.md should not reference profile_generator.md"

    def test_rules_files_exist(self, skill_content):
        for match in re.findall(r'rules/(\S+\.md)', skill_content):
            assert (RULES_DIR / match).exists(), f"SKILL.md references non-existent rules/{match}"

    def test_data_files_exist(self, skill_content):
        for match in re.findall(r'data/(\S+\.json)', skill_content):
            assert (DATA_DIR / match).exists(), f"SKILL.md references non-existent data/{match}"


# ─── Agent References ───────────────────────────────────────────


class TestAgentReferences:
    """Verify agent files reference existing files and use correct structure."""

    @pytest.mark.parametrize("agent", ["work-item-ops", "sprint-planner", "pr-reviewer"])
    def test_no_stale_references(self, agent):
        content = (AGENTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
        assert "middleware/" not in content, f"{agent} references deleted middleware/"
        assert "references/" not in content, f"{agent} references deleted references/"

    @pytest.mark.parametrize("agent", ["work-item-ops", "sprint-planner", "pr-reviewer"])
    def test_has_model_in_frontmatter(self, agent):
        content = (AGENTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
        assert "model:" in content, f"{agent} missing model in frontmatter"

    @pytest.mark.parametrize("agent", ["work-item-ops", "sprint-planner", "pr-reviewer"])
    def test_has_tools_in_frontmatter(self, agent):
        content = (AGENTS_DIR / f"{agent}.md").read_text(encoding="utf-8")
        assert "tools:" in content, f"{agent} missing tools in frontmatter"

    def test_work_item_ops_uses_haiku(self):
        content = (AGENTS_DIR / "work-item-ops.md").read_text(encoding="utf-8")
        assert "model: haiku" in content

    def test_sprint_planner_uses_sonnet(self):
        content = (AGENTS_DIR / "sprint-planner.md").read_text(encoding="utf-8")
        assert "model: sonnet" in content

    def test_pr_reviewer_uses_sonnet(self):
        content = (AGENTS_DIR / "pr-reviewer.md").read_text(encoding="utf-8")
        assert "model: sonnet" in content


# ─── Hooks Consistency ──────────────────────────────────────────


class TestHooksConsistency:
    """Verify hooks.json references existing scripts."""

    @pytest.fixture(scope="class")
    def hooks_config(self):
        with open(HOOKS_DIR / "hooks.json") as f:
            return json.load(f)

    def test_all_referenced_scripts_exist(self, hooks_config):
        for event_name, event_hooks in hooks_config.get("hooks", {}).items():
            for hook_group in event_hooks:
                for hook in hook_group.get("hooks", []):
                    command = hook.get("command", "")
                    match = re.search(r'hooks/([a-zA-Z0-9_-]+\.sh)', command)
                    if match:
                        script = match.group(1)
                        assert (HOOKS_DIR / script).exists(), f"hooks.json references missing script: {script}"

    def test_has_session_start_hook(self, hooks_config):
        assert "SessionStart" in hooks_config["hooks"]

    def test_has_pre_tool_use_hooks(self, hooks_config):
        assert "PreToolUse" in hooks_config["hooks"]
        pre_hooks = hooks_config["hooks"]["PreToolUse"]
        assert len(pre_hooks) >= 2, "Should have at least Bash check and write validation hooks"

    def test_write_validation_hook_targets_correct_tools(self, hooks_config):
        pre_hooks = hooks_config["hooks"]["PreToolUse"]
        # Find the hook with tool_names matcher
        write_hook = None
        for h in pre_hooks:
            matcher = h.get("matcher", "")
            if isinstance(matcher, dict) and "tool_names" in matcher:
                write_hook = h
                break
        assert write_hook is not None, "Should have a write validation hook with tool_names matcher"
        tool_names = write_hook["matcher"]["tool_names"]
        assert "mcp__azure-devops__wit_update_work_item" in tool_names
        assert "mcp__azure-devops__wit_create_work_item" in tool_names


# ─── State Names Consistency ────────────────────────────────────


class TestStateNameConsistency:
    """Verify state names are consistent across state_machine.json."""

    @pytest.fixture(scope="class")
    def state_machine(self):
        with open(DATA_DIR / "state_machine.json") as f:
            return json.load(f)

    def test_role_permission_types_match_state_machine(self, state_machine):
        """Work item types in rolePermissions should exist in workItemTypes."""
        sm_types = set(state_machine["workItemTypes"].keys())
        for role_key, config in state_machine["rolePermissions"].items():
            perms = config.get("permissions", {})
            if isinstance(perms, str):
                continue  # $ref
            for wit_type in perms:
                assert wit_type in sm_types, f"rolePermissions.{role_key} references unknown type '{wit_type}'"

    def test_universal_rules_types_exist(self, state_machine):
        """Universal rules should reference existing work item types."""
        sm_types = set(state_machine["workItemTypes"].keys())
        for rule_name, rule in state_machine["universalRules"].items():
            for wit_type in rule.get("appliesTo", []):
                assert wit_type in sm_types, f"universalRules.{rule_name} references unknown type '{wit_type}'"

    def test_transition_arrow_format_consistent(self, state_machine):
        """All transitions should use ' -> ' format (not ' → ')."""
        for wit_type, config in state_machine["workItemTypes"].items():
            for key in config.get("transitions", {}):
                assert " → " not in key, f"{wit_type}: transition '{key}' uses '→' instead of '->'"

    def test_role_permission_arrows_consistent(self, state_machine):
        """Role permission allowed/blocked should use ' -> ' format."""
        for role_key, config in state_machine["rolePermissions"].items():
            perms = config.get("permissions", {})
            if isinstance(perms, str):
                continue
            for wit_type, wit_perms in perms.items():
                for transition in wit_perms.get("allowed", []) + wit_perms.get("blocked", []):
                    assert " -> " in transition, f"rolePermissions.{role_key}.{wit_type}: '{transition}' should use ' -> ' format"


# ─── Command Uniqueness ─────────────────────────────────────────


class TestCommandUniqueness:
    """Verify command files exist and have unique names."""

    EXPECTED_COMMANDS = [
        "init", "create", "workday", "log-time",
        "timesheet", "standup", "sprint", "task-monitor", "cli-run"
    ]

    def test_all_expected_commands_exist(self):
        for cmd in self.EXPECTED_COMMANDS:
            assert (COMMANDS_DIR / f"{cmd}.md").exists(), f"Command file missing: {cmd}.md"

    def test_command_count(self):
        commands = list(COMMANDS_DIR.glob("*.md"))
        assert len(commands) == 9, f"Expected 9 commands, found {len(commands)}"


# ─── Plugin JSON ─────────────────────────────────────────────────


class TestPluginJson:
    """Verify plugin.json is valid and up-to-date."""

    @pytest.fixture(scope="class")
    def plugin_config(self):
        with open(PLUGIN_ROOT / ".claude-plugin" / "plugin.json") as f:
            return json.load(f)

    def test_version_is_6(self, plugin_config):
        assert plugin_config["version"].startswith("6."), f"Plugin version should be 6.x, got {plugin_config['version']}"

    def test_has_name(self, plugin_config):
        assert plugin_config["name"] == "devops"

    def test_has_author(self, plugin_config):
        assert "author" in plugin_config


# ─── PostToolUseFailure Matcher ────────────────────────────────


class TestFailureHookScoped:
    """Verify PostToolUseFailure hook is scoped to Azure DevOps tools only."""

    @pytest.fixture(scope="class")
    def hooks_config(self):
        with open(HOOKS_DIR / "hooks.json") as f:
            return json.load(f)

    def test_failure_hook_not_empty_matcher(self, hooks_config):
        """PostToolUseFailure matcher must NOT be empty string (catches all tools)."""
        failure_hooks = hooks_config["hooks"].get("PostToolUseFailure", [])
        for hook_group in failure_hooks:
            matcher = hook_group.get("matcher", "")
            assert matcher != "", "PostToolUseFailure matcher must not be empty string — scope to azure-devops tools"

    def test_failure_hook_scoped_to_azure_devops(self, hooks_config):
        """PostToolUseFailure should match only mcp__azure-devops__ tools."""
        failure_hooks = hooks_config["hooks"].get("PostToolUseFailure", [])
        for hook_group in failure_hooks:
            matcher = hook_group.get("matcher", "")
            if isinstance(matcher, dict):
                regex = matcher.get("tool_names_regex", "")
                assert "azure-devops" in regex, f"PostToolUseFailure regex should target azure-devops, got: {regex}"


# ─── Error Ownership Consolidation ─────────────────────────────


class TestErrorOwnership:
    """Verify error handling has a single source of truth in state_machine.json."""

    @pytest.fixture(scope="class")
    def state_machine(self):
        with open(DATA_DIR / "state_machine.json") as f:
            return json.load(f)

    def test_no_common_errors_in_state_machine(self, state_machine):
        """commonErrors should not exist as a top-level key."""
        assert "commonErrors" not in state_machine, "state_machine.json should not contain commonErrors"

    def test_error_patterns_embedded(self, state_machine):
        """errorPatterns should be embedded in state_machine.json with a patterns sub-key."""
        assert "errorPatterns" in state_machine, "state_machine.json should contain errorPatterns"
        ep = state_machine["errorPatterns"]
        assert "patterns" in ep, "errorPatterns should have a 'patterns' sub-key"
        assert len(ep["patterns"]) >= 5, "Should have at least 5 error patterns"

    def test_error_patterns_has_no_bloat(self, state_machine):
        """errorPatterns should not contain emoji, template, or recoveryTypes sections."""
        ep = state_machine["errorPatterns"]
        assert "emojis" not in ep, "errorPatterns should not contain emojis section"
        assert "errorMessageTemplates" not in ep, "errorPatterns should not contain errorMessageTemplates"
        assert "recoveryTypes" not in ep, "errorPatterns should not contain recoveryTypes"
        assert "fieldFriendlyNames" not in ep, "errorPatterns should not contain fieldFriendlyNames"

    def test_error_patterns_recovery_has_steps(self, state_machine):
        """Each error pattern's recovery should have a 'steps' list."""
        for code, pattern in state_machine["errorPatterns"]["patterns"].items():
            recovery = pattern.get("recovery", {})
            assert "steps" in recovery, f"Error {code} recovery missing 'steps' list"
            assert isinstance(recovery["steps"], list), f"Error {code} recovery.steps must be a list"


# ─── Command Completeness ─────────────────────────────────────


class TestCommandCompleteness:
    """Verify command files have examples and primary agent."""

    EXPECTED_COMMANDS = [
        "init", "create", "workday", "log-time",
        "timesheet", "standup", "sprint", "task-monitor", "cli-run"
    ]

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_has_example(self, cmd):
        content = (COMMANDS_DIR / f"{cmd}.md").read_text(encoding="utf-8")
        has_example = "## Example" in content or "Example:" in content or "Examples:" in content or "```" in content
        assert has_example, f"Command {cmd}.md should contain an example section"

    @pytest.mark.parametrize("cmd", EXPECTED_COMMANDS)
    def test_command_has_primary_agent(self, cmd):
        content = (COMMANDS_DIR / f"{cmd}.md").read_text(encoding="utf-8")
        has_agent = "primary_agent:" in content or "Primary Agent" in content
        assert has_agent, f"Command {cmd}.md should identify its primary agent"


# ─── Example Profile ──────────────────────────────────────────


class TestExampleProfile:
    """Verify example profile exists and is realistic."""

    def test_example_profile_exists(self):
        assert (DATA_DIR / "example_profile.md").exists(), "data/example_profile.md not found"

    def test_example_profile_has_identity(self):
        content = (DATA_DIR / "example_profile.md").read_text(encoding="utf-8")
        assert "identity:" in content
        assert "displayName:" in content
        assert "guid:" in content

    def test_example_profile_has_team_members(self):
        content = (DATA_DIR / "example_profile.md").read_text(encoding="utf-8")
        assert "teamMembers:" in content
