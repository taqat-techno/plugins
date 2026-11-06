"""odoo-local MCP server: isolation, safety rails, cleanup-plan contract, protocol.

No WSL, no Postgres, no Odoo: the runner is faked where a tool would reach a runtime,
and agent.py helpers are exercised directly. Live behaviour is smoke-tested by hand
(see CHANGELOG 4.1.0).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "mcp_local"
sys.path.insert(0, str(LOCAL))

import agent  # noqa: E402
import local_tools as T  # noqa: E402
import registry as R  # noqa: E402
import runner  # noqa: E402


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_LOCAL_HOME", str(tmp_path / "odoo-mcp"))
    monkeypatch.delenv("ODOO_LOCAL_SERVICES_FILE", raising=False)
    return tmp_path


def svc(**kw):
    base = {"id": "proj-a", "project": "proj", "runtime": "wsl", "wsl_distro": "Ubuntu",
            "conf": "/home/u/.config/proj/odoo.conf", "http_port": 8069, "gevent_port": 8072,
            "db_host": "127.0.0.1", "db_port": 5432, "main_db": "proj", "data_dir": "/home/u/.local/share/Odoo",
            "python": "/home/u/.venvs/proj/bin/python", "odoo_bin": "/src/odoo-bin", "cwd": "/src",
            "logfile": "/home/u/logs/proj.log", "systemd_unit": "odoo-proj-a"}
    base.update(kw)
    return base


# ------------------------------------------------------------------ registry

def test_registry_lives_apart_from_profiles(home):
    assert R.path().endswith("local-services.json")
    assert "profiles.json" not in R.path()


def test_registry_refuses_profiles_json(monkeypatch, home):
    monkeypatch.setenv("ODOO_LOCAL_SERVICES_FILE", str(home / "odoo-mcp" / "profiles.json"))
    with pytest.raises(R.RegistryError):
        R.path()


@pytest.mark.parametrize("host", ["10.0.0.5", "db.example.com", "staging.acme.com"])
def test_registry_refuses_non_loopback_db(host):
    with pytest.raises(R.RegistryError, match="not loopback"):
        R.save({"services": [svc(db_host=host)]})


def test_registry_refuses_non_loopback_url():
    with pytest.raises(R.RegistryError, match="not loopback"):
        R.save({"services": [svc(url="https://prod.example.com")]})


@pytest.mark.parametrize("host", ["", "localhost", "127.0.0.1", "::1", "False", "/var/run/postgresql", "acme.localhost"])
def test_registry_accepts_loopback(host):
    R.save({"services": [svc(db_host=host)]})
    assert R.get("proj-a")["db_host"] == host


def test_registry_atomic_write_and_backups(home):
    for i in range(13):
        R.save({"services": [svc(http_port=8069 + i)]})
    assert R.get("proj-a")["http_port"] == 8081
    backups = list((home / "odoo-mcp" / "local-backups").iterdir())
    assert 1 <= len(backups) <= R.KEEP_BACKUPS
    assert not (home / "odoo-mcp" / "local-services.json.tmp").exists()


def test_registry_rejects_duplicates_and_bad_ids():
    with pytest.raises(R.RegistryError, match="duplicate"):
        R.save({"services": [svc(), svc()]})
    with pytest.raises(R.RegistryError, match="kebab"):
        R.save({"services": [svc(id="Bad Id")]})


def test_merge_discovered_adds_updates_and_respects_pinned():
    rep = R.merge_discovered([svc(), svc(id="proj-b", http_port=8070)], "Ubuntu")
    assert sorted(rep["added"]) == ["proj-a", "proj-b"]
    doc = R.load()
    for s in doc["services"]:
        if s["id"] == "proj-b":
            s["pinned"] = True
            s["http_port"] = 9999
    R.save(doc)
    rep = R.merge_discovered([svc(http_port=8100), svc(id="proj-b", http_port=8070)], "Ubuntu")
    assert any(u.startswith("proj-a") for u in rep["updated"])
    assert R.get("proj-b")["http_port"] == 9999  # pinned entry kept the user's edit
    assert R.get("proj-a")["created_by"] == "odoo-local"


# -------------------------------------------------------------------- runner

def test_wsl_script_carries_request_as_base64_only():
    req = {"op": "db_drop", "db": "x'; rm -rf / #"}
    script = runner.build_script(req)
    assert script.startswith("set -euo pipefail\n")
    assert "exec python3 - <<'%s'" % runner.HEREDOC in script
    assert "rm -rf /" not in script.split("\n", 2)[1]  # the request line is base64, not text
    b64 = script.split("\n")[1].split("'")[1]
    assert json.loads(base64.b64decode(b64)) == req


def test_parse_output_takes_last_marker_line():
    out = "noise\nODOO_LOCAL_RESULT={\"ok\": true, \"result\": 1}\n"
    assert runner.parse_output(out, "", 0) == {"ok": True, "result": 1}
    assert runner.parse_output("nothing", "boom", 3)["ok"] is False


def test_windows_runtime_runs_agent_natively():
    res = runner.call("windows", None, {"op": "selftest"}, timeout=60)
    assert res["ok"] and res["result"]["ok"]


def test_docker_runtime_is_not_managed():
    assert runner.call("docker", None, {"op": "selftest"})["ok"] is False


# ------------------------------------------------------------- agent rails

def test_guarded_rm_refuses_empty_relative_and_outside(tmp_path):
    root = tmp_path / "data" / "filestore"
    (root / "db1").mkdir(parents=True)
    (tmp_path / "other").mkdir()
    for bad in ("", "  ", "relative/path", str(tmp_path / "other"), str(root)):
        with pytest.raises(agent.Refused):
            agent._guarded_rm(bad, [str(root)])
    assert (root / "db1").exists() and (tmp_path / "other").exists()
    assert agent._guarded_rm(str(root / "db1"), [str(root)]).startswith("removed")
    assert not (root / "db1").exists()


def test_guarded_rm_refuses_traversal(tmp_path):
    root = tmp_path / "fs"
    root.mkdir()
    (tmp_path / "victim").mkdir()
    with pytest.raises(agent.Refused):
        agent._guarded_rm(str(root / ".." / "victim"), [str(root)])
    assert (tmp_path / "victim").exists()


def row(**kw):
    base = {"name": "scratch_1", "size_bytes": 10, "connections": 0, "is_odoo": True,
            "last_activity": time.time() - 60 * 86400}
    base.update(kw)
    return base


def test_keep_reasons():
    assert "main_db" in agent.keep_reason(row(name="proj"), {"proj": "proj-a"}, {})
    assert "connection" in agent.keep_reason(row(connections=1), {}, {})
    assert "active" in agent.keep_reason(row(last_activity=time.time() - 86400), {}, {})
    assert "protected" in agent.keep_reason(row(name="tpl_x"), {}, {"tpl_x": "state file"})
    assert agent.keep_reason(row(last_activity=None), {}, {}) == "last activity unknown"
    assert agent.keep_reason(row(), {}, {}) is None


def test_db_drop_never_drops_keep_list(monkeypatch):
    calls = []
    monkeypatch.setattr(agent, "_db_rows", lambda cl: [row(name="proj"), row(name="busy", connections=2)])
    monkeypatch.setattr(agent, "_last_activity", lambda cl, db, dd: (True, time.time() - 60 * 86400))
    monkeypatch.setattr(agent, "_psql", lambda *a, **k: calls.append(a) or (0, "", ""))
    monkeypatch.setattr(agent, "tool_state_templates", lambda: set())
    for db in ("proj", "busy"):
        with pytest.raises(agent.Refused, match="keep-list"):
            agent.op_db_drop({"cluster": {"label": "U:5432", "port": 5432}, "db": db,
                              "main_dbs": {"proj": "proj-a"}})
    assert calls == []  # no DROP was ever sent


def test_db_drop_dumps_large_db_first(monkeypatch):
    order = []
    monkeypatch.setattr(agent, "_db_rows", lambda cl: [row(name="big", size_bytes=10 ** 10)])
    monkeypatch.setattr(agent, "_last_activity", lambda cl, db, dd: (True, time.time() - 60 * 86400))
    monkeypatch.setattr(agent, "tool_state_templates", lambda: set())
    monkeypatch.setattr(agent, "_dump_verified", lambda cl, db, d: order.append("dump") or {"dump": "x"})
    monkeypatch.setattr(agent, "_psql", lambda cl, sql, **k: order.append(sql) or (0, "", ""))
    res = agent.op_db_drop({"cluster": {"label": "U:5432", "port": 5432}, "db": "big", "drop_filestore": False})
    assert order[0] == "dump" and order[1].startswith("DROP DATABASE") and "FORCE" not in order[1]
    assert res["dropped"] and res["backup"]


def test_describe_conf_flags_traps_and_skips_remote(tmp_path):
    conf_dir = tmp_path / "proj" / "conf"
    conf_dir.mkdir(parents=True)
    (tmp_path / "proj" / "odoo-bin").write_text("#!/usr/bin/env python3\n")
    (conf_dir / "a.conf").write_text("[options]\nhttp_port = 8170\ndb_host = 127.0.0.1\n"
                                     "db_filter = ^proj$\ndev_mode = xml\naddons_path = %s\n" % (tmp_path / "proj"))
    (conf_dir / "remote.conf").write_text("[options]\ndb_host = db.prod.example.com\n")
    svc_a, warn = agent.describe_conf(str(conf_dir / "a.conf"), [], "wsl", "Ubuntu")
    assert warn is None and svc_a["http_port"] == 8170 and svc_a["id"] == "proj-a"
    assert any("dbfilter" in w for w in svc_a["warnings"]) and any("CLI-only" in w for w in svc_a["warnings"])
    assert svc_a["main_db"] == "proj"
    assert svc_a["odoo_bin"].endswith("odoo-bin")
    none, warn = agent.describe_conf(str(conf_dir / "remote.conf"), [], "wsl", "Ubuntu")
    assert none is None and "not loopback" in warn


def test_exact_dbfilter():
    assert agent.exact_dbfilter("^proj$") == "proj"
    assert agent.exact_dbfilter("^proj.*$") is None
    assert agent.exact_dbfilter("proj") is None


# ------------------------------------------------------ cleanup plan contract

def scan(**kw):
    old = time.time() - 90 * 86400
    base = {
        "databases": [{"cluster": "Ubuntu:5432", "databases": [
            row(name="proj", keep="main_db of service proj-a"),
            row(name="test_old", last_activity=old, size_bytes=300 * 1024 * 1024),
            row(name="recent_work", last_activity=time.time() - 10 * 86400),
            row(name="not_odoo", is_odoo=False),
        ]}],
        "filestores": [{"path": "/d/filestore/gone", "db": "gone", "db_exists": False, "size_bytes": 5, "mtime": old},
                       {"path": "/d/filestore/proj", "db": "proj", "db_exists": True, "mtime": old}],
        "confs": [{"service": "dead", "conf": "/c/dead.conf", "main_db": "gone", "db_exists": False,
                   "running": False, "mtime": old},
                  {"service": "proj-a", "conf": "/c/a.conf", "main_db": "proj", "db_exists": True,
                   "running": True, "mtime": old}],
        "logs": [{"path": "/l/old.log.1", "service": "proj-a", "size_bytes": 7, "mtime": old, "current": False}],
        "data_dirs": ["/d"], "cluster_errors": [],
    }
    base.update(kw)
    return base


def test_plan_matches_contract():
    plan, private = T.build_plan(scan(), "Ubuntu", {})
    assert set(plan) >= {"plan_id", "items", "keep"}
    for item in plan["items"]:
        assert set(item) == {"kind", "target", "size_bytes", "reason", "action", "backup"}
        assert item["action"] in ("drop", "archive", "delete")
        assert isinstance(item["backup"], bool)
    for k in plan["keep"]:
        assert set(k) == {"target", "reason"}
    kinds = {(i["kind"], i["target"]) for i in plan["items"]}
    assert ("scratch_db", "Ubuntu:5432/test_old") in kinds
    assert ("orphan_filestore", "Ubuntu:/d/filestore/gone") in kinds
    assert ("dead_conf", "Ubuntu:/c/dead.conf") in kinds
    assert ("stale_log", "Ubuntu:/l/old.log.1") in kinds
    targets = {i["target"] for i in plan["items"]}
    assert "Ubuntu:5432/proj" not in targets and "Ubuntu:5432/recent_work" not in targets
    assert "Ubuntu:5432/not_odoo" not in targets
    big = [i for i in plan["items"] if i["target"].endswith("test_old")][0]
    assert big["backup"] is True
    assert len(private) == len(plan["items"])


def test_plan_skips_orphan_filestores_when_a_cluster_is_unreadable():
    plan, _ = T.build_plan(scan(cluster_errors=["cannot list :5433"]), "Ubuntu", {})
    assert not [i for i in plan["items"] if i["kind"] == "orphan_filestore"]
    assert any("not judged" in k["reason"] for k in plan["keep"])


def _store_plan(home, plan, private, **extra):
    d = home / "odoo-mcp" / "local-plans"
    d.mkdir(parents=True, exist_ok=True)
    stored = {"plan": plan, "private": private, "runtime": "wsl", "distro": "Ubuntu", "data_dirs": ["/d"],
              "log_dirs": ["/l"], "clusters": {"Ubuntu:5432": {"label": "Ubuntu:5432", "port": 5432}}}
    stored.update(extra)
    (d / (plan["plan_id"] + ".json")).write_text(json.dumps(stored))


def test_apply_requires_a_stored_plan_and_known_targets(home, monkeypatch):
    with pytest.raises(T.ToolError, match="unknown plan"):
        T.t_cleanup_apply({"plan_id": "plan-nope"})
    plan, private = T.build_plan(scan(), "Ubuntu", {})
    _store_plan(home, plan, private)
    with pytest.raises(T.ToolError, match="not in the plan"):
        T.t_cleanup_apply({"plan_id": plan["plan_id"], "only": ["Ubuntu:5432/proj"]})


def test_apply_runs_only_selected_items_and_once(home, monkeypatch):
    plan, private = T.build_plan(scan(), "Ubuntu", {})
    _store_plan(home, plan, private)
    R.save({"services": [svc()]})
    sent = []
    monkeypatch.setattr(runner, "call", lambda rt, d, req, timeout=0: sent.append(req) or {"ok": True, "result": "done"})
    res = T.t_cleanup_apply({"plan_id": plan["plan_id"], "only": ["Ubuntu:/d/filestore/gone"]})
    assert len(sent) == 1 and sent[0]["item"]["target"] == "/d/filestore/gone"
    assert "/d/filestore" in sent[0]["allow_roots"]
    assert res["results"][0]["ok"]
    with pytest.raises(T.ToolError, match="already applied"):
        T.t_cleanup_apply({"plan_id": plan["plan_id"]})


def test_apply_refuses_expired_plan(home):
    plan, private = T.build_plan(scan(), "Ubuntu", {})
    plan["expires_at"] = "2000-01-01T00:00:00+00:00"
    _store_plan(home, plan, private)
    with pytest.raises(T.ToolError, match="expired"):
        T.t_cleanup_apply({"plan_id": plan["plan_id"]})


def test_module_tool_starts_background_job(home, monkeypatch):
    R.save({"services": [svc()]})
    sent = []
    monkeypatch.setattr(runner, "call", lambda rt, d, req, timeout=0: sent.append(req) or
                        {"ok": True, "result": {"job_id": req["job_id"]}})
    res = T.t_module({"id": "proj-a", "modules": ["sale_stock"], "action": "upgrade"})
    argv = sent[0]["argv"]
    assert sent[0]["op"] == "job_start"
    assert "--stop-after-init" in argv and "-u" in argv and "sale_stock" in argv and "--no-http" in argv
    assert "local_job" in res["next"]
    with pytest.raises(T.ToolError):
        T.t_module({"id": "proj-a", "modules": ["bad;rm"]})


# ------------------------------------------------------------------ protocol

def _rpc(lines):
    p = subprocess.run([sys.executable, str(LOCAL / "server.py")], input="\n".join(lines) + "\n",
                       capture_output=True, text=True, encoding="utf-8", timeout=60)
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def test_server_handshake_and_tool_list():
    out = _rpc([json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {"protocolVersion": "2025-06-18"}}),
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
                json.dumps({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                            "params": {"name": "nope", "arguments": {}}})])
    assert out[0]["result"]["serverInfo"]["name"] == "odoo-local"
    names = {t["name"] for t in out[1]["result"]["tools"]}
    assert names == set(T.HANDLERS)
    assert "local_cleanup_plan" in names and "local_cleanup_apply" in names
    assert out[2]["result"]["isError"] is True


def test_data_mcp_does_not_import_local_server():
    blob = "".join(f.read_text(encoding="utf-8") for f in (ROOT / "mcp").glob("*.py"))
    assert "mcp_local" not in blob and "local_tools" not in blob


def test_mcp_json_declares_both_servers():
    cfg = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert cfg["odoo"]["args"][0].endswith("mcp/server.py")
    assert cfg["odoo-local"]["args"][0].endswith("mcp_local/server.py")
