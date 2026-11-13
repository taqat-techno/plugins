#!/usr/bin/env python3
"""env-doctor mechanic: a light background watcher for the machine a local service runs on.

The agent is the driver; this is the mechanic. It never talks to the user and never
changes anything. It samples cheap numbers the OS already keeps, matches them against
data/mechanic_rules.json, and appends findings to a file. The hooks in mechanic_hook.py
hand each new finding to the session that started a service, and that agent decides
whether to fix it (within what it started itself) or to ask the user.

Single owner of: the state folder layout, the sampler, rule evaluation, the daemon loop
and session bookkeeping. Rules and wording live in the data file; the authority policy
is explained in skills/machine-mechanic/SKILL.md.

Cost: one process per machine (a lock keeps it single), below-normal priority, one
sample every ~45 s. A sample is two Win32 calls (memory, CPU times) and one disk-usage
call; WSL memory (`tasklist`) every 4th sample; the WSL disk-image check once an hour,
and only when WSL is already running. It exits by itself 30 minutes after the last
session activity, after 12 hours, or when silenced.

Run as `python mechanic.py watch` (the hooks start it). Stdlib only; every probe fails
soft and returns None, and a rule whose metric is None never fires.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import host_pressure as hp  # noqa: E402

GIB = 1024 ** 3
OFF = ("0", "false", "off", "no")
RULES_PATH = os.path.join(os.path.dirname(HERE), "data", "mechanic_rules.json")
IDLE_EXIT = 30 * 60      # no session activity for this long -> the daemon exits
MAX_LIFE = 12 * 3600
FRESH = 20 * 60          # a finding older than this is never delivered
KEEP_FINDINGS = 200


def interval(env=os.environ) -> float:
    try:
        return max(1.0, float(env.get("ENV_DOCTOR_MECHANIC_INTERVAL", "45")))
    except ValueError:
        return 45.0


def silenced(env=os.environ) -> bool:
    return any(str(env.get(k, "")).strip().lower() in OFF
               for k in ("ENV_DOCTOR_MECHANIC", "CLAUDE_PLUGIN_OPTION_MECHANIC"))


# --------------------------------------------------------------------------- state files

def state_dir(env=os.environ) -> str:
    base = env.get("CLAUDE_PLUGIN_DATA") or os.path.join(os.path.expanduser("~"), ".claude", "env-doctor")
    return os.path.join(base, "mechanic")


def _p(sd, *parts):
    return os.path.join(sd, *parts)


def _age(path, now=None):
    try:
        return (now or time.time()) - os.path.getmtime(path)
    except OSError:
        return None


def _touch(path, text=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if text is None and os.path.exists(path):
        os.utime(path, None)
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text or "")


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def safe_id(session_id) -> str | None:
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    return re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:80]


def register(sd, sid, now=None):
    """Mark this session as a driver: it started a service and gets findings from now on."""
    path = _p(sd, "sessions", sid + ".json")
    if not os.path.exists(path):
        _touch(path, json.dumps({"registered": now or time.time()}))
    else:
        os.utime(path, None)


def registered_at(sd, sid):
    try:
        with open(_p(sd, "sessions", sid + ".json"), encoding="utf-8") as fh:
            return float(json.load(fh)["registered"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def seen(sd, sid):
    path = _p(sd, "sessions", sid + ".json")
    if os.path.exists(path):
        os.utime(path, None)


def live_sessions(sd, now=None, idle=IDLE_EXIT) -> int:
    folder = _p(sd, "sessions")
    try:
        names = [n for n in os.listdir(folder) if n.endswith(".json")]
    except OSError:
        return 0
    return sum(1 for n in names if (_age(os.path.join(folder, n), now) or idle + 1) <= idle)


def armed(sd, sid, now=None) -> bool:
    """A listener for this session is alive (its heartbeat is fresh)."""
    age = _age(_p(sd, "sessions", sid + ".listen"), now)
    return age is not None and age < 40


def claim(sd, sid, finding_id) -> bool:
    """Deliver each finding once per session, whichever hook gets there first."""
    folder = _p(sd, "sessions", sid + ".d")
    try:
        os.makedirs(folder, exist_ok=True)
        os.close(os.open(os.path.join(folder, finding_id), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return True
    except FileExistsError:
        return False
    except OSError:
        return False


def read_findings(sd):
    out = []
    try:
        with open(_p(sd, "findings.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def pending(sd, sid, now=None):
    """Findings this session has not had yet, newer than its registration and FRESH."""
    now = now or time.time()
    since = max(registered_at(sd, sid) or now, now - FRESH)
    done = set()
    try:
        done = set(os.listdir(_p(sd, "sessions", sid + ".d")))
    except OSError:
        pass
    return [f for f in read_findings(sd)
            if isinstance(f, dict) and f.get("ts", 0) >= since and f.get("id") not in done]


def message(findings) -> str:
    parts = []
    for f in findings[:3]:
        who = ("You may fix this yourself, limited to services and jobs you started; ask the user before touching "
               "anything else." if f.get("authority") == "agent"
               else "Tell the user and ask before acting.")
        parts.append(f"{f.get('text', '')} {who}")
    return ("[env-doctor mechanic] " + " | ".join(parts)
            + " (Background machine watcher; see the machine-mechanic skill. Silence: ENV_DOCTOR_MECHANIC=off.)")


# --------------------------------------------------------------------------- rules

def load_rules(path=RULES_PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            return [r for r in json.load(fh).get("rules", []) if isinstance(r, dict) and r.get("id")]
    except (OSError, ValueError, AttributeError):
        return []


def _cmp(value, op, ref) -> bool:
    if value is None:
        return False
    try:
        if op == ">=":
            return value >= ref
        if op == ">":
            return value > ref
        if op == "<=":
            return value <= ref
        if op == "<":
            return value < ref
        if op == "==":
            return value == ref
    except TypeError:
        return False
    return False


def _render(rule, metrics) -> str:
    try:
        text = rule.get("text", "").format(**metrics)
    except (KeyError, ValueError, TypeError, IndexError):
        text = rule.get("text", "")
    fix = rule.get("fix", "")
    return f"{text} Suggested: {fix}" if fix else text


def evaluate(rules, metrics, streaks, last_fired, now):
    """Return the findings this sample produces; updates streaks / last_fired in place."""
    out = []
    for rule in rules:
        rid = rule["id"]
        try:
            ok = all(_cmp(metrics.get(m), op, v) for m, op, v in rule.get("when", []))
        except (TypeError, ValueError):
            ok = False
        streaks[rid] = streaks.get(rid, 0) + 1 if ok else 0
        if not ok or streaks[rid] < int(rule.get("sustain", 1)):
            continue
        if rid in last_fired and now - last_fired[rid] < float(rule.get("cooldown_min", 30)) * 60:
            continue
        last_fired[rid] = now
        out.append({"id": f"{rid}-{int(now)}", "rule": rid, "ts": now,
                    "authority": rule.get("authority", "user"), "text": _render(rule, metrics)})
    return out


# --------------------------------------------------------------------------- sampler

def _win_memory():
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(st)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return st.ullTotalPhys, st.ullAvailPhys


def _linux_memory():
    vals = {}
    with open("/proc/meminfo", encoding="ascii") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            vals[key] = int(rest.split()[0]) * 1024
    return vals["MemTotal"], vals.get("MemAvailable", vals.get("MemFree", 0))


def _win_cpu_times():
    import ctypes
    idle, kernel, user = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
    if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        return None
    return idle.value, kernel.value + user.value  # kernel time includes idle time


def _linux_cpu_times():
    with open("/proc/stat", encoding="ascii") as fh:
        nums = [int(x) for x in fh.readline().split()[1:]]
    idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
    return idle, sum(nums)


def _wsl_memory_bytes():
    """Working set of the WSL VM process (vmmemWSL / vmmem), via tasklist. Windows only."""
    try:
        proc = subprocess.run(["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq vmmem*"],
                              capture_output=True, timeout=5, stdin=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return None
    total = 0
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        cells = [c.strip('"') for c in line.split('","')]
        if len(cells) >= 5 and cells[0].lower().startswith("vmmem"):
            digits = re.sub(r"\D", "", cells[4])
            total += int(digits) * 1024 if digits else 0
    return total or None


def _wsl_reclaim_setting():
    path = os.path.join(os.path.expanduser("~"), ".wslconfig")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            m = re.search(r"^\s*autoMemoryReclaim\s*=\s*(\w+)", fh.read(), re.M | re.I)
    except OSError:
        return "not set"
    return m.group(1) if m else "not set"


class Sampler:
    def __init__(self, env=os.environ):
        self.env = env
        self.tick = 0
        self.prev_cpu = None
        self.slow = {}

    def _cpu_pct(self):
        times = _win_cpu_times() if hp.is_windows() else _linux_cpu_times()
        if not times:
            return None
        prev, self.prev_cpu = self.prev_cpu, times
        if not prev:
            return None
        d_idle, d_total = times[0] - prev[0], times[1] - prev[1]
        return 100.0 * (d_total - d_idle) / d_total if d_total > 0 else None

    def sample(self):
        fake = self.env.get("ENV_DOCTOR_MECHANIC_FAKE")
        if fake:  # tests and dry runs: metrics come from a JSON file, re-read every sample
            try:
                with open(fake, encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError):
                return {}
        self.tick += 1
        m = {}
        for name, probe in (("mem", self._mem), ("cpu", self._cpu), ("disk", self._disk)):
            try:
                m.update(probe())
            except Exception:
                continue
        if hp.is_windows():
            try:
                if self.tick % 4 == 1:
                    self.slow["wsl_mem"] = _wsl_memory_bytes()
                    self.slow["wsl_reclaim"] = _wsl_reclaim_setting()
                if self.tick % 80 == 1:
                    self.slow["vhdx_slack_gib"] = self._vhdx_slack()
            except Exception:
                pass
            wsl_mem, total = self.slow.get("wsl_mem"), m.get("mem_total_gib")
            if wsl_mem and total:
                m["wsl_mem_gib"] = wsl_mem / GIB
                m["wsl_mem_pct"] = 100.0 * (wsl_mem / GIB) / total
            m["wsl_reclaim"] = self.slow.get("wsl_reclaim", "not set")
            m["vhdx_slack_gib"] = self.slow.get("vhdx_slack_gib")
        return m

    def _mem(self):
        res = _win_memory() if hp.is_windows() else _linux_memory()
        if not res or not res[0]:
            return {}
        total, avail = res
        return {"mem_total_gib": total / GIB, "mem_avail_gib": avail / GIB,
                "mem_used_pct": 100.0 * (total - avail) / total}

    def _cpu(self):
        pct = self._cpu_pct()
        return {"cpu_pct": pct} if pct is not None else {}

    def _disk(self):
        usage = hp.drive_usage()
        return {"disk_free_gib": usage[0] / GIB} if usage else {}

    @staticmethod
    def _vhdx_slack():
        running = hp.running_distros()
        if not running:
            return None
        worst = None
        for name, vhdx in hp.wsl_distros():
            if not vhdx or name not in running:
                continue
            size, used = hp.file_size(vhdx), hp.wsl_used_bytes(name, running=running)
            if hp.vhdx_bloat(size, used):
                slack = (size - used) / GIB
                worst = max(worst or 0, slack)
        return worst


# --------------------------------------------------------------------------- daemon

def daemon_alive(sd, now=None, env=os.environ) -> bool:
    age = _age(_p(sd, "daemon.beat"), now)
    return age is not None and age < 3 * interval(env) + 10


def ensure_daemon(env=os.environ) -> bool:
    """Start the watcher unless one is already beating. Returns True when one runs or was started."""
    sd = state_dir(env)
    if daemon_alive(sd, env=env):
        return True
    lock = _p(sd, "spawn.lock")
    os.makedirs(sd, exist_ok=True)
    if (_age(lock) or 999) < 30:
        return True  # another hook is starting it right now
    _touch(lock, str(os.getpid()))
    _touch(_p(sd, "active"), "")
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
              "close_fds": True, "env": dict(env), "cwd": sd}
    args = [sys.executable, os.path.abspath(__file__), "watch"]
    if os.name == "nt":
        base = 0x00004000 | 0x00000200 | 0x08000000  # BELOW_NORMAL, NEW_PROCESS_GROUP, NO_WINDOW
        for flags in (base | 0x01000000, base):      # try to leave Claude Code's job object first
            try:
                subprocess.Popen(args, creationflags=flags, **kwargs)
                return True
            except OSError:
                continue
        return False
    try:
        subprocess.Popen(args, start_new_session=True, **kwargs)
        return True
    except OSError:
        return False


def _append(sd, findings):
    if not findings:
        return
    path = _p(sd, "findings.jsonl")
    lines = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()[-KEEP_FINDINGS:]
    except OSError:
        pass
    lines += [json.dumps(f, ensure_ascii=True) + "\n" for f in findings]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(lines)
    os.replace(tmp, path)


def watch(env=os.environ, max_ticks=None) -> int:
    sd = state_dir(env)
    os.makedirs(sd, exist_ok=True)
    if os.name != "nt":
        try:
            os.nice(10)
        except OSError:
            pass
    rules = load_rules()
    sampler = Sampler(env)
    streaks, last_fired = {}, {}
    start = time.time()
    _touch(_p(sd, "active"), "")
    _touch(_p(sd, "daemon.beat"), str(os.getpid()))
    _rm(_p(sd, "spawn.lock"))
    ticks = 0
    try:
        while True:
            now = time.time()
            if silenced(env) or now - start > MAX_LIFE or not live_sessions(sd, now):
                break
            metrics = sampler.sample()
            _append(sd, evaluate(rules, metrics, streaks, last_fired, now))
            _touch(_p(sd, "metrics.json"), json.dumps({"ts": now, **metrics}, default=str))
            _touch(_p(sd, "daemon.beat"), str(os.getpid()))
            ticks += 1
            if max_ticks and ticks >= max_ticks:
                break
            time.sleep(interval(env))
    finally:
        _rm(_p(sd, "daemon.beat"))
        _rm(_p(sd, "active"))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "watch":
        try:
            sys.exit(watch())
        except Exception:
            sys.exit(0)
    print("usage: mechanic.py watch")
