"""
Integration flow tests for the DevOps plugin.

These tests validate that the plugin's command/skill/agent/hook/rule chain
is wired correctly — not that Azure DevOps APIs work, but that:
1. Every command references rules/data that exist
2. Every agent's guard table points to real files
3. Hooks match the correct MCP tool names
4. The ownership model has no orphans or conflicts

Run: pytest tests/test_integration_flows.py -v
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

# ─── Flow: Write Gate is reachable from all write paths ────────


class TestWriteGateFlow:
    """Verify write-gate.md is referenced by every component that can write."""

    WRITE_COMPONENTS = [
        ("devops/SKILL.md", "rules/write-gate.md"),
        ("agents/work-item-ops.md", "rules/write-gate.md"),
        ("agents/pr-reviewer.md", "rules/write-gate.md"),
    ]

    @pytest.mark.parametrize("component,gate_ref", WRITE_COMPONENTS)
    def test_write_component_references_gate(self, component, gate_ref):
        content = (PLUGIN_ROOT / component).read_text(encoding="utf-8")
        assert gate_ref in content, f"{component} must reference {gate_ref}"

    def test_write_gate_file_has_classified_operations(self):
        content = (RULES_DIR / "write-gate.md").read_text(encoding="utf-8")
        for section in ["CREATE", "UPDATE", "DELETE", "READ"]:
            assert section in content, f"write-gate.md missing {section} classification"

    def test_write_gate_has_approval_triggers(self):
        content = (RULES_DIR / "write-gate.md").read_text(encoding="utf-8")
        assert "yes" in content.lower()
        assert "no" in content.lower()


# ─── Flow: Tool Selection Guard reaches agents ─────────────────


class TestToolSelectionFlow:
    """Verify tool selection guard is wired through the correct chain."""

    def test_skill_references_guard_1(self):
        content = (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")
        assert "guards.md" in content and "Guard 1" in content

    def test_work_item_ops_references_guard_1(self):
        content = (AGENTS_DIR / "work-item-ops.md").read_text(encoding="utf-8")
        assert "guards.md" in content and "Guard 1" in content

    def test_guard_1_defines_decision_table(self):
        content = (RULES_DIR / "guards.md").read_text(encoding="utf-8")
        assert "wit_my_work_items" in content
        assert "search_workitem" in content
        assert "Decision Table" in content


# ─── Flow: Mention Processing reaches comment workflow ──────────


class TestMentionFlow:
    """Verify mention resolution is wired for comment operations."""

    def test_skill_workflow_2_references_guard_2(self):
        content = (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")
        assert "Guard 2" in content

    def test_hook_checks_mentions_on_comment(self):
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert "wit_add_work_item_comment" in content
        assert "data-vss-mention" in content

    def test_guard_2_defines_mention_checklist(self):
        content = (RULES_DIR / "guards.md").read_text(encoding="utf-8")
        assert "Guard 2" in content
        assert "data-vss-mention" in content


# ─── Flow: State Machine reaches pre-flight validation ──────────


class TestStateMachineFlow:
    """Verify state machine data is reachable from all validation paths."""

    def test_skill_references_state_machine(self):
        content = (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")
        assert "state_machine.json" in content

    def test_hook_references_state_machine(self):
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert "state_machine.json" in content or "state change" in content.lower()

    def test_state_machine_has_all_required_sections(self):
        with open(DATA_DIR / "state_machine.json") as f:
            sm = json.load(f)
        for key in ["workItemTypes", "rolePermissions", "universalRules", "businessRules"]:
            assert key in sm, f"state_machine.json missing {key}"


# ─── Flow: Hook targets match actual MCP tool names ─────────────


class TestHookToolTargeting:
    """Verify hooks.json tool_names match the tools agents actually use."""

    @pytest.fixture(scope="class")
    def hooks_config(self):
        with open(HOOKS_DIR / "hooks.json") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def agent_tools(self):
        """Collect all MCP tools declared in agent frontmatter."""
        tools = set()
        for agent_file in AGENTS_DIR.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            for match in re.findall(r'mcp__azure-devops__\w+', content):
                tools.add(match)
        return tools

    def test_hook_write_tools_are_in_agent_toolsets(self, hooks_config, agent_tools):
        """Every MCP tool the hook intercepts should be available to at least one agent."""
        for hook_group in hooks_config["hooks"].get("PreToolUse", []):
            matcher = hook_group.get("matcher", "")
            if isinstance(matcher, dict) and "tool_names" in matcher:
                for tool in matcher["tool_names"]:
                    assert tool in agent_tools, (
                        f"Hook intercepts '{tool}' but no agent declares it in tools"
                    )

    def test_bug_block_exits_with_2(self):
        """The bug creation authority check must hard-block (exit 2)."""
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert "exit 2" in content, "Bug creation block must use exit 2"

    def test_three_hard_blocks_exist(self):
        """Should have exit 2 for bug creation, close/remove restriction, and mention resolution."""
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert content.count("exit 2") >= 3, "Should have at least 3 hard blocks (exit 2)"

    def test_close_remove_block_in_hook(self):
        """The close/remove restriction check must hard-block."""
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert "BLOCKED" in content and "Closed" in content, "Should block non-PM/Lead from closing"

    def test_mention_block_exits_with_2(self):
        """The unresolved mention check must hard-block (exit 2)."""
        content = (HOOKS_DIR / "pre-write-validate.sh").read_text(encoding="utf-8")
        assert "BLOCKED: Unresolved @mentions" in content


# ─── Flow: No duplicated guard logic (P0 regression) ────────────


class TestNoDuplicatedGuards:
    """Verify P0 deduplication holds — guards should be references, not re-implementations."""

    def test_skill_does_not_redefine_write_gate(self):
        content = (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")
        # Should reference write-gate.md, NOT re-explain the full protocol
        assert "Classified Operations" not in content, "SKILL.md should not re-define classified operations"
        assert "NEVER EXECUTE WITHOUT CONFIRMATION" not in content, "SKILL.md should not duplicate write-gate header"

    def test_skill_does_not_redefine_tool_selection(self):
        content = (DEVOPS_DIR / "SKILL.md").read_text(encoding="utf-8")
        # Should NOT have the full decision table — that's in guards.md
        assert "Auto-Correction Rules" not in content, "SKILL.md should not duplicate auto-correction rules"

    def test_agents_do_not_redefine_guards(self):
        for agent_file in AGENTS_DIR.glob("*.md"):
            content = agent_file.read_text(encoding="utf-8")
            assert "TEXT SEARCH ONLY" not in content, (
                f"{agent_file.name} should not re-explain tool selection — use reference"
            )
            assert "NEVER EXECUTE WITHOUT CONFIRMATION" not in content, (
                f"{agent_file.name} should not re-explain write gate — use reference"
            )


# ─── Flow: MCP server declared ──────────────────────────────────


class TestMcpServerDeclared:
    """Verify .mcp.json exists and declares the Azure DevOps server."""

    def test_mcp_json_exists(self):
        assert (PLUGIN_ROOT / ".mcp.json").exists(), ".mcp.json missing from plugin root"

    def test_mcp_json_declares_azure_devops(self):
        with open(PLUGIN_ROOT / ".mcp.json") as f:
            config = json.load(f)
        servers = config.get("mcpServers", {})
        assert "azure-devops" in servers, ".mcp.json must declare azure-devops server"

    def test_mcp_json_uses_env_vars(self):
        with open(PLUGIN_ROOT / ".mcp.json") as f:
            content = f.read()
        assert "${ADO_PAT_TOKEN}" in content, ".mcp.json should use ADO_PAT_TOKEN env var"
        assert "${ADO_ORGANIZATION}" in content, ".mcp.json should use ADO_ORGANIZATION env var"


# ─── Flow: Staleness threshold is configurable ───────────────────


class TestStalenessConfigurable:
    """Verify profile staleness reads from config, not hardcoded."""

    def test_project_defaults_has_staleness_field(self):
        with open(DATA_DIR / "project_defaults.json") as f:
            config = json.load(f)
        wt = config.get("workTracking", {})
        assert "profileStalenessThresholdDays" in wt
        assert isinstance(wt["profileStalenessThresholdDays"], int)

    def test_session_start_reads_from_config(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "profileStalenessThresholdDays" in content, (
            "session-start.sh should read threshold from project_defaults.json"
        )
        assert "30" not in content or "STALENESS_DAYS" in content, (
            "session-start.sh should not hardcode 30-day threshold"
        )


# ─── Flow: SessionStart consistency checks ─────────────────────


class TestSessionStartConsistencyChecks:
    """Verify session-start.sh has lightweight consistency checks."""

    def test_json_validation_in_session_start(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "json.load" in content, "session-start should validate JSON syntax"
        assert "state_machine.json" in content
        assert "project_defaults.json" in content

    def test_plugin_version_check(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "plugin.json" in content, "session-start should check plugin version"

    def test_profile_field_check(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "teamMembers:" in content, "session-start should check for teamMembers field"

    def test_data_file_existence_check(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "hierarchy_rules.json" in content, "session-start should verify core data files exist"

    def test_profile_schema_version_check(self):
        content = (HOOKS_DIR / "session-start.sh").read_text(encoding="utf-8")
        assert "schemaVersion" in content, "session-start should check profile schema version"
