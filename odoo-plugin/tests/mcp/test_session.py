"""Session routing: default instance, effective mode, production unlock, client
cache, db auto, audit rotation. Unit level with a fake client - no network.

Run standalone:   python -m pytest tests/mcp/test_session.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "mcp"))

import config as C  # noqa: E402
import session as S  # noqa: E402


class Fake:
    made, dbs, flavor = [], ["acme-stage-2002"], "xmlrpc"

    def __init__(self, inst):
        self.p = inst
        Fake.made.append(inst.qualified)

    def list_databases(self):
        return Fake.dbs


R = {"url": "https://acme-stage.example.com", "username": "u", "api_key": "k-123456"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("ODOO_MCP_HOME", str(tmp_path))
    Fake.made, Fake.dbs = [], ["acme-stage-2002"]
    folder = tmp_path / "acme"
    folder.mkdir()

    def write(**instances):
        f = tmp_path / "profiles.json"
        f.write_bytes(json.dumps({"version": 2, "projects": {
            "acme": {"paths": [str(folder)], "default": "stage", "instances": instances}}}).encode())
        t = time.time_ns()
        os.utime(f, ns=(t, t))

    now = [1_000_000.0]

    def make():
        return S.Session(folder, C.Loader(), client_factory=Fake, clock=lambda: now[0])

    return write, make, now, tmp_path


def test_default_target_and_modes(env):
    write, make, _, _ = env
    write(stage=dict(R, tier="stage", db="s"), prod=dict(R, tier="prod", db="p", access="write"))
    s = make()
    assert s.target(None)[0].mode == "write"
    assert s.target("prod")[0].mode == "read"


def test_unlock_needs_a_verbatim_yes_and_expires(env):
    write, make, now, home = env
    write(stage=dict(R, tier="stage", db="s"), prod=dict(R, tier="prod", db="p", access="full"))
    s = make()
    with pytest.raises(S.ApprovalError, match="approved_by_user"):
        s.unlock("prod", "")
    assert s.unlock("prod", "yes, unlock prod for the fix", minutes=500)["unlocked"] == "acme/prod"
    assert s.target("prod")[0].mode == "write+unlink"
    now[0] += 121 * 60
    assert s.target("prod")[0].mode == "read" and any("expired" in n for n in s.notices)
    assert "yes, unlock prod" in (home / "audit.log").read_text(encoding="utf-8")


def test_unlock_refused_for_read_access_and_for_non_prod(env):
    write, make, _, _ = env
    write(stage=dict(R, tier="stage", db="s"), prod=dict(R, tier="prod", db="p"))
    s = make()
    with pytest.raises(S.ApprovalError, match="widen"):
        s.unlock("prod", "yes")
    with pytest.raises(S.ApprovalError, match="no unlock needed"):
        s.unlock("stage", "yes")


def test_unlock_is_per_instance(env):
    write, make, _, _ = env
    write(stage=dict(R, tier="stage", db="s"), **{
        "c2-prod": dict(R, tier="prod", db="a", access="write"),
        "taqat-prod": dict(R, tier="prod", db="b", access="write")})
    s = make()
    s.unlock("c2-prod", "yes")
    assert s.target("c2-prod")[0].mode == "write" and s.target("taqat-prod")[0].mode == "read"


def test_client_cache_survives_unrelated_edits_and_resets_on_change(env):
    write, make, _, _ = env
    write(stage=dict(R, tier="stage", db="s"), other=dict(R, tier="stage", db="o"))
    s = make()
    s.target("stage")
    s.target("stage")
    s.target("other")
    assert Fake.made == ["acme/stage", "acme/other"]
    write(stage=dict(R, tier="stage", db="s2"), other=dict(R, tier="stage", db="o"))
    s.target("stage")
    s.target("other")
    assert Fake.made == ["acme/stage", "acme/other", "acme/stage"]


def test_db_auto_picks_the_single_database_and_refuses_ambiguity(env):
    write, make, _, _ = env
    write(stage=dict(R, tier="stage", db="auto"))
    assert make().target("stage")[1].p.db == "acme-stage-2002"
    Fake.dbs = ["a-1", "b-2"]
    with pytest.raises(C.ConfigError, match="a-1"):
        make().target("stage")
    write(stage=dict(R, tier="stage", db="auto", db_pattern="^b-"))
    assert make().target("stage")[1].p.db == "b-2"


def test_audit_rotates(env, monkeypatch):
    _, _, _, home = env
    monkeypatch.setattr(S, "AUDIT_MAX_BYTES", 200)
    for i in range(20):
        S.audit({"action": "x", "n": i})
    assert (home / "audit.log.1").exists() and (home / "audit.log").stat().st_size < 400
