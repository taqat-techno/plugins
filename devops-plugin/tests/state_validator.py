"""
Middleware Validator Module

Implements validation logic for:
1. State transitions (with role-based permission checks)
2. Required fields by work item type and target state
3. Work item hierarchy rules
"""

import json
from typing import Dict, List, Optional, Tuple, Any


class MiddlewareValidator:
    """Validates state transitions, required fields, and hierarchy rules."""

    def __init__(self, required_fields_data: Dict, hierarchy_data: Dict, state_permissions_data: Dict):
        """
        Initialize validator with data files.

        Args:
            required_fields_data: Parsed required_fields.json
            hierarchy_data: Parsed hierarchy_rules.json
            state_permissions_data: Parsed state_permissions.json
        """
        self.required_fields = required_fields_data
        self.hierarchy_rules = hierarchy_data
        self.state_permissions = state_permissions_data

    def validate_state_transition(
        self,
        work_item_type: str,
        from_state: str,
        to_state: str,
        role: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a state transition with optional role-based permission check.

        Args:
            work_item_type: Type of work item (e.g., "Task", "Bug", "PBI")
            from_state: Current state
            to_state: Target state
            role: User role for permission check (optional)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        # Step 0: Role-based permission check (if role provided)
        if role:
            blocked_msg = self._check_role_permission(work_item_type, from_state, to_state, role)
            if blocked_msg:
                return False, blocked_msg

        # Check if work item type exists
        if work_item_type not in self.required_fields.get("workItemTypes", {}):
            return False, f"Unknown work item type: {work_item_type}"

        wit_config = self.required_fields["workItemTypes"][work_item_type]

        # Check if to_state is valid for this work item type
        valid_states = wit_config.get("validStates", [])
        if to_state not in valid_states:
            return False, f"{to_state} is not a valid state for {work_item_type}. Valid states: {valid_states}"

        # Check if transition is defined
        transitions = wit_config.get("transitions", {})
        if to_state not in transitions:
            return False, f"No transition defined to {to_state} for {work_item_type}"

        transition_config = transitions[to_state]
        allowed_from_states = transition_config.get("from", [])

        # Check if from_state is in allowed "from" states
        if from_state not in allowed_from_states:
            return False, f"Cannot transition {work_item_type} from {from_state} to {to_state}. " \
                         f"Allowed source states: {allowed_from_states}"

        # Check for intermediate state requirement (e.g., PBI must go through "Ready For QC")
        if "requires_intermediate" in transition_config:
            intermediate = transition_config["requires_intermediate"]
            message = transition_config.get("message", "")
            suggestion = transition_config.get("suggestion", "")
            # Transition is blocked, needs intermediate state first
            return False, f"{message} {suggestion}".strip()

        return True, None

    def validate_required_fields(
        self,
        work_item_type: str,
        to_state: str,
        fields: Dict[str, Any]
    ) -> Tuple[bool, Optional[List[str]], Optional[Dict[str, Any]]]:
        """
        Validate that all required fields are present for a state transition.

        Args:
            work_item_type: Type of work item
            to_state: Target state
            fields: Current field values dict

        Returns:
            Tuple of (is_valid, missing_fields_list or None, auto_set_dict or None)
        """
        if work_item_type not in self.required_fields.get("workItemTypes", {}):
            return True, None, None

        wit_config = self.required_fields["workItemTypes"][work_item_type]
        transitions = wit_config.get("transitions", {})

        if to_state not in transitions:
            return True, None, None

        transition_config = transitions[to_state]
        required = transition_config.get("required", [])
        auto_set = transition_config.get("auto_set", {})

        # Check for missing required fields
        missing = []
        for field_path in required:
            # Extract short field name for lookup
            field_value = fields.get(field_path)
            if field_value is None or field_value == "" or field_value == 0:
                missing.append(field_path)

        if missing:
            return False, missing, auto_set

        return True, None, auto_set

    def validate_hierarchy(
        self,
        child_type: str,
        parent_type: Optional[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that parent-child relationship is allowed.

        Args:
            child_type: Type of child work item
            parent_type: Type of parent work item (None if no parent)

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        hierarchy_rules = self.hierarchy_rules.get("parentChildRules", {})

        if child_type not in hierarchy_rules:
            # No specific rules for this type, allow it
            return True, None

        rules = hierarchy_rules[child_type]
        requirement_level = rules.get("requirementLevel", "NONE")
        valid_parents = rules.get("validParents", [])

        # Check if parent is required (MUST means required, SHOULD means recommended)
        if requirement_level == "MUST" and parent_type is None:
            message = rules.get("noParentMessage", f"{child_type} requires a parent")
            return False, message
        elif requirement_level in ("SHOULD", "OPTIONAL") and parent_type is None:
            # SHOULD/OPTIONAL allows missing parent
            return True, None

        # If parent is provided, validate it's the correct type
        if parent_type is not None and valid_parents and parent_type not in valid_parents:
            error_msg = rules.get("wrongParentMessage",
                                 f"{child_type} cannot be a child of {parent_type}")
            if error_msg:
                error_msg = error_msg.format(parentType=parent_type)
            return False, error_msg

        return True, None

    def get_required_fields_for_transition(
        self,
        work_item_type: str,
        to_state: str
    ) -> Dict[str, Any]:
        """
        Get metadata about required fields for a transition (for prompts, validation, etc.)

        Args:
            work_item_type: Type of work item
            to_state: Target state

        Returns:
            Dict with 'required', 'auto_set', 'prompts', 'defaults', 'options', 'validation'
        """
        if work_item_type not in self.required_fields.get("workItemTypes", {}):
            return {}

        wit_config = self.required_fields["workItemTypes"][work_item_type]
        transitions = wit_config.get("transitions", {})

        if to_state not in transitions:
            return {}

        return transitions[to_state]

    def get_valid_states(self, work_item_type: str) -> List[str]:
        """Get all valid states for a work item type."""
        if work_item_type not in self.required_fields.get("workItemTypes", {}):
            return []
        return self.required_fields["workItemTypes"][work_item_type].get("validStates", [])

    def _check_role_permission(
        self,
        work_item_type: str,
        from_state: str,
        to_state: str,
        role: str
    ) -> Optional[str]:
        """
        Check if a role is allowed to perform a state transition.

        Returns:
            Error message if blocked, None if allowed/unknown
        """
        role_permissions = self.state_permissions.get("rolePermissions", {})

        # Normalize role lookup (handle various role names)
        found_role = None
        for role_key, role_config in role_permissions.items():
            applies_to = role_config.get("appliesTo", [])
            if role.lower() in applies_to:
                found_role = role_key
                break

        if not found_role:
            # No profile found - allow with warning in caller
            return None

        role_config = role_permissions[found_role]
        permissions = role_config.get("permissions", {})

        if work_item_type not in permissions:
            # No restrictions for this work item type
            return None

        wit_perms = permissions[work_item_type]
        transition_str = f"{from_state} → {to_state}"

        blocked = wit_perms.get("blocked", [])
        if transition_str in blocked:
            blocked_msg = wit_perms.get("blockedMessage", "This transition is not allowed for your role")
            return blocked_msg

        # Transition is allowed or not mentioned
        return None
