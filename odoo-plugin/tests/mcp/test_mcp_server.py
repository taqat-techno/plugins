"""End-to-end tests for the bundled Odoo MCP server.

Drives the real process over stdio with real JSON-RPC frames. No Odoo instance
and no network are required: every assertion here covers protocol behaviour,
profile resolution and the safety guards, all of which resolve before any
socket is opened.

Run standalone:   python tests/mcp/test_mcp_server.py
Run under pytest: pytest tests/mcp/test_mcp_server.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SERVER = PLUGIN_ROOT / "mcp" / "server.py"
MCP_DIR = PLUGIN_ROOT / "mcp"


class Client:
    """Minimal MCP client speaking the stdio transport."""

    def __init__(self, env_extra=None, cwd=None):
        env = dict(os.environ)
        # Keep the developer's real configuration out of the test run.
        for var in (
            "ODOO_URL", "ODOO_DB", "ODOO_USERNAME", "ODOO_USER", "ODOO_API_KEY",
            "ODOO_PASSWORD", "ODOO_MCP_PROFILE", "ODOO_MCP_MODE", "ODOO_MCP_PRODUCTION",
            "ODOO_MCP_PROJECT_DIR", "CLAUDE_PROJECT_DIR",
        ):
            env.pop(var, None)
        env["PYTHONIOENCODING"] = "utf-8"
        env.update(env_extra or {})
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, env=env, cwd=str(cwd or PLUGIN_ROOT),
        )
        self._id = 0

    def request(self, method, params=None):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, "server closed stdout while waiting for %s" % method
        assert line.endswith("\n"), "frame not newline-terminated"
        assert line.count("\n") == 1, "frame contained an embedded newline"
        return json.loads(line)

    def notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def call_tool(self, name, arguments=None):
        resp = self.request("tools/call", {"name": name, "arguments": arguments or {}})
        assert "result" in resp, "tools/call returned an error envelope: %s" % resp
        return resp["result"]

    def text(self, name, arguments=None):
        res = self.call_tool(name, arguments)
        return "\n".join(c.get("text", "") for c in res.get("content", [])), res.get("isError")

    def handshake(self):
        resp = self.request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test-harness", "version": "1"},
        })
        self.notify("notifications/initialized")
        return resp

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# --------------------------------------------------------------------------


def test_initialize_handshake():
    with Client() as c:
        resp = c.handshake()
        r = resp["result"]
        assert r["protocolVersion"] == "2025-06-18"
        assert r["serverInfo"]["name"] == "odoo"
        assert "tools" in r["capabilities"]


def test_unknown_protocol_falls_back_to_preferred():
    with Client() as c:
        resp = c.request("initialize", {"protocolVersion": "1999-01-01", "capabilities": {}})
        assert resp["result"]["protocolVersion"] == "2025-06-18"


def test_server_discover_reports_method_not_found():
    """A 2026-07-28 client uses this reply to fall back to `initialize`."""
    with Client() as c:
        c.handshake()
        resp = c.request("server/discover")
        assert resp["error"]["code"] == -32601


def test_tool_surface_is_small_and_well_formed():
    with Client() as c:
        c.handshake()
        tools = c.request("tools/list")["result"]["tools"]
        names = [t["name"] for t in tools]
        assert len(tools) == 10, "tool surface grew to %d: %s" % (len(tools), names)
        assert len(set(names)) == len(names)
        for t in tools:
            assert t["description"].strip()
            assert t["inputSchema"]["type"] == "object"
        for required in ("odoo_status", "odoo_search", "odoo_write", "odoo_unlink"):
            assert required in names
        # No tool may offer a shell / SQL / filesystem / module-install path.
        blob = json.dumps(tools).lower()
        for banned in ("sql", "shell", "exec(", "subprocess", "install_module"):
            assert banned not in blob, "tool surface mentions %r" % banned


def test_ping_and_empty_capability_lists():
    with Client() as c:
        c.handshake()
        assert c.request("ping")["result"] == {}
        assert c.request("resources/list")["result"]["resources"] == []
        assert c.request("prompts/list")["result"]["prompts"] == []


def test_unknown_tool_is_an_error_not_a_crash():
    with Client() as c:
        c.handshake()
        text, is_error = c.text("odoo_nonexistent")
        assert is_error is True
        assert "unknown tool" in text.lower()
        assert c.request("ping")["result"] == {}  # still alive


def test_malformed_json_does_not_kill_the_server():
    with Client() as c:
        c.handshake()
        c.proc.stdin.write("{not json at all\n")
        c.proc.stdin.flush()
        err = json.loads(c.proc.stdout.readline())
        assert err["error"]["code"] == -32700
        assert c.request("ping")["result"] == {}


def test_status_without_configuration_explains_setup():
    with Client() as c:
        c.handshake()
        text, is_error = c.text("odoo_status")
        assert is_error is False
        data = json.loads(text)
        assert data["connected"] is False
        assert ".odoo-mcp.json" in data["help"]
        assert "Developer API Keys" in data["help"]
        # It must say where it looked, so a user can fix it.
        assert any(".odoo-mcp.json" in s for s in data["searched"])


def _profile_dir(tmp, **overrides):
    prof = {
        "url": "http://127.0.0.1:1",   # deliberately dead: guards must fire first
        "db": "testdb",
        "username": "mcp_user",
        "api_key": "test-key-value-123456",
        "mode": "read",
    }
    prof.update(overrides)
    (tmp / ".odoo-mcp.json").write_text(
        json.dumps({"profiles": {"local": prof}, "default": "local"}), encoding="utf-8"
    )
    return {"ODOO_MCP_PROJECT_DIR": str(tmp)}


def test_project_profile_is_discovered_and_key_never_leaks():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = _profile_dir(tmp)
        with Client(env_extra=env) as c:
            c.handshake()
            text, _ = c.text("odoo_status")
            assert "test-key-value-123456" not in text, "API key leaked into tool output"
            data = json.loads(text)
            assert data["profile"]["database"] == "testdb"
            assert data["profile"]["api_key_set"] is True
            assert data["profile"]["mode"] == "read"
            # url is dead, so connecting fails - that is expected and must be graceful
            assert data["connected"] is False


def test_read_mode_refuses_every_write_verb():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp)) as c:
            c.handshake()
            for tool, args in (
                ("odoo_create", {"model": "res.partner", "values": [{"name": "x"}]}),
                ("odoo_write", {"model": "res.partner", "ids": [1], "values": {"name": "x"}}),
                ("odoo_unlink", {"model": "res.partner", "ids": [1]}),
            ):
                text, is_error = c.text(tool, args)
                assert is_error is True, "%s was not refused in read mode" % tool
                assert "read-only" in text.lower()


def test_write_mode_still_blocks_privilege_escalation_models():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp, mode="write", allow_unlink=True)) as c:
            c.handshake()
            for model in ("res.users", "ir.actions.server", "ir.config_parameter", "ir.cron"):
                text, is_error = c.text(
                    "odoo_write", {"model": model, "ids": [1], "values": {"x": 1}}
                )
                assert is_error is True, "%s write was allowed" % model
                assert "blocked" in text.lower()


def test_unlink_needs_its_own_switch_even_in_write_mode():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp, mode="write")) as c:
            c.handshake()
            text, is_error = c.text("odoo_unlink", {"model": "res.partner", "ids": [1]})
            assert is_error is True
            assert "allow_unlink" in text


def test_production_profile_refuses_writes():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = _profile_dir(tmp, mode="write", production=True)
        with Client(env_extra=env) as c:
            c.handshake()
            text, is_error = c.text(
                "odoo_write", {"model": "res.partner", "ids": [1], "values": {"name": "x"}}
            )
            assert is_error is True
            assert "production" in text.lower()


def test_private_and_dangerous_methods_are_refused():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp, mode="write")) as c:
            c.handshake()
            text, is_error = c.text(
                "odoo_call", {"model": "res.partner", "method": "_compute_display_name"}
            )
            assert is_error is True and "private" in text.lower()

            text, is_error = c.text(
                "odoo_call", {"model": "ir.module.module", "method": "button_immediate_install"}
            )
            assert is_error is True and "blocked" in text.lower()


def test_audit_suppressing_context_keys_are_refused():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp, mode="write")) as c:
            c.handshake()
            text, is_error = c.text("odoo_search", {
                "model": "res.partner", "context": {"tracking_disable": True},
            })
            assert is_error is True
            assert "tracking_disable" in text


def test_string_domain_is_rejected_as_injection_vector():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        with Client(env_extra=_profile_dir(tmp)) as c:
            c.handshake()
            text, is_error = c.text("odoo_search", {
                "model": "res.partner", "domain": "[('id','=',1)]",
            })
            assert is_error is True
            assert "must be a list" in text


def test_env_var_expansion_in_profile():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / ".odoo-mcp.json").write_text(json.dumps({
            "profiles": {"local": {
                "url": "http://127.0.0.1:1", "db": "d", "username": "u",
                "api_key": "${MY_SECRET_KEY}", "mode": "read",
            }},
            "default": "local",
        }), encoding="utf-8")
        env = {"ODOO_MCP_PROJECT_DIR": str(tmp), "MY_SECRET_KEY": "expanded-secret-999"}
        with Client(env_extra=env) as c:
            c.handshake()
            text, _ = c.text("odoo_status")
            assert "expanded-secret-999" not in text
            assert json.loads(text)["profile"]["api_key_set"] is True


def test_broken_profile_json_reports_clearly():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / ".odoo-mcp.json").write_text("{ oops, not json }", encoding="utf-8")
        with Client(env_extra={"ODOO_MCP_PROJECT_DIR": str(tmp)}) as c:
            c.handshake()
            text, _ = c.text("odoo_status")
            assert "not valid JSON" in text


def test_production_plus_disabled_tls_is_refused():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = _profile_dir(tmp, production=True, verify_ssl=False)
        with Client(env_extra=env) as c:
            c.handshake()
            text, _ = c.text("odoo_status")
            assert "Refusing" in text or "refus" in text.lower()


def test_guards_module_has_no_sql_or_shell_paths():
    """Structural: the server must not contain an execution escape hatch.

    The strings below are ASSERTED ABSENT from the server source - this test
    scans for them, it never evaluates them. Scope is mcp/*.py only, so this
    test file's own mention of the patterns is not scanned.
    """
    blob = ""
    for f in sorted(MCP_DIR.glob("*.py")):
        blob += f.read_text(encoding="utf-8")
    for banned in ("subprocess", "os.system", "eval(", "exec(", "psycopg2", "pty."):
        assert banned not in blob, "MCP server contains %r" % banned


# --------------------------------------------------------------------------

def _run_all():
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    passed, failed = 0, []
    for name, fn in fns:
        try:
            fn()
            passed += 1
            print("  PASS  %s" % name)
        except AssertionError as exc:
            failed.append((name, str(exc) or "assertion failed"))
            print("  FAIL  %s\n        %s" % (name, str(exc)[:400]))
        except Exception as exc:
            failed.append((name, "%s: %s" % (type(exc).__name__, exc)))
            print("  ERROR %s\n        %s: %s" % (name, type(exc).__name__, str(exc)[:400]))
    print("\n%d passed, %d failed, %d total" % (passed, len(failed), len(fns)))
    return 1 if failed else 0


if __name__ == "__main__":
    print("Odoo MCP server test suite\n" + "-" * 60)
    raise SystemExit(_run_all())
