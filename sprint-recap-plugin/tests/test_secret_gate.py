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

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pre_commit_secret_gate.py"

ALLOW, BLOCK = 0, 2

# A directory that is NOT a sprint-recap project, and one that is.
PLAIN = Path(tempfile.mkdtemp(prefix="sr-gate-plain-"))
PROJECT = Path(tempfile.mkdtemp(prefix="sr-gate-project-"))
(PROJECT / ".sprint-recap").mkdir()
(PROJECT / "app" / "src").mkdir(parents=True)


def tearDownModule():
    shutil.rmtree(PLAIN, ignore_errors=True)
    shutil.rmtree(PROJECT, ignore_errors=True)


def run_full(command: str, cwd: Path = PLAIN) -> tuple[int, str, str]:
    """Invoke the hook exactly as Claude Code does: JSON on stdin, with a cwd."""
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    proc = subprocess.run(
        [sys.executable, str(HOOK)], cwd=cwd,
        input=payload.encode("utf-8"), capture_output=True, timeout=30,
    )
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def run(command: str, cwd: Path = PLAIN) -> int:
    return run_full(command, cwd)[0]


def ask_reason(out: str) -> str:
    hso = json.loads(out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "ask"
    return hso["permissionDecisionReason"]


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

    def test_force_add_in_a_project_asks(self):
        code, out, err = run_full("git add --force build/output.js", PROJECT)
        self.assertEqual((code, err.strip()), (ALLOW, ""))
        self.assertIn("--force", ask_reason(out))

    def test_force_add_from_a_subdirectory_asks(self):
        code, out, _ = run_full("git add -f dist/app.js", PROJECT / "app" / "src")
        self.assertIn("bypasses .gitignore", ask_reason(out))

    def test_force_add_outside_a_project_is_silent(self):
        self.assertEqual(run_full("git add --force build/output.js"), (ALLOW, "", ""))

    def test_commit_naming_the_file_as_a_path(self):
        self.assertEqual(
            run("git commit .sprint-recap.local.json -m 'oops'"), BLOCK
        )


class BlocksCachedSessionState(unittest.TestCase):
    """capture_steps.py caches each role's storage state (cookies) under .auth/."""

    def test_auth_state_file(self):
        self.assertEqual(
            run("git add .sprint-recap/runs/sprint-3/03-capture/.auth/admin.json"),
            BLOCK,
        )

    def test_auth_directory(self):
        self.assertEqual(run("git add .sprint-recap/runs/sprint-3/03-capture/.auth/"), BLOCK)
        self.assertEqual(run("git add .sprint-recap/runs/sprint-3/03-capture/.auth"), BLOCK)

    def test_windows_separators(self):
        self.assertEqual(
            run("git add .sprint-recap\\runs\\s3\\capture\\.auth\\qa.json"), BLOCK
        )

    def test_auth_directly_under_recap_dir(self):
        self.assertEqual(run("git add .sprint-recap/.auth/x.json"), BLOCK)

    def test_commit_of_auth_path(self):
        self.assertEqual(
            run("git commit .sprint-recap/runs/s3/capture/.auth/admin.json -m 'x'"),
            BLOCK,
        )

    def test_similar_names_are_not_auth(self):
        self.assertEqual(run("git add .sprint-recap/runs/s3/oauth-notes.md"), ALLOW)
        self.assertEqual(run("git add .sprint-recap/runs/s3/.authors"), ALLOW)
        self.assertEqual(run("git add src/.auth/helpers.py"), ALLOW)

    def test_message_mentioning_auth_dir_is_allowed(self):
        self.assertEqual(
            run("git commit -m 'never commit .sprint-recap/**/.auth/ state'"), ALLOW
        )

    def test_broad_add_note_mentions_auth(self):
        _, out, _ = run_full("git add -A", PROJECT)
        self.assertIn(".auth/", json.loads(out)["hookSpecificOutput"]["additionalContext"])


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


class ShellBypassForms(unittest.TestCase):
    """Forms found by security review that once slipped past the segment parser."""

    AUTH = ".sprint-recap/runs/s3/03-capture/.auth/admin.json"

    def test_background_ampersand(self):
        self.assertEqual(run("git add .sprint-recap.local.json & true"), BLOCK)
        self.assertEqual(run("true & git add " + self.AUTH), BLOCK)

    def test_bash_c_script(self):
        self.assertEqual(run('bash -c "git add ' + self.AUTH + '"'), BLOCK)
        self.assertEqual(run("sh -lc 'cd app && git add .sprint-recap.local.json'"), BLOCK)
        self.assertEqual(run('/usr/bin/zsh -c "git commit .sprint-recap/credentials/a.html"'), BLOCK)

    def test_runner_prefixes(self):
        self.assertEqual(run("nohup git add .sprint-recap.local.json"), BLOCK)
        self.assertEqual(run("time git add " + self.AUTH), BLOCK)
        self.assertEqual(run("{ git add .sprint-recap.local.json; }"), BLOCK)
        self.assertEqual(run("sudo -u dev git add .sprint-recap.local.json"), BLOCK)

    def test_xargs_pipe_asks(self):
        # The path reaches git through stdin; the segment parser cannot see it,
        # so the backstop asks instead of letting it pass.
        code, out, _ = run_full("echo .sprint-recap.local.json | xargs git add")
        self.assertEqual(code, ALLOW)
        self.assertIn(".sprint-recap.local.json", ask_reason(out))
        self.assertEqual(run("xargs -0 git add .sprint-recap.local.json < list"), BLOCK)

    def test_unparsed_shell_syntax_asks(self):
        code, out, _ = run_full("$(echo git) add .sprint-recap.local.json")
        self.assertEqual(code, ALLOW)
        self.assertIn("cannot parse safely", ask_reason(out))

    def test_harmless_lines_stay_silent(self):
        self.assertEqual(run_full("bash -c 'git status' & true"), (ALLOW, "", ""))
        self.assertEqual(run_full("nohup git add src/app.py"), (ALLOW, "", ""))


class BroadAddNoteReachesClaude(unittest.TestCase):
    """Exit-0 stderr never reaches the model; the note must be additionalContext."""

    def test_broad_add_note_is_additional_context(self):
        code, out, err = run_full("git add -A", PROJECT)
        self.assertEqual(code, ALLOW)
        self.assertEqual(err.strip(), "")
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertNotIn("permissionDecision", hso)
        self.assertIn("git check-ignore", hso["additionalContext"])

    def test_explicit_path_add_is_silent(self):
        self.assertEqual(run_full("git add src/app.py", PROJECT), (ALLOW, "", ""))

    def test_broad_add_outside_a_project_is_silent(self):
        self.assertEqual(run_full("git add -A"), (ALLOW, "", ""))


class MatchesTheCommandThatRuns(unittest.TestCase):
    """Quoted text, echo and grep patterns are not git commands (SEC-08)."""

    def test_echo_of_a_git_command_never_blocks(self):
        # Not run as git, so no block; the fail-closed backstop still asks,
        # because the line mentions both a staging verb and a secret path.
        code, out, err = run_full('echo "git add -f .sprint-recap.local.json"', PROJECT)
        self.assertEqual((code, err.strip()), (ALLOW, ""))
        self.assertIn("cannot parse safely", ask_reason(out))

    def test_grep_pattern_is_ignored(self):
        self.assertEqual(run("grep -rn 'git add --force' docs/", PROJECT), ALLOW)

    def test_git_log_naming_the_file_is_not_staging(self):
        self.assertEqual(run("git log -- .sprint-recap.local.json"), ALLOW)

    def test_git_global_options_are_skipped(self):
        self.assertEqual(run("git -C ../app add .sprint-recap.local.json"), BLOCK)
        self.assertEqual(run("git -c core.autocrlf=false add .sprint-recap.local.json"), BLOCK)

    def test_env_prefix_and_chained_commands(self):
        self.assertEqual(run("cd app && GIT_TRACE=0 git add .sprint-recap/credentials/x.html"), BLOCK)
        self.assertEqual(run("git status; git add docs/s3-credentials.html"), BLOCK)

    def test_stash_push_of_the_config_blocks(self):
        self.assertEqual(run("git stash push .sprint-recap.local.json"), BLOCK)

    def test_fail_open_on_garbage(self):
        proc = subprocess.run([sys.executable, str(HOOK)], input=b"not json",
                              capture_output=True, timeout=30)
        self.assertEqual((proc.returncode, proc.stdout), (0, b""))

    def test_non_ascii_command_survives(self):
        self.assertEqual(run("git add \u0645\u0644\u0641.txt .sprint-recap.local.json"), BLOCK)

    def test_blocks_still_report_on_stderr(self):
        code, out, err = run_full("git add .sprint-recap.local.json")
        self.assertEqual(code, BLOCK)
        self.assertEqual(out.strip(), "")
        self.assertIn("BLOCKED", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
