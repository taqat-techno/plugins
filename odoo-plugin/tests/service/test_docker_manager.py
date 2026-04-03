"""Tests for scripts/docker_manager.py — Docker file generation and commands."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _setup_path(scripts_dir):
    """Ensure the scripts directory is on sys.path for every test."""


def test_dockerfiles_has_all_versions():
    """DOCKERFILES dict contains keys for Odoo 14 through 19."""
    from docker_manager import DOCKERFILES

    for version in [14, 15, 16, 17, 18, 19]:
        assert version in DOCKERFILES


def test_dockerfiles_17_uses_python310():
    """DOCKERFILES[17] contains python:3.10."""
    from docker_manager import DOCKERFILES

    assert "python:3.10" in DOCKERFILES[17]


def test_dockerfiles_19_uses_python312():
    """DOCKERFILES[19] contains python:3.12."""
    from docker_manager import DOCKERFILES

    assert "python:3.12" in DOCKERFILES[19]


def test_compose_cmd_default():
    """_compose_cmd with no args returns ['docker-compose']."""
    from docker_manager import _compose_cmd

    cmd = _compose_cmd()
    assert cmd == ["docker-compose"]


def test_compose_cmd_with_file():
    """_compose_cmd with a compose file includes -f flag."""
    from docker_manager import _compose_cmd

    cmd = _compose_cmd(compose_file="custom-compose.yml")
    assert cmd == ["docker-compose", "-f", "custom-compose.yml"]


def test_generate_dockerfile(tmp_path):
    """generate_dockerfile creates a Dockerfile with correct content."""
    from docker_manager import generate_dockerfile

    result = generate_dockerfile(17, str(tmp_path))
    assert result.exists()
    assert result.name == "Dockerfile"
    content = result.read_text(encoding="utf-8")
    assert "python:3.10" in content
    assert "EXPOSE 8069 8072" in content


def test_generate_dockerfile_invalid_version(tmp_path):
    """generate_dockerfile raises ValueError for unsupported version."""
    from docker_manager import generate_dockerfile

    with pytest.raises(ValueError, match="Unsupported Odoo version"):
        generate_dockerfile(99, str(tmp_path))


def test_generate_compose(tmp_path):
    """generate_compose creates docker-compose.yml with project name."""
    from docker_manager import generate_compose

    result = generate_compose("myproject", 17, 8069, str(tmp_path))
    assert result.exists()
    assert result.name == "docker-compose.yml"
    content = result.read_text(encoding="utf-8")
    assert "myproject" in content
    assert "8069" in content


def test_init_docker_project(tmp_path):
    """init_docker_project creates all expected files and directories."""
    from docker_manager import init_docker_project

    out = tmp_path / "project"
    init_docker_project("testproject", 17, 8069, str(out))

    assert (out / "Dockerfile").exists()
    assert (out / "docker-compose.yml").exists()
    assert (out / ".env.example").exists()
    assert (out / "conf").is_dir()
    assert (out / "logs").is_dir()
    assert (out / "backups").is_dir()
    assert (out / "projects" / "testproject").is_dir()


def test_build_calls_run():
    """build calls _run with docker-compose build."""
    from docker_manager import build

    with patch("docker_manager._run", return_value=0) as mock_run:
        rc = build()
        call_args = mock_run.call_args[0][0]
        assert "docker-compose" in call_args
        assert "build" in call_args
        assert rc == 0


def test_up_calls_run_detached():
    """up with detach=True includes -d flag."""
    from docker_manager import up

    with patch("docker_manager._run", return_value=0) as mock_run:
        rc = up(detach=True)
        call_args = mock_run.call_args[0][0]
        assert "-d" in call_args
        assert rc == 0


def test_down_calls_run():
    """down calls _run with docker-compose down."""
    from docker_manager import down

    with patch("docker_manager._run", return_value=0) as mock_run:
        rc = down()
        call_args = mock_run.call_args[0][0]
        assert "down" in call_args
        assert rc == 0


def test_down_with_volumes():
    """down with volumes=True includes -v flag."""
    from docker_manager import down

    with patch("docker_manager._run", return_value=0) as mock_run:
        down(volumes=True)
        call_args = mock_run.call_args[0][0]
        assert "-v" in call_args
