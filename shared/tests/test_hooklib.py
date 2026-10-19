"""Tests for shared/hooklib.py (stdlib only, offline)."""
import io
import json
import os
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import hooklib  # noqa: E402


class _Stdin:
    def __init__(self, data: bytes):
        self.buffer = io.BytesIO(data)


def test_read_payload_decodes_utf8_bytes():
    payload = {"tool_input": {"command": "echo تجربة"}}
    got = hooklib.read_payload(_Stdin(json.dumps(payload, ensure_ascii=False).encode("utf-8")))
    assert got == payload


def test_read_payload_returns_none_for_garbage():
    for raw in (b"", b"   ", b"not json", b"[1, 2]", b"\xff\xfe"):
        assert hooklib.read_payload(_Stdin(raw)) is None


def test_tool_input_is_safe_on_bad_shapes():
    assert hooklib.tool_input({"tool_input": {"a": 1}}) == {"a": 1}
    for bad in (None, [], {"tool_input": 5}, {}):
        assert hooklib.tool_input(bad) == {}


def test_emitters_write_hook_specific_output(capsys):
    hooklib.ask("confirm the drop")
    out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert out == {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                   "permissionDecisionReason": "confirm the drop"}
    hooklib.deny("no", event="PreToolUse")
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"
    hooklib.context("SessionStart", "note")
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"] == "note"


def test_emit_survives_a_cp1252_stdout(tmp_path):
    script = tmp_path / "e.py"
    script.write_text(textwrap.dedent(f"""
        import sys; sys.path.insert(0, {os.path.dirname(hooklib.__file__)!r})
        import hooklib
        hooklib.ask("حذف قاعدة البيانات؟")
    """), encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, env=env, timeout=20)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout.decode("ascii"))
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "حذف قاعدة البيانات؟"


def test_redact_masks_common_secret_shapes():
    samples = [
        "token ghp_" + "a" * 36,
        "key sk-ant-" + "b" * 30,
        "AKIA" + "C" * 16,
        "Authorization: Bearer " + "d" * 24,
        "password=hunter2secret",
        "postgres://user:s3cretpass@db.example.com/app",
        "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
    ]
    for s in samples:
        out = hooklib.redact(s)
        assert "[REDACTED]" in out, s
    assert hooklib.redact("postgres://user:s3cretpass@db/app") == "postgres://user:[REDACTED]@db/app"
    assert hooklib.redact("password=hunter2secret") == "password=[REDACTED]"
    assert hooklib.redact("nothing secret here") == "nothing secret here"


def test_run_fails_open_on_exception(tmp_path):
    script = tmp_path / "h.py"
    script.write_text(textwrap.dedent(f"""
        import sys; sys.path.insert(0, {os.path.dirname(hooklib.__file__)!r})
        import hooklib
        def main():
            raise RuntimeError("boom")
        hooklib.run(main)
    """), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, timeout=20)
    assert proc.returncode == 0
    assert proc.stdout == b""


def test_watchdog_exits_zero(tmp_path):
    script = tmp_path / "w.py"
    script.write_text(textwrap.dedent(f"""
        import sys, time; sys.path.insert(0, {os.path.dirname(hooklib.__file__)!r})
        import hooklib
        hooklib.watchdog(0.2)
        time.sleep(5)
        sys.exit(3)
    """), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, timeout=20)
    assert proc.returncode == 0
