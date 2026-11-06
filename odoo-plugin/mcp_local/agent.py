#!/usr/bin/env python3
"""odoo-local agent - runs INSIDE the environment that hosts the local Odoo services.

The `odoo-local` MCP server (mcp_local/server.py) runs on the developer's machine
(usually Windows). To act on a WSL distro it pipes a small bash script into
`wsl.exe -d <distro> -- bash -s`; that script runs this file with `python3 -` and passes
the request as base64 JSON in ODOO_LOCAL_ARGS. On a Windows-native or plain Linux
runtime the server runs this file directly. Either way the result is printed as one
line `ODOO_LOCAL_RESULT=<json>`; everything else on stdout/stderr is diagnostics.

Standard library only (python3 >= 3.8). No argument ever reaches a shell: every
subprocess call is an argv list, and every path removal goes through _guarded_rm.

Ops (request key "op"):
  discover, status, start, stop, logs, job_start, job_status,
  db_list, db_drop, cleanup_scan, apply_item, snapshot, relaunch, selftest
"""

from __future__ import annotations

import base64
import configparser
import glob
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

RESULT_MARK = "ODOO_LOCAL_RESULT="
HOME = os.path.expanduser("~")
IS_WINDOWS = os.name == "nt"
LOOPBACK = {"", "localhost", "127.0.0.1", "::1", "false", "none"}
LOG_LEVEL_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ (\d+) (ERROR|CRITICAL) ")
LOG_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\d+) (\w+) ")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "filestore",
             "sessions", "addons", ".cache", "site-packages"}
JOBS_DIR = os.path.join(HOME, ".cache", "odoo-local", "jobs")
SNAP_DIR = os.path.join(HOME, ".cache", "odoo-local", "snapshots")
BACKUP_ROOT = os.path.join(HOME, "odoo-backups")
DAY = 86400.0


class Refused(Exception):
    """A safety rail said no. The message says which rail and why."""


# --------------------------------------------------------------------- helpers

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(argv, env=None, timeout=60, input_bytes=None):
    """Run argv (never a shell string). Returns (rc, stdout, stderr) as text."""
    try:
        p = subprocess.run(argv, input=input_bytes, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, env=env, timeout=timeout)
    except FileNotFoundError:
        return 127, "", "not found: %s" % argv[0]
    except subprocess.TimeoutExpired:
        return 124, "", "timeout after %ss: %s" % (timeout, argv[0])
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def is_loopback(host) -> bool:
    h = str(host or "").strip().lower()
    return h in LOOPBACK or h.startswith("127.") or h.endswith(".localhost") or h.startswith("/")


def read_conf(path: str) -> dict:
    cp = configparser.RawConfigParser(strict=False, interpolation=None)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            cp.read_file(fh)
    except (OSError, configparser.Error):
        return {}
    if not cp.has_section("options"):
        return {}
    return {k.strip().lower(): (v or "").strip() for k, v in cp.items("options")}


def conf_int(conf: dict, *keys, default=None):
    for k in keys:
        v = conf.get(k)
        if v not in (None, "", "False", "false"):
            try:
                return int(v)
            except ValueError:
                pass
    return default


def exact_dbfilter(value: str):
    m = re.fullmatch(r"\^?([A-Za-z0-9_.\-]+)\$?", value or "")
    if m and value.startswith("^") and value.endswith("$"):
        return m.group(1)
    return None


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "odoo"


def port_open(port: int, host="127.0.0.1", timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def http_probe(port: int, timeout=4.0):
    """Return (http_status or None, server_version or None)."""
    url = "http://127.0.0.1:%d/web/webclient/version_info" % int(port)
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": {}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace") or "{}")
            return r.status, (data.get("result") or {}).get("server_version")
    except urllib.error.HTTPError as e:  # type: ignore[attr-defined]
        return e.code, None
    except Exception:
        return None, None


# ------------------------------------------------------------------ processes

def listeners() -> dict:
    """{port: pid} for listening TCP sockets (Linux: ss; Windows: netstat)."""
    out = {}
    if IS_WINDOWS:
        rc, text, _ = run(["netstat", "-ano", "-p", "TCP"], timeout=20)
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[3].upper() == "LISTENING":
                try:
                    out.setdefault(int(parts[1].rsplit(":", 1)[1]), int(parts[4]))
                except ValueError:
                    pass
        return out
    rc, text, _ = run(["ss", "-ltnpH"], timeout=20)
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            port = int(parts[3].rsplit(":", 1)[1])
        except ValueError:
            continue
        m = re.search(r"pid=(\d+)", line)
        out.setdefault(port, int(m.group(1)) if m else None)
    return out


def cmdline(pid) -> list:
    if not pid:
        return []
    if IS_WINDOWS:
        rc, text, _ = run(["powershell", "-NoProfile", "-Command",
                           "(Get-CimInstance Win32_Process -Filter \"ProcessId=%d\").CommandLine" % int(pid)],
                          timeout=20)
        return text.strip().split() if rc == 0 else []
    try:
        with open("/proc/%d/cmdline" % int(pid), "rb") as fh:
            return [a.decode("utf-8", "replace") for a in fh.read().split(b"\0") if a]
    except OSError:
        return []


def proc_cwd(pid):
    try:
        return os.readlink("/proc/%d/cwd" % int(pid))
    except OSError:
        return None


