#!/usr/bin/env python3
"""The credential commit gate must block staging, not discussion.

Matching the raw command string means a commit MESSAGE that names the
credential file trips the gate -- which blocks the very commit that documents
why the file must never be committed. The gate has to look at the part of the
command that can name a path to stage, and nothing else.

Both directions matter, so both are pinned here: a message that merely mentions
the file passes, and every real staging attempt still blocks.

    python tests/test_secret_gate.py
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pre_commit_secret_gate.py"

ALLOW, BLOCK = 0, 2


def run(command: str) -> int:
    """Invoke the hook exactly as Claude Code does: JSON on stdin."""
    payload = json.dumps({"tool_input": {"command": command}})
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=30,
    )
    return proc.returncode


class BlocksRealStaging(unittest.TestCase):
    """The regressions this gate exists to prevent."""

    def test_explicit_path(self):
        self.assertEqual(run("git add .sprint-recap.local.json"), BLOCK)

    def test_force_add_of_the_config(self):
        self.assertEqual(run("git add -f .sprint-recap.local.json"), BLOCK)

    def test_credentials_directory(self):
        self.assertEqual(
            run("git add .sprint-recap/credentials/sprint-3-credentials.html"),
            BLOCK,
        )

    def test_generated_page_moved_elsewhere(self):
        self.assertEqual(run("git add docs/sprint3-credentials.html"), BLOCK)

    def test_force_add_anything(self):
        self.assertEqual(run("git add --force build/output.js"), BLOCK)

    def test_commit_naming_the_file_as_a_path(self):
        self.assertEqual(
            run("git commit .sprint-recap.local.json -m 'oops'"), BLOCK
        )


class AllowsDiscussion(unittest.TestCase):
    """A commit message is not a path."""

    def test_heredoc_message_mentioning_the_file(self):
        command = (
            "git commit -F - <<'EOF'\n"
            "docs: explain the credential split\n"
            "\n"
            "Credentials live in .sprint-recap.local.json, which is gitignored\n"
            "and must never be committed.\n"
            "EOF"
        )
        self.assertEqual(run(command), ALLOW)

    def test_inline_message_mentioning_the_file(self):
        self.assertEqual(
            run("git commit -m 'note that .sprint-recap.local.json is ignored'"),
            ALLOW,
        )

    def test_inline_message_mentioning_the_credentials_page(self):
        self.assertEqual(
            run('git commit -m "the sprint-3-credentials.html page stays local"'),
            ALLOW,
        )

    def test_ordinary_commit_untouched(self):
        self.assertEqual(run("git commit -m 'feat: add a thing'"), ALLOW)

    def test_non_git_command_untouched(self):
        self.assertEqual(run("cat .sprint-recap.local.json"), ALLOW)


class StillBlocksWhenMessageIsPresent(unittest.TestCase):
    """Stripping the message must not create a hole."""

    def test_staging_plus_innocent_message(self):
        self.assertEqual(
            run("git add .sprint-recap.local.json && git commit -m 'wip'"),
            BLOCK,
        )

    def test_heredoc_commit_that_also_stages_on_line_one(self):
        command = (
            "git add .sprint-recap.local.json && git commit -F - <<'EOF'\n"
            "some message\n"
            "EOF"
        )
        self.assertEqual(run(command), BLOCK)


if __name__ == "__main__":
    unittest.main(verbosity=2)
