"""The Odoo.sh approval prompt (hooks/pre_odoo_sh_guard.py), run the way Claude Code runs it.

The hook returns `ask` so the user answers; the model cannot supply that answer. Offline:
profiles live in a temp ODOO_SH_HOME, nothing connects anywhere.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "pre_odoo_sh_guard.py"
TOOL = "mcp__plugin_odoo_odoo-sh__sh_"


@pytest.fixture
def home(tmp_path):
    def prof(branch, role, allow):
        return {"project": "acme", "branch": branch, "role": role, "allow": allow,
                "url": "https://acme-%s.odoo.com" % branch}
    doc = {"version": 1, "default": "prod", "profiles": {
        "prod": prof("main", "prod", ["read", "update", "restart", "shell", "odoo_shell"]),
        "prod-ro": prof("main", "prod", ["read"]),
        "stage": prof("staging", "stage", ["read", "update", "shell"]),
    }}
    (tmp_path / "odoo-sh.json").write_text(json.dumps(doc), encoding="utf-8")
    return tmp_path


def run(payload, home, **extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ("ODOO_SH_APPROVAL_PROMPT", "ODOO_SH_FILE", "ODOO_SH_PROJECT_DIR", "CLAUDE_PROJECT_DIR")}
    env.update(ODOO_SH_HOME=str(home), **extra)
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env, timeout=30)
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.decode("utf-8", "replace").strip()
    return json.loads(out)["hookSpecificOutput"] if out else None


def tool(action, **args):
    return {"tool_name": TOOL + action, "tool_input": args, "cwd": str(PLUGIN_ROOT)}


def bash(command, name="Bash"):
    return {"tool_name": name, "tool_input": {"command": command}, "cwd": str(PLUGIN_ROOT)}


def test_fixture_profiles_load(home):
    """Guard against a fixture the config loader rejects (the hook would then stay silent)."""
    sys.path.insert(0, str(PLUGIN_ROOT / "mcp_sh"))
    import shconfig
    old = os.environ.get("ODOO_SH_HOME")
    os.environ["ODOO_SH_HOME"] = str(home)
    try:
        assert set(shconfig.load()["profiles"]) == {"prod", "prod-ro", "stage"}
    finally:
        if old is None:
            os.environ.pop("ODOO_SH_HOME")
        else:
            os.environ["ODOO_SH_HOME"] = old


@pytest.mark.parametrize("action,args,needle", [
    ("update", {"profile": "prod", "modules": "sale,stock"}, "sale,stock"),
    ("restart", {"profile": "prod"}, "restart"),
    ("shell", {"profile": "prod", "command": "rm -rf ~/data/x"}, "rm -rf ~/data/x"),
    ("odoo_shell", {"profile": "prod", "snippet": "env['res.users'].search([])"}, "res.users"),
    ("update", {"modules": "sale"}, "prod"),  # no profile given: the default one is prod
])
def test_production_calls_ask_every_time(home, action, args, needle):
    out = run(tool(action, **args), home, CLAUDE_PROJECT_DIR=str(home))
    assert out["permissionDecision"] == "ask"
    reason = out["permissionDecisionReason"]
    assert "PRODUCTION" in reason and needle in reason and "acme-main.odoo.com" in reason


def test_no_profile_named_asks_when_any_resolution_lands_on_production(home, tmp_path):
    """The server may resolve the profile without the folder this hook sees. A stage profile
    bound to the working folder must not hide that the default profile is production."""
    doc = json.loads((home / "odoo-sh.json").read_text(encoding="utf-8"))
    work = tmp_path / "work"
    work.mkdir()
    doc["profiles"]["stage"]["paths"] = [str(work)]
    (home / "odoo-sh.json").write_text(json.dumps(doc), encoding="utf-8")
    payload = dict(tool("update", modules="sale"), cwd=str(work))
    for extra in ({}, {"CLAUDE_PROJECT_DIR": str(work)}, {"ODOO_SH_PROJECT_DIR": str(work)}):
        out = run(payload, home, **extra)
        assert out["permissionDecision"] == "ask" and "PRODUCTION" in out["permissionDecisionReason"]
    # naming the stage profile is unambiguous, so it stays silent
    assert run(dict(tool("update", profile="stage", modules="sale"), cwd=str(work)), home) is None


def test_an_approval_text_from_the_model_does_not_skip_the_prompt(home):
    out = run(tool("restart", profile="prod", approved_by_user="yes, go ahead"), home)
    assert out["permissionDecision"] == "ask"


def test_long_commands_are_shortened_in_the_prompt(home):
    out = run(tool("shell", profile="prod", command="echo " + "x" * 2000), home)
    assert len(out["permissionDecisionReason"]) < 800


@pytest.mark.parametrize("payload", [
    tool("update", profile="stage", modules="sale"),      # user opted in; not production
    tool("restart", profile="stage"),                     # not allowed: the server refuses
    tool("shell", profile="prod-ro", command="ls"),       # not allowed: the server refuses
    tool("update", profile="nope", modules="sale"),       # unknown profile: the server refuses
    tool("logs", profile="prod"),                         # read tool
    tool("status"),
    {"tool_name": "mcp__plugin_odoo_odoo__odoo_write", "tool_input": {}},
])
def test_silent_when_not_a_production_write(home, payload):
    assert run(payload, home) is None


@pytest.mark.parametrize("command,needle", [
    ("python scripts/mcp/odoo_sh.py allow stage restart --approved-by 'yes'", "restart"),
    ("python3 /x/odoo_sh.py allow prod-ro update shell --approved-by yes", "update, shell"),
    ("cd /tmp && py -3 odoo_sh.py allow stage update shell odoo_shell --approved-by ok", "odoo_shell"),
    ("bash -lc \"python odoo_sh.py allow prod-ro restart --approved-by yes\"", "restart"),
    ("python odoo_sh.py allow ghost update --approved-by yes", "ghost"),
])
def test_widening_allow_asks(home, command, needle):
    out = run(bash(command), home)
    assert out["permissionDecision"] == "ask" and needle in out["permissionDecisionReason"]


def test_widening_allow_asks_from_powershell(home):
    out = run(bash('python "C:\\plugins\\odoo\\scripts\\mcp\\odoo_sh.py" allow prod-ro shell --approved-by "yes"',
                   name="PowerShell"), home)
    assert out["permissionDecision"] == "ask" and "shell" in out["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "python odoo_sh.py allow stage update --approved-by yes",   # already allowed: nothing added
    "python odoo_sh.py allow prod",                             # narrows to read-only
    "python odoo_sh.py list",
    "python odoo_sh.py show prod",
    "python odoo_sh.py run logs --profile prod --grep allow",
    "python odoo_sh.py edit stage --role prod",                 # stricter, not looser
    "python odoo_sh.py add new --role stage --project acme --branch dev",
    "grep -n 'odoo_sh.py allow prod shell' docs/notes.md",
    "echo python odoo_sh.py allow prod-ro shell",
    "git log --grep 'odoo_sh.py allow'",
])
def test_cli_commands_that_do_not_widen_stay_silent(home, command):
    assert run(bash(command), home) is None


def test_downgrading_a_production_role_asks(home):
    out = run(bash("python odoo_sh.py edit prod --role stage"), home)
    assert out["permissionDecision"] == "ask" and "role prod to role stage" in out["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "python -c \"import json; open('/home/j/.odoo-mcp/odoo-sh.json','w').write('{}')\"",
    "echo '{}' > ~/.odoo-mcp/odoo-sh.json",
    "sed -i 's/prod/stage/' ~/.odoo-mcp/odoo-sh.json",
    "cp /tmp/x.json ~/.odoo-mcp/odoo-sh.json",
])
def test_direct_writes_to_the_profile_file_ask(home, command):
    out = run(bash(command), home)
    assert out["permissionDecision"] == "ask" and "odoo-sh.json" in out["permissionDecisionReason"]


@pytest.mark.parametrize("command", [
    "cat ~/.odoo-mcp/odoo-sh.json",
    "ls -la ~/.odoo-mcp/odoo-sh.json && wc -c ~/.odoo-mcp/odoo-sh.json",
    "cat docs/odoo-sh.json",
])
def test_reading_the_profile_file_stays_silent(home, command):
    assert run(bash(command), home) is None


def test_switch_off_is_the_users_environment_only(home):
    assert run(tool("restart", profile="prod"), home, ODOO_SH_APPROVAL_PROMPT="off") is None


def test_bad_input_fails_open(home):
    env = dict(os.environ, ODOO_SH_HOME=str(home))
    proc = subprocess.run([sys.executable, str(HOOK)], input=b"not json", capture_output=True, env=env, timeout=30)
    assert proc.returncode == 0 and proc.stdout.strip() == b""


def test_hook_is_registered_for_tools_and_both_shells():
    data = json.loads((PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    groups = [g for g in data["hooks"]["PreToolUse"] if "pre_odoo_sh_guard.py" in json.dumps(g)]
    matchers = {g["matcher"] for g in groups}
    assert {"Bash", "PowerShell"} <= matchers
    import re
    mcp = next(m for m in matchers if m.startswith("mcp__"))
    for action in ("update", "restart", "shell", "odoo_shell"):
        assert re.fullmatch(mcp, TOOL + action)
    assert not re.fullmatch(mcp, TOOL + "logs")