def proc_etime(pid):
    try:
        with open("/proc/%d/stat" % int(pid)) as fh:
            start_ticks = int(fh.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/uptime") as fh:
            uptime = float(fh.read().split()[0])
        return int(uptime - start_ticks / os.sysconf("SC_CLK_TCK"))
    except Exception:
        return None


def is_odoo_cmd(argv: list) -> bool:
    joined = " ".join(argv)
    return bool(argv) and ("odoo-bin" in joined or re.search(r"(^|[/\\ ])odoo(\.py)?( |$)", joined) is not None
                           or " -m odoo" in joined)


def odoo_processes() -> list:
    if IS_WINDOWS:
        return []
    procs = []
    for d in glob.glob("/proc/[0-9]*"):
        pid = int(os.path.basename(d))
        if pid == os.getpid():
            continue
        argv = cmdline(pid)
        if not is_odoo_cmd(argv) or "odoo-local-agent" in " ".join(argv):
            continue
        procs.append({"pid": pid, "argv": argv, "cwd": proc_cwd(pid), "uptime_s": proc_etime(pid),
                      "stop_after_init": "--stop-after-init" in argv})
    return procs


def pid_alive(pid) -> bool:
    if IS_WINDOWS:
        rc, text, _ = run(["tasklist", "/FI", "PID eq %d" % int(pid), "/NH"], timeout=15)
        return str(pid) in text
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def terminate(pid, grace=15.0) -> str:
    """SIGTERM a verified Odoo PID, escalate to SIGKILL only after the grace period."""
    if IS_WINDOWS:
        run(["taskkill", "/PID", str(pid), "/T"], timeout=20)
        deadline = time.time() + grace
        while time.time() < deadline and pid_alive(pid):
            time.sleep(0.5)
        if pid_alive(pid):
            run(["taskkill", "/PID", str(pid), "/T", "/F"], timeout=20)
            return "killed"
        return "terminated"
    try:
        os.kill(int(pid), signal.SIGTERM)
    except OSError:
        return "gone"
    deadline = time.time() + grace
    while time.time() < deadline:
        if not pid_alive(pid):
            return "terminated"
        time.sleep(0.5)
    try:
        os.kill(int(pid), signal.SIGKILL)
    except OSError:
        return "terminated"
    return "killed"


def have_systemd_user() -> bool:
    if IS_WINDOWS or not shutil.which("systemd-run"):
        return False
    rc, _, _ = run(["systemctl", "--user", "is-system-running"], timeout=10)
    return rc in (0, 1)  # 1 = degraded, still usable


def linger_warning():
    """systemd --user units stop shortly after the last login session closes unless the
    user lingers. Under WSL every `wsl.exe` call is a session, so without linger a
    started server dies ~20 s after the call that started it returns."""
    if IS_WINDOWS or not shutil.which("loginctl"):
        return None
    user = os.environ.get("USER") or os.path.basename(HOME)
    rc, text, _ = run(["loginctl", "show-user", user, "-p", "Linger", "--value"], timeout=10)
    if rc == 0 and text.strip() == "no":
        return ("Linger=no: systemd --user units are stopped when the last WSL session closes, so a "
                "service started here lives only while some wsl.exe session stays attached. One-time fix "
                "(the developer's decision): `loginctl enable-linger %s` inside WSL; WSL's own VM idle-stop "
                "additionally needs a VM keep-alive (see the env-doctor plugin)." % user)
    return None


def unit_state(unit: str):
    if not unit or IS_WINDOWS or not shutil.which("systemctl"):
        return None
    rc, text, _ = run(["systemctl", "--user", "show", unit, "-p", "ActiveState", "-p", "MainPID"], timeout=10)
    props = dict(l.split("=", 1) for l in text.splitlines() if "=" in l)
    if rc != 0 or "ActiveState" not in props:
        return None
    pid = props.get("MainPID", "0")
    return {"active": props["ActiveState"], "main_pid": int(pid) if pid.isdigit() and pid != "0" else None}


# ------------------------------------------------------------------ discovery

def find_up(start: str, names, levels=4):
    cur = os.path.abspath(start)
    for _ in range(levels):
        for n in names:
            cand = os.path.join(cur, n)
            if os.path.exists(cand):
                return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return None


LAUNCHERS = ("odoo-bin", os.path.join("setup", "odoo"))


def source_root(odoo_bin):
    """odoo-bin sits in the source root; setup/odoo one level below it."""
    d = os.path.dirname(odoo_bin)
    return os.path.dirname(d) if os.path.basename(d) == "setup" else d


def odoo_version_of(odoo_bin, python=None):
    """From odoo/release.py next to the launcher, else the launcher text (project
    bridges name the sources/<ver> checkout they import), else the venv's site-packages."""
    cands = [os.path.join(source_root(odoo_bin), "odoo", "release.py")] if odoo_bin else []
    if python:
        venv = os.path.dirname(os.path.dirname(python))
        cands += glob.glob(os.path.join(venv, "lib", "python3*", "site-packages", "odoo", "release.py"))
    for rel in cands:
        try:
            text = open(rel, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = re.search(r"version_info\s*=\s*\(\s*(?:'saas~)?(\d+)\s*,\s*(\d+)", text)
        if m:
            return "%s.%s" % (m.group(1), m.group(2))
    if odoo_bin:
        try:
            head = open(odoo_bin, encoding="utf-8", errors="replace").read(4000)
        except OSError:
            head = ""
        m = re.search(r"sources[/\\](\d{2})\.0|Odoo (\d{2})(?:\.0)?\b", head)
        if m:
            return "%s.0" % (m.group(1) or m.group(2))
    return None


def venv_python(root, project=None):
    dirs = []
    if root:
        dirs += [os.path.join(root, n) for n in (".venv", "venv", "env", ".env")]
    if project:
        for p in {project, project.replace("_", "-"), project.lower(), project.lower().replace("_", "-")}:
            dirs += [os.path.join(HOME, ".venvs", p), os.path.join(HOME, ".virtualenvs", p)]
    for d in dirs:
        cand = os.path.join(d, "Scripts", "python.exe") if IS_WINDOWS else os.path.join(d, "bin", "python")
        if os.path.exists(cand):
            return cand
    return None


def conf_paths(roots, max_depth=4) -> list:
    found = []
    if not IS_WINDOWS:
        found += sorted(glob.glob(os.path.join(HOME, ".config", "*", "*.conf")))
    for root in roots or []:
        root = os.path.expanduser(root)
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for cur, dirs, files in os.walk(root):
            depth = cur.count(os.sep) - base_depth
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("_archive")
                       and not d.startswith(".") and depth < max_depth]
            if os.path.basename(cur) == "conf":
                found += sorted(os.path.join(cur, f) for f in files if f.endswith(".conf"))
    seen, out = set(), []
    for p in found:
        rp = os.path.realpath(p)
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def describe_conf(path: str, procs: list, runtime: str, distro):
    conf = read_conf(path)
    if not conf:
        return None, None
    warnings = []
    db_host = conf.get("db_host", "")
    if not is_loopback(db_host):
        return None, "%s: db_host %r is not loopback - not a local service, skipped" % (path, db_host)
    addons = [a.strip() for a in conf.get("addons_path", "").split(",") if a.strip()]
    conf_dir = os.path.dirname(os.path.abspath(path))
    in_xdg = (not IS_WINDOWS) and conf_dir.startswith(os.path.join(HOME, ".config") + os.sep)
    if os.path.basename(conf_dir) == "conf":
        root = os.path.dirname(conf_dir)
        project = os.path.basename(root)
    elif in_xdg:
        project = os.path.basename(conf_dir)
        root = None
    else:
        root = conf_dir
        project = os.path.basename(conf_dir)
    odoo_bin = None
    for entry in addons + ([root] if root else []):
        odoo_bin = find_up(entry, LAUNCHERS, levels=4)
        if odoo_bin:
            break
    if not root and odoo_bin:
        root = find_up(os.path.dirname(odoo_bin), [".venv", "venv", "conf", ".git"], levels=4)
        root = os.path.dirname(root) if root else os.path.dirname(odoo_bin)
    if not root and addons:
        root = os.path.commonpath([os.path.abspath(a) for a in addons]) if len(addons) > 1 else addons[0]
    python = venv_python(root, project) or (venv_python(os.path.dirname(root)) if root else None)
    running = [p for p in procs if os.path.realpath(path) in [os.path.realpath(a) for a in p["argv"] if a.endswith(".conf")]
               or path in p["argv"]]
    if not python and running:
        python = running[0]["argv"][0]
    db_name = conf.get("db_name", "")
    dbf = conf.get("dbfilter", "")
    if conf.get("db_filter") and not dbf:
        warnings.append("conf key 'db_filter' is ignored by Odoo; the key is 'dbfilter'")
    if db_name and dbf:
        warnings.append("db_name and dbfilter are both set: every request does a DB lookup and the pool can run dry; a single-DB conf sets db_name and leaves dbfilter empty")
    if conf.get("dev_mode"):
        warnings.append("dev_mode in a conf file is ignored; dev mode is CLI-only (--dev=...)")
    main_db = db_name if db_name and "," not in db_name and db_name.lower() != "false" else exact_dbfilter(dbf or conf.get("db_filter", ""))
    stem = os.path.splitext(os.path.basename(path))[0]
    sid = slug(project) if stem in ("odoo", "odoo.wsl", "odoo-local", project) else "%s-%s" % (slug(project), slug(stem.replace("odoo.", "").replace("odoo-", "")))
    svc = {
        "id": sid,
        "project": project,
        "odoo_version": odoo_version_of(odoo_bin, python),
        "runtime": runtime,
        "wsl_distro": distro,
        "cwd": source_root(odoo_bin) if odoo_bin else root,
        "python": python,
        "odoo_bin": odoo_bin,
        "conf": os.path.abspath(path),
        "http_port": conf_int(conf, "http_port", "xmlrpc_port", default=8069),
        "gevent_port": conf_int(conf, "gevent_port", "longpolling_port", default=8072),
        "db_host": db_host or "",
        "db_port": conf_int(conf, "db_port", default=5432),
        "main_db": main_db,
        "dbfilter": (dbf or conf.get("db_filter") or None),
        "data_dir": os.path.expanduser(conf.get("data_dir") or (os.path.join(HOME, "AppData", "Local", "OpenERP S.A", "Odoo") if IS_WINDOWS else os.path.join(HOME, ".local", "share", "Odoo"))),
        "systemd_unit": "odoo-%s" % sid if runtime == "wsl" or (runtime == "linux") else None,
        "logfile": conf.get("logfile") or None,
        "warnings": warnings,
    }
    if not odoo_bin:
        warnings.append("odoo-bin not found from addons_path or project root; start/module need it set by hand")
    if running:
        svc["running_pid"] = running[0]["pid"]
    return svc, None


def pg_clusters() -> list:
    out = []
    if IS_WINDOWS:
        return out
    rc, text, _ = run(["pg_lsclusters", "-h"], timeout=20)
    for line in text.splitlines():
        p = line.split()
        if len(p) >= 4 and p[2].isdigit():
            out.append({"version": p[0], "name": p[1], "port": int(p[2]), "status": p[3],
                        "data_directory": p[5] if len(p) > 5 else None, "managed": True})
    known = {c["port"] for c in out}
    for port, pid in listeners().items():
        if port in known:
            continue
        argv = cmdline(pid)
        if argv and os.path.basename(argv[0]).startswith("postgres"):
            data = argv[argv.index("-D") + 1] if "-D" in argv and argv.index("-D") + 1 < len(argv) else None
            out.append({"version": None, "name": "unmanaged", "port": port, "status": "online",
                        "data_directory": data, "managed": False, "pid": pid})
    return out


def op_discover(req):
    procs = odoo_processes()
    services, warnings, ids = [], [], {}
    for path in conf_paths(req.get("roots") or []):
        svc, warn = describe_conf(path, procs, req.get("runtime", "wsl"), req.get("distro"))
        if warn:
            warnings.append(warn)
        if not svc:
            continue
        n = ids.get(svc["id"], 0)
        ids[svc["id"]] = n + 1
        if n:
            svc["id"] = "%s-%d" % (svc["id"], n + 1)
            if svc["systemd_unit"]:
                svc["systemd_unit"] = "odoo-%s" % svc["id"]
        services.append(svc)
    ports = {}
    for s in services:
        ports.setdefault(s["http_port"], []).append(s["id"])
    for port, owners in ports.items():
        if len(owners) > 1:
            warnings.append("http_port %s is shared by %s: only one can run at a time" % (port, ", ".join(owners)))
    lw = linger_warning()
    if lw:
        warnings.insert(0, lw)
    return {"services": services, "clusters": pg_clusters(), "warnings": warnings,
            "odoo_processes": [{"pid": p["pid"], "cwd": p["cwd"], "uptime_s": p["uptime_s"],
                                "stop_after_init": p["stop_after_init"],
                                "cmd": " ".join(p["argv"])[:300]} for p in procs]}


# ------------------------------------------------------------------- services

def svc_status(svc: dict, lst=None, deep=True) -> dict:
    lst = listeners() if lst is None else lst
    port = int(svc.get("http_port") or 8069)
    pid = lst.get(port)
    argv = cmdline(pid) if pid else []
    owner_ok = bool(argv) and (svc.get("conf") in argv or os.path.basename(svc.get("conf") or "-") in " ".join(argv))
    st = {"id": svc["id"], "http_port": port, "listening": port in lst, "pid": pid,
          "owner_matches_conf": owner_ok if pid else None,
          "uptime_s": proc_etime(pid) if pid and not IS_WINDOWS else None,
          "unit": unit_state(svc.get("systemd_unit"))}
    if port in lst and deep:
        code, ver = http_probe(port)
        st["http_status"], st["server_version"] = code, ver
    if pid and not owner_ok and argv:
        st["owner_cmd"] = " ".join(argv)[:200]
    st["state"] = ("running" if port in lst and (owner_ok or not argv) else
                   "port-taken-by-other" if port in lst else "stopped")
    return st


def op_status(req):
    lst = listeners()
    return {"services": [svc_status(s, lst, deep=req.get("deep", True)) for s in req["services"]]}


def _odoo_argv(svc, extra):
    if not svc.get("odoo_bin") or not svc.get("python"):
        raise Refused("service %s has no odoo_bin/python recorded; run local_discover or set them" % svc["id"])
    return [svc["python"], svc["odoo_bin"], "-c", svc["conf"]] + list(extra or [])


def _env_for(svc):
    env = dict(os.environ)
    vbin = os.path.dirname(svc["python"]) if svc.get("python") else None
    if vbin and os.path.isdir(vbin):
        # A venv python started by path loses the venv at Odoo's first self-reload
        # ("No module named psycopg2"); the venv bin must be on PATH.
        env["PATH"] = vbin + os.pathsep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = os.path.dirname(vbin)
    return env


def op_start(req):
    svc = req["service"]
    st = svc_status(svc, deep=False)
    if st["state"] == "running":
        return {"started": False, "state": "already-running", "status": st}
    if st["state"] == "port-taken-by-other":
        raise Refused("port %s is held by pid %s (%s), not this service; stop it first or change the port"
                      % (st["http_port"], st["pid"], st.get("owner_cmd", "?")))
    argv = _odoo_argv(svc, req.get("extra_args"))
    env = _env_for(svc)
    how, durability = None, None
    if svc.get("runtime") in ("wsl", "linux") and have_systemd_user():
        unit = svc.get("systemd_unit") or "odoo-%s" % svc["id"]
        run(["systemctl", "--user", "reset-failed", unit], timeout=10)
        cmd = ["systemd-run", "--user", "--unit=%s" % unit, "--collect",
               "--working-directory=%s" % (svc.get("cwd") or HOME),
               "--setenv=PATH=%s" % env["PATH"]]
        if env.get("VIRTUAL_ENV"):
            cmd.append("--setenv=VIRTUAL_ENV=%s" % env["VIRTUAL_ENV"])
        rc, out, err = run(cmd + argv, timeout=30)
        if rc != 0:
            raise Refused("systemd-run failed (%s): %s" % (rc, (err or out).strip()[:400]))
        how = "systemd user unit %s" % unit
        durability = linger_warning()
    else:
        logf = open(os.path.join(JOBS_DIR, "..", "start-%s.out" % svc["id"]), "ab") if _ensure(JOBS_DIR) else subprocess.DEVNULL
        kw = {"creationflags": 0x00000008 | 0x00000200} if IS_WINDOWS else {"start_new_session": True}
        subprocess.Popen(argv, cwd=svc.get("cwd") or None, env=env, stdout=logf, stderr=logf,
                         stdin=subprocess.DEVNULL, **kw)
        how = "detached process" + ("" if IS_WINDOWS else " (no systemd --user: it may die with this WSL session)")
    wait = max(0, min(int(req.get("wait_s", 40)), 90))
    deadline = time.time() + wait
    while time.time() < deadline:
        if port_open(svc["http_port"]):
            break
        time.sleep(1.0)
    st = svc_status(svc)
    return {"started": True, "how": how, "durability": durability,
            "state": "ready" if st["state"] == "running" else "starting",
            "status": st, "hint": None if st["state"] == "running" else
            "still booting (a cold registry load on a slow mount can take minutes); call local_services later - do not poll in a loop"}


def op_stop(req):
    svc = req["service"]
    lst = listeners()
    done = []
    unit = svc.get("systemd_unit")
    ust = unit_state(unit)
    if ust and ust["active"] in ("active", "activating", "reloading"):
        run(["systemctl", "--user", "stop", unit], timeout=60)
        done.append("stopped unit %s" % unit)
    for port in (svc.get("http_port"), svc.get("gevent_port")):
        pid = listeners().get(port) if done else lst.get(port)
        if not pid:
            continue
        argv = cmdline(pid)
        if not is_odoo_cmd(argv):
            raise Refused("port %s is held by pid %s which is not an Odoo process (%s); not touching it"
                          % (port, pid, " ".join(argv)[:160] or "unknown"))
        if svc.get("conf") and svc["conf"] not in argv and os.path.basename(svc["conf"]) not in " ".join(argv):
            raise Refused("port %s is held by Odoo pid %s started with another conf (%s); stop that service instead"
                          % (port, pid, " ".join(argv)[:160]))
        done.append("pid %s on :%s %s" % (pid, port, terminate(pid)))
    return {"stopped": bool(done), "actions": done, "status": svc_status(svc, deep=False)}


def op_logs(req):
    svc = req["service"]
    n = max(1, min(int(req.get("lines", 200)), 3000))
    pattern = re.compile(req["grep"]) if req.get("grep") else None
    since = req.get("since")
    errors_only = bool(req.get("errors_only"))
    pid_filter = str(req["pid"]) if req.get("pid") else None
    path = svc.get("logfile")
    raw = []
    source = path
    if path and os.path.exists(path):
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 8 * 1024 * 1024))
            raw = fh.read().decode("utf-8", "replace").splitlines()
    elif svc.get("systemd_unit") and not IS_WINDOWS:
        rc, text, _ = run(["journalctl", "--user", "-u", svc["systemd_unit"], "-n", str(max(n * 4, 2000)),
                           "--no-pager", "-o", "cat"], timeout=30)
        raw, source = text.splitlines(), "journal:%s" % svc["systemd_unit"]
    else:
        return {"source": path, "lines": [], "note": "no logfile on disk and no unit journal"}
    sel, in_err = [], False
    errors = 0
    for line in raw:
        m = LOG_LINE_RE.match(line)
        if m:
            in_err = m.group(3) in ("ERROR", "CRITICAL")
            if since and m.group(1) < since:
                continue
            if pid_filter and m.group(2) != pid_filter:
                continue
            if in_err:
                errors += 1
        elif since and not sel:
            continue
        if errors_only and not (in_err or line.startswith("Traceback") or line.startswith(" ")):
            continue
        if errors_only and not in_err:
            continue
        if pattern and not pattern.search(line):
            continue
        sel.append(line)
    return {"source": source, "error_count": errors, "lines": sel[-n:]}


