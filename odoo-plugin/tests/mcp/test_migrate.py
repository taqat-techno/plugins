"""odoo_migrate: version-1 profiles.json and project .mcp.json Odoo servers ->
a reviewable plan (no keys) -> version 2.

Run standalone:   python -m pytest tests/mcp/test_migrate.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "mcp"))
sys.path.insert(0, str(HERE.parents[1] / "mcp"))

import odoo_migrate as M  # noqa: E402

V1 = {"profiles": {
    "cluster2-production": {"url": "https://cluster2.odoo.com", "db": "c2-main-1", "username": "admin",
                            "api_key": "KEY-PROD", "mode": "write", "allow_unlink": True},
    "cluster2-production-ro": {"url": "https://cluster2.odoo.com/", "db": "c2-main-1", "username": "admin",
                               "api_key": "KEY-PROD", "mode": "read"},
    "cluster2-stage": {"url": "https://cluster2-stage.odoo.com", "db": "cluster2-stage-40287889",
                       "username": "admin", "api_key": "KEY-STAGE", "mode": "write", "allow_unlink": True},
    "nafla-production": {"url": "https://nafla.odoo.com", "db": "nafla-main-1", "username": "admin",
                         "api_key": "KEY-N", "tier": "production", "ceiling": "write+unlink",
                         "projects": ["C:/p/Nafla-19"]}}}


def test_plan_is_safe_merged_and_keyless():
    plan = M.build_plan(V1, [])
    c2 = plan["projects"]["cluster2"]["instances"]
    prod = [v for v in c2.values() if v["tier"] == "prod"]
    assert len(prod) == 1 and prod[0]["access"] == "read"
    stage = [v for v in c2.values() if v["tier"] == "stage"][0]
    assert stage["db"] == "auto" and stage["access"] == "full"
    assert any("merged" in n for n in plan["notes"])
    assert plan["projects"]["nafla"]["paths"] == ["C:/p/Nafla-19"]
    assert plan["projects"]["nafla"]["instances"]["nafla-production"]["access"] == "read"
    assert "KEY-" not in json.dumps(plan)
    assert any("cluster2" in u and "paths" in u for u in plan["unresolved"])


def test_scan_finds_project_servers_in_env_and_bash_forms(tmp_path):
    p = tmp_path / "taqat_refactoring"
    (p / ".claude" / "mcp" / ".secrets").mkdir(parents=True)
    (p / ".claude" / "mcp" / ".secrets" / "k").write_text("FILE-KEY\n")
    (p / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "odoo-cluster2": {"command": "wsl", "args": ["-e", "bash", "-lc",
            "cd /x && export ODOO_URL=http://127.0.0.1:8074 ODOO_DB=cluster2_fresh ODOO_USERNAME=admin "
            "ODOO_PASSWORD=INLINE && exec python /x/odoo_xmlrpc_mcp.py"]},
        "odoo-stage": {"command": "python", "args": ["odoo_xmlrpc_mcp.py"], "env": {
            "ODOO_URL": "https://cluster2-stage.odoo.com", "ODOO_DB": "cluster2-stage-37914291",
            "ODOO_USERNAME": "admin", "ODOO_API_KEY_FILE": str(p / ".claude/mcp/.secrets/k")}},
        "playwright": {"command": "npx", "args": ["@playwright/mcp"]}}}))
    plan = M.build_plan(None, [tmp_path])
    inst = plan["projects"]["taqat_refactoring"]["instances"]
    assert sorted(v["tier"] for v in inst.values()) == ["local", "stage"]
    assert plan["retire"][0]["servers"] == ["odoo-cluster2", "odoo-stage"]
    assert "INLINE" not in json.dumps(plan) and "FILE-KEY" not in json.dumps(plan)


def test_same_odoo_sh_stage_from_v1_and_a_project_server_is_merged(tmp_path):
    """Two rebuild-stamped databases on one url both become "auto": the same instance."""
    p = tmp_path / "taqat_refactoring"
    p.mkdir()
    (p / ".mcp.json").write_text(json.dumps({"mcpServers": {"odoo-cluster2-odoosh": {
        "command": "python", "args": ["odoo_xmlrpc_mcp.py"], "env": {
            "ODOO_URL": "https://cluster2-stage.odoo.com", "ODOO_DB": "cluster2-stage-37914291",
            "ODOO_USERNAME": "admin", "ODOO_PASSWORD": "x"}}}}))
    plan = M.build_plan(V1, [tmp_path])
    stages = [(pn, i) for pn, pr in plan["projects"].items() for i, s in pr["instances"].items()
              if s["url"] == "https://cluster2-stage.odoo.com"]
    assert stages == [("cluster2", "cluster2-stage")]
    assert any("merged" in n and "odoo-cluster2-odoosh" in n for n in plan["notes"])


def test_apply_needs_approval_then_writes_backs_up_and_retires(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("ODOO_MCP_HOME", str(home))
    (home / "profiles.json").write_text(json.dumps(V1))
    proj = tmp_path / "taqat_refactoring"
    (proj / ".claude" / "mcp").mkdir(parents=True)
    (proj / ".mcp.json").write_text(json.dumps({"mcpServers": {
        "odoo-cluster2": {"command": "python", "args": ["odoo_xmlrpc_mcp.py"], "env": {
            "ODOO_URL": "http://127.0.0.1:8074", "ODOO_DB": "c2", "ODOO_USERNAME": "admin",
            "ODOO_PASSWORD": "pw"}},
        "playwright": {"command": "npx", "args": ["@playwright/mcp"]}}}))
    (proj / ".claude" / "settings.local.json").write_text(json.dumps(
        {"enabledMcpjsonServers": ["odoo-cluster2", "odoo-oksouq", "playwright"]}))
    plan = M.build_plan(V1, [tmp_path])
    plan["projects"]["cluster2"]["paths"] = [str(tmp_path / "c2")]
    plan["unresolved"] = []
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, V1, approved_by=None)
    assert e.value.code == 3
    M.apply_plan(plan, V1, approved_by="yes migrate")
    written = json.loads((home / "profiles.json").read_text())
    assert written["version"] == 2
    assert written["projects"]["taqat_refactoring"]["instances"]["cluster2"]["api_key"] == "pw"
    assert (home / "backups" / "profiles-v1.json").exists()
    assert list(json.loads((proj / ".mcp.json").read_text())["mcpServers"]) == ["playwright"]
    assert json.loads((proj / ".claude" / "settings.local.json").read_text())[
        "enabledMcpjsonServers"] == ["playwright"]
    assert not (proj / ".claude" / "mcp").exists() and list((proj / ".claude").glob("mcp.retired-*"))


def test_apply_refuses_while_anything_is_unresolved(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path))
    plan = M.build_plan(V1, [])
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, V1, approved_by="yes")
    assert e.value.code == 2 and not (tmp_path / "profiles.json").exists()


def test_apply_never_moves_a_source_key_to_another_host(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path))
    plan = M.build_plan(V1, [])
    for p in plan["projects"].values():
        p["paths"] = p["paths"] or [str(tmp_path / "x")]
    plan["unresolved"] = []
    plan["projects"]["cluster2"]["instances"]["cluster2-stage"]["url"] = "https://attacker.example.com"
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, V1, approved_by="yes")
    assert e.value.code == 2 and not (tmp_path / "profiles.json").exists()


def test_key_files_outside_the_project_folder_are_not_read(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path / "home"))
    secret = tmp_path / "elsewhere" / "credentials"
    secret.parent.mkdir()
    secret.write_text("NOT-AN-ODOO-KEY")
    proj = tmp_path / "scan" / "cloned"
    proj.mkdir(parents=True)
    (proj / ".mcp.json").write_text(json.dumps({"mcpServers": {"odoo-x": {
        "command": "python", "args": ["odoo_xmlrpc_mcp.py"], "env": {
            "ODOO_URL": "http://127.0.0.1:8069", "ODOO_DB": "d", "ODOO_USERNAME": "a",
            "ODOO_PASSWORD_FILE": str(secret)}}}}))
    plan = M.build_plan(None, [tmp_path / "scan"])
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, None, approved_by="yes")
    assert e.value.code == 2 and not (tmp_path / "home" / "profiles.json").exists()


def test_key_file_symlinked_out_of_the_project_is_not_read(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path / "home"))
    secret = tmp_path / "elsewhere" / "credentials"
    secret.parent.mkdir()
    secret.write_text("NOT-AN-ODOO-KEY")
    proj = tmp_path / "scan" / "cloned"
    (proj / ".claude" / "mcp").mkdir(parents=True)
    link = proj / ".claude" / "mcp" / "k"
    try:
        os.symlink(secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("this machine does not allow creating symlinks")
    (proj / ".mcp.json").write_text(json.dumps({"mcpServers": {"odoo-x": {
        "command": "python", "args": ["odoo_xmlrpc_mcp.py"], "env": {
            "ODOO_URL": "http://127.0.0.1:8069", "ODOO_DB": "d", "ODOO_USERNAME": "a",
            "ODOO_PASSWORD_FILE": str(link)}}}}))
    plan = M.build_plan(None, [tmp_path / "scan"])
    plan["retire"] = []
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, None, approved_by="yes")
    assert e.value.code == 2 and not (tmp_path / "home" / "profiles.json").exists()


def test_symlinked_claude_folder_is_not_edited_or_renamed(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path / "home"))
    outside = tmp_path / "outside"
    (outside / "mcp").mkdir(parents=True)
    (outside / "settings.local.json").write_text('{"enabledMcpjsonServers": ["a"]}')
    proj = tmp_path / "scan" / "cloned"
    proj.mkdir(parents=True)
    try:
        os.symlink(outside, proj / ".claude", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("this machine does not allow creating symlinks")
    (proj / ".mcp.json").write_text('{"mcpServers": {}}')
    plan = {"version": 2, "projects": {}, "notes": [], "unresolved": [], "remove_pins": [],
            "retire": [{"mcp_json": str(proj / ".mcp.json"), "servers": [],
                        "settings_local": str(proj / ".claude" / "settings.local.json"),
                        "mcp_dir": str(proj / ".claude" / "mcp")}]}
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, None, approved_by="yes")
    assert e.value.code == 2 and (outside / "mcp").is_dir()


@pytest.mark.parametrize("field", ["pin", "mcp_json", "mcp_dir"])
def test_plan_can_only_touch_the_files_migration_owns(tmp_path, monkeypatch, field):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path / "home"))
    victim = tmp_path / "important.txt"
    victim.write_text("keep me")
    folder = tmp_path / "victim-dir"
    folder.mkdir()
    plan = {"version": 2, "projects": {}, "notes": [], "unresolved": [], "remove_pins": [],
            "retire": []}
    if field == "pin":
        plan["remove_pins"] = [str(victim)]
    elif field == "mcp_json":
        plan["retire"] = [{"mcp_json": str(victim), "servers": [], "settings_local": None,
                           "mcp_dir": None}]
    else:
        (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
        plan["retire"] = [{"mcp_json": str(tmp_path / ".mcp.json"), "servers": [],
                           "settings_local": None, "mcp_dir": str(folder)}]
    with pytest.raises(SystemExit) as e:
        M.apply_plan(plan, None, approved_by="yes")
    assert e.value.code == 2 and victim.read_text() == "keep me" and folder.is_dir()


def test_prod_without_db_and_shared_prod_db_are_unresolved():
    v1 = {"profiles": {
        "nafla-production": {"url": "https://nafla.odoo.com", "username": "a", "api_key": "k",
                             "tier": "production"},
        "cluster2-production": {"url": "https://cluster2.odoo.com", "db": "c2-main", "username": "a",
                                "api_key": "k"},
        "cluster6-production": {"url": "https://www.reliefcenter.com", "db": "c2-main", "username": "a",
                                "api_key": "k"}}}
    unresolved = " ".join(M.build_plan(v1, [])["unresolved"])
    assert "nafla/nafla-production" in unresolved and "c2-main" in unresolved
