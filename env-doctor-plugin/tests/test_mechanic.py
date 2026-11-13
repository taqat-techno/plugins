"""Offline tests for the env-doctor mechanic (hooks/mechanic.py, hooks/mechanic_hook.py).

Metrics come from a fake JSON file (ENV_DOCTOR_MECHANIC_FAKE) and state goes to a temp
CLAUDE_PLUGIN_DATA, so nothing here reads the real machine or the developer's state.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(HOOKS / "_vendor"))
import mechanic  # noqa: E402
import mechanic_hook  # noqa: E402

RULES = mechanic.load_rules()


def by_id(rid):
    return next(r for r in RULES if r["id"] == rid)


def test_rules_file_is_well_formed():
    assert RULES, "no rules loaded"
    for r in RULES:
        assert r["authority"] in ("agent", "user"), r["id"]
        assert r["when"] and all(len(c) == 3 for c in r["when"]), r["id"]
        assert r.get("text") and r.get("fix"), r["id"]


def test_rule_needs_sustain_then_respects_cooldown():
    rule = by_id("memory-high")
    streaks, fired = {}, {}
    hot = {"mem_used_pct": 95.0, "mem_avail_gib": 0.8}
    assert mechanic.evaluate([rule], hot, streaks, fired, 1000) == []
    assert mechanic.evaluate([rule], hot, streaks, fired, 1045) == []
    out = mechanic.evaluate([rule], hot, streaks, fired, 1090)
    assert len(out) == 1 and out[0]["authority"] == "agent"
    assert "95% used" in out[0]["text"] and "0.8 GiB free" in out[0]["text"]
    assert mechanic.evaluate([rule], hot, streaks, fired, 1135) == []  # cooldown
    assert len(mechanic.evaluate([rule], hot, streaks, fired, 1090 + 31 * 60)) == 1


def test_a_cool_sample_resets_the_streak():
    rule = by_id("memory-high")
    streaks, fired = {}, {}
    for t, pct in ((0, 95), (45, 95), (90, 50), (135, 95), (180, 95)):
        assert mechanic.evaluate([rule], {"mem_used_pct": pct, "mem_avail_gib": 1}, streaks, fired, t) == []


def test_missing_metric_never_fires():
    assert mechanic.evaluate(RULES, {}, {}, {}, 0) == []
    assert mechanic.evaluate([by_id("wsl-memory-hog")], {"mem_used_pct": 99}, {}, {}, 0) == []


def test_disk_rules_do_not_overlap():
    streaks, fired = {}, {}
    out = mechanic.evaluate([by_id("disk-low"), by_id("disk-critical")], {"disk_free_gib": 2.0}, streaks, fired, 0)
    assert [f["rule"] for f in out] == ["disk-critical"]


def test_message_states_authority():
    msg = mechanic.message([{"text": "A.", "authority": "agent"}, {"text": "B.", "authority": "user"}])
    assert msg.startswith("[env-doctor mechanic]")
    assert "You may fix this yourself" in msg and "ask before acting" in msg


@pytest.mark.parametrize("command,expected", [
    ("cd /x && ./odoo-bin -c odoo.conf", True),
    ("python manage.py runserver 0.0.0.0:8000", True),
    ("npm run dev", True),
    ("docker compose up -d", True),
    ("grep -rn odoo-bin .", False),
    ("cat docs/runserver.md", False),
    ("git log -- odoo-bin", False),
    ("pytest tests", False),
])
def test_starts_service(command, expected):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    assert mechanic_hook.starts_service(payload) is expected


def test_starts_service_odoo_local_tools():
    assert mechanic_hook.starts_service({"tool_name": "mcp__plugin_odoo_odoo-local__local_start"})
    assert not mechanic_hook.starts_service({"tool_name": "mcp__plugin_odoo_odoo-local__local_logs"})


def test_findings_reach_a_registered_session_once(tmp_path):
    sd = str(tmp_path)
    mechanic.register(sd, "s1", now=100)
    mechanic._append(sd, [{"id": "old-1", "ts": 50, "text": "old", "authority": "user"},
                          {"id": "new-1", "ts": 150, "text": "new", "authority": "user"}])
    got = mechanic.pending(sd, "s1", now=200)
    assert [f["id"] for f in got] == ["new-1"]
    assert mechanic.claim(sd, "s1", "new-1") and not mechanic.claim(sd, "s1", "new-1")
    assert mechanic.pending(sd, "s1", now=200) == []
    assert mechanic.registered_at(sd, "other") is None


def _env(tmp_path, metrics, **extra):
    fake = tmp_path / "metrics.json"
    fake.write_text(json.dumps(metrics), encoding="utf-8")
    e = {k: v for k, v in os.environ.items()
         if k not in ("ENV_DOCTOR_MECHANIC", "CLAUDE_PLUGIN_OPTION_MECHANIC", "HOOKLIB_DEBUG")}
    e.update(CLAUDE_PLUGIN_DATA=str(tmp_path / "data"), ENV_DOCTOR_MECHANIC_FAKE=str(fake),
             ENV_DOCTOR_MECHANIC_INTERVAL="1")
    e.update(extra)
    return e


def test_watch_writes_findings_and_cleans_up(tmp_path):
    env = _env(tmp_path, {"disk_free_gib": 2.0})
    sd = mechanic.state_dir(env)
    mechanic.register(sd, "s1")
    mechanic.watch(env, max_ticks=1)
    found = mechanic.read_findings(sd)
    assert [f["rule"] for f in found] == ["disk-critical"]
    assert not os.path.exists(os.path.join(sd, "active")), "marker left behind"
    assert not os.path.exists(os.path.join(sd, "daemon.beat"))


def test_watch_exits_without_live_sessions(tmp_path):
    env = _env(tmp_path, {"disk_free_gib": 2.0})
    mechanic.watch(env, max_ticks=5)
    assert mechanic.read_findings(mechanic.state_dir(env)) == []


def _hook(mode, payload, env, timeout=60):
    return subprocess.run([sys.executable, str(HOOKS / "mechanic_hook.py"), mode],
                          input=json.dumps(payload).encode(), env=env, capture_output=True, timeout=timeout)


def test_start_hook_wakes_the_agent_end_to_end(tmp_path):
    """Real processes: the start hook spawns the watcher, the watcher finds low disk,
    the hook exits 2 with the note on stderr (what asyncRewake shows the agent)."""
    env = _env(tmp_path, {"disk_free_gib": 2.0})
    payload = {"session_id": "e2e", "tool_use_id": "t1", "tool_name": "Bash",
               "tool_input": {"command": "./odoo-bin -c odoo.conf"}}
    started = time.time()
    res = _hook("start", payload, env)
    assert res.returncode == 2, res.stderr
    note = res.stderr.decode("utf-8")
    assert note.startswith("[env-doctor mechanic]") and "Tell the user" in note
    assert time.time() - started < 30
    # The same finding is not delivered again by the prompt hook.
    out = _hook("prompt", {"session_id": "e2e", "prompt": "hi"}, env)
    assert out.returncode == 0 and out.stdout == b""


def test_prompt_hook_delivers_what_the_listener_missed(tmp_path):
    env = _env(tmp_path, {})
    sd = mechanic.state_dir(env)
    mechanic.register(sd, "s2", now=time.time() - 10)
    mechanic._touch(os.path.join(sd, "daemon.beat"), "1")
    mechanic._append(sd, [{"id": "x-1", "ts": time.time(), "text": "Disk low.", "authority": "user"}])
    out = _hook("prompt", {"session_id": "s2", "prompt": "hi"}, env)
    ctx = json.loads(out.stdout)["hookSpecificOutput"]
    assert ctx["hookEventName"] == "UserPromptSubmit" and "Disk low." in ctx["additionalContext"]


def test_unregistered_session_and_non_service_commands_stay_silent(tmp_path):
    env = _env(tmp_path, {"disk_free_gib": 2.0})
    res = _hook("start", {"session_id": "s3", "tool_use_id": "t", "tool_name": "Bash",
                          "tool_input": {"command": "grep odoo-bin x"}}, env)
    assert res.returncode == 0 and not os.path.exists(os.path.join(mechanic.state_dir(env), "sessions"))
    assert _hook("prompt", {"session_id": "s3", "prompt": "hi"}, env).stdout == b""


def test_silenced_does_nothing(tmp_path):
    env = _env(tmp_path, {"disk_free_gib": 2.0}, ENV_DOCTOR_MECHANIC="off")
    res = _hook("start", {"session_id": "s4", "tool_use_id": "t", "tool_name": "Bash",
                          "tool_input": {"command": "npm run dev"}}, env)
    assert res.returncode == 0 and not os.path.exists(mechanic.state_dir(env))


def test_real_sampler_returns_sane_numbers():
    m = mechanic.Sampler({}).sample()
    if "mem_used_pct" in m:
        assert 0 <= m["mem_used_pct"] <= 100 and m["mem_total_gib"] > 0
    if "disk_free_gib" in m:
        assert m["disk_free_gib"] >= 0