# ----------------------------------------------------------------------- jobs

def _ensure(d) -> bool:
    try:
        os.makedirs(d, exist_ok=True)
        return True
    except OSError:
        return False


def op_job_start(req):
    """Start a background job (module install/upgrade, DB create/clone, cleanup apply).

    The job is a self-contained bash (Linux) or python (Windows) script under
    JOBS_DIR/<id>/. It writes out.log, rc and finished; op_job_status reads them."""
    jid = req["job_id"]
    jdir = os.path.join(JOBS_DIR, jid)
    _ensure(jdir)
    meta = dict(req.get("meta") or {})
    meta.update({"job_id": jid, "created_at": now_iso(), "argv": req["argv"]})
    with open(os.path.join(jdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    env = dict(os.environ)
    env.update(req.get("env") or {})
    if IS_WINDOWS:
        wrapper = [sys.executable, "-c",
                   "import subprocess,sys,time;o=open(sys.argv[1]+'/out.log','ab');"
                   "r=subprocess.call(sys.argv[2:],stdout=o,stderr=o);"
                   "open(sys.argv[1]+'/rc','w').write(str(r));open(sys.argv[1]+'/finished','w').write(str(time.time()))",
                   jdir] + req["argv"]
        subprocess.Popen(wrapper, cwd=req.get("cwd") or None, env=env, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=0x00000008 | 0x00000200)
        return {"job_id": jid, "how": "detached process", "dir": jdir}
    script = os.path.join(jdir, "run.sh")
    q = lambda a: "'" + a.replace("'", "'\\''") + "'"  # noqa: E731 - single-quote for bash
    with open(script, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("#!/bin/bash\nset +e\ncd %s || exit 97\n" % q(req.get("cwd") or HOME))
        for k, v in (req.get("env") or {}).items():
            if re.fullmatch(r"[A-Z_][A-Z0-9_]*", k):
                fh.write("export %s=%s\n" % (k, q(str(v))))
        fh.write("%s > %s 2>&1\nrc=$?\n" % (" ".join(q(a) for a in req["argv"]), q(os.path.join(jdir, "out.log"))))
        fh.write("echo $rc > %s\ndate +%%s > %s\n" % (q(os.path.join(jdir, "rc")), q(os.path.join(jdir, "finished"))))
    os.chmod(script, 0o700)
    if have_systemd_user():
        unit = "odoo-local-job-%s" % jid
        rc, out, err = run(["systemd-run", "--user", "--unit=%s" % unit, "--collect", "/bin/bash", script], timeout=30)
        if rc != 0:
            raise Refused("systemd-run failed: %s" % (err or out).strip()[:300])
        return {"job_id": jid, "how": "systemd user unit %s" % unit, "dir": jdir}
    subprocess.Popen(["/bin/bash", script], start_new_session=True, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"job_id": jid, "how": "detached bash (no systemd --user: may die with this WSL session)", "dir": jdir}


def _creds(cluster):
    """Fill user/password from the cluster's conf on THIS side, so a password never
    travels through the MCP request or a command line."""
    if cluster.get("conf") and "password" not in cluster:
        conf = read_conf(cluster["conf"])
        cluster["password"] = conf.get("db_password") if conf.get("db_password") not in (None, "", "False") else None
        cluster.setdefault("user", conf.get("db_user") or None)
        h = conf.get("db_host") or ""
        cluster.setdefault("host", h if h and h.lower() != "false" else None)
    return cluster


def _psql(cluster, sql, db="postgres", timeout=60):
    cluster = _creds(cluster)
    env = dict(os.environ)
    if cluster.get("password"):
        env["PGPASSWORD"] = cluster["password"]
    argv = ["psql", "-X", "-q", "-A", "-t", "-F", "\t", "-v", "ON_ERROR_STOP=1",
            "-p", str(cluster["port"]), "-d", db, "-c", sql]
    if cluster.get("host"):
        argv[1:1] = ["-h", cluster["host"]]
    if cluster.get("user"):
        argv[1:1] = ["-U", cluster["user"]]
    return run(argv, env=env, timeout=timeout)


def op_job_status(req):
    jdir = os.path.join(JOBS_DIR, req["job_id"])
    try:
        meta = json.load(open(os.path.join(jdir, "meta.json"), encoding="utf-8"))
    except OSError:
        raise Refused("unknown job %s" % req["job_id"])
    rc_path = os.path.join(jdir, "rc")
    finished = os.path.exists(rc_path)
    res = {"job_id": req["job_id"], "kind": meta.get("kind"), "state": "finished" if finished else "running",
           "created_at": meta.get("created_at")}
    log = os.path.join(jdir, "out.log")
    lines = []
    if os.path.exists(log):
        with open(log, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 4 * 1024 * 1024))
            lines = fh.read().decode("utf-8", "replace").splitlines()
    errors = [l for l in lines if LOG_LEVEL_RE.match(l)]
    res["error_count"] = len(errors)
    res["first_errors"] = errors[:5]
    res["tail"] = lines[-int(req.get("tail", 40)):]
    summary = [l for l in lines if re.search(r"\d+ failed, \d+ error\(s\) of \d+ tests", l)]
    if summary:
        res["test_summary"] = summary[-1]
    if not finished:
        unit = "odoo-local-job-%s" % req["job_id"]
        us = unit_state(unit)
        res["unit"] = us
        if us and us["active"] in ("inactive", "failed") and not os.path.exists(rc_path):
            res["state"] = "died"
        return res
    res["exit_code"] = int(open(rc_path).read().strip() or -1)
    if meta.get("modules") and meta.get("db") and meta.get("cluster"):
        names = ",".join("'%s'" % m for m in meta["modules"] if re.fullmatch(r"[a-z0-9_]+", m))
        rc, out, err = _psql(meta["cluster"], "select name, state from ir_module_module where name in (%s)" % names,
                             db=meta["db"])
        res["module_states"] = dict(l.split("\t", 1) for l in out.splitlines() if "\t" in l) if rc == 0 else {"error": err.strip()[:200]}
    ok = res["exit_code"] == 0 and res["error_count"] == 0
    if "module_states" in res and isinstance(res["module_states"], dict):
        ok = ok and all(v == "installed" for k, v in res["module_states"].items() if k != "error") \
            and "error" not in res["module_states"]
    if "test_summary" in res:
        ok = ok and bool(re.search(r" 0 failed, 0 error\(s\)", res["test_summary"]))
    res["verdict"] = "ok" if ok else "failed"
    res["note"] = "verdict uses module state + ERROR/CRITICAL count + test summary, not the exit code alone (odoo-bin -i exits 0 on a failed install)"
    return res


# ------------------------------------------------------------------ databases

def _db_rows(cluster):
    sql = ("select d.datname, pg_database_size(d.datname), d.datistemplate, "
           "(select count(*) from pg_stat_activity a where a.datname = d.datname and a.pid <> pg_backend_pid()) "
           "from pg_database d where d.datallowconn and d.datname not in ('postgres','template0','template1') order by 1")
    rc, out, err = _psql(cluster, sql)
    if rc != 0:
        raise Refused("cannot list databases on :%s: %s" % (cluster["port"], err.strip()[:300]))
    rows = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) == 4:
            rows.append({"name": p[0], "size_bytes": int(p[1]), "is_template": p[2] == "t",
                         "connections": int(p[3])})
    return rows


def _last_activity(cluster, db, data_dirs):
    """Newest of: last Odoo login, last module/attachment write, filestore mtime."""
    rc, out, _ = _psql(cluster, "select extract(epoch from greatest("
                       "(select max(create_date) from res_users_log),"
                       "(select max(write_date) from ir_attachment),"
                       "(select max(write_date) from ir_module_module)))::bigint, "
                       "(select count(*) from ir_module_module where state='installed')", db=db, timeout=30)
    is_odoo, ts = False, 0.0
    if rc == 0 and out.strip():
        p = out.strip().split("\t")
        is_odoo = True
        ts = float(p[0]) if p[0] else 0.0
    for d in data_dirs:
        fs = os.path.join(d, "filestore", db)
        try:
            ts = max(ts, os.stat(fs).st_mtime)
            for sub in os.scandir(fs):
                ts = max(ts, sub.stat().st_mtime)
        except OSError:
            pass
    return is_odoo, ts or None


def tool_state_templates() -> set:
    """Template DB names referenced by fast-test tool state files - never drop those."""
    names = set()
    for f in glob.glob(os.path.join(HOME, ".config", "*", "fast", "*.env")) + \
            glob.glob(os.path.join(HOME, ".config", "*", "fast", "tpl_*")):
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        names.update(re.findall(r"\b((?:tpl|kg_tpl)_[A-Za-z0-9_]+)\b", text))
        names.add(os.path.splitext(os.path.basename(f))[0])
    return names


def filter_regex(value):
    """An Odoo dbfilter as a regex: %h / %d (host / first host label) match anything here."""
    if not value or str(value).strip().lower() in ("false", "none"):
        return None
    try:
        return re.compile(str(value).replace("%h", ".*").replace("%d", ".*"))
    except re.error:
        return re.compile(r"(?!x)x")  # unparsable filter: matches nothing; caught by the unknown-main rule


def keep_reason(row, main_dbs, protected, active_days=7.0, rails=None, cluster_label=None):
    """Why a DB must be kept, or None. `rails` (from the server):
      main_filters  [[service, filter]]   - DBs matching a service's dbfilter/db_filter are its main DBs
      unknown_main  {cluster_label: [service]} - services with neither db_name nor a filter: keep every
                                             non-scratch DB on that cluster
      scratch_pattern regex string
    """
    rails = rails or {}
    name = row["name"]
    if name in main_dbs:
        return "main_db of service %s" % main_dbs[name]
    for sid, flt in rails.get("main_filters") or []:
        rx = filter_regex(flt)
        if rx is not None and rx.match(name):
            return "main_db of service %s (matches its dbfilter %s)" % (sid, flt)
    unknown = (rails.get("unknown_main") or {}).get(cluster_label) or []
    if unknown:
        scratch = re.compile(rails.get("scratch_pattern") or r"(?!x)x", re.IGNORECASE)
        if not scratch.search(name):
            return "main DB of %s unknown (no db_name or dbfilter); non-scratch DBs on this cluster are kept" % unknown[0]
    if row["name"] in protected:
        return "protected: %s" % protected[row["name"]]
    if row["connections"] > 0:
        return "%d open connection(s)" % row["connections"]
    la = row.get("last_activity")
    if la and time.time() - la < active_days * DAY:
        return "active %.1f days ago (< %d)" % ((time.time() - la) / DAY, active_days)
    if row.get("last_activity") is None and row.get("is_odoo"):
        return "last activity unknown"
    return None


def op_db_list(req):
    out = []
    data_dirs = req.get("data_dirs") or []
    tpl = tool_state_templates()
    protected = dict(req.get("protected") or {})
    for t in tpl:
        protected.setdefault(t, "referenced by a fast-test tool state file")
    for cl in req["clusters"]:
        try:
            rows = _db_rows(cl)
        except Refused as e:
            out.append({"cluster": cl["label"], "error": str(e)})
            continue
        for r in rows:
            r["is_odoo"], r["last_activity"] = _last_activity(cl, r["name"], data_dirs) if req.get("activity", True) else (None, None)
            r["cluster"] = cl["label"]
            r["keep"] = keep_reason(r, req.get("main_dbs") or {}, protected, rails=req.get("rails"),
                                    cluster_label=cl["label"])
        out.append({"cluster": cl["label"], "databases": rows})
    return {"clusters": out}


def _dump_verified(cl, db, dest_dir):
    """pg_dump -Fc to dest_dir/<db>.dump, then check the TOC holds one TABLE DATA entry per table."""
    _ensure(dest_dir)
    dest = os.path.join(dest_dir, "%s.dump" % db)
    cl = _creds(cl)
    env = dict(os.environ)
    if cl.get("password"):
        env["PGPASSWORD"] = cl["password"]
    base = ["-p", str(cl["port"])] + (["-h", cl["host"]] if cl.get("host") else []) + (["-U", cl["user"]] if cl.get("user") else [])
    with open(dest, "wb") as fh:
        p = subprocess.run(["pg_dump", "-Fc"] + base + ["-d", db], stdout=fh, stderr=subprocess.PIPE, env=env)
    if p.returncode != 0:
        raise Refused("pg_dump %s failed: %s" % (db, p.stderr.decode("utf-8", "replace")[:300]))
    rc, toc, err = run(["pg_restore", "-l", dest], timeout=600)
    data_entries = sum(1 for l in toc.splitlines() if " TABLE DATA " in l)
    rc2, out, _ = _psql(cl, "select count(*) from pg_tables where schemaname not in ('pg_catalog','information_schema')", db=db)
    tables = int(out.strip() or -1) if rc2 == 0 else -1
    if rc != 0 or tables < 0 or data_entries < tables:
        raise Refused("dump of %s failed TOC verification (%s data entries for %s tables); not dropping"
                      % (db, data_entries, tables))
    return {"dump": dest, "bytes": os.path.getsize(dest), "toc_data_entries": data_entries, "tables": tables,
            "restore": "pg_restore -p %s -C -d postgres %s" % (cl["port"], dest)}


def op_db_drop(req):
    """Drop one database through both rails. No override exists for the keep-list."""
    cl, db = req["cluster"], req["db"]
    rows = {r["name"]: r for r in _db_rows(cl)}
    if db not in rows:
        raise Refused("database %s does not exist on %s" % (db, cl["label"]))
    row = rows[db]
    row["is_odoo"], row["last_activity"] = _last_activity(cl, db, req.get("data_dirs") or [])
    protected = dict(req.get("protected") or {})
    for t in tool_state_templates():
        protected.setdefault(t, "referenced by a fast-test tool state file")
    reason = keep_reason(row, req.get("main_dbs") or {}, protected, rails=req.get("rails"),
                         cluster_label=cl.get("label"))
    if reason:
        raise Refused("keep-list: %s is kept (%s)" % (db, reason))
    result = {"db": db, "size_bytes": row["size_bytes"]}
    if row["size_bytes"] >= int(req.get("backup_threshold_bytes", 200 * 1024 * 1024)) or req.get("backup"):
        result["backup"] = _dump_verified(cl, db, req.get("backup_dir") or os.path.join(
            BACKUP_ROOT, "odoo-local_%s" % datetime.now().strftime("%Y%m%d")))
    rc, out, err = _psql(cl, 'DROP DATABASE "%s"' % db.replace('"', '""'))  # no FORCE: in-use DBs fail
    if rc != 0:
        raise Refused("DROP DATABASE %s failed (in use?): %s" % (db, err.strip()[:300]))
    result["dropped"] = True
    if req.get("drop_filestore", True):
        for d in req.get("data_dirs") or []:
            fs = os.path.join(d, "filestore", db)
            if os.path.isdir(fs):
                result.setdefault("filestore_removed", []).append(_guarded_rm(fs, req.get("allow_roots") or []))
    return result


# -------------------------------------------------------------------- cleanup

def _du(path) -> int:
    total = 0
    for cur, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(cur, f)).st_size
            except OSError:
                pass
    return total


