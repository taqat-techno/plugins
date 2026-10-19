"""Offline tests for hooks/risky_git_advisory.py.

Pure-function tests import the module; contract tests run it as a subprocess with a
JSON payload on stdin, exactly as Claude Code does. Every test pins the mode
environment variables so the developer's own settings cannot change the result.
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "risky_git_advisory.py"
sys.path.insert(0, str(ROOT / "hooks"))
import risky_git_advisory as rga  # noqa: E402


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("GIT_SAFETY_MODE", "CLAUDE_PLUGIN_OPTION_GUARD_MODE", "HOOKLIB_DEBUG")}
    env.update(extra)
    return env


def run_hook(payload, env=None, raw=None):
    data = raw if raw is not None else json.dumps(payload).encode("utf-8")
    return subprocess.run([sys.executable, str(HOOK)], input=data, env=env or clean_env(),
                          capture_output=True, timeout=30)


def bash(command, cwd=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd:
        payload["cwd"] = cwd
    return payload


@pytest.fixture
def no_repo(tmp_path):
    return str(tmp_path)


# ----------------------------------------------------------------- detection table

@pytest.mark.parametrize("command,expected", rga.SELF_TEST)
def test_detection_table(command, expected):
    assert rga.detect(command) == expected


def test_self_test_flag_passes():
    proc = subprocess.run([sys.executable, str(HOOK), "--self-test"], capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stdout
    assert b"detection cases passed" in proc.stdout


@pytest.mark.parametrize("command", [
    "git push origin main --force",
    "git push -u origin main -f",
    "git push origin +main",
    "git -C repo reset --hard",
    "git --git-dir=.git --work-tree=. clean -fdx",
    "git branch -D old",
    "git push origin --delete main",
    "git checkout -f",
    "git tag -d v1",
    "git gc --prune=now",
    "git reflog expire --expire=now --all",
    "git filter-branch HEAD",
    "git update-ref -d refs/heads/x",
])
def test_audit_bypasses_are_now_detected(command):
    assert rga.detect(command), command


def test_most_severe_first():
    rules = rga.detect("git add -A && git stash && git reset --hard")
    assert rules[0] == "reset-hard"
    assert set(rules) == {"reset-hard", "stash", "add-all"}


# ----------------------------------------------------------------- modes

def test_mode_resolution():
    assert rga.effective_mode({}, {}) == "advise"
    assert rga.effective_mode({"GIT_SAFETY_MODE": "ask"}, {}) == "ask"
    assert rga.effective_mode({"CLAUDE_PLUGIN_OPTION_GUARD_MODE": "off"}, {}) == "off"
    assert rga.effective_mode({"GIT_SAFETY_MODE": "advise", "CLAUDE_PLUGIN_OPTION_GUARD_MODE": "ask"}, {}) == "advise"
    assert rga.effective_mode({"GIT_SAFETY_MODE": "bogus"}, {}) == "advise"
    # project file raises, never lowers
    assert rga.effective_mode({}, {"mode": "ask"}) == "ask"
    assert rga.effective_mode({"GIT_SAFETY_MODE": "ask"}, {"mode": "off"}) == "ask"
    assert rga.effective_mode({}, {"mode": "off"}) == "advise"


@pytest.mark.parametrize("command", [
    "git reset --hard", "git clean -fd", "git push --force", "git push origin main -f",
    "git branch -D x", "git push origin --delete x", "git checkout -f", "git checkout -- .",
])
def test_ask_mode_asks_for_each_irreversible_shape(command, no_repo):
    proc = run_hook(bash(command, no_repo), clean_env(GIT_SAFETY_MODE="ask"))
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert out["permissionDecision"] == "ask"
    assert "[git-safety]" in out["permissionDecisionReason"]


def test_ask_mode_uses_plugin_option(no_repo):
    proc = run_hook(bash("git reset --hard", no_repo), clean_env(CLAUDE_PLUGIN_OPTION_GUARD_MODE="ask"))
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_ask_mode_only_advises_for_reversible_shapes(no_repo):
    proc = run_hook(bash("git add -A", no_repo), clean_env(GIT_SAFETY_MODE="ask"))
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert "permissionDecision" not in out
    assert "git add -A" in out["additionalContext"]


def test_advise_mode_never_emits_a_decision(no_repo):
    proc = run_hook(bash("git reset --hard && git push --force", no_repo))
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert "permissionDecision" not in out
    assert out["additionalContext"].startswith("[git-safety]")
    assert "force push" in out["additionalContext"].lower()


def test_off_mode_is_silent(no_repo):
    proc = run_hook(bash("git reset --hard", no_repo), clean_env(GIT_SAFETY_MODE="off"))
    assert proc.returncode == 0 and proc.stdout == b""


# ----------------------------------------------------------------- project config

def _repo(tmp, config=None, head="ref: refs/heads/main\n"):
    root = pathlib.Path(tmp)
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text(head, encoding="utf-8")
    if config is not None:
        (root / ".claude").mkdir()
        (root / ".claude" / "git-safety.local.json").write_text(
            config if isinstance(config, str) else json.dumps(config), encoding="utf-8")
    sub = root / "src"
    sub.mkdir()
    return str(sub)


def test_project_file_raises_mode_to_ask():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = _repo(tmp, {"mode": "ask"})
        out = json.loads(run_hook(bash("git reset --hard", cwd)).stdout)["hookSpecificOutput"]
        assert out["permissionDecision"] == "ask"


def test_project_file_cannot_turn_guard_off():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = _repo(tmp, {"mode": "off"})
        proc = run_hook(bash("git reset --hard", cwd))
        assert b"additionalContext" in proc.stdout


def test_protected_branch_push_is_flagged():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = _repo(tmp, {"protected_branches": ["main", "release/*"]})
        for command in ("git push origin main", "git push", "git push origin HEAD:release/2.0"):
            out = json.loads(run_hook(bash(command, cwd)).stdout)["hookSpecificOutput"]
            assert "protected" in out["additionalContext"], command
        assert run_hook(bash("git push origin feature/x", cwd)).stdout == b""


def test_absent_or_broken_config_means_defaults():
    with tempfile.TemporaryDirectory() as tmp:
        cwd = _repo(tmp, "{not json")
        assert run_hook(bash("git push origin main", cwd)).stdout == b""
        out = json.loads(run_hook(bash("git reset --hard", cwd)).stdout)["hookSpecificOutput"]
        assert "permissionDecision" not in out


# ----------------------------------------------------------------- stdin contract

@pytest.mark.parametrize("raw", [b"", b"not json", b"[1,2]", b"\xff\xfe\x00garbage", b'{"tool_input": 5}'])
def test_garbage_input_fails_open(raw):
    proc = run_hook(None, raw=raw)
    assert proc.returncode == 0 and proc.stdout == b""


def test_non_git_command_is_silent(no_repo):
    proc = run_hook(bash("ls -la && echo done", no_repo))
    assert proc.returncode == 0 and proc.stdout == b""


def test_non_ascii_command_is_read_as_utf8(no_repo):
    proc = run_hook(bash("git commit -m 'تحديث' && git reset --hard", no_repo))
    out = json.loads(proc.stdout.decode("utf-8"))["hookSpecificOutput"]
    assert "reset --hard" in out["additionalContext"]


def test_powershell_payload(no_repo):
    payload = {"tool_name": "PowerShell", "tool_input": {"command": "git.exe push origin main --force"},
               "cwd": no_repo}
    out = json.loads(run_hook(payload).stdout)["hookSpecificOutput"]
    assert "force push" in out["additionalContext"].lower()


def test_hook_never_echoes_command_text(no_repo):
    secret_path = "acme-internal-path-xyz"
    proc = run_hook(bash(f"git -C {secret_path} reset --hard", no_repo))
    assert secret_path.encode() not in proc.stdout
