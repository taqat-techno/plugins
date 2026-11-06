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

PINNED = ("ENV_DOCTOR_HOST_CHECKS", "ENV_DOCTOR_HINT", "CLAUDE_PLUGIN_OPTION_SESSION_CHECKS", "CLAUDE_PROJECT_DIR", "HOOKLIB_DEBUG",
          "ACME_TOKEN", "ACME_URL")


def env(tmp_path, **extra):
    e = {k: v for k, v in os.environ.items() if k not in PINNED}
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    e.update(HOME=str(home), USERPROFILE=str(home))
    # Host checks read the real machine (drive, WSL); project tests pin them off and the
    # check_host tests below drive them through a fake.
    e["ENV_DOCTOR_HOST_CHECKS"] = "off"
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
    assert hook.findings(str(tmp_path / "does-not-exist"), {"ENV_DOCTOR_HOST_CHECKS": "off"}) == []


# ----------------------------------------------------------------- host-pressure checks

class FakeHP:
    """Stand-in for hooks/host_pressure.py so the checks are tested without the machine."""
    GIB = 1024 ** 3

    def __init__(self, windows=True, free=500, total=1000, version=(3, 0, 3), distros=(("Ubuntu", "x.vhdx"),),
                 running=("Ubuntu",), size=100, used=90):
        self._w, self._free, self._total, self._v = windows, free, total, version
        self._d, self._r, self._size, self._used = list(distros), running, size, used
        self.df_calls = 0

    def is_windows(self):
        return self._w

    def drive_usage(self):
        return self._free * self.GIB, self._total * self.GIB

    def wsl_version(self):
        return self._v

    def known_bad_wsl(self, v):
        import host_pressure
        return host_pressure.known_bad_wsl(v)

    def wsl_distros(self):
        return self._d

    def running_distros(self):
        return list(self._r) if self._r is not None else None

    def file_size(self, _):
        return self._size * self.GIB

    def wsl_used_bytes(self, name, running=None):
        self.df_calls += 1
        return self._used * self.GIB

    def vhdx_bloat(self, size, used):
        import host_pressure
        return host_pressure.vhdx_bloat(size, used)


def test_host_checks_silent_when_healthy():
    assert hook.check_host({}, FakeHP()) == []


def test_host_checks_off_switch_and_non_windows():
    assert hook.check_host({"ENV_DOCTOR_HOST_CHECKS": "off"}, FakeHP(free=1)) == []
    assert hook.check_host({}, FakeHP(windows=False, free=1)) == []


def test_low_system_drive_reported():
    out = hook.check_host({}, FakeHP(free=50, total=1000))
    assert len(out) == 1 and "5%" in out[0] and "0x8007000e" in out[0]


def test_known_bad_wsl_version_reported():
    out = hook.check_host({}, FakeHP(version=(2, 6, 3)))
    assert len(out) == 1 and "2.6.3" in out[0] and "wsl --update" in out[0]


def test_vhdx_bloat_reported_only_for_running_distro():
    out = hook.check_host({}, FakeHP(size=92, used=51))
    assert len(out) == 1 and "'Ubuntu'" in out[0] and "92 GiB" in out[0]


def test_vhdx_check_never_runs_df_when_wsl_is_stopped():
    hp = FakeHP(size=92, used=10, running=())
    assert hook.check_host({}, hp) == [] and hp.df_calls == 0
    hp = FakeHP(size=92, used=10, running=None)
    assert hook.check_host({}, hp) == [] and hp.df_calls == 0


def test_small_slack_is_not_bloat():
    import host_pressure
    gib = host_pressure.GIB
    assert not host_pressure.vhdx_bloat(14 * gib, 5 * gib)       # 2.8x but only 9 GiB slack
    assert host_pressure.vhdx_bloat(92 * gib, 51 * gib)
    assert not host_pressure.vhdx_bloat(136 * gib, 126 * gib)
    assert not host_pressure.vhdx_bloat(None, 5)
