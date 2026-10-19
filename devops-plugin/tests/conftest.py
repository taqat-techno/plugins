"""
Pytest configuration and shared fixtures: the plugin's JSON data files.
"""

import json
import pytest
from pathlib import Path


# Determine the data directory
DATA_DIR = Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def state_machine_data():
    """Load state_machine.json (merged source of truth)"""
    with open(DATA_DIR / "state_machine.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def hierarchy_rules_data():
    """Load hierarchy_rules.json"""
    with open(DATA_DIR / "hierarchy_rules.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def required_fields_data(state_machine_data):
    """Extract required fields view from state_machine.json for backward compatibility."""
    return state_machine_data


@pytest.fixture(scope="session")
def state_permissions_data(state_machine_data):
    """Extract state permissions view from state_machine.json for backward compatibility."""
    return state_machine_data
