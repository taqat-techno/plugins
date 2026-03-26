"""
Tests for data/state_machine.json — the single source of truth for
state transitions, role permissions, required fields, and business rules.

Validates the merged schema's internal consistency and correctness.
"""

import json
import re
import pytest
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="module")
def state_machine():
    with open(DATA_DIR / "state_machine.json") as f:
        return json.load(f)


# ─── Schema Validation ───────────────────────────────────────────


class TestSchema:
    """Verify state_machine.json has all required top-level keys and structure."""

    def test_has_required_top_level_keys(self, state_machine):
        for key in ["workItemTypes", "rolePermissions", "universalRules", "businessRules", "preFlightFields"]:
            assert key in state_machine, f"Missing top-level key: {key}"

    def test_has_meta(self, state_machine):
        assert "_meta" in state_machine
        assert "version" in state_machine["_meta"]

    def test_work_item_types_not_empty(self, state_machine):
        assert len(state_machine["workItemTypes"]) >= 5, "Should have at least Task, Bug, PBI, UserStory, Enhancement"

    def test_role_permissions_not_empty(self, state_machine):
        assert len(state_machine["rolePermissions"]) >= 3, "Should have at least developer, qa, pm"


# ─── Transition Completeness ─────────────────────────────────────


class TestTransitionCompleteness:
    """Every work item type should have at least entry -> done transitions."""

    @pytest.mark.parametrize("wit_type", ["Task", "Bug", "ProductBacklogItem", "UserStory", "Enhancement", "Feature", "Epic"])
    def test_type_has_states(self, state_machine, wit_type):
        assert wit_type in state_machine["workItemTypes"], f"{wit_type} not found"
        config = state_machine["workItemTypes"][wit_type]
        assert "states" in config, f"{wit_type} missing 'states'"
        assert len(config["states"]) >= 2, f"{wit_type} should have at least 2 states"

    @pytest.mark.parametrize("wit_type", ["Task", "Bug", "ProductBacklogItem", "UserStory", "Enhancement", "Feature", "Epic"])
    def test_type_has_transitions(self, state_machine, wit_type):
        config = state_machine["workItemTypes"][wit_type]
        assert "transitions" in config, f"{wit_type} missing 'transitions'"
        assert len(config["transitions"]) >= 1, f"{wit_type} should have at least 1 transition"

    @pytest.mark.parametrize("wit_type", ["Task", "Bug", "ProductBacklogItem", "UserStory", "Enhancement", "Feature", "Epic"])
    def test_type_has_happy_path(self, state_machine, wit_type):
        config = state_machine["workItemTypes"][wit_type]
        assert "happyPath" in config, f"{wit_type} missing 'happyPath'"
        assert len(config["happyPath"]) >= 2

    def test_transition_keys_reference_valid_states(self, state_machine):
        """Every transition 'From -> To' should reference states that exist."""
        for wit_type, config in state_machine["workItemTypes"].items():
            states = set(config["states"])
            for key in config.get("transitions", {}):
                if key.startswith("Any"):
                    continue
                parts = key.split(" -> ")
                assert len(parts) == 2, f"{wit_type}: invalid transition format '{key}'"
                from_state, to_state = parts
                assert from_state in states, f"{wit_type}: transition '{key}' references unknown from-state '{from_state}'"
                assert to_state in states, f"{wit_type}: transition '{key}' references unknown to-state '{to_state}'"

    def test_happy_path_states_exist(self, state_machine):
        for wit_type, config in state_machine["workItemTypes"].items():
            states = set(config["states"])
            for state in config.get("happyPath", []):
                assert state in states, f"{wit_type}: happyPath state '{state}' not in states"

    def test_return_path_states_exist(self, state_machine):
        for wit_type, config in state_machine["workItemTypes"].items():
            states = set(config["states"])
            for state in config.get("returnPath", []):
                assert state in states, f"{wit_type}: returnPath state '{state}' not in states"


# ─── Role Coverage ───────────────────────────────────────────────


