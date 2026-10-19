"""Behaviour of the registered hooks, run as subprocesses the way Claude Code runs them.

Covers the volume / destructive-command guard (ask, Odoo-scoped, no override token,
matches executed commands only), the restart advisory, the inline-script check (Odoo
modules only, data blocks allowed, opt-out), the core-file / grant-file guard and the
SessionStart note. Offline: every test works in a temp directory.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOKS = PLUGIN_ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

import _odoo_shell as sh  # noqa: E402

ODOO_COMPOSE = "services:\n  web:\n    image: odoo:19\n  db:\n    image: postgres:16\n"
OTHER_COMPOSE = "services:\n  web:\n    image: nginx\n  db:\n    image: postgres:16\n"


def _env(**extra):
    env = dict(os.environ)
    for var in ("ODOO_DESTRUCTIVE_GUARD", "ODOO_INLINE_SCRIPT_CHECK", "CLAUDE_PROJECT_DIR",
                "CLAUDE_PROJECT_ROOT", "CLAUDE_PLUGIN_ROOT"):
        env.pop(var, None)
    env.update(extra)
    return env


def run_hook(script, payload, cwd=None, **env):
    proc = subprocess.run([sys.executable, str(HOOKS / script)],
                          input=json.dumps(payload).encode("utf-8"), capture_output=True,
                          env=_env(**env), timeout=30, cwd=str(cwd or PLUGIN_ROOT))
    out = proc.stdout.decode("utf-8", "replace").strip()
    return proc.returncode, (json.loads(out)["hookSpecificOutput"] if out else None)


def bash(command, cwd):
    return {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}


@pytest.fixture
def odoo_stack(tmp_path):
    d = tmp_path / "odoo_stack"
    d.mkdir()
    (d / "docker-compose.yml").write_text(ODOO_COMPOSE, encoding="utf-8")
    return d


@pytest.fixture
def other_stack(tmp_path):
    d = tmp_path / "other_stack"
    d.mkdir()
    (d / "docker-compose.yml").write_text(OTHER_COMPOSE, encoding="utf-8")
    return d


# ------------------------------------------------------------ shell parsing


def test_commands_split_respects_quotes_and_comments():
    cmds = sh.commands('echo "docker volume rm x; rm -rf /" && git commit -m "dropdb" # docker volume prune')
    assert [c[0] for c in cmds] == ["echo", "git"]


def test_commands_strip_env_and_sudo_and_recurse_into_bash_c():
    cmds = sh.commands("FOO=1 sudo -E docker volume rm a | cat; bash -c 'docker compose down -v'")
    assert cmds[0][:3] == ["docker", "volume", "rm"]
    assert cmds[2][:3] == ["docker", "compose", "down"]


def test_python_script_detection():
    assert sh.python_script(["python3", "-u", "/x/db_manager.py", "drop"]) == ("db_manager.py", ["drop"])
    assert sh.python_script(["python", "-m", "odoo"]) is None
    assert sh.python_script(["node", "db_manager.py"]) is None


def test_is_odoo_project(tmp_path, odoo_stack):
    assert sh.is_odoo_project(str(odoo_stack))
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "docker-compose.yml").write_text(OTHER_COMPOSE, encoding="utf-8")
    assert not sh.is_odoo_project(str(plain), max_up=0)
    mod = tmp_path / "addons" / "my_mod" / "models"
    mod.mkdir(parents=True)
    (tmp_path / "addons" / "my_mod" / "__manifest__.py").write_text("{}", encoding="utf-8")
    assert sh.is_odoo_project(str(mod))


# ------------------------------------------------------------ volume guard


@pytest.mark.parametrize("command", [
    "docker compose down -v",
    "docker compose -f docker-compose.yml down --volumes",
    "docker-compose down -v --remove-orphans",
    "docker volume rm stack_db stack_filestore",
    "docker volume prune -f",
    "docker system prune -a --volumes",
    "cd . && sudo docker compose down -v",
])
def test_volume_guard_asks_on_an_odoo_stack(odoo_stack, command):
    code, out = run_hook("pre_odoo_volume_guard.py", bash(command, odoo_stack), cwd=odoo_stack)
    assert code == 0
    assert out and out["permissionDecision"] == "ask", command
    reason = out["permissionDecisionReason"]
    # No override token the model could append to the command.
    for token in ("ALLOW_VOLUME_DELETE", "--i-understand-data-loss", "re-run with"):
        assert token not in reason


@pytest.mark.parametrize("command", [
    "docker compose down",
    "docker compose down -v",          # not an Odoo stack
    "docker volume prune -f",          # not an Odoo stack
    "docker volume ls",
    'echo "docker volume rm odoo_db"',
    "grep -rn 'docker compose down -v' docs/",
    'git commit -m "guard docker volume rm odoo_db"',
])
def test_volume_guard_is_silent_elsewhere(other_stack, command):
    code, out = run_hook("pre_odoo_volume_guard.py", bash(command, other_stack), cwd=other_stack)
    assert (code, out) == (0, None), command


def test_volume_named_odoo_asks_anywhere(other_stack):
    code, out = run_hook("pre_odoo_volume_guard.py", bash("docker volume rm odoo19_db", other_stack),
                         cwd=other_stack)
    assert out["permissionDecision"] == "ask"


def test_compose_file_flag_decides_scope(other_stack):
    (other_stack / "odoo.yml").write_text(ODOO_COMPOSE, encoding="utf-8")
    code, out = run_hook("pre_odoo_volume_guard.py",
                         bash("docker compose -f odoo.yml down -v", other_stack), cwd=other_stack)
    assert out["permissionDecision"] == "ask"


def test_old_override_token_no_longer_bypasses(odoo_stack):
    code, out = run_hook("pre_odoo_volume_guard.py",
                         bash("docker volume rm stack_db  # ALLOW_VOLUME_DELETE", odoo_stack),
                         cwd=odoo_stack)
    assert out["permissionDecision"] == "ask"


def test_env_switch_disables_guard(odoo_stack):
    code, out = run_hook("pre_odoo_volume_guard.py", bash("docker volume rm stack_db", odoo_stack),
                         cwd=odoo_stack, ODOO_DESTRUCTIVE_GUARD="off")
    assert (code, out) == (0, None)


@pytest.mark.parametrize("command", [
    'python "/p/scripts/service/db_manager.py" drop --db old --yes',
    "python3 db_manager.py reset-admin --db prod --password-stdin",
    "py -3 db_manager.py restore --file a.dump --db live --no-create",
    "python server_manager.py stop --all --yes",
])
def test_destructive_plugin_scripts_ask(tmp_path, command):
    code, out = run_hook("pre_odoo_volume_guard.py", bash(command, tmp_path), cwd=tmp_path)
    assert out and out["permissionDecision"] == "ask", command


@pytest.mark.parametrize("command", [
    "python db_manager.py list",
    "python db_manager.py backup --db x",
    "python db_manager.py restore --file a.dump --db fresh",
    "python server_manager.py stop --all",
    "python server_manager.py stop --port 8069",
])
def test_safe_plugin_scripts_pass(tmp_path, command):
    assert run_hook("pre_odoo_volume_guard.py", bash(command, tmp_path), cwd=tmp_path) == (0, None)


def test_dropdb_asks_only_in_an_odoo_project(odoo_stack, other_stack):
    _, out = run_hook("pre_odoo_volume_guard.py", bash("dropdb -h localhost mydb", odoo_stack),
                      cwd=odoo_stack)
    assert out["permissionDecision"] == "ask"
    assert run_hook("pre_odoo_volume_guard.py", bash("dropdb mydb", other_stack),
                    cwd=other_stack) == (0, None)


def test_volume_guard_fails_open_on_bad_input():
    proc = subprocess.run([sys.executable, str(HOOKS / "pre_odoo_volume_guard.py")],
                          input=b"not json", capture_output=True, env=_env(), timeout=30)
    assert proc.returncode == 0 and not proc.stdout


# ------------------------------------------------------------ restart advisory


@pytest.mark.parametrize("command,needle", [
    ("curl --retry 50 --retry-connrefused http://localhost:8069/web/login", "retry-storm"),
    ("pkill -f odoo-bin && ./odoo-bin -c conf/x.conf", "self-matches"),
    ("pkill -f odoo; python -m odoo -c x.conf", "self-matches"),
])
def test_restart_guard_advises(tmp_path, command, needle):
    code, out = run_hook("pre_odoo_restart_guard.py", bash(command, tmp_path), cwd=tmp_path)
    assert code == 0 and needle in out["additionalContext"]
    assert "permissionDecision" not in out


def test_template_clone_advice_only_in_odoo_project(odoo_stack, other_stack):
    cmd = 'psql -c "CREATE DATABASE copy TEMPLATE live"'
    _, out = run_hook("pre_odoo_restart_guard.py", bash(cmd, odoo_stack), cwd=odoo_stack)
    assert "filestore" in out["additionalContext"]
    assert run_hook("pre_odoo_restart_guard.py", bash(cmd, other_stack), cwd=other_stack) == (0, None)
    _, out = run_hook("pre_odoo_restart_guard.py", bash("createdb -T live copy", odoo_stack),
                      cwd=odoo_stack)
    assert "filestore" in out["additionalContext"]


@pytest.mark.parametrize("command", [
    "curl --retry 5 --retry-connrefused --max-time 30 http://localhost:8069/web",
    "curl -s http://localhost:8069/web",
    "pkill -f odoo-bin",
    'echo "pkill -f odoo && odoo-bin"',
    "grep -n 'curl --retry-connrefused http://localhost:8069' notes.md",
])
def test_restart_guard_silent_on_safe_forms(tmp_path, command):
    assert run_hook("pre_odoo_restart_guard.py", bash(command, tmp_path), cwd=tmp_path) == (0, None)


# ------------------------------------------------------------ inline script check


def _module(tmp_path):
    mod = tmp_path / "my_module"
    (mod / "views").mkdir(parents=True)
    (mod / "__manifest__.py").write_text("{'name': 'My'}\n", encoding="utf-8")
    return mod / "views" / "templates.xml"


def _write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": content}}


def test_inline_script_denied_in_odoo_module(tmp_path):
    code, out = run_hook("frontend/pre_write_check.py",
                         _write(_module(tmp_path), "<t><script>var a = 1;</script></t>"))
    assert code == 0 and out["permissionDecision"] == "deny"


def test_inline_script_in_edit_new_string(tmp_path):
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(_module(tmp_path)),
                                                   "old_string": "x", "new_string": "<script>go()</script>"}}
    assert run_hook("frontend/pre_write_check.py", payload)[1]["permissionDecision"] == "deny"


@pytest.mark.parametrize("content", [
    '<t><script type="application/ld+json">{"@type": "Organization"}</script></t>',
    "<t><script type='text/template'><div/></script></t>",
    '<t><script type="text/x-template">hello</script></t>',
    '<t><script src="/my_module/static/src/js/a.js"></script></t>',
    "<t><script>   </script></t>",
])
def test_data_blocks_and_src_tags_pass(tmp_path, content):
    assert run_hook("frontend/pre_write_check.py", _write(_module(tmp_path), content)) == (0, None)


def test_xml_outside_an_odoo_module_passes(tmp_path):
    path = tmp_path / "site" / "page.xml"
    path.parent.mkdir()
    assert run_hook("frontend/pre_write_check.py",
                    _write(path, "<x><script>alert(1)</script></x>")) == (0, None)


def test_inline_script_check_opt_out_and_warn(tmp_path):
    payload = _write(_module(tmp_path), "<t><script>alert(1)</script></t>")
    assert run_hook("frontend/pre_write_check.py", payload, ODOO_INLINE_SCRIPT_CHECK="off") == (0, None)
    _, out = run_hook("frontend/pre_write_check.py", payload, ODOO_INLINE_SCRIPT_CHECK="warn")
    assert "permissionDecision" not in out and "Inline JavaScript" in out["additionalContext"]


# ------------------------------------------------------------ core / grant guard


@pytest.mark.parametrize("path", [
    "/opt/odoo19/odoo/addons/sale/models/sale.py",
    "/usr/lib/python3/dist-packages/odoo/models.py",
    "/venv/lib/python3.12/site-packages/odoo/addons/web/x.js",
])
def test_core_files_denied(path):
    _, out = run_hook("upgrade/guard_core_odoo.py", _write(path, "x"))
    assert out["permissionDecision"] == "deny"


@pytest.mark.parametrize("path", [
    "/home/jane/.odoo-mcp/grants/prod.json",
    "C:\\Users\\jane\\.odoo-mcp\\grant.key",
])
def test_grant_files_denied(path):
    _, out = run_hook("upgrade/guard_core_odoo.py", _write(path, "{}"))
    assert out["permissionDecision"] == "deny" and "odoo_mcp_ctl.py" in out["permissionDecisionReason"]


def test_custom_module_write_passes():
    assert run_hook("upgrade/guard_core_odoo.py",
                    _write("/work/projects/acme/my_module/models/a.py", "x")) == (0, None)


# ------------------------------------------------------------ session start


def test_session_start_silent_outside_odoo(tmp_path):
    payload = {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}
    assert run_hook("frontend/session_start.py", payload, cwd=tmp_path) == (0, None)


def test_session_start_reports_versions(tmp_path):
    (tmp_path / "odoo17").mkdir()
    _, out = run_hook("frontend/session_start.py",
                      {"hook_event_name": "SessionStart", "cwd": str(tmp_path)}, cwd=tmp_path)
    assert out["hookEventName"] == "SessionStart"
    assert "Odoo 17" in out["additionalContext"] and "Owl 1.x" in out["additionalContext"]