def _guarded_rm(path, allow_roots) -> str:
    """Remove a path only if it sits strictly below an allowed root. Empty or relative
    paths, the roots themselves, and anything outside them are refused - the generic
    form of `rm -rf -- "${base:?}/${d:?}"`."""
    if not path or not str(path).strip() or not os.path.isabs(path):
        raise Refused("refusing to remove an empty or relative path: %r" % path)
    real = os.path.realpath(path)
    roots = [os.path.realpath(r) for r in allow_roots if r and os.path.isabs(r)]
    if not any(real.startswith(r.rstrip(os.sep) + os.sep) and real != r for r in roots):
        raise Refused("refusing to remove %s: not below an allowed root %s" % (real, roots))
    if real in (os.path.realpath(HOME), "/", os.path.realpath(os.path.join(HOME, ".local", "share", "Odoo"))):
        raise Refused("refusing to remove %s" % real)
    if not os.path.lexists(real):
        return "absent: %s" % real
    if os.path.isdir(real) and not os.path.islink(real):
        shutil.rmtree(real)
    else:
        os.remove(real)
    return "removed: %s" % real


def op_cleanup_scan(req):
    """Read-only inventory the server turns into a plan."""
    services = req["services"]
    data_dirs = sorted({s["data_dir"] for s in services if s.get("data_dir")} |
                       ({os.path.join(HOME, ".local", "share", "Odoo"), os.path.join(HOME, ".local", "share", "odoo")}
                        if not IS_WINDOWS else set()))
    dbl = op_db_list({"clusters": req["clusters"], "data_dirs": data_dirs, "main_dbs": req.get("main_dbs"),
                      "protected": req.get("protected"), "rails": req.get("rails")})
    all_dbs, cluster_errors = set(), []
    for c in dbl["clusters"]:
        if "error" in c:
            cluster_errors.append(c["error"])
        for r in c.get("databases", []):
            all_dbs.add(r["name"])
    filestores = []
    for d in data_dirs:
        for fs in glob.glob(os.path.join(d, "filestore", "*")):
            name = os.path.basename(fs)
            if os.path.isdir(fs):
                filestores.append({"path": fs, "db": name, "db_exists": name in all_dbs, "data_dir": d,
                                   "size_bytes": _du(fs) if name not in all_dbs else None,
                                   "mtime": os.stat(fs).st_mtime})
    confs = []
    lst = listeners()
    for s in services:
        c = s.get("conf")
        if not c or not os.path.exists(c):
            continue
        confs.append({"service": s["id"], "conf": c, "main_db": s.get("main_db"),
                      "db_exists": (s.get("main_db") in all_dbs) if s.get("main_db") else None,
                      "running": s.get("http_port") in lst, "mtime": os.stat(c).st_mtime})
    logs = []
    for s in services:
        lf = s.get("logfile")
        if not lf:
            continue
        for f in glob.glob(lf + "*"):
            if os.path.isfile(f):
                st = os.stat(f)
                logs.append({"path": f, "service": s["id"], "size_bytes": st.st_size, "mtime": st.st_mtime,
                             "current": f == lf})
    return {"databases": dbl["clusters"], "filestores": filestores, "confs": confs, "logs": logs,
            "data_dirs": data_dirs, "cluster_errors": cluster_errors, "scanned_at": now_iso()}


