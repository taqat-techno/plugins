"""Schema v2 of ~/.odoo-mcp/profiles.json: parsing, folder matching, reload.

Pure unit tests of mcp/config.py - no server process, no network.

Run standalone:   python -m pytest tests/mcp/test_config.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp"))

import config as C  # noqa: E402

REMOTE = "https://acme-stage.example.com"


def inst(**kw):
    base = {"url": REMOTE, "db": "acme", "username": "u", "api_key": "k-123456", "tier": "stage"}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


def doc(**projects):
    return json.dumps({"version": 2, "projects": projects})


def proj(*paths, default=None, **instances):
    d = {"paths": list(paths or ["C:/work/acme"]), "instances": instances}
    if default:
        d["default"] = default
    return d


def parse(**projects):
    return C.parse(doc(**projects), Path("profiles.json"))


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------


def test_access_defaults_follow_the_tier():
    cfg = parse(acme=proj(local=inst(url="http://127.0.0.1:8069", tier=None),
                          stage=inst(), prod=inst(tier="prod")))
    i = cfg.projects["acme"].instances
    assert (i["local"].tier, i["local"].access) == ("local", "full")
    assert i["stage"].access == "write" and i["prod"].access == "read"


def test_remote_without_tier_is_broken_not_guessed():
    b = parse(acme=proj(x=inst(tier=None))).projects["acme"].instances["x"]
    assert isinstance(b, C.BrokenInstance) and '"tier"' in b.error and "prod" in b.error


def test_local_tier_needs_loopback():
    b = parse(acme=proj(x=inst(tier="local"))).projects["acme"].instances["x"]
    assert isinstance(b, C.BrokenInstance) and "loopback" in b.error


@pytest.mark.parametrize("db", ["auto", None, ""])
def test_prod_needs_an_explicit_db(db):
    b = parse(acme=proj(p=inst(tier="prod", db=db))).projects["acme"].instances["p"]
    assert isinstance(b, C.BrokenInstance) and "db" in b.error


def test_stage_db_auto_is_allowed():
    s = parse(acme=proj(s=inst(db="auto"))).projects["acme"].instances["s"]
    assert s.db_auto is True and s.db == ""


def test_prod_refuses_disabled_tls():
    b = parse(acme=proj(p=inst(tier="prod", verify_ssl=False))).projects["acme"].instances["p"]
    assert isinstance(b, C.BrokenInstance) and "verify_ssl" in b.error


def test_unset_env_var_breaks_only_that_instance(monkeypatch):
    monkeypatch.delenv("NOPE_KEY_FOR_TEST", raising=False)
    i = parse(acme=proj(a=inst(api_key="${NOPE_KEY_FOR_TEST}"), b=inst())).projects["acme"].instances
    assert isinstance(i["a"], C.BrokenInstance) and "NOPE_KEY_FOR_TEST is not set" in i["a"].error
    assert isinstance(i["b"], C.Instance)


def test_invalid_access_value_is_broken():
    b = parse(acme=proj(x=inst(access="admin"))).projects["acme"].instances["x"]
    assert isinstance(b, C.BrokenInstance) and "read, write, full" in b.error


def test_syntax_error_reports_line_and_column():
    with pytest.raises(C.ConfigError, match=r"line \d+ col \d+"):
        C.parse('{"version": 2, "projects": {},}', Path("profiles.json"))


def test_same_path_in_two_projects_is_an_error():
    with pytest.raises(C.ConfigError, match="listed by both"):
        parse(a=proj("C:/w/x", s=inst()), b=proj("c:\\w\\x\\", s=inst()))


@pytest.mark.parametrize("bad", ["a/b", "a b", ""])
def test_bad_instance_name_is_an_error(bad):
    with pytest.raises(C.ConfigError, match="name"):
        C.parse(json.dumps({"version": 2, "projects": {
            "acme": {"paths": ["C:/w"], "instances": {bad: inst()}}}}), Path("p"))


def test_default_must_name_an_instance():
    with pytest.raises(C.ConfigError, match="default"):
        parse(acme=proj(default="nope", s=inst()))


def test_unsupported_version():
    with pytest.raises(C.ConfigError, match="version"):
        C.parse('{"version": 3, "projects": {}}', Path("p"))


def test_default_name_prefers_single_local_then_single_stage():
    cfg = parse(a=proj("C:/a", l=inst(url="http://127.0.0.1:1", tier=None), s=inst()),
                b=proj("C:/b", s1=inst(), s2=inst()),
                c=proj("C:/c", s=inst(), p=inst(tier="prod")))
    assert cfg.projects["a"].default_name() == "l"
    assert cfg.projects["b"].default_name() is None
    assert cfg.projects["c"].default_name() == "s"


@pytest.mark.parametrize("url,ok", [
    ("http://localhost:8069", True), ("http://odoo.localhost", True),
    ("http://127.0.0.2:8069", True), ("http://[::1]:8069", True),
    ("http://127.evil.example.com", False), ("http://dev-box.test:8069", False),
    ("http://localhost.evil.example.com", False), ("https://acme.odoo.com", False),
])
def test_loopback_is_proven_not_spelled(url, ok):
    assert C.is_loopback(url) is ok


def _one(**kw):
    return parse(acme=proj(s=inst(**kw))).projects["acme"].instances["s"]


def test_moving_tls_and_protected_models_are_widenings():
    old = _one(access="read")
    assert C.widenings(old, _one(access="read", url="https://elsewhere.example.com"))
    assert C.widenings(old, _one(access="read", verify_ssl=False))
    assert C.widenings(old, _one(access="read", allow_write_models=["res.users"]))
    assert C.widenings(old, _one(access="read", username="other")) == []


def test_describe_never_contains_the_key():
    i = parse(acme=proj(s=inst())).projects["acme"].instances["s"]
    assert "k-123456" not in json.dumps(i.describe()) and i.describe()["api_key_set"] is True


# --------------------------------------------------------------------------
# folder -> project, instance lookup
# --------------------------------------------------------------------------


def _cfg_paths(**projects):
    return parse(**{n: proj(*paths, s=inst()) for n, paths in projects.items()})


def test_subfolder_matches_and_longest_path_wins():
    cfg = _cfg_paths(outer=["C:/w"], inner=["C:/w/acme"])
    assert cfg.match([Path("C:/w/acme/addons/x")]).name == "inner"
    assert cfg.match([Path("C:/w/other")]).name == "outer"


def test_parent_of_two_projects_matches_none():
    cfg = _cfg_paths(a=["C:/TQ/odoo/projects/A"], b=["C:/TQ/odoo/projects/B"])
    assert cfg.match([Path("C:/TQ/odoo")]) is None


def test_windows_path_spellings_match():
    cfg = _cfg_paths(acme=["C:\\Work\\Acme\\"])
    assert cfg.match([Path("c:/work/acme/sub")]).name == "acme"


def test_tilde_path_matches(tmp_path, monkeypatch):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = _cfg_paths(acme=["~/acme"])
    assert cfg.match([tmp_path / "acme" / "x"]).name == "acme"


def make_worktree(main, wt, name="wt1", gitdir_text=None, back_pointer=True):
    """A git worktree as git lays it out: <wt>/.git is a file naming the admin dir,
    and <main>/.git/worktrees/<name>/gitdir points back at <wt>/.git."""
    admin = main / ".git" / "worktrees" / name
    admin.mkdir(parents=True)
    wt.mkdir(parents=True, exist_ok=True)
    (wt / ".git").write_text("gitdir: %s\n" % (gitdir_text or admin.as_posix()), encoding="utf-8")
    if back_pointer:
        (admin / "gitdir").write_text((wt / ".git").as_posix() + "\n", encoding="utf-8")
    return admin


def test_worktree_outside_the_project_resolves_to_its_main_checkout(tmp_path):
    main = tmp_path / "projects" / "taqat" / "Cluster2"
    wt = tmp_path / "wt" / "c2_paymail"
    make_worktree(main, wt)
    (wt / "src").mkdir()
    folders = C.session_folders(wt / "src")
    assert C.norm_path(folders[-1]) == C.norm_path(main)
    assert _cfg_paths(taqat=[str(tmp_path / "projects" / "taqat")]).match(folders).name == "taqat"


def test_relative_gitdir_is_resolved_against_the_worktree(tmp_path):
    main = tmp_path / "main"
    make_worktree(main, tmp_path / "w", name="w", gitdir_text="../main/.git/worktrees/w")
    assert C.norm_path(C.session_folders(tmp_path / "w")[-1]) == C.norm_path(main)


def test_forged_git_file_without_back_pointer_is_ignored(tmp_path):
    """A cloned folder whose .git file merely names another project's worktree dir
    must not inherit that project (and its production instances)."""
    main = tmp_path / "projects" / "taqat"
    make_worktree(main, tmp_path / "wt", back_pointer=False)
    assert C.session_folders(tmp_path / "wt") == [tmp_path / "wt"]


def test_git_file_whose_back_pointer_names_another_folder_is_ignored(tmp_path):
    main = tmp_path / "projects" / "taqat"
    admin = make_worktree(main, tmp_path / "real-wt")
    forged = tmp_path / "forged"
    forged.mkdir()
    (forged / ".git").write_text("gitdir: %s\n" % admin.as_posix(), encoding="utf-8")
    assert C.session_folders(forged) == [forged]


def test_lookup_rules():
    cfg = parse(a=proj("C:/a", s=inst(), p=inst(tier="prod")), b=proj("C:/b", s=inst()))
    cur = cfg.projects["a"]
    assert cfg.lookup(None, cur).qualified == "a/s"
    assert cfg.lookup("p", cur).qualified == "a/p"
    assert cfg.lookup("b/s", cur).qualified == "b/s"
    with pytest.raises(C.ConfigError, match=r"project/instance"):
        cfg.lookup(None, None)
    with pytest.raises(C.ConfigError, match="nope"):
        cfg.lookup("nope", cur)


# --------------------------------------------------------------------------
# loader, v1, save
# --------------------------------------------------------------------------


def _write(p, text, bump=[0]):
    p.write_bytes(text.encode("utf-8"))
    bump[0] += 1
    os.utime(p, ns=(bump[0] * 10**9, bump[0] * 10**9))


def test_reload_picks_up_an_edit(tmp_path):
    f = tmp_path / "profiles.json"
    _write(f, doc(a=proj("C:/a", s=inst())))
    L = C.Loader(f)
    assert "a" in L.get()[0].projects
    _write(f, doc(b=proj("C:/b", s=inst())))
    assert "b" in L.get()[0].projects


def test_invalid_after_valid_keeps_last_good_with_warning(tmp_path):
    f = tmp_path / "profiles.json"
    _write(f, doc(a=proj("C:/a", s=inst())))
    L = C.Loader(f)
    L.get()
    _write(f, '{"version": 2, "projects": {},}')
    cfg, warn = L.get()
    assert "a" in cfg.projects and any("last valid version" in w and "line" in w for w in warn)
    _write(f, doc(a=proj("C:/a", s=inst())))
    assert L.get()[1] == []


def test_empty_file_after_valid_keeps_last_good(tmp_path):
    f = tmp_path / "profiles.json"
    _write(f, doc(a=proj("C:/a", s=inst())))
    L = C.Loader(f)
    L.get()
    _write(f, "")
    cfg, warn = L.get()
    assert "a" in cfg.projects and warn


def test_invalid_with_no_last_good_raises(tmp_path):
    f = tmp_path / "profiles.json"
    _write(f, "{")
    with pytest.raises(C.ConfigError):
        C.Loader(f).get()


def test_missing_file_is_not_an_error(tmp_path):
    assert C.Loader(tmp_path / "profiles.json").get() == (None, [])


def test_bom_and_crlf_file_loads(tmp_path):
    f = tmp_path / "profiles.json"
    f.write_bytes(b"\xef\xbb\xbf" + doc(a=proj("C:/a", s=inst())).replace("\n", "\r\n").encode())
    assert "a" in C.Loader(f).get()[0].projects


def test_v1_file_loads_read_only_and_never_guesses_staging(tmp_path):
    f = tmp_path / "profiles.json"
    _write(f, json.dumps({"default": "x", "profiles": {
        "cluster2-production": {"url": "https://c2.example.com", "db": "c2", "username": "a",
                                "api_key": "k-1", "mode": "write", "allow_unlink": True},
        "loc": {"url": "http://127.0.0.1:8069", "db": "d", "username": "a", "api_key": "k-2"}}}))
    cfg, warn = C.Loader(f).get()
    leg = cfg.projects["legacy"]
    assert cfg.version == 1 and leg.paths == ()
    assert leg.instances["cluster2-production"].tier == "prod"
    assert all(i.access == "read" and i.legacy for i in leg.instances.values())
    assert leg.instances["loc"].tier == "local" and any("migrate" in w for w in warn)
    assert cfg.match([Path("C:/anything")]) is None


def test_save_validates_backs_up_and_writes_lf(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path))
    good = json.loads(doc(a=proj("C:/a", s=inst())))
    assert C.save(good) is None
    for _ in range(12):
        C.save(good)
    raw = C.config_path().read_bytes()
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")
    assert len(list((tmp_path / "backups").glob("profiles-*.json"))) == 10
    with pytest.raises(C.ConfigError):
        C.save({"version": 2, "projects": {"a": {"paths": [], "instances": {}}}})
    with pytest.raises(C.ConfigError, match="tier"):
        C.save(json.loads(doc(a=proj("C:/a", s=inst(tier=None)))))


def test_save_keeps_the_store_private(tmp_path, monkeypatch):
    """Keys live in profiles.json and its backups: folders 0700, files 0600 (POSIX
    meaning; on Windows the user-profile ACL already restricts them)."""
    home = tmp_path / "store"
    monkeypatch.setenv("ODOO_MCP_HOME", str(home))
    modes = {}
    real_chmod = os.chmod
    monkeypatch.setattr(C.os, "chmod", lambda p, m: (modes.__setitem__(Path(p).name, m), real_chmod(p, m)))
    good = json.loads(doc(a=proj("C:/a", s=inst())))
    C.save(good)
    backup = C.save(good)
    assert modes["store"] == 0o700 and modes["backups"] == 0o700
    assert modes[backup.name] == 0o600 and modes["profiles.json.tmp"] == 0o600
