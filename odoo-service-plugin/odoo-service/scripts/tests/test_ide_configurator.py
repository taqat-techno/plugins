"""Tests for scripts/ide_configurator.py — IDE configuration generation."""

import json

import pytest


@pytest.fixture(autouse=True)
def _setup_path(scripts_dir):
    """Ensure the scripts directory is on sys.path for every test."""


def test_vscode_launch_json_valid(tmp_path):
    """generate_vscode_launch creates valid JSON with 'configurations' key."""
    from ide_configurator import generate_vscode_launch

    result = generate_vscode_launch(config_file="test.conf", output_dir=str(tmp_path))
    content = json.loads(result.read_text(encoding="utf-8"))
    assert "configurations" in content
    assert isinstance(content["configurations"], list)
    assert len(content["configurations"]) > 0


def test_vscode_tasks_json_valid(tmp_path):
    """generate_vscode_tasks creates valid JSON with 'tasks' key."""
    from ide_configurator import generate_vscode_tasks

    result = generate_vscode_tasks("myproject", output_dir=str(tmp_path))
    content = json.loads(result.read_text(encoding="utf-8"))
    assert "tasks" in content
    assert isinstance(content["tasks"], list)
    assert len(content["tasks"]) > 0


def test_vscode_settings_json_valid(tmp_path):
    """generate_vscode_settings creates valid JSON with python settings."""
    from ide_configurator import generate_vscode_settings

    result = generate_vscode_settings(output_dir=str(tmp_path))
    content = json.loads(result.read_text(encoding="utf-8"))
    assert "python.defaultInterpreterPath" in content
    assert "python.analysis.extraPaths" in content


def test_vscode_extensions_json_valid(tmp_path):
    """generate_vscode_extensions creates valid JSON with recommendations."""
    from ide_configurator import generate_vscode_extensions

    result = generate_vscode_extensions(output_dir=str(tmp_path))
    content = json.loads(result.read_text(encoding="utf-8"))
    assert "recommendations" in content
    assert isinstance(content["recommendations"], list)
    assert "ms-python.python" in content["recommendations"]


def test_pycharm_run_config_valid_xml(tmp_path):
    """generate_pycharm_local_config creates XML with project name."""
    from ide_configurator import generate_pycharm_local_config

    result = generate_pycharm_local_config(
        project_name="myproject",
        config_file="myproject.conf",
        output_dir=str(tmp_path),
    )
    content = result.read_text(encoding="utf-8")
    assert "<component" in content
    assert "myproject" in content
    assert "configuration" in content


def test_pycharm_docker_config_valid_xml(tmp_path):
    """generate_pycharm_docker_config creates XML with project name."""
    from ide_configurator import generate_pycharm_docker_config

    result = generate_pycharm_docker_config(
        project_name="dockerproj",
        output_dir=str(tmp_path),
    )
    content = result.read_text(encoding="utf-8")
    assert "dockerproj" in content
    assert "docker-compose" in content.lower()


def test_gitignore_created(tmp_path):
    """generate_gitignore creates file with expected patterns."""
    from ide_configurator import generate_gitignore

    result = generate_gitignore(output_dir=str(tmp_path))
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "__pycache__" in content
    assert ".venv/" in content
    assert ".idea/" in content


def test_gitignore_not_overwritten(tmp_path):
    """generate_gitignore does not overwrite existing .gitignore."""
    from ide_configurator import generate_gitignore

    existing = tmp_path / ".gitignore"
    existing.write_text("# my custom gitignore\n", encoding="utf-8")

    generate_gitignore(output_dir=str(tmp_path))

    content = existing.read_text(encoding="utf-8")
    assert content == "# my custom gitignore\n"


def test_generate_all_vscode_creates_four_files(tmp_path):
    """generate_all_vscode creates all 4 VSCode config files."""
    from ide_configurator import generate_all_vscode

    generate_all_vscode(
        project_name="fulltest",
        config_file="fulltest.conf",
        output_dir=str(tmp_path),
    )
    vscode_dir = tmp_path / ".vscode"
    assert (vscode_dir / "launch.json").exists()
    assert (vscode_dir / "tasks.json").exists()
    assert (vscode_dir / "settings.json").exists()
    assert (vscode_dir / "extensions.json").exists()


def test_env_example_created(tmp_path):
    """generate_env_example creates .env.example with project name."""
    from ide_configurator import generate_env_example

    result = generate_env_example("myproject", output_dir=str(tmp_path))
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "myproject" in content
    assert "POSTGRES_USER" in content
