"""Tests for scripts/shared.py — environment detection and venv helpers."""

import sys
from pathlib import Path


def test_detect_environment_docker_compose(scripts_dir, tmp_path):
    """detect_environment returns 'docker' when docker-compose.yml exists."""
    from shared import detect_environment

    (tmp_path / "docker-compose.yml").write_text("")
    assert detect_environment(str(tmp_path)) == "docker"


def test_detect_environment_dockerfile(scripts_dir, tmp_path):
    """detect_environment returns 'docker' when Dockerfile exists."""
    from shared import detect_environment

    (tmp_path / "Dockerfile").write_text("")
    assert detect_environment(str(tmp_path)) == "docker"


def test_detect_environment_venv_windows(scripts_dir, tmp_path):
    """detect_environment returns 'venv' when .venv/Scripts/python.exe exists."""
    from shared import detect_environment

    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("")
    assert detect_environment(str(tmp_path)) == "venv"


def test_detect_environment_bare(scripts_dir, tmp_path):
    """detect_environment returns 'bare' when nothing exists."""
    from shared import detect_environment

    assert detect_environment(str(tmp_path)) == "bare"


def test_find_python_in_venv_windows(scripts_dir, tmp_path):
    """find_python_in_venv returns path when .venv/Scripts/python.exe exists."""
    from shared import find_python_in_venv

    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("")
    result = find_python_in_venv(str(tmp_path))
    assert result is not None
    assert result.endswith("python.exe")


def test_find_python_in_venv_linux(scripts_dir, tmp_path):
    """find_python_in_venv returns path when .venv/bin/python exists."""
    from shared import find_python_in_venv

    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").write_text("")
    result = find_python_in_venv(str(tmp_path))
    assert result is not None
    assert "python" in result


def test_find_python_in_venv_none(scripts_dir, tmp_path):
    """find_python_in_venv returns None when no venv directory exists."""
    from shared import find_python_in_venv

    assert find_python_in_venv(str(tmp_path)) is None
