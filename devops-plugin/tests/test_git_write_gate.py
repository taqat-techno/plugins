"""
Regression tests for hooks/pre_git_write_gate.py.

Focus: issue #16 — Gate 2 (identity/owner access check) must NOT false-block a
GitHub Wiki (.wiki) push. A wiki is not a separate API repo; it shares the base
repo's permissions, so the access probe must run against the base repo.
"""
import io
import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

import pre_git_write_gate as gate  # noqa: E402


def test_base_repo_strips_wiki_suffix():
    assert gate._base_repo("ArchivingSystem.wiki") == "ArchivingSystem"
    assert gate._base_repo("ArchivingSystem") == "ArchivingSystem"
    assert gate._base_repo("") == ""
    assert gate._base_repo(None) is None


def test_wiki_remote_url_parses_to_wiki_pseudo_repo():
    # The raw URL parse stays faithful; normalization to the base repo is _base_repo's job.
    owner, repo = gate._owner_repo_from_url(
        "https://github.com/taqat-techno/ArchivingSystem.wiki.git"
    )
    assert owner == "taqat-techno"
    assert repo == "ArchivingSystem.wiki"


def _run_gate(command, monkeypatch, *, active_account, lacks_access):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(gate, "_active_gh_account", lambda: active_account)
    monkeypatch.setattr(gate, "_active_account_lacks_access", lacks_access)
    return gate.main()


def test_wiki_push_probes_base_repo_and_does_not_block(monkeypatch):
    """Issue #16: an authorized org member pushing a wiki update must not be hard-blocked."""
    seen = {}

    def spy(owner, repo):
        seen["owner"], seen["repo"] = owner, repo
        return False  # base repo IS accessible

    rc = _run_gate(
        "git push https://github.com/taqat-techno/ArchivingSystem.wiki.git master",
        monkeypatch,
        active_account="a-lakosha",  # differs from owner -> Gate 2 engages
        lacks_access=spy,
    )
    assert rc == 0, "wiki push by an authorized member must not be blocked (exit 2)"
    assert seen.get("repo") == "ArchivingSystem", "Gate 2 must probe the BASE repo, not <repo>.wiki"


def test_confirmed_no_access_non_wiki_still_blocks(monkeypatch):
    """Guard: a genuine no-access push to a (non-wiki) protected branch still hard-blocks."""
    rc = _run_gate(
        "git push https://github.com/someorg/private-repo.git main",
        monkeypatch,
        active_account="a-lakosha",
        lacks_access=lambda owner, repo: True,  # provably no access
    )
    assert rc == 2
