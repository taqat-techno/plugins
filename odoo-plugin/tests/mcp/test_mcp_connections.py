"""Connection model tests: tiers, ceilings, approvals, session isolation, local
profiles and database auto-follow.

Every test runs against a throwaway ODOO_MCP_HOME, never the developer's real
~/.odoo-mcp. The database-follow tests drive a tiny fake Odoo (XML-RPC + the
/web/database/list JSON route) on 127.0.0.1.

Run standalone:   python tests/mcp/test_mcp_connections.py
Run under pytest: pytest tests/mcp/test_mcp_connections.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_mcp_server import MCP_DIR, Client  # noqa: E402

REMOTE = "https://acme-stage.example.com"
DEAD_LOCAL = "http://127.0.0.1:1"


def _home_with(servers=None, **extra):
    home = Path(tempfile.mkdtemp())
    if servers is not None:
        (home / "servers.json").write_text(json.dumps(servers), encoding="utf-8")
    for rel, content in extra.items():
        path = home / rel.replace("__", "/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    return home


def _client(home, project):
    return Client(env_extra={"ODOO_MCP_HOME": str(home), "ODOO_MCP_PROJECT_DIR": str(project)})


def _status(c):
    text, err = c.text("odoo_status")
    assert err is False, text
    return json.loads(text)


def _prof(**kw):
    base = {"url": REMOTE, "db": "acme_stage", "username": "mcp", "api_key": "${NOPE_KEY}"}
    base.update(kw)
    return base


# --------------------------------------------------------------------------
# resolution
# --------------------------------------------------------------------------


def test_remote_default_is_never_auto_selected():
    home = _home_with({"default": "stage", "profiles": {"stage": _prof(mode="write", allow_unlink=True)}})
    project = Path(tempfile.mkdtemp())
    with _client(home, project) as c:
        c.handshake()
        data = _status(c)
        assert data["connected"] is False
        assert any("NOT auto-selected" in w for w in data.get("warnings", [])), data


def test_remote_profile_bound_to_the_project_is_selected_read_only():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": _prof(projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        prof = _status(c)["profile"]
        assert prof["profile"] == "stage" and prof["tier"] == "staging"
        assert prof["mode"] == "read" and prof["ceiling"] == "write"
        assert prof["approval_to_raise"] == "chat"


def test_local_tier_requires_a_loopback_url():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"x": _prof(tier="local", projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        data = _status(c)
        assert "loopback" in data.get("configuration_error", ""), data


def test_production_with_no_approval_is_a_config_error():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"p": _prof(tier="production", approval="none", projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        assert "approval" in _status(c).get("configuration_error", "")


def test_local_store_profile_is_used_for_its_checkout():
    project = Path(tempfile.mkdtemp())
    store = {"version": 1, "project_dir": str(project), "active": "devdb",
             "profiles": {"devdb": {"url": DEAD_LOCAL, "db": "devdb", "username": "admin",
                                    "api_key": "local-key-123456", "created_at": "2026-09-27T00:00:00Z"}}}
    home = _home_with(local__proj_abc123_json=store)
    (home / "local" / "proj_abc123_json").rename(home / "local" / "proj-abc123.json")
    with _client(home, project) as c:
        c.handshake()
        data = _status(c)
        prof = data["profile"]
        assert prof["kind"] == "local" and prof["tier"] == "local"
        assert prof["profile"] == "local:%s/devdb" % project.name
        assert prof["mode"] == "write", "local profiles start in write"
        assert "local-key-123456" not in json.dumps(data)


# --------------------------------------------------------------------------
# approvals and ceilings
# --------------------------------------------------------------------------


def _pinned_local(project, **kw):
    prof = {"url": DEAD_LOCAL, "db": "testdb", "username": "u", "api_key": "k-123456", "mode": "read"}
    prof.update(kw)
    (project / ".odoo-mcp.json").write_text(json.dumps({"profiles": {"loc": prof}, "default": "loc"}),
                                           encoding="utf-8")


def test_local_session_raises_mode_without_approval():
    project = Path(tempfile.mkdtemp())
    _pinned_local(project)
    with _client(_home_with(), project) as c:
        c.handshake()
        text, err = c.text("odoo_write", {"model": "res.partner", "ids": [1], "values": {"name": "x"}})
        assert err and "read-only" in text
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write"})
        assert err is False, text
        text, err = c.text("odoo_write", {"model": "res.partner", "ids": [1], "values": {"name": "x"}})
        assert "Refused" not in text, "guard still refused after a local elevation: %s" % text


def test_staging_raise_needs_the_developers_verbatim_yes():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": _prof(projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write"})
        assert err and "approved_by_user" in text
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write",
                                            "approved_by_user": "yes, switch stage to write",
                                            "reason": "fix a partner"})
        assert err is False, text
        out = json.loads(text)
        assert out["mode"] == "write" and out["approval"] == "chat" and out["minutes_left"] > 0
    log = (home / "audit.log").read_text(encoding="utf-8")
    assert "yes, switch stage to write" in log and "fix a partner" in log


def test_nothing_can_exceed_the_developers_ceiling():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": _prof(projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write+unlink",
                                            "approved_by_user": "yes"})
        assert err and "ceiling" in text


def test_production_write_needs_a_human_grant_not_a_chat_yes():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"prod": _prof(tier="production", ceiling="write",
                                                  projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write",
                                            "approved_by_user": "yes do it"})
        assert err and "odoo_mcp_ctl.py" in text, text
        grants = home / "grants"
        grants.mkdir()
        import time
        (grants / "prod.json").write_text(json.dumps(
            {"profile": "prod", "mode": "write", "created_at": time.time(),
             "expires_at": time.time() + 600}), encoding="utf-8")
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write"})
        assert err is False and "human-grant" in text, text


def test_production_approval_can_be_set_to_chat_by_the_developer():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"prod": _prof(tier="production", ceiling="write", approval="chat",
                                                  projects=[str(project)])}})
    with _client(home, project) as c:
        c.handshake()
        text, err = c.text("odoo_session", {"action": "mode", "mode": "write", "approved_by_user": "yes"})
        assert err is False, text


def test_switching_to_production_needs_an_explicit_yes_and_stays_read_only():
    project = Path(tempfile.mkdtemp())
    _pinned_local(project)
    home = _home_with({"profiles": {"prod": _prof(tier="production")}})
    with _client(home, project) as c:
        c.handshake()
        text, err = c.text("odoo_session", {"action": "use", "profile": "prod"})
        assert err and "approved_by_user" in text
        text, err = c.text("odoo_session", {"action": "use", "profile": "prod", "approved_by_user": "yes"})
        assert err is False, text
        assert _status(c)["profile"]["mode"] == "read"


def test_an_elevation_never_leaks_into_another_session():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": _prof(projects=[str(project)])}})
    with _client(home, project) as a, _client(home, project) as b:
        a.handshake()
        b.handshake()
        a.text("odoo_session", {"action": "mode", "mode": "write", "approved_by_user": "yes"})
        assert _status(a)["profile"]["mode"] == "write"
        assert _status(b)["profile"]["mode"] == "read"
    assert json.loads((home / "servers.json").read_text())["profiles"]["stage"].get("mode") is None, \
        "the developer's file must never be written"


def test_staging_elevation_expires_back_to_read():
    sys.path.insert(0, str(MCP_DIR))
    import profiles as P
    import session_state as S

    old_home = os.environ.get("ODOO_MCP_HOME")
    os.environ["ODOO_MCP_HOME"] = tempfile.mkdtemp()
    real_now = S._now
    try:
        prof = P._build("stage", _prof(), "test")
        st = S.SessionState()
        st.set_mode(prof, "write", ttl_minutes=5, approved_by_user="yes")
        assert st.effective(prof).mode == "write"
        S._now = lambda: real_now() + 6 * 60
        assert st.effective(prof).mode == "read", "elevation outlived its TTL"
        assert any("expired" in n for n in st.notices)
    finally:
        S._now = real_now
        if old_home is None:
            os.environ.pop("ODOO_MCP_HOME", None)
        else:
            os.environ["ODOO_MCP_HOME"] = old_home


def test_approve_cli_refuses_without_an_interactive_terminal():
    proc = subprocess.run([sys.executable, str(MCP_DIR.parent / "scripts" / "mcp" / "odoo_mcp_ctl.py"), "approve", "prod", "write"],
                          input="prod\n", capture_output=True, text=True, timeout=30)
    assert proc.returncode == 3, proc.stderr
    assert "interactive terminal" in proc.stderr


def test_hygiene_warnings_flag_literal_keys_and_stray_files():
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": _prof(api_key="literal-secret-value", projects=[str(project)])}},
                      **{"seed.json": "{}"})
    with _client(home, project) as c:
        c.handshake()
        data = _status(c)
        w = " ".join(data.get("warnings", []))
        assert "literally" in w and "seed.json" in w
        assert "literal-secret-value" not in json.dumps(data)


def test_legacy_profiles_file_still_loads():
    project = Path(tempfile.mkdtemp())
    home = _home_with()
    (home / "profiles.json").write_text(json.dumps(
        {"default": "loc", "profiles": {"loc": {"url": DEAD_LOCAL, "db": "d", "username": "u",
                                                 "api_key": "k-123456", "mode": "write"}}}), encoding="utf-8")
    with _client(home, project) as c:
        c.handshake()
        prof = _status(c)["profile"]
        assert prof["profile"] == "loc" and prof["tier"] == "local" and prof["mode"] == "write"


# --------------------------------------------------------------------------
# database auto-follow, against a fake Odoo 17
# --------------------------------------------------------------------------


class FakeOdoo(BaseHTTPRequestHandler):
    live_db = "acme-stage-2002"
    key_valid = True

    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/web/database/list":
            return self._send(json.dumps({"jsonrpc": "2.0", "result": [self.live_db]}), "application/json")
        params, method = xmlrpc.client.loads(raw)
        cls = type(self)
        try:
            if method == "version":
                result = {"server_version": "17.0", "server_version_info": [17, 0, 0, "final", 0]}
            elif method == "authenticate":
                db = params[0]
                if db != cls.live_db:
                    raise xmlrpc.client.Fault(1, 'psycopg2.OperationalError: FATAL:  database "%s" does not exist' % db)
                result = 2 if cls.key_valid else False
            elif method == "execute_kw":
                result = [{"id": 7, "name": "Acme"}] if params[4] == "search_read" else 1
            elif method == "list":
                result = [cls.live_db]
            else:
                raise xmlrpc.client.Fault(1, "unknown method %s" % method)
            body = xmlrpc.client.dumps((result,), methodresponse=True, allow_none=True)
        except xmlrpc.client.Fault as fault:
            body = xmlrpc.client.dumps(fault, methodresponse=True)
        self._send(body, "text/xml")


def _fake_server(key_valid=True):
    handler = type("H", (FakeOdoo,), {"key_valid": key_valid})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def _follow_setup(tier="staging", key_valid=True):
    srv, url = _fake_server(key_valid)
    project = Path(tempfile.mkdtemp())
    home = _home_with({"profiles": {"stage": {"url": url, "db": "acme-stage-1001", "username": "mcp",
                                              "api_key": "${NOPE_KEY}", "tier": tier,
                                              "projects": [str(project)]}}})
    os.environ["NOPE_KEY"] = "rebuild-key-123456"
    return srv, home, project


def test_renamed_staging_database_is_followed_automatically():
    srv, home, project = _follow_setup()
    try:
        before = (home / "servers.json").read_text(encoding="utf-8")
        with _client(home, project) as c:
            c.handshake()
            text, err = c.text("odoo_search", {"model": "res.partner", "fields": ["name"]})
            assert err is False, text
            assert "acme-stage-1001" in text and "acme-stage-2002" in text and "changed" in text
            assert '"Acme"' in text, "the retried call must return the records"
        assert (home / "servers.json").read_text(encoding="utf-8") == before, "developer file was modified"
        learned = json.loads((home / "state" / "learned.json").read_text(encoding="utf-8"))
        assert learned["stage"]["db"] == "acme-stage-2002"
        with _client(home, project) as c2:   # a later session starts on the new database
            c2.handshake()
            assert _status(c2)["profile"]["database"] == "acme-stage-2002"
    finally:
        srv.shutdown()


def test_production_database_change_is_reported_not_followed():
    srv, home, project = _follow_setup(tier="production")
    try:
        with _client(home, project) as c:
            c.handshake()
            text, err = c.text("odoo_search", {"model": "res.partner", "fields": ["name"]})
            assert err and "not re-pointed automatically" in text and "acme-stage-2002" in text
        assert not (home / "state" / "learned.json").exists()
    finally:
        srv.shutdown()


def test_key_lost_in_a_rebuild_gets_the_durable_fix():
    srv, home, project = _follow_setup(key_valid=False)
    try:
        with _client(home, project) as c:
            c.handshake()
            text, err = c.text("odoo_search", {"model": "res.partner", "fields": ["name"]})
            assert err and "acme-stage-2002" in text and "PRODUCTION" in text, text
    finally:
        srv.shutdown()


# --------------------------------------------------------------------------


def _run_all():
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print("  PASS  %s" % name)
        except Exception as exc:
            failed += 1
            print("  FAIL  %s\n        %s: %s" % (name, type(exc).__name__, str(exc)[:500]))
    print("\n%d passed, %d failed, %d total" % (len(fns) - failed, failed, len(fns)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