def op_apply_item(req):
    """Execute ONE plan item after re-validating it against the live state."""
    item = req["item"]
    kind, action = item["kind"], item["action"]
    allow = req.get("allow_roots") or []
    if kind == "scratch_db" and action == "drop":
        return op_db_drop(dict(req["drop"], backup=item.get("backup")))
    if kind == "orphan_filestore" and action == "delete":
        db = os.path.basename(item["target"].rstrip("/"))
        for cl in req.get("clusters") or []:
            if db in {r["name"] for r in _db_rows(cl)}:
                raise Refused("database %s exists again on %s; filestore kept" % (db, cl["label"]))
        return {"result": _guarded_rm(item["target"], allow)}
    if kind == "stale_log" and action == "delete":
        return {"result": _guarded_rm(item["target"], allow)}
    if kind == "dead_conf" and action == "archive":
        src = item["target"]
        if not os.path.isfile(src):
            return {"result": "absent: %s" % src}
        dest_dir = os.path.join(os.path.dirname(src), "_archive_%s" % datetime.now().strftime("%Y%m%d"))
        _ensure(dest_dir)
        dest = os.path.join(dest_dir, os.path.basename(src))
        shutil.move(src, dest)
        return {"result": "archived: %s -> %s" % (src, dest)}
    raise Refused("unsupported plan item %s/%s" % (kind, action))


