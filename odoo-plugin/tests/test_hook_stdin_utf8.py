"""Hook scripts must decode their stdin payload as UTF-8.

Claude Code sends the hook payload as UTF-8 JSON. On Windows, Python reads a
piped stdin with the locale code page (cp1252) unless PYTHONIOENCODING /
PYTHONUTF8 say otherwise, so `json.load(sys.stdin)` mis-decodes non-ASCII text.
For Arabic it usually raises UnicodeDecodeError (byte 0x81 of U+0641 is
undefined in cp1252): a guard that catches ValueError then silently exits 0 -
fail-open - and one that does not crashes with exit 1.

Each test runs the real script as a subprocess with *bytes* on stdin and the
encoding overrides removed from the environment, so it reproduces exactly what
a Windows host does.
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
                "CLAUDE_PROJECT_ROOT", "CLAUDE_PLUGIN_ROOT"):
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


def test_guard_core_odoo_blocks_core_file_with_arabic_payload():
    code, _, err = _run("upgrade/guard_core_odoo.py", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "C:/work/odoo19/odoo/addons/sale/%s.py" % ARABIC,
            "content": "# %s\n" % ARABIC,
        },
    })
    assert code == 2, "core-file guard did not block (exit %s): %s" % (code, err)
    assert "BLOCKED" in err
    assert "Traceback" not in err
    # The refusal names the file - it must be the real path, not cp1252 mojibake.
    assert ARABIC in err, err


def test_volume_guard_blocks_volume_rm_with_arabic_payload():
    code, _, err = _run("pre_odoo_volume_guard.py", {
        "tool_name": "Bash",
        "tool_input": {"command": "docker volume rm odoo_db  # %s" % ARABIC,
                       "description": ARABIC},
    })
    assert code == 2, "volume guard did not block (exit %s): %s" % (code, err)
    assert "BLOCKED" in err


def test_pre_write_check_blocks_inline_script_with_arabic_payload():
    code, _, err = _run("frontend/pre_write_check.py", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "views/%s.xml" % ARABIC,
            "content": "<t><p>%s</p><script>alert(1)</script></t>" % ARABIC,
        },
    })
    assert code == 2, "inline-script check did not block (exit %s): %s" % (code, err)
    assert "Inline JavaScript" in err


def test_post_write_check_reports_with_arabic_payload():
    code, out, err = _run("frontend/post_write_check.py", {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "theme_x/static/%s.scss" % ARABIC,
            "content": "/* %s */ .a { @extend .ml-2; }" % ARABIC,
        },
    })
    assert code == 0, err
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "SCSS modified" in ctx


def test_check_odoo19_compat_reports_with_arabic_payload(tmp_path):
    target = tmp_path / "odoo19" / ARABIC / "views.xml"
    target.parent.mkdir(parents=True)
    target.write_bytes(("<odoo><tree string=\"%s\"/></odoo>\n" % ARABIC).encode("utf-8"))
    code, out, err = _run("upgrade/check_odoo19_compat.py", {
        "tool_name": "Write",
        "tool_input": {"file_path": str(target), "content": ARABIC},
    })
    assert code == 0, err
    assert out.strip(), "compat check produced no output (payload not parsed?)"
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "<tree>" in ctx


def test_session_start_survives_arabic_payload(tmp_path):
    (tmp_path / "odoo19").mkdir()
    code, out, err = _run("frontend/session_start.py",
                          {"hook_event_name": "SessionStart", "cwd": ARABIC},
                          cwd=tmp_path)
    assert code == 0, err
    data = json.loads(out)
    assert "Odoo 19" in data["hookSpecificOutput"]["additionalContext"]


def test_no_hook_reads_stdin_with_the_locale_codec():
    offenders = []
    for py in HOOKS.rglob("*.py"):
        src = py.read_text(encoding="utf-8")
        if "json.load(sys.stdin)" in src or "sys.stdin.read()" in src:
            offenders.append(str(py.relative_to(PLUGIN_ROOT)))
    assert not offenders, "stdin read without UTF-8 decode: %s" % offenders
