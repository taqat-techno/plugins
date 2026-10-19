#!/usr/bin/env python3
"""scripts/redact_evidence.py and scripts/totp.py, offline.

    python -m pytest -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REDACT = ROOT / "scripts" / "redact_evidence.py"
TOTP = ROOT / "scripts" / "totp.py"

SECRET_COOKIE = "sid=placeholder-session-value-123"
SECRET_PW = "placeholder-pass-456"
JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJqYW5lLWRvZSJ9.c2lnbmF0dXJlLXBsYWNlaG9sZGVy"


def run(script, *args, env=None):
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True,
                          env=env or dict(os.environ), timeout=30)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


class RedactEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        net = {"requests": [
            {"url": "https://staging.example.com/api/login", "method": "POST",
             "headers": [{"name": "Cookie", "value": SECRET_COOKIE},
                         {"name": "Accept", "value": "application/json"}],
             "body": {"username": "jane@example.com", "password": SECRET_PW},
             "response": {"token": JWT, "status": 200}}]}
        (self.dir / "network.json").write_text(json.dumps(net), encoding="utf-8")
        (self.dir / "console.log").write_text(
            f"info ready\nAuthorization: Bearer {JWT}\n", encoding="utf-8")
        (self.dir / "notes.md").write_text("all good\n", encoding="utf-8")
        (self.dir / "screenshot.png").write_bytes(b"\x89PNG\r\n")

    def tearDown(self):
        self.tmp.cleanup()

    def all_text(self):
        return "".join(p.read_text(encoding="utf-8") for p in self.dir.iterdir()
                       if p.suffix != ".png")

    def test_check_finds_secrets_without_printing_them(self):
        code, out, err = run(REDACT, "--check", str(self.dir))
        self.assertEqual(code, 1)
        for secret in (SECRET_COOKIE, SECRET_PW, JWT):
            self.assertNotIn(secret, out + err)
        self.assertIn("network.json", out)
        self.assertIn("console.log", out)
        self.assertNotIn("notes.md", out.split("scan:")[0])
        self.assertIn("1 image(s) not scanned", out)
        self.assertIn(SECRET_PW, self.all_text(), "--check must not modify files")

    def test_redact_masks_and_is_idempotent(self):
        code, _, _ = run(REDACT, str(self.dir))
        self.assertEqual(code, 0)
        text = self.all_text()
        for secret in (SECRET_COOKIE, SECRET_PW, JWT):
            self.assertNotIn(secret, text)
        data = json.loads((self.dir / "network.json").read_text(encoding="utf-8"))
        req = data["requests"][0]
        self.assertEqual(req["headers"][1]["value"], "application/json")
        self.assertEqual(req["body"]["username"], "jane@example.com")
        self.assertEqual(req["response"]["status"], 200)
        self.assertEqual(run(REDACT, "--check", str(self.dir))[0], 0)

    def test_clean_directory_passes(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "console.json").write_text('[{"level": "info", "message": "ok"}]',
                                               encoding="utf-8")
            self.assertEqual(run(REDACT, "--check", d)[0], 0)

    def test_usage_error(self):
        self.assertEqual(run(REDACT)[0], 2)


class Totp(unittest.TestCase):
    SEED = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # RFC 6238 SHA-1 test key "12345678901234567890"

    def env(self, value):
        env = dict(os.environ)
        env.pop("QA_TEST_TOTP", None)
        if value is not None:
            env["QA_TEST_TOTP"] = value
        return env

    def test_rfc6238_vectors(self):
        for at, want in ((59, "94287082"), (1111111109, "07081804"), (2000000000, "69279037")):
            code, out, _ = run(TOTP, "QA_TEST_TOTP", "--digits", "8", "--at", str(at),
                               env=self.env(self.SEED))
            self.assertEqual((code, out.strip()), (0, want))

    def test_default_six_digits_and_seed_never_printed(self):
        code, out, err = run(TOTP, "QA_TEST_TOTP", env=self.env(self.SEED))
        self.assertEqual(code, 0)
        self.assertRegex(out.strip(), r"^\d{6}$")
        self.assertNotIn(self.SEED, out + err)

    def test_unset_and_invalid_seed_exit_2(self):
        self.assertEqual(run(TOTP, "QA_TEST_TOTP", env=self.env(None))[0], 2)
        code, out, err = run(TOTP, "QA_TEST_TOTP", env=self.env("not base32 !!"))
        self.assertEqual(code, 2)
        self.assertNotIn("not base32", out + err)
        self.assertEqual(run(TOTP)[0], 2)


if __name__ == "__main__":
    unittest.main()
