"""Offline unit tests for the stage scripts and their shared helpers.

No browser, network, Azure DevOps, npm or real transcripts: every external call is
replaced by a double, or the function under test is pure.

    python -m pytest -q -p no:cacheprovider tests/test_scripts.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import _common  # noqa: E402
import _yaml  # noqa: E402
import build_remotion  # noqa: E402
import capture_steps  # noqa: E402
import collect_evidence as ce  # noqa: E402

GIT = shutil.which("git")


# --------------------------------------------------------------------------- ids

class TestExtractIds:
    @pytest.mark.parametrize("text,ids", [
        ("Fix export #4512", ["4512"]),
        ("AB#4512 and #4518", ["4512", "4518"]),
        ("feature/4512-customer-export", ["4512"]),
        ("bugfix_4518", ["4518"]),
        ("release/2026-planning", []),           # a year is not a work item
        ("no references here", []),
        ("", []),
    ])
    def test_builtin_rules(self, text, ids):
        assert ce.extract_ids(text) == ids

    def test_squash_merge_pr_suffix_is_not_a_work_item(self):
        subject = "Fix the customer export (#412)"
        assert ce.extract_ids(ce.PR_SUFFIX_RE.sub("", subject)) == []
        # An explicit reference earlier in the subject survives.
        assert ce.extract_ids(ce.PR_SUFFIX_RE.sub("", "#4512 export fix (#412)")) == ["4512"]

    def test_custom_pattern_replaces_builtin_rules(self):
        assert ce.extract_ids("PROJ-77 and #4512", r"PROJ-(\d+)") == ["77"]


class TestCorrelate:
    def _commit(self, ids):
        return {"work_items": ids, "subject": "x"}

    def test_board_items_attract_their_commits(self):
        items = {"4512": ce.blank_item("4512")}
        un = ce.correlate(items, [self._commit(["4512"]), self._commit(["9999"])], [])
        assert len(items["4512"]["commits"]) == 1
        assert len(un["commits"]) == 1          # 9999 is not on the board

    def test_without_a_board_items_are_synthesised(self):
        items = {}
        un = ce.correlate(items, [self._commit(["4512"])], [])
        assert "4512" in items and un["commits"] == []

    def test_sessions_without_ids_are_unattributed(self):
        un = ce.correlate({}, [], [{"work_items": []}])
        assert len(un["sessions"]) == 1


# --------------------------------------------------------------------------- sessions

def _transcript(home: Path, cwd: str, text: str):
    folder = home / ".claude" / "projects" / "proj"
    folder.mkdir(parents=True, exist_ok=True)
    rec = {"type": "user", "timestamp": "2026-09-03T10:00:00Z", "cwd": cwd,
           "gitBranch": "feature/4512-export", "sessionId": "s1",
           "message": {"content": text}}
    (folder / "abc.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")


def _args(**kw):
    base = dict(no_sessions=False, since="2026-09-01", until="2026-09-14",
                with_prompts=False, id_pattern=None)
    base.update(kw)
    return SimpleNamespace(**base)


class TestSessions:
    PROMPT = "deploy with token ghp_" + "A" * 30 + " and mail jane.doe@example.com"

    def test_default_copies_no_prompt_text(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _transcript(tmp_path, str(repo), self.PROMPT)
        with mock.patch.object(ce.Path, "home", return_value=tmp_path):
            sessions, status = ce.collect_sessions([repo], _args())
        assert len(sessions) == 1 and "no prompt text" in status
        blob = json.dumps(sessions)
        assert "prompts" not in sessions[0] and "jane.doe" not in blob and "ghp_" not in blob
        assert sessions[0]["work_items"] == ["4512"]
        assert sessions[0]["transcript"] == "abc.jsonl"   # no absolute path / user name
        assert "cwd" not in sessions[0]

    def test_with_prompts_redacts_secrets_and_emails(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _transcript(tmp_path, str(repo), self.PROMPT)
        with mock.patch.object(ce.Path, "home", return_value=tmp_path):
            sessions, _ = ce.collect_sessions([repo], _args(with_prompts=True))
        prompt = sessions[0]["prompts"][0]
        assert "[REDACTED]" in prompt and "[EMAIL]" in prompt
        assert "ghp_AAAA" not in prompt and "jane.doe@example.com" not in prompt

    def test_sibling_repo_with_same_prefix_is_not_matched(self, tmp_path):
        repo, sibling = tmp_path / "app", tmp_path / "app-legacy"
        repo.mkdir()
        sibling.mkdir()
        _transcript(tmp_path, str(sibling), "work on #4512")
        with mock.patch.object(ce.Path, "home", return_value=tmp_path):
            sessions, _ = ce.collect_sessions([repo], _args())
        assert sessions == []

    def test_in_repo(self):
        assert ce.in_repo("/r/app", "/r/app") and ce.in_repo("/r/app/src", "/r/app")
        assert not ce.in_repo("/r/app-legacy", "/r/app")


class TestGitSource:
    def test_dubious_ownership_is_a_degraded_source(self, tmp_path):
        (tmp_path / ".git").mkdir()
        args = SimpleNamespace(since="2026-09-01", until="2026-09-14", author=None, id_pattern=None)
        with mock.patch.object(ce, "git_run", return_value=(
                128, "", "fatal: detected dubious ownership in repository")):
            commits, notes = ce.collect_git([tmp_path], args)
        assert commits == [] and "owned by another user" in notes[0]

    def test_git_wrapper_does_not_override_safe_directory(self):
        calls = []
        with mock.patch.object(_common.subprocess, "run",
                               side_effect=lambda argv, **kw: calls.append(argv)
                               or SimpleNamespace(returncode=0, stdout="", stderr="")):
            _common.git(["status"], Path("."))
        assert calls[0][:2] == ["git", "status"]
        assert not any("safe.directory" in str(a) for a in calls[0])

    @pytest.mark.skipif(not GIT, reason="git not on PATH")
    def test_commit_subject_pr_number_is_ignored(self, tmp_path):
        env = {"GIT_AUTHOR_DATE": "2026-09-03T10:00:00", "GIT_COMMITTER_DATE": "2026-09-03T10:00:00"}
        run = lambda *a: subprocess.run([GIT, *a], cwd=tmp_path, check=True, capture_output=True,
                                        env={**__import__("os").environ, **env})  # noqa: E731
        run("init", "-q")
        run("-c", "user.name=Jane Doe", "-c", "user.email=jane@example.com",
            "commit", "--allow-empty", "-q", "-m", "Fix customer export (#412)")
        args = SimpleNamespace(since="2026-09-01", until="2026-09-14", author=None, id_pattern=None)
        commits, _ = ce.collect_git([tmp_path], args)
        assert len(commits) == 1 and commits[0]["work_items"] == []


# --------------------------------------------------------------------------- no shell

class TestToolArgv:
    def test_resolves_and_runs_without_shell(self):
        with mock.patch.object(_common.shutil, "which", return_value="/usr/bin/az"):
            assert _common.tool_argv(["az", "boards", "query"]) == ["/usr/bin/az", "boards", "query"]

    @pytest.mark.parametrize("arg", ['a" & calc', "100%PATH%", "x|whoami", "a^b", "a<b"])
    def test_batch_shim_refuses_cmd_metacharacters(self, arg):
        with mock.patch.object(_common.shutil, "which", return_value="C:/tools/az.cmd"):
            with pytest.raises(_common.UnsafeArgument):
                _common.tool_argv(["az", "boards", "query", "--wiql", arg])

    def test_batch_shim_allows_plain_wiql(self):
        wiql = "SELECT [System.Id] FROM WorkItems WHERE [System.IterationPath] UNDER 'P\\Sprint 24'"
        with mock.patch.object(_common.shutil, "which", return_value="C:/tools/az.cmd"):
            assert _common.tool_argv(["az", "--wiql", wiql])[-1] == wiql

    def test_missing_program(self):
        with mock.patch.object(_common.shutil, "which", return_value=None):
            with pytest.raises(FileNotFoundError):
                _common.tool_argv(["az"])

    def test_no_shell_true_anywhere(self):
        for script in (ROOT / "scripts").glob("*.py"):
            assert "shell=(os.name" not in script.read_text(encoding="utf-8"), script.name
            text = script.read_text(encoding="utf-8")
            assert "shell=True," not in text and "shell=True)" not in text, script.name


# --------------------------------------------------------------------------- YAML

class TestYamlSubset:
    TEMPLATE = (ROOT / "templates" / "steps.example.yaml").read_text(encoding="utf-8")

    def test_template_parses_with_the_subset(self):
        data = _yaml._load_subset(self.TEMPLATE)
        assert data["items"] and all(s["caption"] for i in data["items"] for s in i["steps"])

    def test_template_identical_under_pyyaml(self):
        yaml = pytest.importorskip("yaml")
        assert _yaml._load_subset(self.TEMPLATE) == yaml.safe_load(self.TEMPLATE)

    def test_unknown_escape_is_rejected_like_pyyaml(self):
        text = 'iteration_path: "Project\\Sprint 24"\n'
        with pytest.raises(_yaml.YamlSubsetError):
            _yaml._load_subset(text)

    def test_known_escapes_and_single_quotes(self):
        data = _yaml._load_subset('a: "x\\ty\\u00e9"\nb: \'it\'\'s\'\nc: \'P\\Sprint\'\n')
        assert data == {"a": "x\ty\u00e9", "b": "it's", "c": "P\\Sprint"}


# --------------------------------------------------------------------------- capture gates

class TestProductionAndCaptureGates:
    @pytest.mark.parametrize("url,prod", [
        ("https://app-prod.example.com", True),
        ("https://www.example.com", True),
        ("https://live.example.com/admin", True),
        ("https://staging.delivery-app.io", False),     # "delivery" contains "live"
        ("https://app.example.com", False),
        ("http://localhost:3000", False),
    ])
    def test_label_based_production_detection(self, url, prod):
        assert _common.is_production(url, {}) is prod

    def test_custom_markers_replace_the_default(self):
        assert _common.is_production("https://app.acme.com", {"production_markers": ["acme.com"]})
        assert not _common.is_production("https://prod.example.com", {"production_markers": ["acme"]})

    @pytest.mark.parametrize("url", ["http://localhost:8000", "http://127.0.0.1", "https://shop.test",
                                     "http://api.localhost"])
    def test_local_hosts_need_no_opt_in(self, url):
        assert _common.capture_refusal(url, {}, {}) is None

    def test_remote_host_needs_allow_capture(self):
        reason = _common.capture_refusal("https://staging.example.com", {}, {}, name="staging")
        assert reason and "allow_capture" in reason and "'staging'" in reason
        assert _common.capture_refusal("https://staging.example.com",
                                       {"allow_capture": True}, {}) is None

    def test_production_refused_even_with_allow_capture(self):
        assert "production" in _common.capture_refusal(
            "https://prod.example.com", {"allow_capture": True}, {})
        assert _common.capture_refusal("https://prod.example.com", {"allow_capture": True}, {},
                                       allow_production=True) is None

    def test_goto_must_stay_on_host(self):
        base = "https://staging.example.com"
        script = {"items": [{"work_item": 1, "steps": [{"id": "s1", "actions": [
            {"do": "goto", "target": "/orders"},
            {"do": "goto", "target": "https://staging.example.com/x"},
            {"do": "goto", "target": "https://evil.example.net/phish"}]}]}]}
        assert capture_steps.off_host_gotos(script, base) == ["1-s1: https://evil.example.net/phish"]
        assert capture_steps.goto_url("/orders", base) == "https://staging.example.com/orders"

    def test_run_actions_refuses_off_host_goto(self):
        page = mock.Mock()
        with pytest.raises(RuntimeError, match="leaves the target host"):
            capture_steps.run_actions(page, {"actions": [{"do": "goto", "target": "https://x.example.net"}]},
                                      1000, "https://staging.example.com")
        page.goto.assert_not_called()

    def test_mask_reveals_nothing(self):
        assert _common.mask("hunter22") == "********" == _common.mask("ab")
        assert _common.mask("") == ""


class TestStorageState:
    CFG = {"targets": {"staging": {"base_url": "https://staging.example.com", "roles": {
        "sso": {"storage_state": "PLACEHOLDER"}}}}}

    def test_role_with_storage_state_needs_no_password(self, tmp_path):
        state = tmp_path / "saved.json"
        state.write_text('{"cookies": []}', encoding="utf-8")
        cfg = json.loads(json.dumps(self.CFG).replace("PLACEHOLDER", state.as_posix()))
        assert _common.resolve_role(cfg, "staging", "sso")["storage_state"] == state.as_posix()
        run_dir = tmp_path / "run-auth"
        run_dir.mkdir()
        got = capture_steps.storage_for_role(None, None, cfg["targets"]["staging"], cfg,
                                             "staging", "sso", run_dir, 1000)
        assert got.read_text(encoding="utf-8") == '{"cookies": []}'
        assert got.parent == run_dir   # a copy in the run's temp dir, not the user's file

    def test_capture_uses_a_temp_dir_and_cleans_up(self):
        src = (ROOT / "scripts" / "capture_steps.py").read_text(encoding="utf-8")
        assert 'tempfile.mkdtemp(prefix="sprint-recap-auth-")' in src
        assert "shutil.rmtree(state_dir, ignore_errors=True)" in src


# --------------------------------------------------------------------------- render

class TestTimeline:
    def _log(self, tmp_path):
        clip = tmp_path / "1-s1.webm"
        clip.write_bytes(b"webm")
        return {"sprint": "Sprint 24", "base_url": "https://staging.example.com", "steps": [
            {"status": "ok", "clip": str(clip), "work_item": 4512, "caption": "Open orders",
             "role": "qa_admin", "start": "/orders", "wall_ms": 2000},
            {"status": "failed", "clip": None, "work_item": 4512, "caption": "Broken"}]}

    def test_scenes_and_wall_clock_fallback(self, tmp_path):
        project = tmp_path / "proj"
        with mock.patch.object(build_remotion, "which", return_value=False), \
             mock.patch.object(build_remotion, "warn") as warn:
            scenes = build_remotion.build_timeline(self._log(tmp_path), project, 30,
                                                   {"items": [{"work_item": 4512, "title": "Orders"}]})
        assert [s["type"] for s in scenes] == ["title", "item", "step", "outro"]
        step = scenes[2]
        assert step["caption"] == "Open orders" and step["measuredBy"] == "unmeasured"
        assert step["durationInFrames"] == build_remotion.scene_frames(2.0 + build_remotion.PAD_SECONDS, 30)
        assert (project / "public" / "clips" / "1-s1.webm").exists()
        warn.assert_called_once()

    def test_no_usable_clips_dies(self, tmp_path):
        log = {"steps": [{"status": "failed"}]}
        with pytest.raises(SystemExit):
            build_remotion.build_timeline(log, tmp_path / "p", 30, None)

    def test_render_uses_the_project_local_cli_only(self, tmp_path):
        assert build_remotion.local_remotion(tmp_path) is None
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        name = "remotion.cmd" if sys.platform == "win32" else "remotion"
        (bin_dir / name).write_text("", encoding="utf-8")
        assert build_remotion.local_remotion(tmp_path).endswith(name)
        src = (ROOT / "scripts" / "build_remotion.py").read_text(encoding="utf-8")
        assert '"--yes"' not in src

    def test_run_local_refuses_cmd_metacharacters_for_shims(self):
        with pytest.raises(_common.UnsafeArgument):
            build_remotion.run_local(["C:/p/node_modules/.bin/remotion.cmd", "render", "a&b.mp4"])

    def test_template_pins_exact_versions(self):
        pkg = json.loads((ROOT / "templates" / "remotion" / "package.json").read_text(encoding="utf-8"))
        for deps in (pkg["dependencies"], pkg["devDependencies"]):
            for name, version in deps.items():
                assert version[0].isdigit(), (name, version)


# --------------------------------------------------------------------------- check_config

@pytest.mark.skipif(not GIT, reason="git not on PATH")
class TestCheckConfig:
    def _report(self, tmp_path, config):
        subprocess.run([GIT, "init", "-q"], cwd=tmp_path, check=True)
        (tmp_path / ".gitignore").write_text(".sprint-recap.local.json\n.sprint-recap/\n", encoding="utf-8")
        (tmp_path / ".sprint-recap.local.json").write_text(json.dumps(config), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_config.py"), "--json"],
                              cwd=tmp_path, capture_output=True, timeout=60)
        return json.loads(proc.stdout.decode("utf-8"))

    def test_remote_target_without_allow_capture_warns(self, tmp_path):
        rep = self._report(tmp_path, {"targets": {"staging": {
            "base_url": "https://staging.example.com",
            "roles": {"qa": {"username": "qa@example.com", "password": "pw-1234"}}}}})
        assert any("allow_capture" in w for w in rep["warnings"])
        assert rep["targets"]["staging"]["roles"]["qa"]["password"] == "********"
        assert not any(".sprint-recap/runs/" in w for w in rep["warnings"])

    def test_storage_state_role_is_not_a_problem(self, tmp_path):
        rep = self._report(tmp_path, {"targets": {"local": {
            "base_url": "http://localhost:3000",
            "roles": {"sso": {"storage_state": "~/saved.json"}}}}})
        assert rep["problems"] == [] and not any("allow_capture" in w for w in rep["warnings"])


# --------------------------------------------------------------------------- manifest + commands

class TestManifestAndCommands:
    def test_user_config_is_strict(self):
        manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        allowed = {"type", "title", "description", "required", "default", "sensitive", "min", "max"}
        for key, opt in manifest["userConfig"].items():
            assert set(opt) <= allowed, key
        assert manifest["userConfig"]["include_session_prompts"]["default"] is False

    def test_commands_use_the_options(self):
        run = (ROOT / "commands" / "run.md").read_text(encoding="utf-8")
        assert "${user_config.include_session_prompts}" in run and "${user_config.tts_voice}" in run

    @pytest.mark.parametrize("old,new", [("sprint-recap", "run"), ("sprint-recap-target", "target")])
    def test_renamed_commands_keep_a_deprecated_stub(self, old, new):
        stub = (ROOT / "commands" / f"{old}.md").read_text(encoding="utf-8")
        assert f'description: "Deprecated: use /sprint-recap:{new}"' in stub
        assert f"${{CLAUDE_PLUGIN_ROOT}}/commands/{new}.md" in stub

    def test_target_never_collects_passwords_in_chat(self):
        text = (ROOT / "commands" / "target.md").read_text(encoding="utf-8")
        assert "without ever taking a password in chat" in text

    def test_skills_are_trigger_first_and_nested(self):
        for skill in (ROOT / "skills").glob("*/SKILL.md"):
            head = skill.read_text(encoding="utf-8").split("---", 2)[1]
            desc = next(ln for ln in head.splitlines() if ln.startswith("description:"))
            assert desc.startswith('description: "Use when'), skill.parent.name
            assert len(desc) <= 1024 + len('description: ""')
            assert not any(ln.startswith("version:") for ln in head.splitlines()), skill.parent.name

    def test_no_client_looking_example_data(self):
        for path in list(ROOT.rglob("*.md")) + list(ROOT.rglob("*.yaml")):
            if path.name == "CHANGELOG.md" or "tests" in path.parts:
                continue
            text = path.read_text(encoding="utf-8").lower()
            for word in ("khairgate", "donor", "beneficiar", "cairo"):
                assert word not in text, (path.name, word)
