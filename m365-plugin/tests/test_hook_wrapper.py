"""The shell wrapper in hooks.json must FAIL CLOSED: if the check script or Python cannot run, the human is asked."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent


def _bash():
    if os.name == "nt":  # the WSL launcher in System32 cannot see Windows paths; use Git for Windows' bash
        for root in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), os.environ.get("LOCALAPPDATA", "") + "/Programs"):
            cand = Path(root) / "Git" / "bin" / "bash.exe"
            if root and cand.is_file():
                return str(cand)
        return None
    return shutil.which("bash")


BASH = _bash()
pytestmark = pytest.mark.skipif(BASH is None, reason="no POSIX shell available")


def _command():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


def _run(root, path_dirs, stdin=b"{}"):
    env = {k: v for k, v in os.environ.items() if k != "PATH"}
    env["CLAUDE_PLUGIN_ROOT"] = Path(root).as_posix()
    env["PATH"] = os.pathsep.join(path_dirs)
    r = subprocess.run([BASH, "-c", _command()], input=stdin, capture_output=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.decode("utf-8"))["hookSpecificOutput"]


def _fake(bindir, name, code):
    p = Path(bindir) / name
    p.write_bytes(f"#!/bin/sh\nexit {code}\n".encode("utf-8"))
    p.chmod(0o755)


def test_script_missing_asks_the_human(tmp_path):
    out = _run(tmp_path, [str(tmp_path)])
    assert out["permissionDecision"] == "ask" and "could not run" in out["permissionDecisionReason"]


def test_no_python_anywhere_asks_the_human(tmp_path):
    (tmp_path / "hooks").mkdir()
    shutil.copy(PLUGIN / "hooks" / "pre_write_confirm.py", tmp_path / "hooks")
    empty = tmp_path / "empty"; empty.mkdir()
    assert _run(tmp_path, [str(empty)])["permissionDecision"] == "ask"


@pytest.mark.parametrize("code", [1, 2, 49])
def test_a_failing_or_stub_interpreter_asks_the_human(tmp_path, code):
    (tmp_path / "hooks").mkdir()
    shutil.copy(PLUGIN / "hooks" / "pre_write_confirm.py", tmp_path / "hooks")
    bindir = tmp_path / "bin"; bindir.mkdir()
    for n in ("python3", "python", "py"):
        _fake(bindir, n, code)
    assert _run(tmp_path, [str(bindir)])["permissionDecision"] == "ask"


def test_normal_run_prints_exactly_one_decision_from_the_script():
    real = Path(shutil.which("python3") or shutil.which("python") or "")
    if not real.name:
        pytest.skip("no python on PATH")
    payload = json.dumps({"tool_name": "mcp__plugin_m365_m365__email_send_draft", "tool_input": {"draft_id": "D-77"}}).encode("utf-8")
    out = _run(PLUGIN, [str(real.parent), os.path.dirname(BASH)], stdin=payload)
    assert out["permissionDecision"] == "ask" and "D-77" in out["permissionDecisionReason"]
    assert "could not run" not in out["permissionDecisionReason"]
