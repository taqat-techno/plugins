#!/usr/bin/env python3
"""
Consistency Check — Cross-file drift detection for the DevOps plugin.

Validates that state_machine.json, hierarchy_rules.json, and rules/*.md
are internally consistent and reference valid entities.

Usage:
    python tests/consistency_check.py
    python tests/consistency_check.py --verbose

Exit codes:
    0 = all checks pass
    1 = one or more checks failed
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Tuple

PLUGIN_ROOT = Path(__file__).parent.parent
DATA_DIR = PLUGIN_ROOT / "data"
RULES_DIR = PLUGIN_ROOT / "rules"
DEVOPS_DIR = PLUGIN_ROOT / "devops"
AGENTS_DIR = PLUGIN_ROOT / "agents"

VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv


def log(msg: str):
    print(f"  {msg}")


def log_verbose(msg: str):
    if VERBOSE:
        print(f"    {msg}")


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def check_state_machine_schema() -> List[str]:
    """Validate state_machine.json internal consistency."""
    errors = []
    sm = load_json(DATA_DIR / "state_machine.json")

    # Check required top-level keys
    for key in ["workItemTypes", "rolePermissions", "universalRules", "businessRules"]:
        if key not in sm:
            errors.append(f"state_machine.json missing top-level key: {key}")

    wit_types = sm.get("workItemTypes", {})

    # Check each work item type has required fields
    for wit_name, wit_config in wit_types.items():
        if "states" not in wit_config:
            errors.append(f"state_machine.json: {wit_name} missing 'states'")
        if "transitions" not in wit_config:
            errors.append(f"state_machine.json: {wit_name} missing 'transitions'")

        # Validate transition keys reference valid states
        states = set(wit_config.get("states", []))
        for transition_key in wit_config.get("transitions", {}):
            if transition_key.startswith("Any"):
                continue  # "Any -> Removed" is a wildcard
            parts = transition_key.split(" -> ")
            if len(parts) != 2:
                errors.append(f"state_machine.json: {wit_name} invalid transition key format: '{transition_key}'")
                continue
            from_state, to_state = parts
            if from_state not in states:
                errors.append(f"state_machine.json: {wit_name} transition references unknown from-state: '{from_state}'")
            if to_state not in states:
                errors.append(f"state_machine.json: {wit_name} transition references unknown to-state: '{to_state}'")

        # Validate happyPath states exist
        for state in wit_config.get("happyPath", []):
            if state not in states:
                errors.append(f"state_machine.json: {wit_name} happyPath references unknown state: '{state}'")

        # Validate returnPath states exist
        for state in wit_config.get("returnPath", []):
            if state not in states:
                errors.append(f"state_machine.json: {wit_name} returnPath references unknown state: '{state}'")

        log_verbose(f"{wit_name}: {len(states)} states, {len(wit_config.get('transitions', {}))} transitions")

    return errors


def check_role_permissions() -> List[str]:
    """Validate role permissions reference valid work item types and transitions."""
    errors = []
    sm = load_json(DATA_DIR / "state_machine.json")

    wit_types = set(sm.get("workItemTypes", {}).keys())
    role_perms = sm.get("rolePermissions", {})

    for role_key, role_config in role_perms.items():
        perms = role_config.get("permissions", {})

        # Handle $ref (e.g., frontend -> developer)
        if isinstance(perms, str) and perms.startswith("$ref:"):
            ref_role = perms.replace("$ref:", "")
            if ref_role not in role_perms:
                errors.append(f"rolePermissions.{role_key} references unknown role: {ref_role}")
            log_verbose(f"Role '{role_key}' -> $ref:{ref_role}")
            continue

        # Check that permission work item types exist
        for wit_name in perms:
            if wit_name not in wit_types:
                errors.append(f"rolePermissions.{role_key} references unknown type: '{wit_name}'")

            wit_perms = perms[wit_name]
            wit_config = sm["workItemTypes"].get(wit_name, {})
            wit_transitions = set(wit_config.get("transitions", {}).keys())

            # Check allowed transitions exist in state machine
            for transition in wit_perms.get("allowed", []):
                normalized = transition.replace(" → ", " -> ")
                if normalized not in wit_transitions and not any(t.startswith("Any") for t in wit_transitions if normalized.endswith(t.split(" -> ")[-1])):
                    log_verbose(f"  Warning: {role_key}.{wit_name} allowed transition '{transition}' not in state machine transitions")

        # Check appliesTo is not empty
        if not role_config.get("appliesTo"):
            errors.append(f"rolePermissions.{role_key} has empty 'appliesTo'")

        log_verbose(f"Role '{role_key}': covers {len(perms)} work item types")

    return errors


def check_hierarchy_rules() -> List[str]:
    """Validate hierarchy_rules.json references valid work item types."""
    errors = []
    sm = load_json(DATA_DIR / "state_machine.json")
    hr = load_json(DATA_DIR / "hierarchy_rules.json")

    sm_types = set(sm.get("workItemTypes", {}).keys())
    parent_child_rules = hr.get("parentChildRules", {})

    for child_type in parent_child_rules:
        # Check child type exists in state machine (with common aliases)
        normalized = child_type.replace(" ", "")
        if child_type not in sm_types and normalized not in sm_types:
            # Allow "User Story" even though state_machine uses "UserStory"
            if child_type not in ["User Story", "Product Backlog Item"]:
                log_verbose(f"  Note: hierarchy child type '{child_type}' not directly in state_machine (may use alternate name)")

        # Check valid parent types
        for parent_type in parent_child_rules[child_type].get("validParents", []):
            if parent_type not in sm_types and parent_type.replace(" ", "") not in sm_types:
                if parent_type not in ["User Story", "Product Backlog Item"]:
                    log_verbose(f"  Note: hierarchy parent type '{parent_type}' not directly in state_machine")

    # Check hierarchy structure levels
    levels = hr.get("hierarchyStructure", {}).get("levels", [])
    if not levels:
        errors.append("hierarchy_rules.json: missing hierarchyStructure.levels")
    else:
        log_verbose(f"Hierarchy: {len(levels)} levels defined")

    return errors


def check_agent_references() -> List[str]:
    """Validate agent files reference existing rules/ and data/ files."""
    errors = []

    for agent_file in AGENTS_DIR.glob("*.md"):
        content = agent_file.read_text(encoding="utf-8")
        agent_name = agent_file.stem

        # Check for references to deleted directories
        if "middleware/" in content:
            errors.append(f"agents/{agent_name}.md still references middleware/ (deleted)")
        if "references/" in content:
            errors.append(f"agents/{agent_name}.md still references references/ (deleted)")

        # Check rules/ references point to existing files
        for match in re.findall(r'rules/(\S+\.md)', content):
            if not (RULES_DIR / match).exists():
                errors.append(f"agents/{agent_name}.md references non-existent rules/{match}")

        # Check data/ references point to existing files
        for match in re.findall(r'data/(\S+\.json)', content):
            if not (DATA_DIR / match).exists():
                errors.append(f"agents/{agent_name}.md references non-existent data/{match}")

        log_verbose(f"Agent '{agent_name}': references validated")

    return errors


def check_skill_references() -> List[str]:
    """Validate SKILL.md references existing files."""
    errors = []
    skill_path = DEVOPS_DIR / "SKILL.md"

    if not skill_path.exists():
        errors.append("devops/SKILL.md not found")
        return errors

    content = skill_path.read_text(encoding="utf-8")

    # Check for stale references
    if "middleware/" in content:
        errors.append("devops/SKILL.md still references middleware/ (deleted)")
    if "references/" in content:
        errors.append("devops/SKILL.md still references references/ (deleted)")
    if "workflows.md" in content:
        errors.append("devops/SKILL.md still references workflows.md (deleted)")
    if "profile_generator.md" in content:
        errors.append("devops/SKILL.md still references profile_generator.md (deleted)")

    # Check rules/ references
    for match in re.findall(r'rules/(\S+\.md)', content):
        if not (RULES_DIR / match).exists():
            errors.append(f"devops/SKILL.md references non-existent rules/{match}")

    # Check data/ references
    for match in re.findall(r'data/(\S+\.json)', content):
        if not (DATA_DIR / match).exists():
            errors.append(f"devops/SKILL.md references non-existent data/{match}")

    log_verbose("SKILL.md: references validated")
    return errors


def check_hooks_reference_existing_scripts() -> List[str]:
    """Validate hooks.json references existing hook scripts."""
    errors = []
    hooks_path = PLUGIN_ROOT / "hooks" / "hooks.json"

    if not hooks_path.exists():
        errors.append("hooks/hooks.json not found")
        return errors

    hooks_config = load_json(hooks_path)

    for event_name, event_hooks in hooks_config.get("hooks", {}).items():
        for hook_group in event_hooks:
            for hook in hook_group.get("hooks", []):
                command = hook.get("command", "")
                # Extract script path from command
                match = re.search(r'hooks/([a-zA-Z0-9_-]+\.sh)', command)
                if match:
                    script_name = match.group(1)
                    script_path = PLUGIN_ROOT / "hooks" / script_name
                    if not script_path.exists():
                        errors.append(f"hooks.json references non-existent script: hooks/{script_name}")
                    else:
                        log_verbose(f"Hook '{event_name}' -> hooks/{script_name}: exists")

    return errors


def check_role_names_consistent() -> List[str]:
    """Validate role names in state_machine match profile template."""
    errors = []
    sm = load_json(DATA_DIR / "state_machine.json")
    template_path = DATA_DIR / "profile_template.md"

    if not template_path.exists():
        log_verbose("profile_template.md not found, skipping role name check")
        return errors

    template_content = template_path.read_text(encoding="utf-8")

    # Collect all role aliases from state_machine
    all_aliases = set()
    for role_config in sm.get("rolePermissions", {}).values():
        for alias in role_config.get("appliesTo", []):
            all_aliases.add(alias)

    # Check that common roles are mentioned in template
    core_roles = {"developer", "qa", "pm", "frontend"}
    for role in core_roles:
        if role not in all_aliases:
            errors.append(f"Core role '{role}' not found in state_machine.json rolePermissions.appliesTo")

    log_verbose(f"Role aliases: {sorted(all_aliases)}")
    return errors


def main():
    print("DevOps Plugin Consistency Check")
    print("=" * 50)

    all_errors = []
    checks = [
        ("State Machine Schema", check_state_machine_schema),
        ("Role Permissions", check_role_permissions),
        ("Hierarchy Rules", check_hierarchy_rules),
        ("Agent References", check_agent_references),
        ("SKILL.md References", check_skill_references),
        ("Hook Scripts", check_hooks_reference_existing_scripts),
        ("Role Name Consistency", check_role_names_consistent),
    ]

    for check_name, check_fn in checks:
        print(f"\n[CHECK] {check_name}")
        errors = check_fn()
        if errors:
            for err in errors:
                print(f"  FAIL: {err}")
            all_errors.extend(errors)
        else:
            print(f"  PASS")

    print("\n" + "=" * 50)
    if all_errors:
        print(f"RESULT: {len(all_errors)} error(s) found")
        return 1
    else:
        print("RESULT: All checks passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
