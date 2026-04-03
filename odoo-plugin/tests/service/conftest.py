"""Shared fixtures for odoo-service-plugin script tests."""

import sys
from pathlib import Path

import pytest


@pytest.fixture
def scripts_dir():
    """Return the Path to the scripts directory and ensure it is importable."""
    d = Path(__file__).resolve().parent.parent
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    return d


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temp directory with a mock Odoo project structure."""
    # Virtual environment stubs
    scripts_dir = tmp_path / ".venv" / "Scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "python.exe").write_text("")

    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").write_text("")

    # Config directory
    (tmp_path / "conf").mkdir()

    # Docker compose file
    (tmp_path / "docker-compose.yml").write_text("")

    return tmp_path
