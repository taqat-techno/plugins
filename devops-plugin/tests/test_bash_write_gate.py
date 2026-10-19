"""hooks/pre_bash_write_gate.py: ask before Azure DevOps CLI writes and ADO pushes.

RA-DEV-01 / DEV-P2-09: subagents that hold Bash could run `az boards work-item update`
or `git push` with no plugin gate. The hook classifies az commands with the same verb
rule as /cli-run and asks on writes; reads and unrelated commands get no decision.
Run as a subprocess, the way Claude Code runs it. Offline.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parent.parent
HOOK = PLUGIN / "hooks" / "pre_bash_write_gate.py"
sys.path.insert(0, str(PLUGIN / "hooks"))

import pre_bash_write_gate as gate  # noqa: E402

GIT = shutil.which("git")


def run(command, cwd=None, **env):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if cwd:
        payload["cwd"] = str(cwd)
    e = dict(os.environ)
    e.pop("DEVOPS_BASH_WRITE_GATE", None)
    e.update(env)
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, env=e, timeout=30, cwd=str(cwd or PLUGIN))
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode("utf-8").strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


@pytest.mark.parametrize("command", [
    "az boards work-item update --id 12 --state Done",
    "az repos pr update --id 7 --status completed",
    "az pipelines run --name build",
    "az pipelines variable-group delete --id 3 --yes",
    "az devops project delete --id 1234 --query id",      # --query never makes a read
    "az devops extension install --extension-id x --publisher-id y",
    "az repos pr set-vote --id 7 --vote approve",
    "az boards work-item create --title T --type Task -o table",
    "az devops invoke --area wit --resource workitems --http-method PATCH",
    "az devops invoke --area wit --resource workitems --in-file body.json",
    "az boards frobnicate --id 1",                        # unknown verb = write
    "cd repo && az repos pr update --id 7 --status abandoned",
    "bash -lc 'az boards work-item update --id 1 --state Closed'",
    'eval "az pipelines run --name x"',
    "sudo -E az boards work-item delete --id 4 --yes",
    'powershell -Command "az repos pr update --id 1 --status completed"',
])
def test_az_writes_ask(command):
    out = run(command)
    assert out and out["permissionDecision"] == "ask", command
    assert "Azure DevOps CLI write" in out["permissionDecisionReason"]
    assert "ALLOW" not in out["permissionDecisionReason"]  # no override token


@pytest.mark.parametrize("command", [
    "az boards work-item show --id 12",
    "az boards query --wiql 'SELECT [System.Id] FROM WorkItems'",
    "az repos pr list --status active -o table",
    "az pipelines runs list --top 5",
    "az devops team list-member --team T",
    "az devops invoke --area wit --resource workitems",
    "az devops invoke --area wit --resource workitems --http-method GET",
    "az boards work-item update --help",
    "az account show",                    # not an Azure DevOps group
    "az login",
    'echo "az boards work-item update --id 1"',
    'git commit -m "az repos pr update --status completed"',
    "ls -la",
    "lazy-cmd --frobnicate",
])
def test_reads_and_other_commands_pass_silently(command):
    assert run(command) is None, command


def test_opt_out():
    assert run("az pipelines run --name x", DEVOPS_BASH_WRITE_GATE="off") is None


def test_bad_payload_fails_open():
    p = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True,
                       timeout=30)
    assert p.returncode == 0 and p.stdout.strip() == b""


def test_token_in_command_is_redacted_in_the_reason():
    out = run("az devops login --organization x token=abcdef0123456789")
    assert "abcdef0123456789" not in out["permissionDecisionReason"]


# ------------------------------------------------------------- git push

def test_git_push_parse():
    assert gate.git_push(["git", "push", "origin", "main"]) == (None, "origin")
    assert gate.git_push(["git", "-C", "repo", "push", "-u", "--force-with-lease"]) == ("repo", None)
    assert gate.git_push(["git", "-c", "x=y", "push", "-o", "ci.skip", "ado"]) == (None, "ado")
    assert gate.git_push(["git", "status"]) is None


def test_git_push_to_an_ado_url_asks_without_a_repo(tmp_path):
    out = run("git push https://dev.azure.com/contoso/proj/_git/repo main", cwd=tmp_path)
    assert out and out["permissionDecision"] == "ask"


@pytest.mark.skipif(not GIT, reason="git not installed")
class TestPushToRemotes:
    def _repo(self, tmp_path, url):
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", url], cwd=repo, check=True)
        return repo

    @pytest.mark.parametrize("url", [
        "https://contoso@dev.azure.com/contoso/proj/_git/repo",
        "git@ssh.dev.azure.com:v3/contoso/proj/repo",
        "https://contoso.visualstudio.com/proj/_git/repo",
    ])
    def test_push_to_ado_remote_asks(self, tmp_path, url):
        repo = self._repo(tmp_path, url)
        for command in ("git push", "git push origin feature/x", "git push -u origin HEAD"):
            out = run(command, cwd=repo)
            assert out and out["permissionDecision"] == "ask", command
            assert "Azure DevOps remote" in out["permissionDecisionReason"]

    def test_push_to_other_host_is_silent(self, tmp_path):
        repo = self._repo(tmp_path, "https://github.com/example/repo.git")
        assert run("git push origin main", cwd=repo) is None
        assert run("git fetch origin && git diff origin/main...HEAD", cwd=repo) is None

    def test_git_dash_c_points_at_the_repo(self, tmp_path):
        self._repo(tmp_path, "https://dev.azure.com/contoso/proj/_git/repo")
        out = run("git -C repo push", cwd=tmp_path)
        assert out and out["permissionDecision"] == "ask"
