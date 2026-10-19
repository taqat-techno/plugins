"""Hook scripts must decode their stdin payload as UTF-8.

Claude Code sends the hook payload as UTF-8 JSON. On Windows, Python reads a
piped stdin with the locale code page (cp1252) unless PYTHONIOENCODING /
PYTHONUTF8 say otherwise, so `json.load(sys.stdin)` mis-decodes non-ASCII text.
For Arabic it usually raises UnicodeDecodeError (byte 0x81 of U+0641 is
undefined in cp1252): a guard that catches ValueError then silently exits 0 -
fail-open - and one that does not crashes with exit 1.

Each test runs the real script as a subprocess with *bytes* on stdin and the
encoding overrides removed from the environment, so it reproduces exactly what
a Windows host does. The registered hooks read stdin through the vendored
hooklib.read_payload().
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOKS = PLUGIN_ROOT / "hooks"

# "invoice" in Arabic. U+0641 encodes as D9 81; 0x81 is undefined in cp1252.
ARABIC = "\u0641\u0627\u062a\u0648\u0631\u0629"


def _env():
    env = dict(os.environ)
    for var in ("PYTHONIOENCODING", "PYTHONUTF8", "CLAUDE_PROJECT_DIR",
                "CLAUDE_PROJECT_ROOT", "CLAUDE_PLUGIN_ROOT", "ODOO_DESTRUCTIVE_GUARD",
                "ODOO_INLINE_SCRIPT_CHECK"):
        env.pop(var, None)
    return env


def _run(script, payload, cwd=None):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert b"\xd9\x81" in data, "payload must carry raw UTF-8 Arabic bytes"
    proc = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=data, capture_output=True, env=_env(), timeout=30,
        cwd=str(cwd or PLUGIN_ROOT),
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), \
        proc.stderr.decode("utf-8", "replace")


def _decision(out):
    return json.loads(out)["hookSpecificOutput"]


def test_guard_core_odoo_blocks_core_file_with_arabic_payload():
    code, out, err = _run("upgrade/guard_core_odoo.py", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "C:/work/odoo19/odoo/addons/sale/%s.py" % ARABIC,
            "content": "# %s\n" % ARABIC,
        },
    })
    assert code == 0, err
    d = _decision(out)
    assert d["permissionDecision"] == "deny"
    assert "BLOCKED" in d["permissionDecisionReason"]
    # The refusal names the file - it must be the real path, not cp1252 mojibake.
    assert ARABIC in d["permissionDecisionReason"]


def test_volume_guard_asks_on_volume_rm_with_arabic_payload(tmp_path):
    (tmp_path / "docker-compose.yml").write_text("services:\n  odoo:\n    image: odoo:19\n",
                                                 encoding="utf-8")
    code, out, err = _run("pre_odoo_volume_guard.py", {
        "tool_name": "Bash",
        "cwd": str(tmp_path),
        "tool_input": {"command": "docker volume rm stack_db  # %s" % ARABIC,
                       "description": ARABIC},
    }, cwd=tmp_path)
    assert code == 0, err
    assert _decision(out)["permissionDecision"] == "ask"


def test_pre_write_check_blocks_inline_script_with_arabic_payload(tmp_path):
    module = tmp_path / ARABIC
    (module / "views").mkdir(parents=True)
    (module / "__manifest__.py").write_text("{'name': 'x'}\n", encoding="utf-8")
    code, out, err = _run("frontend/pre_write_check.py", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(module / "views" / ("%s.xml" % ARABIC)),
            "content": "<t><p>%s</p><script>alert(1)</script></t>" % ARABIC,
        },
    })
    assert code == 0, err
    d = _decision(out)
    assert d["permissionDecision"] == "deny" and "Inline JavaScript" in d["permissionDecisionReason"]


def test_pre_write_check_covers_multiedit_edits(tmp_path):
    module = tmp_path / ARABIC
    (module / "views").mkdir(parents=True)
    (module / "__manifest__.py").write_text("{'name': 'x'}\n", encoding="utf-8")
    code, out, err = _run("frontend/pre_write_check.py", {
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": str(module / "views" / "v.xml"),
            "edits": [{"old_string": "a", "new_string": "<p>%s</p>" % ARABIC},
                      {"old_string": "b", "new_string": "<script>alert(1)</script>"}],
        },
    })
    assert code == 0, err
    assert _decision(out)["permissionDecision"] == "deny"


def test_registered_write_guards_match_multiedit():
    data = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    matchers = [g["matcher"] for g in data["hooks"]["PreToolUse"] if "Write" in g["matcher"]]
    assert matchers and all("MultiEdit" in m.split("|") for m in matchers), matchers


def test_session_start_survives_arabic_payload(tmp_path):
    (tmp_path / "odoo19").mkdir()
    code, out, err = _run("frontend/session_start.py",
                          {"hook_event_name": "SessionStart", "cwd": ARABIC},
                          cwd=tmp_path)
    assert code == 0, err
    data = json.loads(out)
    assert "Odoo 19" in data["hookSpecificOutput"]["additionalContext"]


def test_restart_guard_advises_with_arabic_payload():
    code, out, err = _run("pre_odoo_restart_guard.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "curl --retry 99 --retry-connrefused http://localhost:8069/web",
                       "description": ARABIC},
    })
    assert code == 0, err
    assert "retry-storm" in _decision(out)["additionalContext"]


def test_no_hook_reads_stdin_with_the_locale_codec():
    offenders = []
    for py in HOOKS.rglob("*.py"):
        if "_vendor" in py.parts:
            continue  # hooklib.read_payload() itself, which reads bytes
        src = py.read_text(encoding="utf-8")
        if "json.load(sys.stdin)" in src or "sys.stdin.read()" in src:
            offenders.append(str(py.relative_to(PLUGIN_ROOT)))
    assert not offenders, "stdin read without UTF-8 decode: %s" % offenders


def test_registered_hooks_use_the_vendored_hooklib():
    data = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    import re
    for groups in data["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                rel = re.search(r"/hooks/([^\"]+\.py)", hook["command"]).group(1)
                src = (HOOKS / rel).read_text(encoding="utf-8")
                assert "import hooklib" in src and "hooklib.run(main)" in src, rel
