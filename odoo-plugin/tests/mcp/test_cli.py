"""scripts/mcp/odoo_mcp.py - the only writer of ~/.odoo-mcp/profiles.json.

Every test uses a throwaway ODOO_MCP_HOME. Run standalone:
    python -m pytest tests/mcp/test_cli.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[2] / "scripts" / "mcp" / "odoo_mcp.py"


def run(home, *args, stdin=""):
    p = subprocess.run([sys.executable, str(CLI), *args], input=stdin, capture_output=True,
                       text=True, encoding="utf-8",
                       env={**os.environ, "ODOO_MCP_HOME": str(home), "PYTHONIOENCODING": "utf-8"})
    return p.returncode, p.stdout, p.stderr


def doc(home):
    return json.loads((home / "profiles.json").read_text(encoding="utf-8"))


KEY = ("--username", "admin", "--key-stdin")


def test_bare_command_is_check_and_handles_no_file(tmp_path):
    code, out, _ = run(tmp_path)
    assert code == 0 and "profiles.json" in out


def test_add_remote_write_needs_approval_off_tty(tmp_path):
    a = ("add", "acme", "stage", "--url", "https://s.example.com", "--tier", "stage", "--db", "auto",
         "--access", "write", *KEY, "--path", str(tmp_path))
    code, out, err = run(tmp_path, *a, stdin="k-secret-1\n")
    assert code == 3 and "--approved-by" in err and not (tmp_path / "profiles.json").exists()
    code, out, err = run(tmp_path, *a, "--approved-by", "yes add it", stdin="k-secret-1\n")
    assert code == 0, err
    assert doc(tmp_path)["projects"]["acme"]["instances"]["stage"]["access"] == "write"
    assert "k-secret-1" not in out + err
    assert '"widen"' in (tmp_path / "audit.log").read_text(encoding="utf-8")


def test_add_read_only_remote_and_local_need_no_approval(tmp_path):
    assert run(tmp_path, "add", "acme", "ro", "--url", "https://p.example.com", "--tier", "prod",
               "--db", "p", "--access", "read", *KEY, "--path", str(tmp_path), stdin="k\n")[0] == 0
    assert run(tmp_path, "add", "acme", "local", "--url", "http://127.0.0.1:8069", "--db", "d",
               *KEY, stdin="k\n")[0] == 0


def test_remote_without_tier_is_refused(tmp_path):
    assert run(tmp_path, "add", "acme", "x", "--url", "https://p.example.com", "--db", "p",
               *KEY, "--path", str(tmp_path), stdin="k\n")[0] == 2


def test_bind_rejects_a_folder_owned_by_another_project(tmp_path):
    for p in ("a", "b"):
        run(tmp_path, "add", p, "local", "--url", "http://127.0.0.1:1", "--db", "d", *KEY,
            "--path", str(tmp_path / p), stdin="k\n")
    assert run(tmp_path, "bind", "b", str(tmp_path / "a"))[0] == 2


def test_check_never_prints_keys(tmp_path):
    run(tmp_path, "add", "acme", "local", "--url", "http://127.0.0.1:1", "--db", "d", *KEY,
        "--path", str(tmp_path), stdin="k-very-secret\n")
    code, out, _ = run(tmp_path, "check")
    assert code == 0 and "k-very-secret" not in out


def test_changing_an_instance_keeps_its_key_and_lowering_needs_no_approval(tmp_path):
    base = ("add", "acme", "stage", "--url", "https://s.example.com", "--tier", "stage",
            "--db", "auto", "--path", str(tmp_path))
    assert run(tmp_path, *base, "--access", "write", *KEY, "--approved-by", "yes",
               stdin="k-keep-me\n")[0] == 0
    assert run(tmp_path, *base, "--access", "read")[0] == 0
    inst = doc(tmp_path)["projects"]["acme"]["instances"]["stage"]
    assert inst["access"] == "read" and inst["api_key"] == "k-keep-me"


def test_remove_a_project_with_prod_needs_approval(tmp_path):
    run(tmp_path, "add", "acme", "prod", "--url", "https://p.example.com", "--tier", "prod",
        "--db", "p", *KEY, "--path", str(tmp_path), stdin="k\n")
    assert run(tmp_path, "remove", "acme")[0] == 3
    assert run(tmp_path, "remove", "acme", "--approved-by", "yes remove")[0] == 0
    assert doc(tmp_path)["projects"] == {}
