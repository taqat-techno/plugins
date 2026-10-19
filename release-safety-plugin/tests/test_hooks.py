"""Offline tests for the release-safety hooks. Mode/env variables are pinned per test."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))
import release_push_guard as rpg  # noqa: E402
import session_start_release_advisory as ssa  # noqa: E402

PINNED = ("RELEASE_SAFETY_MODE", "RELEASE_SAFETY_HINT", "CLAUDE_PLUGIN_OPTION_GUARD_MODE",
          "CLAUDE_PLUGIN_OPTION_SESSION_HINT", "CLAUDE_PLUGIN_DATA", "CLAUDE_PROJECT_DIR", "HOOKLIB_DEBUG")


def env(**extra):
    e = {k: v for k, v in os.environ.items() if k not in PINNED}
    e.update(extra)
    return e


def run(script, payload=None, raw=None, environ=None):
    data = raw if raw is not None else json.dumps(payload or {}).encode("utf-8")
    return subprocess.run([sys.executable, str(HOOKS / script)], input=data, env=environ or env(),
                          capture_output=True, timeout=30)


# ------------------------------------------------------------------ release_push_guard

@pytest.mark.parametrize("command,expected", rpg.SELF_TEST)
def test_push_guard_table(command, expected):
    assert rpg.detect(command) == expected


def test_push_guard_self_test_flag():
    proc = subprocess.run([sys.executable, str(HOOKS / "release_push_guard.py"), "--self-test"],
                          capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stdout


def test_push_guard_default_is_advisory():
    proc = run("release_push_guard.py", {"tool_input": {"command": "git push origin main --tags"}})
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in out
    assert out["additionalContext"].startswith("[release-safety]")


@pytest.mark.parametrize("key", ["RELEASE_SAFETY_MODE", "CLAUDE_PLUGIN_OPTION_GUARD_MODE"])
def test_push_guard_ask_mode(key):
    proc = run("release_push_guard.py", {"tool_input": {"command": "gh release create v1.0.0"}},
               environ=env(**{key: "ask"}))
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "ask"


def test_push_guard_env_beats_option():
    proc = run("release_push_guard.py", {"tool_input": {"command": "git push --tags"}},
               environ=env(RELEASE_SAFETY_MODE="off", CLAUDE_PLUGIN_OPTION_GUARD_MODE="ask"))
    assert proc.stdout == b""


@pytest.mark.parametrize("raw", [b"", b"nope", b"[]", b"\xff\xfe", b'{"tool_input": "x"}'])
def test_push_guard_fails_open(raw):
    proc = run("release_push_guard.py", raw=raw)
    assert proc.returncode == 0 and proc.stdout == b""


def test_push_guard_silent_on_plain_push():
    proc = run("release_push_guard.py", {"tool_input": {"command": "git push origin main"}})
    assert proc.returncode == 0 and proc.stdout == b""


# ------------------------------------------------------------------ session start

def test_session_silent_without_release_signals(tmp_path):
    proc = run("session_start_release_advisory.py", {"cwd": str(tmp_path)},
               environ=env(CLAUDE_PLUGIN_DATA=str(tmp_path / "data")))
    assert proc.returncode == 0 and proc.stdout == b""


def test_session_speaks_once_per_project(tmp_path):
    project = tmp_path / "proj"
    (project / ".github" / "workflows").mkdir(parents=True)
    (project / ".github" / "workflows" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    data = tmp_path / "data"
    e = env(CLAUDE_PLUGIN_DATA=str(data), CLAUDE_PROJECT_DIR=str(project))
    first = run("session_start_release_advisory.py", {"cwd": str(project)}, environ=e)
    out = json.loads(first.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "GitHub Actions" in out["additionalContext"]
    assert "/release-safety:release-verify" in out["additionalContext"]
    assert "check_release.py" in out["additionalContext"]
    second = run("session_start_release_advisory.py", {"cwd": str(project)}, environ=e)
    assert second.stdout == b""


def test_empty_workflows_dir_is_not_a_signal(tmp_path):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert ssa.release_signals(str(tmp_path)) == []


@pytest.mark.parametrize("key,value", [("RELEASE_SAFETY_HINT", "off"),
                                       ("CLAUDE_PLUGIN_OPTION_SESSION_HINT", "false")])
def test_session_can_be_silenced(tmp_path, key, value):
    (tmp_path / "fly.toml").write_text("app = 'x'\n", encoding="utf-8")
    proc = run("session_start_release_advisory.py", {"cwd": str(tmp_path)},
               environ=env(CLAUDE_PROJECT_DIR=str(tmp_path), **{key: value}))
    assert proc.stdout == b""


def test_session_garbage_stdin_fails_open(tmp_path):
    proc = run("session_start_release_advisory.py", raw=b"\xff\x00not json",
               environ=env(CLAUDE_PROJECT_DIR=str(tmp_path)))
    assert proc.returncode == 0 and proc.stdout == b""
