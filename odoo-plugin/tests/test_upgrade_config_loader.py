"""hooks/upgrade/config_loader.py must find the project override via
CLAUDE_PROJECT_DIR - the variable Claude Code actually exports. It used to read
CLAUDE_PROJECT_ROOT, so a project's odoo-upgrade.config.json was never loaded
and the core-path guard could not be configured."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
UPGRADE = PLUGIN_ROOT / "hooks" / "upgrade"
sys.path.insert(0, str(UPGRADE))

import config_loader  # noqa: E402

CUSTOM = {"core_path_patterns": [r"forbidden_zone/"], "default_target_version": 17}


def _clean(monkeypatch):
    for var in ("CLAUDE_PROJECT_DIR", "CLAUDE_PROJECT_ROOT", "CLAUDE_PLUGIN_ROOT"):
        monkeypatch.delenv(var, raising=False)


def _write(tmp_path):
    (tmp_path / "odoo-upgrade.config.json").write_text(json.dumps(CUSTOM), encoding="utf-8")


def test_project_dir_override_is_loaded(tmp_path, monkeypatch):
    _clean(monkeypatch)
    _write(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    cfg = config_loader.load_config()
    assert cfg["core_path_patterns"] == CUSTOM["core_path_patterns"]
    assert cfg["default_target_version"] == 17


def test_legacy_project_root_still_works_as_fallback(tmp_path, monkeypatch):
    _clean(monkeypatch)
    _write(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_ROOT", str(tmp_path))
    assert config_loader.load_config()["default_target_version"] == 17


def test_project_dir_wins_over_legacy_name(tmp_path, monkeypatch):
    _clean(monkeypatch)
    _write(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_ROOT", str(other))
    assert config_loader.load_config()["default_target_version"] == 17


def test_defaults_without_any_override(monkeypatch):
    _clean(monkeypatch)
    assert config_loader.load_config() == config_loader.DEFAULT_CONFIG


def test_core_guard_honours_project_override_end_to_end(tmp_path):
    """The acceptance case: a project config changes what guard_core_odoo blocks."""
    _write(tmp_path)
    env = dict(os.environ)
    for var in ("CLAUDE_PROJECT_ROOT", "CLAUDE_PLUGIN_ROOT"):
        env.pop(var, None)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    payload = json.dumps({"tool_input": {"file_path": "/x/forbidden_zone/a.py"}}).encode()
    proc = subprocess.run(
        [sys.executable, str(UPGRADE / "guard_core_odoo.py")],
        input=payload, capture_output=True, env=env, timeout=30,
    )
    assert proc.returncode == 2, proc.stderr.decode("utf-8", "replace")
