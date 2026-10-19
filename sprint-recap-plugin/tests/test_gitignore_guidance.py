#!/usr/bin/env python3
"""The cached .auth/ session state must be covered by the gitignore guidance.

capture_steps.py writes each role's Playwright storage state (live session
cookies) to <run>/<capture>/.auth/<role>.json. Every place that tells the user
what to gitignore must name `.sprint-recap/**/.auth/`, and check_config.py must
warn when it is not ignored.

    python tests/test_gitignore_guidance.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "scripts" / "check_config.py"
GIT = shutil.which("git")
AUTH = ".sprint-recap/**/.auth/"


class GuidanceNamesAuthDir(unittest.TestCase):
    def test_docs(self):
        for rel in ("README.md", "commands/sprint-recap-target.md",
                    "skills/sprint-repro-guide/SKILL.md"):
            with self.subTest(rel=rel):
                self.assertIn(AUTH, (ROOT / rel).read_text(encoding="utf-8"))

    def test_capture_still_writes_auth_dir(self):
        # Pins the path the guidance and the gate are written against.
        src = (ROOT / "scripts" / "capture_steps.py").read_text(encoding="utf-8")
        self.assertIn('out_dir / ".auth"', src)


@unittest.skipUnless(GIT, "git not on PATH")
class CheckConfigWarnsOnAuth(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sr-gitignore-"))
        subprocess.run([GIT, "init", "-q"], cwd=self.tmp, check=True)
        (self.tmp / ".sprint-recap.local.json").write_text(
            json.dumps({"targets": {}}), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _warnings(self):
        proc = subprocess.run([sys.executable, str(CHECK), "--json"], cwd=self.tmp,
                              capture_output=True, timeout=60)
        return json.loads(proc.stdout.decode("utf-8"))["warnings"]

    def test_warns_when_auth_not_ignored(self):
        (self.tmp / ".gitignore").write_text(
            ".sprint-recap.local.json\n.sprint-recap/credentials/\n", encoding="utf-8")
        self.assertTrue(any(".auth/" in w for w in self._warnings()))

    def test_quiet_when_auth_ignored(self):
        (self.tmp / ".gitignore").write_text(
            ".sprint-recap.local.json\n.sprint-recap/credentials/\n" + AUTH + "\n",
            encoding="utf-8")
        self.assertFalse(any(".auth/" in w for w in self._warnings()))


if __name__ == "__main__":
    unittest.main()