class TestRoleCoverage:
    """Every role should have meaningful permissions for the core work item types."""

    CORE_TYPES = ["Task", "Bug", "ProductBacklogItem", "Enhancement"]

    @pytest.mark.parametrize("role", ["developer", "qa", "pm"])
    def test_role_has_permissions_for_core_types(self, state_machine, role):
        perms = state_machine["rolePermissions"][role].get("permissions", {})
        if isinstance(perms, str) and perms.startswith("$ref:"):
            return  # Reference to another role, skip
        for wit_type in self.CORE_TYPES:
            assert wit_type in perms, f"Role '{role}' missing permissions for {wit_type}"

    @pytest.mark.parametrize("role", ["developer", "qa", "pm"])
    def test_role_has_at_least_one_allowed_transition(self, state_machine, role):
        perms = state_machine["rolePermissions"][role].get("permissions", {})
        if isinstance(perms, str):
            return
        total_allowed = sum(len(p.get("allowed", [])) for p in perms.values())
        assert total_allowed >= 1, f"Role '{role}' has no allowed transitions"

    def test_developer_cannot_close(self, state_machine):
        dev_perms = state_machine["rolePermissions"]["developer"]["permissions"]
        for wit_type in ["Task", "Bug", "Enhancement"]:
            blocked = dev_perms.get(wit_type, {}).get("blocked", [])
            close_transitions = [t for t in blocked if "Closed" in t]
            assert len(close_transitions) > 0, f"Developer should be blocked from closing {wit_type}"

    def test_qa_cannot_resolve_bugs(self, state_machine):
        qa_perms = state_machine["rolePermissions"]["qa"]["permissions"]
        bug_blocked = qa_perms.get("Bug", {}).get("blocked", [])
        assert any("Resolved" in t for t in bug_blocked), "QA should be blocked from resolving Bugs"

    def test_pm_can_close(self, state_machine):
        pm_perms = state_machine["rolePermissions"]["pm"]["permissions"]
        for wit_type in ["Task", "Bug"]:
            allowed = pm_perms.get(wit_type, {}).get("allowed", [])
            assert any("Closed" in t for t in allowed), f"PM should be able to close {wit_type}"

    def test_frontend_ref_is_valid(self, state_machine):
        frontend = state_machine["rolePermissions"].get("frontend", {})
        perms = frontend.get("permissions", "")
        if isinstance(perms, str) and perms.startswith("$ref:"):
            ref_target = perms.replace("$ref:", "")
            assert ref_target in state_machine["rolePermissions"], f"Frontend $ref target '{ref_target}' not found"

    def test_all_roles_have_applies_to(self, state_machine):
        for role_key, config in state_machine["rolePermissions"].items():
            assert config.get("appliesTo"), f"Role '{role_key}' has empty appliesTo"


# ─── Required Fields ─────────────────────────────────────────────


class TestRequiredFields:
    """Validate required field definitions in transitions."""

    def test_task_done_requires_hours(self, state_machine):
        task = state_machine["workItemTypes"]["Task"]
        transition = task["transitions"].get("In Progress -> Done", {})
        required = [f["field"] for f in transition.get("requiredFields", [])]
        assert "Microsoft.VSTS.Scheduling.OriginalEstimate" in required
        assert "Microsoft.VSTS.Scheduling.CompletedWork" in required

    def test_task_done_auto_sets_remaining_work(self, state_machine):
        task = state_machine["workItemTypes"]["Task"]
        transition = task["transitions"].get("In Progress -> Done", {})
        auto_set = transition.get("autoSetFields", {})
        assert "Microsoft.VSTS.Scheduling.RemainingWork" in auto_set

    def test_bug_resolved_requires_reason(self, state_machine):
        bug = state_machine["workItemTypes"]["Bug"]
        transition = bug["transitions"].get("In Progress -> Resolved", {})
        required = [f["field"] for f in transition.get("requiredFields", [])]
        assert "Microsoft.VSTS.Common.ResolvedReason" in required

    def test_bug_resolved_has_default(self, state_machine):
        bug = state_machine["workItemTypes"]["Bug"]
        transition = bug["transitions"].get("In Progress -> Resolved", {})
        for field in transition.get("requiredFields", []):
            if field["field"] == "Microsoft.VSTS.Common.ResolvedReason":
                assert field.get("default") == "Fixed"

    def test_required_fields_have_prompts(self, state_machine):
        """Every required field should have a prompt for the user."""
        for wit_type, config in state_machine["workItemTypes"].items():
            for trans_key, trans_config in config.get("transitions", {}).items():
                for field in trans_config.get("requiredFields", []):
                    assert "prompt" in field, f"{wit_type} {trans_key}: field '{field['field']}' missing prompt"
                    assert "field" in field, f"{wit_type} {trans_key}: required field entry missing 'field' key"

    def test_field_paths_are_valid_format(self, state_machine):
        """Field paths should follow Microsoft.VSTS.* or System.* format."""
        for wit_type, config in state_machine["workItemTypes"].items():
            for trans_key, trans_config in config.get("transitions", {}).items():
                for field in trans_config.get("requiredFields", []):
                    field_name = field["field"]
                    assert "." in field_name, f"Field '{field_name}' doesn't look like a valid Azure DevOps field path"


