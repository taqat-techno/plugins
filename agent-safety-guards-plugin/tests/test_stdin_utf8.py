"""UTF-8 stdin regression tests for the hooks (ECO-14).

Claude Code writes hook stdin as UTF-8. On Windows, ``sys.stdin`` is a cp1252
text stream (errors=surrogateescape), so ``sys.stdin.read()`` turned an Arabic
prompt into mojibake with lone surrogates - which then crashes any later
``print`` of that text. Hooks must decode ``sys.stdin.buffer`` as UTF-8.
"""
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"

# "فاتورة العميل" - contains byte 0x81 (U+0641 -> D9 81), undefined in cp1252.
ARABIC = "فاتورة العميل"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _windows_like_stdin(text):
    raw = json.dumps({"prompt": text}, ensure_ascii=False).encode("utf-8")
    return io.TextIOWrapper(io.BytesIO(raw), encoding="cp1252", errors="surrogateescape")


def test_prompt_decoded_as_utf8_even_on_cp1252_stdin(monkeypatch):
    mod = _load("credential_paste_advisory")
    monkeypatch.setattr(sys, "stdin", _windows_like_stdin(ARABIC))
    assert mod._read_prompt() == ARABIC


def test_no_hook_reads_text_stdin():
    for script in HOOKS.glob("*.py"):
        src = script.read_text(encoding="utf-8")
        assert not re.search(r"sys\.stdin\.read\(|json\.load\(sys\.stdin\)", src), script.name
