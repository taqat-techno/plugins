"""Offline tests for scripts/check_release.py. Git is stubbed with an explicit tag list,
except for one test that builds a throwaway repository when git is available."""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_release.py"
sys.path.insert(0, str(ROOT / "scripts"))
import check_release as cr  # noqa: E402


def project(tmp_path, manifest=("package.json", '{"name": "acme", "version": "1.2.0"}'),
            changelog="# Changelog\n\n## [1.2.0] - 2026-10-19\n\n- x\n\n## [1.1.0] - 2026-09-01\n"):
    if manifest:
        (tmp_path / manifest[0]).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / manifest[0]).write_text(manifest[1], encoding="utf-8")
    if changelog is not None:
        (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return str(tmp_path)


def statuses(result):
    return {c["name"]: c["status"] for c in result["checks"]}


def test_all_pass(tmp_path):
    r = cr.check(project(tmp_path), "v1.2.0", None, None, None, ["v1.0.0", "v1.1.0"])
    assert r["ok"] and set(statuses(r).values()) == {"pass"}


def test_manifest_mismatch_fails(tmp_path):
    r = cr.check(project(tmp_path), "v1.3.0", None, None, None, ["v1.2.0"])
    s = statuses(r)
    assert s["tag-matches-manifest"] == "fail" and s["changelog-entry"] == "fail"
    assert not r["ok"]


def test_retag_and_downgrade_fail(tmp_path):
    root = project(tmp_path)
    assert statuses(cr.check(root, "v1.2.0", None, None, None, ["v1.2.0", "v1.1.0"]))["semver-monotonic"] == "pass"
    r = cr.check(root, "v1.2.0", None, None, None, ["v1.3.0"])
    assert statuses(r)["semver-monotonic"] == "fail"


def test_existing_same_tag_without_tag_arg_is_a_retag(tmp_path):
    r = cr.check(project(tmp_path), None, "1.2.0", None, None, ["v1.2.0"])
    assert statuses(r)["semver-monotonic"] == "fail"


def test_prefixes_are_separate_series(tmp_path):
    root = project(tmp_path, manifest=(".claude-plugin/plugin.json", '{"name": "acme", "version": "0.3.0"}'),
                   changelog="## [0.3.0] - 2026-10-19\n")
    r = cr.check(root, "acme-v0.3.0", None, None, None, ["acme-v0.2.9", "other-v9.0.0", "v5.0.0"])
    assert r["ok"], r


def test_prerelease_ordering():
    assert cr.version_key("1.0.0") > cr.version_key("1.0.0-rc.2") > cr.version_key("1.0.0-rc.1")
    assert cr.version_key("1.10.0") > cr.version_key("1.9.9")


@pytest.mark.parametrize("name,text", [
    ("pyproject.toml", '[project]\nname = "acme"\nversion = "1.2.0"\n'),
    ("pyproject.toml", '[tool.poetry]\nname = "acme"\nversion = "1.2.0"\n'),
    ("Cargo.toml", '[package]\nname = "acme"\nversion = "1.2.0"\n'),
    ("VERSION", "1.2.0\n"),
])
def test_manifest_formats(tmp_path, name, text):
    root = project(tmp_path, manifest=(name, text))
    assert cr.manifest_version(root) == ("1.2.0", name)


def test_changelog_heading_styles(tmp_path):
    for heading in ("## [1.2.0] - 2026-10-19", "## 1.2.0", "## v1.2.0 (2026-10-19)", "### 1.2.0"):
        (tmp_path / "CHANGELOG.md").write_text(f"# x\n\n{heading}\n", encoding="utf-8")
        assert cr.changelog_has(str(tmp_path), "1.2.0")[0], heading
    (tmp_path / "CHANGELOG.md").write_text("## [1.2.10]\n", encoding="utf-8")
    assert not cr.changelog_has(str(tmp_path), "1.2.1")[0]


def test_missing_files_are_skipped_not_failed(tmp_path):
    r = cr.check(str(tmp_path), "v1.0.0", None, None, None, [])
    assert statuses(r) == {"tag-matches-manifest": "skip", "changelog-entry": "skip", "semver-monotonic": "pass"}
    assert r["ok"]


def test_bad_tag_is_an_input_error(tmp_path):
    assert "error" in cr.check(str(tmp_path), "latest", None, None, None, [])


def test_cli_json_and_exit_codes(tmp_path):
    root = project(tmp_path)
    ok = subprocess.run([sys.executable, str(SCRIPT), "--root", root, "--version", "1.2.0", "--json"],
                        capture_output=True, text=True, timeout=30)
    assert json.loads(ok.stdout)["version"] == "1.2.0"
    bad = subprocess.run([sys.executable, str(SCRIPT), "--root", root, "--tag", "v9.9.9"],
                         capture_output=True, text=True, timeout=30)
    assert bad.returncode == 1 and "FAIL" in bad.stdout
    err = subprocess.run([sys.executable, str(SCRIPT), "--root", root, "--tag", "nightly"],
                         capture_output=True, text=True, timeout=30)
    assert err.returncode == 2


@pytest.mark.skipif(not shutil.which("git"), reason="git not installed")
def test_reads_tags_from_a_local_repository(tmp_path):
    root = project(tmp_path)
    git = ["git", "-c", "user.name=Jane Doe", "-c", "user.email=jane@example.com", "-c", "commit.gpgsign=false",
           "-c", "tag.gpgsign=false"]
    subprocess.run(["git", "init", "-q", root], check=True)
    subprocess.run(git + ["-C", root, "add", "-A"], check=True)
    subprocess.run(git + ["-C", root, "commit", "-qm", "init"], check=True)
    subprocess.run(git + ["-C", root, "tag", "v1.1.0"], check=True)
    proc = subprocess.run([sys.executable, str(SCRIPT), "--root", root, "--tag", "v1.2.0", "--json"],
                          capture_output=True, text=True, timeout=30)
    result = json.loads(proc.stdout)
    assert proc.returncode == 0, result
    assert any("v1.1.0" in c["detail"] for c in result["checks"])
