"""Offline tests for hooks/session_start_env_advisory.py (CED-P1-01, CED-P2-06).

The hook must stay silent in a healthy project and speak only when a check finds
something. HOME is redirected so the developer's own ~/.claude/settings.json cannot
change results.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "session_start_env_advisory.py"
sys.path.insert(0, str(ROOT / "hooks"))
import session_start_env_advisory as hook  # noqa: E402

PINNED = ("ENV_DOCTOR_HINT", "CLAUDE_PLUGIN_OPTION_SESSION_CHECKS", "CLAUDE_PROJECT_DIR", "HOOKLIB_DEBUG",
          "ACME_TOKEN", "ACME_URL")


def env(tmp_path, **extra):
    e = {k: v for k, v in os.environ.items() if k not in PINNED}
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    e.update(HOME=str(home), USERPROFILE=str(home))
    e.update(extra)
    return e


def run(project, environ, raw=None):
    data = raw if raw is not None else json.dumps({"cwd": str(project)}).encode()
    return subprocess.run([sys.executable, str(HOOK)], input=data, env=environ, capture_output=True, timeout=30)


def write_mcp(project, servers):
    (project / ".mcp.json").write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


def test_healthy_project_is_silent(project, tmp_path):
    write_mcp(project, {"docs": {"command": "node", "args": ["server.js"], "env": {"TOKEN": "${ACME_TOKEN:-}"}}})
    proc = run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project)))
    assert proc.returncode == 0 and proc.stdout == b""


def test_empty_project_is_silent(project, tmp_path):
    assert run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project))).stdout == b""


def test_unset_variable_without_default_is_reported_by_name_only(project, tmp_path):
    write_mcp(project, {"acme": {"command": "acme-mcp", "env": {"TOKEN": "${ACME_TOKEN}"}, "args": ["${ACME_URL}"]}})
    proc = run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project)))
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    text = out["additionalContext"]
    assert "'acme'" in text and "${ACME_TOKEN}" in text and "${ACME_URL}" in text
    assert "/env-doctor:diagnose" in text


def test_set_variable_is_fine_and_value_never_printed(project, tmp_path):
    write_mcp(project, {"acme": {"command": "acme-mcp", "env": {"TOKEN": "${ACME_TOKEN}"}}})
    proc = run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project), ACME_TOKEN="example-value-123"))
    assert proc.stdout == b""


def test_variable_from_settings_env_counts_as_set(project, tmp_path):
    write_mcp(project, {"acme": {"command": "acme-mcp", "env": {"TOKEN": "${ACME_TOKEN}"}}})
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text(json.dumps({"env": {"ACME_TOKEN": "x"}}), encoding="utf-8")
    assert run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project))).stdout == b""


def test_invalid_mcp_json_is_reported(project, tmp_path):
    (project / ".mcp.json").write_text("{ not json", encoding="utf-8")
    out = json.loads(run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project))).stdout)
    assert "not valid JSON" in out["hookSpecificOutput"]["additionalContext"]


def test_syncthing_heavy_dir_not_ignored(tmp_path):
    synced = tmp_path / "synced"
    (synced / ".stfolder").mkdir(parents=True)
    project = synced / "app"
    (project / "node_modules").mkdir(parents=True)
    out = json.loads(run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project))).stdout)
    assert "node_modules" in out["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize("line", ["(?d)node_modules", "node_modules", "**/node_modules", "app/node_modules",
                                  "#include .stglobalignore"])
def test_syncthing_ignored_dir_is_silent(tmp_path, line):
    synced = tmp_path / "synced"
    (synced / ".stfolder").mkdir(parents=True)
    (synced / ".stignore").write_text(line + "\n", encoding="utf-8")
    project = synced / "app"
    (project / "node_modules").mkdir(parents=True)
    assert run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project))).stdout == b""


@pytest.mark.parametrize("key,value", [("ENV_DOCTOR_HINT", "off"), ("CLAUDE_PLUGIN_OPTION_SESSION_CHECKS", "false")])
def test_can_be_silenced(project, tmp_path, key, value):
    (project / ".mcp.json").write_text("{ not json", encoding="utf-8")
    assert run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project), **{key: value})).stdout == b""


@pytest.mark.parametrize("raw", [b"", b"garbage", b"\xff\xfe", b"[]"])
def test_garbage_stdin_fails_open(project, tmp_path, raw):
    proc = run(project, env(tmp_path, CLAUDE_PROJECT_DIR=str(project)), raw=raw)
    assert proc.returncode == 0 and proc.stdout == b""


def test_findings_function_never_raises(tmp_path):
    assert hook.findings(str(tmp_path / "does-not-exist"), {}) == []
