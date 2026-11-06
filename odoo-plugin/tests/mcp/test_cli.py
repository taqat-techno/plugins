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


def run(home, *args, stdin="", cwd=None, devnull=False):
    """devnull=True runs like Claude's shell tools: stdin on NUL, which Windows reports
    as a terminal."""
    io = {"stdin": subprocess.DEVNULL} if devnull else {"input": stdin}
    p = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True,
                       encoding="utf-8", timeout=60, cwd=cwd,
                       env={**os.environ, "ODOO_MCP_HOME": str(home), "PYTHONIOENCODING": "utf-8"},
                       **io)
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


def test_moving_an_instance_to_another_host_never_carries_its_key(tmp_path):
    base = ("add", "acme", "prod", "--tier", "prod", "--db", "p", "--path", str(tmp_path))
    assert run(tmp_path, *base, "--url", "https://p.example.com", *KEY, stdin="k-prod-secret\n")[0] == 0
    moved = (*base, "--url", "https://elsewhere.example.com")
    code, _, err = run(tmp_path, *moved)
    assert code == 2 and "key" in err
    code, _, err = run(tmp_path, *moved, "--key-stdin", stdin="k-new\n")
    assert code == 3 and "elsewhere" in err
    assert run(tmp_path, *moved, "--key-stdin", "--approved-by", "yes move it", stdin="k-new\n")[0] == 0
    assert doc(tmp_path)["projects"]["acme"]["instances"]["prod"]["api_key"] == "k-new"


def test_migrate_plan_from_the_cli_is_keyless_and_refuses_a_v2_file(tmp_path):
    (tmp_path / "profiles.json").write_text(json.dumps({"profiles": {"acme-stage": {
        "url": "https://acme-stage.odoo.com", "db": "acme-stage-1", "username": "a",
        "api_key": "K-SECRET"}}}), encoding="utf-8")
    code, out, err = run(tmp_path, "migrate", "--plan")
    assert code == 0, err
    assert "acme" in json.loads(out)["projects"] and "K-SECRET" not in out
    (tmp_path / "profiles.json").write_text('{"version": 2, "projects": {}}', encoding="utf-8")
    assert run(tmp_path, "migrate", "--plan")[0] == 2


def test_widening_from_a_tool_shell_needs_a_yes_and_never_waits_for_a_key(tmp_path):
    run(tmp_path, "add", "acme", "stage", "--url", "https://s.example.com", "--tier", "stage",
        "--db", "auto", "--access", "read", *KEY, "--path", str(tmp_path), stdin="k\n")
    code, _, err = run(tmp_path, "add", "acme", "stage", "--access", "write", devnull=True)
    assert code == 3 and "--approved-by" in err
    assert doc(tmp_path)["projects"]["acme"]["instances"]["stage"]["access"] == "read"
    code, _, err = run(tmp_path, "add", "acme", "stage", "--access", "write",
                       "--approved-by", "yes widen", devnull=True)
    assert code == 0, err


def test_removing_a_project_with_prod_from_a_tool_shell_needs_a_yes(tmp_path):
    run(tmp_path, "add", "acme", "prod", "--url", "https://p.example.com", "--tier", "prod",
        "--db", "p", *KEY, "--path", str(tmp_path), stdin="k\n")
    assert run(tmp_path, "remove", "acme", devnull=True)[0] == 3


def test_add_from_a_worktree_binds_the_main_checkout(tmp_path):
    main = tmp_path / "Nafla-19"
    admin = main / ".git" / "worktrees" / "w"
    admin.mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: %s" % admin.as_posix())
    (admin / "gitdir").write_text((wt / ".git").as_posix())
    home = tmp_path / "home"
    code, _, err = run(home, "add", "nafla", "local", "--url", "http://127.0.0.1:1", "--db", "d",
                       *KEY, stdin="k\n", cwd=str(wt))
    assert code == 0, err
    assert doc(home)["projects"]["nafla"]["paths"] == [os.path.abspath(str(main))]


def test_servers_json_from_3x_is_planned_for_migration(tmp_path):
    (tmp_path / "servers.json").write_text(json.dumps({"profiles": {"acme-stage": {
        "url": "https://acme-stage.odoo.com", "db": "acme-stage-1", "username": "a",
        "api_key": "K"}}}), encoding="utf-8")
    code, out, err = run(tmp_path, "migrate", "--plan")
    assert code == 0, err
    assert "acme" in json.loads(out)["projects"]


def test_local_refuses_a_remote_url(tmp_path):
    code, _, err = run(tmp_path, "local", "--url", "https://x.example.com", "--dry-run")
    assert code == 2 and "loopback" in err


def test_project_for_unbound_worktree_uses_main_checkout(tmp_path):
    sys.path.insert(0, str(CLI.parent))
    sys.path.insert(0, str(CLI.parents[2] / "mcp"))
    import odoo_local

    main = tmp_path / "Nafla-19"
    admin = main / ".git" / "worktrees" / "w"
    admin.mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: %s" % admin.as_posix())
    (admin / "gitdir").write_text((wt / ".git").as_posix())
    name, paths, created = odoo_local.project_for(wt, None)
    assert (name, created) == ("Nafla-19", True) and paths == [str(main)]


def test_remove_a_project_with_prod_needs_approval(tmp_path):
    run(tmp_path, "add", "acme", "prod", "--url", "https://p.example.com", "--tier", "prod",
        "--db", "p", *KEY, "--path", str(tmp_path), stdin="k\n")
    assert run(tmp_path, "remove", "acme")[0] == 3
    assert run(tmp_path, "remove", "acme", "--approved-by", "yes remove")[0] == 0
    assert doc(tmp_path)["projects"] == {}