# ---------------------------------------------------------- snapshot/relaunch

def op_snapshot(req):
    procs = [p for p in odoo_processes() if not p["stop_after_init"]]
    _ensure(SNAP_DIR)
    snap = {"taken_at": now_iso(), "servers": [{"pid": p["pid"], "cwd": p["cwd"], "argv": p["argv"],
                                                "path": _proc_path(p["pid"])} for p in procs]}
    name = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(SNAP_DIR, "%s.json" % name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1)
    return {"snapshot": path, "servers": len(snap["servers"]),
            "items": [{"cwd": s["cwd"], "cmd": " ".join(s["argv"])[:200]} for s in snap["servers"]]}


def _proc_path(pid):
    try:
        env = open("/proc/%d/environ" % pid, "rb").read().split(b"\0")
        for e in env:
            if e.startswith(b"PATH="):
                return e[5:].decode("utf-8", "replace")
    except OSError:
        pass
    return None


def op_relaunch(req):
    files = sorted(glob.glob(os.path.join(SNAP_DIR, "*.json")))
    path = req.get("snapshot") or (files[-1] if files else None)
    if not path or not os.path.exists(path):
        raise Refused("no snapshot found under %s" % SNAP_DIR)
    snap = json.load(open(path, encoding="utf-8"))
    if not have_systemd_user():
        raise Refused("systemd --user is not available; relaunch needs it so servers survive this WSL session")
    lst = listeners()
    out = []
    for i, s in enumerate(snap["servers"], 1):
        ports = [int(a.split("=", 1)[1]) for a in s["argv"] if a.startswith("--http-port=")]
        if any(p in lst for p in ports):
            out.append({"cmd": " ".join(s["argv"])[:160], "result": "skipped: port already listening"})
            continue
        unit = "odoo-restored-%d" % i
        cmd = ["systemd-run", "--user", "--unit=%s" % unit, "--collect",
               "--working-directory=%s" % (s.get("cwd") or HOME)]
        if s.get("path"):
            cmd.append("--setenv=PATH=%s" % s["path"])
        run(["systemctl", "--user", "reset-failed", unit], timeout=10)
        rc, o, e = run(cmd + s["argv"], timeout=30)
        out.append({"cmd": " ".join(s["argv"])[:160], "unit": unit,
                    "result": "started" if rc == 0 else "failed: %s" % (e or o).strip()[:200]})
    return {"snapshot": path, "relaunched": out}


# ----------------------------------------------------------------------- main

OPS = {
    "discover": op_discover, "status": op_status, "start": op_start, "stop": op_stop, "logs": op_logs,
    "job_start": op_job_start, "job_status": op_job_status, "db_list": op_db_list, "db_drop": op_db_drop,
    "cleanup_scan": op_cleanup_scan, "apply_item": op_apply_item, "snapshot": op_snapshot,
    "relaunch": op_relaunch, "selftest": lambda req: {"ok": True, "python": sys.version.split()[0],
                                                      "home": HOME, "windows": IS_WINDOWS},
}


def main() -> int:
    raw = os.environ.get("ODOO_LOCAL_ARGS", "")
    try:
        req = json.loads(base64.b64decode(raw).decode("utf-8")) if raw else {"op": "selftest"}
        fn = OPS[req["op"]]
        payload = {"ok": True, "result": fn(req)}
    except Refused as e:
        payload = {"ok": False, "refused": True, "error": str(e)}
    except KeyError as e:
        payload = {"ok": False, "error": "bad request: missing %s" % e}
    except Exception as e:  # report, never hang
        payload = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    sys.stdout.write(RESULT_MARK + json.dumps(payload, default=str) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