# ─── Return Loop Handling ────────────────────────────────────────


class TestReturnLoops:
    """Validate return transitions require comments."""

    @pytest.mark.parametrize("wit_type,transition", [
        ("Bug", "Resolved -> Return"),
        ("ProductBacklogItem", "Ready For QC -> Return"),
        ("Enhancement", "Committed -> Return"),
    ])
    def test_return_requires_comment(self, state_machine, wit_type, transition):
        config = state_machine["workItemTypes"][wit_type]
        trans = config["transitions"].get(transition, {})
        assert trans.get("requiresComment") is True, f"{wit_type} {transition} should require a comment"
        assert "commentPrompt" in trans, f"{wit_type} {transition} should have a commentPrompt"

    def test_return_types_have_return_path(self, state_machine):
        for wit_type in ["Bug", "ProductBacklogItem", "Enhancement"]:
            config = state_machine["workItemTypes"][wit_type]
            assert config.get("hasReturn") is True, f"{wit_type} should have hasReturn=true"
            assert "returnPath" in config, f"{wit_type} should have returnPath"


# ─── Gates ───────────────────────────────────────────────────────


class TestGates:
    """Validate QC gate and Committed gate definitions."""

    def test_pbi_has_qc_gate(self, state_machine):
        pbi = state_machine["workItemTypes"]["ProductBacklogItem"]
        assert "qcGate" in pbi, "PBI should have qcGate"
        gate = pbi["qcGate"]
        assert "blockedTransitions" in gate
        assert "requiredIntermediate" in gate
        assert gate["requiredIntermediate"] == "Ready For QC"

    def test_user_story_has_committed_gate(self, state_machine):
        us = state_machine["workItemTypes"]["UserStory"]
        assert "committedGate" in us, "UserStory should have committedGate"
        gate = us["committedGate"]
        assert gate["requiredIntermediate"] == "Committed"

    def test_pbi_qc_gate_blocks_direct_done(self, state_machine):
        pbi = state_machine["workItemTypes"]["ProductBacklogItem"]
        blocked = pbi["qcGate"]["blockedTransitions"]
        assert "In Progress -> Done" in blocked


# ─── Business Rules ──────────────────────────────────────────────


class TestBusinessRules:
    """Validate business rules section."""

    def test_task_naming_has_prefixes(self, state_machine):
        naming = state_machine["businessRules"]["taskNaming"]
        prefixes = naming["defaultPrefixes"]
        assert len(prefixes) >= 5
        prefix_names = [p["prefix"] for p in prefixes]
        assert "[Dev]" in prefix_names
        assert "[Front]" in prefix_names

    def test_bug_creation_authority_defined(self, state_machine):
        bug_auth = state_machine["businessRules"]["bugCreationAuthority"]
        assert "qaRoles" in bug_auth
        assert len(bug_auth["qaRoles"]) >= 2
        assert "developerRedirect" in bug_auth

    def test_user_story_format_defined(self, state_machine):
        fmt = state_machine["businessRules"]["userStoryFormat"]
        assert "sections" in fmt
        assert len(fmt["sections"]) == 3

    def test_error_patterns_embedded(self, state_machine):
        """errorPatterns should be embedded directly in state_machine.json."""
        assert "commonErrors" not in state_machine, "commonErrors should be removed"
        assert "_errorReference" not in state_machine, "_errorReference pointer should be removed — errorPatterns is embedded"
        assert "errorPatterns" in state_machine, "state_machine should have embedded errorPatterns"
        assert "patterns" in state_machine["errorPatterns"], "errorPatterns should have patterns sub-key"


# ─── Universal Rules ─────────────────────────────────────────────


class TestUniversalRules:
    """Validate universal permission rules."""

    def test_close_restriction_exists(self, state_machine):
        rule = state_machine["universalRules"]["closeRestriction"]
        assert "pm" in rule["allowedRoles"] or "lead" in rule["allowedRoles"]

    def test_remove_restriction_exists(self, state_machine):
        rule = state_machine["universalRules"]["removeRestriction"]
        assert "pm" in rule["allowedRoles"]

    def test_return_handling_requires_comment(self, state_machine):
        rule = state_machine["universalRules"]["returnHandling"]
        assert rule["requireComment"] is True

    def test_no_profile_fallback(self, state_machine):
        rule = state_machine["universalRules"]["noProfileFallback"]
        assert rule["behavior"] == "warn-and-allow"
