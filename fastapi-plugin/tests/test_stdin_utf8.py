"""UTF-8 stdin structural gate for the hooks (ECO-14).

Claude Code writes hook stdin as UTF-8. On Windows, ``sys.stdin`` is a cp1252
text stream (errors=surrogateescape), so ``sys.stdin.read()`` /
``json.load(sys.stdin)`` turn an Arabic payload into mojibake with lone
surrogates. Every hook must read ``sys.stdin.buffer`` and decode UTF-8 itself.
"""
import io
import re
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
TEXT_STDIN = re.compile(r"sys\.stdin\.read\(|json\.load\(sys\.stdin\)")


class StdinUtf8Tests(unittest.TestCase):
    def test_no_hook_reads_text_stdin(self):
        scripts = [p for p in HOOKS.rglob("*.py") if not p.name.startswith("test_")]
        self.assertTrue(scripts)
        for script in scripts:
            with self.subTest(script=script.name):
                self.assertIsNone(TEXT_STDIN.search(script.read_text(encoding="utf-8")))

    def test_buffer_decode_recovers_arabic_from_cp1252_stream(self):
        arabic = "فاتورة"  # contains byte 0x81
        stream = io.TextIOWrapper(io.BytesIO(arabic.encode("utf-8")),
                                  encoding="cp1252", errors="surrogateescape")
        self.assertEqual(stream.buffer.read().decode("utf-8", "replace"), arabic)


if __name__ == "__main__":
    unittest.main()
