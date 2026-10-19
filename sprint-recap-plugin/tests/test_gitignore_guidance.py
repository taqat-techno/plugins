#!/usr/bin/env python3
"""Session state must stay out of the repository, and the guidance must say so.

Since 0.4 capture_steps.py keeps each role's Playwright storage state (live
session cookies) in a temporary directory that is deleted after the run.
Versions before 0.4 wrote it to <run>/<capture>/.auth/<role>.json, so every
place that tells the user what to gitignore still names `.sprint-recap/**/.auth/`
(or the whole `.sprint-recap/` folder), and check_config.py warns when it is not
ignored.

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
        for rel in ("README.md", "commands/target.md",
                    "skills/sprint-repro-guide/SKILL.md"):
            with self.subTest(rel=rel):
                self.assertIn(AUTH, (ROOT / rel).read_text(encoding="utf-8"))

    def test_capture_keeps_session_state_in_a_temp_dir(self):
        src = (ROOT / "scripts" / "capture_steps.py").read_text(encoding="utf-8")
        self.assertIn('tempfile.mkdtemp(prefix="sprint-recap-auth-")', src)
        self.assertIn("shutil.rmtree(state_dir, ignore_errors=True)", src)
        # The only remaining use of the old path is deleting what old versions left.
        self.assertIn("shutil.rmtree(legacy, ignore_errors=True)", src)

    def test_docs_recommend_ignoring_the_whole_folder(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(".sprint-recap.local.json\n.sprint-recap/\n", readme)


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
