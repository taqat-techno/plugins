"""Offline tests for hooks/long_job_advisory.py (PreToolUse, advisory only).

The hook must speak on the long-job shapes when the call would block in the foreground,
stay quiet on short/targeted runs, background runs and explicit short timeouts, and never
exit non-zero.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "long_job_advisory.py"
sys.path.insert(0, str(ROOT / "hooks"))
import long_job_advisory as hook  # noqa: E402

LONG = [
    "./odoo-bin -c conf/x.conf -d db --test-enable --stop-after-init",
    "python odoo-bin -c x.conf -d db --test-tags /my_module --stop-after-init",
    "odoo-bin -d db --test-tags /my_module:TestThing --stop-after-init",
    "odoo-bin -d db -i my_module --stop-after-init",
    "odoo-bin -d db -u all --stop-after-init",
    "odoo-bin -d db -u my_mod --test-enable --test-tags /my_mod:T.test_a --stop-after-init",
    "pytest",
    "python -m pytest tests/",
    "cd backend && python manage.py test",
    "python manage.py test --parallel 4",
    "npm run test:e2e",
    "pnpm test:e2e",
    "npx playwright test",
    "pg_dump -Fc -p 5434 bigdb > /tmp/big.dump",
    "pg_restore -C -d postgres big.dump",
    # wrappers that hide the job inside one quoted string
    'wsl.exe -d Ubuntu -- bash -lc "cd ~/p && ./odoo-bin -c x.conf --test-enable --stop-after-init"',
    "wsl -d Ubuntu -- bash -lc 'source venv/bin/activate; python -m pytest'",
]

SHORT = [
    "odoo-bin -d db --test-tags /my_module:TestThing.test_one --stop-after-init",
    "odoo-bin -d db --test-tags /my_module.test_one --stop-after-init",
    "odoo-bin -c x.conf",  # a server start, not a test run
    "pytest tests/test_api.py",
    "pytest tests/test_api.py::test_login -x",
    "python -m pytest -k login",
    "pytest --lf",
    "python manage.py test users.tests.TestLogin",
    "python manage.py migrate",
    "npx playwright test tests/login.spec.ts",
    "npm run test",
    "git status",
    "ls -la && cat README.md",
    "echo pytest is great",
    "grep -rn 'pg_dump' docs/",
]


@pytest.mark.parametrize("command", LONG)
def test_long_shapes_are_recognised(command):
    assert hook.long_job_reason(command), command


@pytest.mark.parametrize("command", SHORT)
def test_short_shapes_are_not(command):
    assert hook.long_job_reason(command) is None, command


def test_echo_and_grep_mentions_are_not_jobs():
    # "pytest" as an argument to echo is a known, accepted false positive only if it is the
    # command itself; here it is the second token of echo, which shlex keeps as a word.
    assert hook.long_job_reason("echo pytest is great") is None


@pytest.mark.parametrize("timeout", [None, 600000, 1800000])
def test_advises_when_foreground_and_long_or_default_timeout(timeout):
    ti = {"command": "python -m pytest", "timeout": timeout} if timeout else {"command": "python -m pytest"}
    text = hook.advice(ti)
    assert text and "run_in_background" in text and "long-running-jobs" in text


def test_quiet_when_backgrounded():
    assert hook.advice({"command": "python -m pytest", "run_in_background": True, "timeout": 1800000}) is None


def test_quiet_with_explicit_short_timeout():
    assert hook.advice({"command": "python -m pytest", "timeout": 180000}) is None
    assert hook.advice({"command": "python -m pytest", "timeout": 90000}) is None


def test_wait_loop_and_self_match_advised_even_with_short_timeout():
    text = hook.advice({"command": "while kill -0 $P; do sleep 30; done", "timeout": 60000})
    assert text and "wait loop" in text
    text = hook.advice({"command": "pgrep -f odoo-bin || echo dead", "timeout": 60000})
    assert text and "own command line" in text
    text = hook.advice({"command": "while ($true) { if (Test-Path done.txt) { break }; Start-Sleep 20 }"})
    assert text and "wait loop" in text


def test_plain_commands_are_quiet():
    for c in ("git status", "ls", "python -m pytest tests/test_x.py", "pg_lsclusters", "pkill -x odoo"):
        assert hook.advice({"command": c}) is None, c


def _run(payload, **env_extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("ENV_DOCTOR_LONG_JOBS", "CLAUDE_PLUGIN_OPTION_LONG_JOB_ADVICE")}
    env.update(env_extra)
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    return subprocess.run([sys.executable, str(HOOK)], input=raw, env=env, capture_output=True, timeout=30)


def test_end_to_end_emits_pretooluse_context_and_exits_0():
    proc = _run({"tool_name": "Bash", "tool_input": {"command": "npm run test:e2e", "timeout": 1200000}})
    assert proc.returncode == 0
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in out  # advisory only, never a decision
    assert "test:e2e" in out["additionalContext"]


def test_end_to_end_non_ascii_command_is_decoded_as_utf8():
    payload = {"tool_name": "Bash", "tool_input": {"command": "pytest  # عربي"}}
    proc = _run(payload)
    assert proc.returncode == 0 and b"long-running-jobs" in proc.stdout


def test_end_to_end_quiet_paths():
    assert _run({"tool_name": "Bash", "tool_input": {"command": "git status"}}).stdout == b""
    assert _run({"tool_name": "Read", "tool_input": {"command": "pytest"}}).stdout == b""
    assert _run({"tool_name": "Bash", "tool_input": {"command": "pytest"}}, ENV_DOCTOR_LONG_JOBS="off").stdout == b""
    assert _run({"tool_name": "Bash", "tool_input": {"command": "pytest"}},
                CLAUDE_PLUGIN_OPTION_LONG_JOB_ADVICE="false").stdout == b""
    for raw in (b"", b"not json", b"[1,2]", b"\xff\xfe"):
        proc = _run(raw)
        assert proc.returncode == 0 and proc.stdout == b""
