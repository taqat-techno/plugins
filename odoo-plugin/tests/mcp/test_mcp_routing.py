"""Per-call instance routing through the real server process, against fake Odoos.

Every test runs against a throwaway ODOO_MCP_HOME, never the developer's real
~/.odoo-mcp.

Run standalone:   python -m pytest tests/mcp/test_mcp_routing.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_odoo import serve  # noqa: E402
from test_mcp_server import Client  # noqa: E402


def home_with(tmp_path, instances, default="stage", extra_projects=None):
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    proj = tmp_path / "acme"
    proj.mkdir(exist_ok=True)
    projects = {"acme": {"paths": [str(proj)], "default": default, "instances": instances}}
    projects.update(extra_projects or {})
    (home / "profiles.json").write_bytes(json.dumps({"version": 2, "projects": projects}).encode())
    return {"ODOO_MCP_HOME": str(home), "ODOO_MCP_PROJECT_DIR": str(proj)}


def odoo(url, **kw):
    return {k: v for k, v in dict({"url": url, "username": "admin", "api_key": "k-123456",
                                   "tier": "stage", "db": "auto"}, **kw).items() if v is not None}


@pytest.fixture
def servers():
    s, surl = serve("acme-stage-2002")
    p, purl = serve("acme")
    yield s, surl, p, purl
    s.shutdown()
    p.shutdown()


COUNT = {"model": "res.partner"}


def test_tag_and_alternation_without_switching(tmp_path, servers):
    _, surl, _, purl = servers
    env = home_with(tmp_path, {"stage": odoo(surl),
                               "prod": odoo(purl, tier="prod", db="acme", access="write")})
    with Client(env_extra=env) as c:
        c.handshake()
        t1, e1 = c.text("odoo_count", COUNT)
        t2, e2 = c.text("odoo_count", dict(COUNT, instance="prod"))
        assert not e1 and t1.startswith("[acme/stage · acme-stage-2002 · write]"), t1
        assert not e2 and t2.startswith("[acme/prod · acme · read]"), t2


def test_prod_write_needs_unlock_and_unlock_stays_in_this_session(tmp_path, servers):
    _, _, _, purl = servers
    env = home_with(tmp_path, {"prod": odoo(purl, tier="prod", db="acme", access="write")},
                    default="prod")
    args = {"model": "res.partner", "ids": [7], "values": {"name": "X"}}
    with Client(env_extra=env) as a, Client(env_extra=env) as b:
        a.handshake()
        b.handshake()
        text, err = a.text("odoo_write", args)
        assert err and "action=unlock" in text, text
        text, err = a.text("odoo_session", {"action": "unlock", "instance": "prod",
                                            "approved_by_user": "yes go"})
        assert not err, text
        text, err = a.text("odoo_write", args)
        assert not err and "unlocked until" in text.splitlines()[0], text
        assert b.text("odoo_write", args)[1] is True


def test_qualified_name_reaches_another_project_and_unknown_lists_projects(tmp_path, servers):
    _, surl, _, _ = servers
    env = home_with(tmp_path, {"stage": odoo(surl)}, extra_projects={
        "other": {"paths": [str(tmp_path / "o")], "instances": {"stage": odoo(surl)}}})
    with Client(env_extra=env) as c:
        c.handshake()
        text, _ = c.text("odoo_count", dict(COUNT, instance="other/stage"))
        assert text.startswith("[other/stage"), text
        text, err = c.text("odoo_count", dict(COUNT, instance="nope/x"))
        assert err and "acme" in text and "other" in text, text


def test_broken_instance_does_not_break_its_neighbours(tmp_path, servers):
    _, surl, _, _ = servers
    env = home_with(tmp_path, {"stage": odoo(surl), "bad": odoo("https://x.example.com", tier=None)})
    with Client(env_extra=env) as c:
        c.handshake()
        assert c.text("odoo_count", COUNT)[1] is False
        text, err = c.text("odoo_count", dict(COUNT, instance="bad"))
        assert err and '"tier"' in text, text


def test_db_auto_follows_a_rebuild_and_fixed_prod_db_is_never_followed(tmp_path, servers):
    s, surl, p, purl = servers
    env = home_with(tmp_path, {"stage": odoo(surl), "prod": odoo(purl, tier="prod", db="acme")})
    with Client(env_extra=env) as c:
        c.handshake()
        c.text("odoo_count", COUNT)
        c.text("odoo_count", dict(COUNT, instance="prod"))
        s.RequestHandlerClass.live_db = "acme-stage-2003"
        p.RequestHandlerClass.live_db = "acme-new"
        text, err = c.text("odoo_count", COUNT)
        assert not err and text.startswith("[acme/stage · acme-stage-2003 ·"), text
        text, err = c.text("odoo_count", dict(COUNT, instance="prod"))
        assert err and "acme-new" in text and "Not followed" in text, text
        assert text.startswith("[acme/prod · acme ·"), text


def test_edit_applies_on_the_next_call(tmp_path, servers):
    _, surl, _, purl = servers
    env = home_with(tmp_path, {"stage": odoo(surl)})
    with Client(env_extra=env) as c:
        c.handshake()
        c.text("odoo_count", COUNT)
        f = Path(env["ODOO_MCP_HOME"]) / "profiles.json"
        f.write_bytes(f.read_bytes().replace(surl.encode(), purl.encode()))
        t = time.time_ns() + 10**9
        os.utime(f, ns=(t, t))
        assert purl in c.text("odoo_status")[0]


def test_every_tool_takes_instance_and_count_is_eleven():
    with Client() as c:
        c.handshake()
        tools = c.request("tools/list")["result"]["tools"]
        assert len(tools) == 11
        assert all("instance" in t["inputSchema"]["properties"] for t in tools)
