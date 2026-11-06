"""odoo-local MCP tools: typed, guarded operations on LOCAL Odoo services only.

Scope = the services in ~/.odoo-mcp/local-services.json (loopback by construction, see
registry.py). Inside that scope no per-call approval is needed: start, stop, restart,
status, logs, module install/upgrade and discovery just run. Two rails guard destructive
database work and can never be switched off through a tool argument:

  1. keep-list - a project's main_db, any DB with open connections, any DB active in the
     last 7 days, and template DBs referenced by fast-test state files are never dropped;
  2. dump-before-drop - a DB above the size threshold is pg_dump -Fc'd and its TOC
     verified before DROP DATABASE (no FORCE, so a DB in use fails instead of breaking).

Cleanup is plan-first: local_cleanup_plan stores a plan and returns its id;
local_cleanup_apply executes only items of a stored, unexpired plan, re-validating each.
"""

from __future__ import annotations

import hashlib
import json
import ntpath
import os
import posixpath
import re
import time
import uuid
from datetime import datetime, timezone

import registry
import runner

PLAN_TTL_S = 24 * 3600
BACKUP_THRESHOLD = 200 * 1024 * 1024
# A DB whose name says it is a reference copy is never dropped for inactivity alone.
PROTECTED_NAME = r"(prod|bk|backup|baseline|golden|reference|vanilla|e2e)"
SUMMARY_TOP = 20
PAGE_DEFAULT, PAGE_MAX = 100, 500
DEFAULT_SCRATCH = (r"^(test|tmp|temp|scratch|odoo_local_test|ft|qc|copy|bak|old|demo|try)[_-]"
                   r"|[_-](test|tmp|temp|copy|bak|old|scratch|clone|\d{8}(_?\d{4,6})?)$")

_svc = {"type": "string", "description": "Service id from local_services / local-services.json"}

TOOLS = [
    {"name": "local_discover",
     "description": "Find local Odoo services: scans WSL distros (~/.config/*/*.conf and conf/*.conf under the roots) "
                    "and the Windows project folder for Odoo confs, venvs, odoo-bin, ports, Postgres clusters and running "
                    "odoo-bin processes, and writes new/changed entries to ~/.odoo-mcp/local-services.json "
                    "(loopback services only). Run it first; safe to repeat.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "distro": {"type": "string", "description": "WSL distro (default: every distro except docker-desktop)"},
         "roots": {"type": "array", "items": {"type": "string"},
                   "description": "Extra roots to scan for conf/*.conf (default ~/workspace)"},
         "write": {"type": "boolean", "description": "Write results to the services file (default true)"}}}},
    {"name": "local_services",
     "description": "Status of local Odoo services: listening?, PID, owner matches the conf?, uptime, HTTP status "
                    "and server version, systemd unit state. No id = all services.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "id": _svc, "deep": {"type": "boolean", "description": "HTTP probe (default true)"}}}},
    {"name": "local_start",
     "description": "Start a local Odoo service from its venv with its conf (WSL: as a systemd --user unit "
                    "odoo-<id>, so it survives the wsl call). Refuses if another process holds the port. "
                    "Readiness wait is bounded (default 40 s); a slow boot returns state 'starting'.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["id"], "properties": {
         "id": _svc, "wait_s": {"type": "integer", "minimum": 0, "maximum": 90},
         "extra_args": {"type": "array", "items": {"type": "string"},
                        "description": "Extra odoo-bin args, e.g. [\"--dev=xml\", \"-d\", \"mydb\"]"}}}},
    {"name": "local_stop",
     "description": "Stop a local Odoo service by the process holding its listening port (never pkill -f): "
                    "stops its systemd unit, verifies the PID is Odoo with this conf, SIGTERM then SIGKILL after 15 s.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["id"], "properties": {"id": _svc}}},
    {"name": "local_restart",
     "description": "Stop then start a local Odoo service (needed after a -u that removed or renamed a field, "
                    "after editing a .po or adding manifest assets).",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["id"], "properties": {
         "id": _svc, "wait_s": {"type": "integer", "minimum": 0, "maximum": 90},
         "extra_args": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "local_logs",
     "description": "Tail a local service's log (conf logfile, else its unit journal). Filters: grep regex, "
                    "errors_only (ERROR/CRITICAL by log level, not 'Traceback' text), since 'YYYY-MM-DD HH:MM:SS', pid.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["id"], "properties": {
         "id": _svc, "lines": {"type": "integer", "minimum": 1, "maximum": 3000},
         "grep": {"type": "string"}, "errors_only": {"type": "boolean"},
         "since": {"type": "string"}, "pid": {"type": "integer"}}}},
    {"name": "local_module",
     "description": "Install (-i) or upgrade (-u) modules on a local database as a BACKGROUND job "
                    "(--stop-after-init --no-http), optionally with --test-enable --test-tags. Returns a job id at once; "
                    "read the result with local_job. Never blocks on long runs.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["id", "modules"], "properties": {
         "id": _svc, "modules": {"type": "array", "items": {"type": "string"}, "minItems": 1},
         "action": {"type": "string", "enum": ["install", "upgrade"]},
         "db": {"type": "string", "description": "Database (default: the service's main_db)"},
         "test_tags": {"type": "string", "description": "Enables --test-enable with these --test-tags"},
         "extra_args": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "local_job",
     "description": "Status/result of a background job from local_module or local_db: running/finished/died, "
                    "exit code, ERROR/CRITICAL count, module states, test summary, verdict, log tail. "
                    "Call it when you need the result; do not poll it in a loop.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["job_id"], "properties": {
         "job_id": {"type": "string"}, "tail": {"type": "integer", "minimum": 0, "maximum": 500}}}},
    {"name": "local_db",
     "description": "Local databases on the Postgres clusters used by registered services. "
                    "list: name, size, connections, last activity, owning service, keep reason. "
                    "create: new Odoo DB via odoo-bin -i (background job). clone: via Odoo's exp_duplicate_database, "
                    "filestore included (background job). drop: through the keep-list and dump-before-drop rails.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["action"], "properties": {
         "action": {"type": "string", "enum": ["list", "create", "clone", "drop"]},
         "id": {"type": "string", "description": "Service whose cluster/conf to use (list: default all)"},
         "name": {"type": "string", "description": "Target DB (create/clone/drop)"},
         "source": {"type": "string", "description": "Source DB for clone"},
         "modules": {"type": "array", "items": {"type": "string"}, "description": "create: modules to install (default base)"},
         "demo": {"type": "boolean", "description": "create: load demo data (default false)"},
         "activity": {"type": "boolean", "description": "list: compute last activity (default true)"}}}},
    {"name": "local_cleanup_plan",
     "description": "Plan (never execute) cleanup of local Odoo leftovers: scratch DBs by name/age, orphan "
                    "filestores whose DB is gone, dead confs (archived, never deleted), stale logs. Returns "
                    "{plan_id, items:[{kind,target,size_bytes,reason,action,backup}], keep:[{target,reason}]} - by default a "
                    "summary (totals per kind, groups, largest 20 items); detail=true pages the full lists. "
                    "Show it to the user; only local_cleanup_apply with this plan_id executes it.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "distro": {"type": "string"}, "min_age_days": {"type": "integer", "minimum": 7},
         "log_age_days": {"type": "integer", "minimum": 7},
         "scratch_pattern": {"type": "string", "description": "Regex for scratch DB names (has a default)"},
         "plan_id": {"type": "string", "description": "Re-read a stored plan instead of scanning"},
         "detail": {"type": "boolean", "description": "Return a page of the full items/keep lists (default: summary)"},
         "offset": {"type": "integer", "minimum": 0},
         "limit": {"type": "integer", "minimum": 1, "maximum": 500}}}},
    {"name": "local_cleanup_apply",
     "description": "Execute a plan from local_cleanup_plan that the user has seen. Every item is re-checked "
                    "against live state (keep-list, connections, path allow-list) before acting; DB drops dump "
                    "first when the plan says backup. 'only' limits it to the listed targets.",
     "inputSchema": {"type": "object", "additionalProperties": False, "required": ["plan_id"], "properties": {
         "plan_id": {"type": "string"}, "only": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "local_snapshot",
     "description": "Record every long-running odoo-bin server in a WSL distro (cwd, argv, PATH) before a WSL "
                    "restart or shutdown.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {"distro": {"type": "string"}}}},
    {"name": "local_relaunch",
     "description": "Bring the servers of the latest (or a named) snapshot back as systemd --user units "
                    "odoo-restored-N, skipping any whose port already listens.",
     "inputSchema": {"type": "object", "additionalProperties": False, "properties": {
         "distro": {"type": "string"}, "snapshot": {"type": "string"}}}},
]


class ToolError(Exception):
    pass


def _P(runtime):
    """Path module for paths INSIDE a runtime: WSL/Linux paths are posix even when this
    server runs on Windows."""
    return ntpath if runtime == "windows" else posixpath


# ---------------------------------------------------------------- utilities

def _home() -> str:
    return registry.base_dir()


def _ok(res: dict) -> dict:
    if not res.get("ok"):
        prefix = "refused" if res.get("refused") else "failed"
        raise ToolError("%s: %s" % (prefix, res.get("error")))
    return res["result"]


def _call(svc_or_rt, request: dict, timeout=90) -> dict:
    if isinstance(svc_or_rt, dict):
        rt, distro = svc_or_rt.get("runtime"), svc_or_rt.get("wsl_distro")
    else:
        rt, distro = svc_or_rt
    return _ok(runner.call(rt, distro, request, timeout=timeout))


def _distros(args) -> list:
    if args.get("distro"):
        return [args["distro"]]
    found = runner.list_distros()
    return found or ([None] if os.name != "nt" else [])


def _clusters(services, sid=None) -> dict:
    """{label: {runtime, distro, cluster}} - one per (runtime, distro, db_port)."""
    out = {}
    for s in services:
        if sid and s["id"] != sid:
            continue
        if s.get("runtime") not in ("wsl", "linux", "windows"):
            continue
        label = "%s:%s" % (s.get("wsl_distro") or s.get("runtime"), s.get("db_port") or 5432)
        if label not in out:
            out[label] = {"runtime": s["runtime"], "distro": s.get("wsl_distro"),
                          "cluster": {"label": label, "port": s.get("db_port") or 5432, "conf": s.get("conf")}}
    return out


def _main_dbs(services) -> dict:
    return {s["main_db"]: s["id"] for s in services if s.get("main_db")}


def _cluster_label(s) -> str:
    return "%s:%s" % (s.get("wsl_distro") or s.get("runtime"), s.get("db_port") or 5432)


def _rails(services, scratch_pattern=None) -> dict:
    """Keep-list inputs beyond main_db names, sent to the agent with every list/drop/scan.

    * main_filters: a service without db_name protects every DB its filter matches. Both
      spellings count: Odoo ignores `db_filter`, but the developer meant it.
    * unknown_main: a service with neither db_name nor a filter keeps every non-scratch DB
      on its cluster - we cannot tell which one is its main DB.
    """
    filters, unknown = [], {}
    for s in services:
        if s.get("main_db"):
            continue
        flt = s.get("dbfilter")
        if flt and str(flt).strip().lower() not in ("false", "none", ".*", "^.*$"):
            filters.append([s["id"], flt])
        else:
            unknown.setdefault(_cluster_label(s), []).append(s["id"])
    return {"main_filters": filters, "unknown_main": unknown,
            "scratch_pattern": scratch_pattern or DEFAULT_SCRATCH}


def _data_dirs(services, runtime, distro) -> list:
    return sorted({s["data_dir"] for s in services
                   if s.get("data_dir") and s.get("runtime") == runtime and s.get("wsl_distro") == distro})


def _job_index_path():
    return os.path.join(_home(), "local-jobs.json")


def _remember_job(job_id, svc, meta):
    p = _job_index_path()
    try:
        idx = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        idx = {}
    idx[job_id] = {"runtime": svc["runtime"], "distro": svc.get("wsl_distro"), "service": svc["id"],
                   "kind": meta.get("kind"), "created_at": _now()}
    if len(idx) > 200:
        for k in sorted(idx, key=lambda k: idx[k].get("created_at", ""))[:-200]:
            idx.pop(k)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(idx, fh, indent=1)
    os.replace(tmp, p)


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_job_id(kind):
    return "%s-%s-%s" % (kind, datetime.now().strftime("%Y%m%d%H%M%S"), uuid.uuid4().hex[:6])


def _safe_name(name, what="database") -> str:
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]{0,62}", name):
        raise ToolError("invalid %s name %r" % (what, name))
    return name


def _start_job(svc, kind, argv, meta, cwd=None, env=None):
    jid = _new_job_id(kind)
    meta = dict(meta, kind=kind, service=svc["id"])
    res = _call(svc, {"op": "job_start", "job_id": jid, "argv": argv, "cwd": cwd or svc.get("cwd"),
                      "env": env or {}, "meta": meta})
    _remember_job(jid, svc, meta)
    res["next"] = "continue with other work; call local_job job_id=%s when you need the result" % jid
    return res


def _venv_env(svc):
    py = svc.get("python") or ""
    P = _P(svc.get("runtime"))
    vbin = P.dirname(py) if "/" in py or "\\" in py else ""
    if not vbin:
        return {}
    sep = ";" if svc.get("runtime") == "windows" else ":"
    base = "%SystemRoot%\\system32" if svc.get("runtime") == "windows" else "/usr/local/bin:/usr/bin:/bin"
    return {"PATH": vbin + sep + base, "VIRTUAL_ENV": P.dirname(vbin)}


# -------------------------------------------------------------------- tools

def t_discover(args):
    write = args.get("write", True)
    out = {"distros": {}}
    for d in _distros(args):
        rt = "wsl" if os.name == "nt" else "linux"
        roots = args.get("roots") or ["~/workspace"]
        res = _call((rt, d), {"op": "discover", "roots": roots, "runtime": rt, "distro": d}, timeout=180)
        entry = {"services": [{k: s.get(k) for k in ("id", "odoo_version", "http_port", "db_port", "main_db",
                                                       "conf", "warnings")} | ({"running_pid": s["running_pid"]}
                                                                                if s.get("running_pid") else {})
                              for s in res["services"]],
                 "clusters": res["clusters"], "warnings": res["warnings"], "odoo_processes": res["odoo_processes"]}
        if write:
            entry["registry"] = registry.merge_discovered(res["services"], d)
        out["distros"][d or "local"] = entry
    proj = os.environ.get("ODOO_LOCAL_PROJECT_DIR") or os.environ.get("ODOO_MCP_PROJECT_DIR")
    if os.name == "nt" and proj and os.path.isdir(proj):
        res = _call(("windows", None), {"op": "discover", "roots": [proj], "runtime": "windows"}, timeout=120)
        winsvc = [s for s in res["services"] if re.match(r"^[A-Za-z]:", (s.get("odoo_bin") or s.get("conf") or ""))
                  and (not s.get("odoo_bin") or re.match(r"^[A-Za-z]:", s["odoo_bin"]))]
        out["windows"] = {"services": [s["id"] for s in winsvc], "warnings": res["warnings"]}
        if write and winsvc:
            out["windows"]["registry"] = registry.merge_discovered(winsvc, None)
    out["file"] = registry.path()
    return out


def t_services(args):
    svcs = registry.services()
    if args.get("id"):
        svcs = [registry.get(args["id"])]
    if not svcs:
        return {"services": [], "hint": "no services registered yet - run local_discover"}
    groups = {}
    for s in svcs:
        groups.setdefault((s["runtime"], s.get("wsl_distro")), []).append(s)
    out = []
    for (rt, d), group in groups.items():
        if rt == "docker":
            out += [{"id": s["id"], "state": "unmanaged", "note": "docker service: use the odoo docker skill"} for s in group]
            continue
        try:
            res = _call((rt, d), {"op": "status", "services": group, "deep": args.get("deep", True)}, timeout=120)
            out += res["services"]
        except ToolError as e:
            out += [{"id": s["id"], "state": "unknown", "error": str(e)} for s in group]
    return {"services": out}


def t_start(args):
    svc = registry.get(args["id"])
    return _call(svc, {"op": "start", "service": svc, "wait_s": args.get("wait_s", 40),
                       "extra_args": args.get("extra_args") or []}, timeout=150)


def t_stop(args):
    svc = registry.get(args["id"])
    return _call(svc, {"op": "stop", "service": svc}, timeout=120)


def t_restart(args):
    stopped = t_stop(args)
    started = t_start(args)
    return {"stop": stopped, "start": started}


def t_logs(args):
    svc = registry.get(args["id"])
    req = {"op": "logs", "service": svc}
    req.update({k: args[k] for k in ("lines", "grep", "errors_only", "since", "pid") if k in args})
    return _call(svc, req, timeout=60)


def t_module(args):
    svc = registry.get(args["id"])
    mods = [m for m in args["modules"] if re.fullmatch(r"[a-z0-9_]+", m)]
    if len(mods) != len(args["modules"]):
        raise ToolError("module names must be technical names (a-z, 0-9, _)")
    db = _safe_name(args.get("db") or svc.get("main_db") or "", "database") if (args.get("db") or svc.get("main_db")) else None
    if not db:
        raise ToolError("service %s has no main_db; pass db" % svc["id"])
    flag = "-i" if args.get("action", "upgrade") == "install" else "-u"
    extra = ["-d", db, "--db-filter=^%s$" % re.escape(db), flag, ",".join(mods), "--stop-after-init", "--no-http"]
    if args.get("test_tags"):
        extra += ["--test-enable", "--test-tags", args["test_tags"]]
    extra += args.get("extra_args") or []
    if not svc.get("python") or not svc.get("odoo_bin"):
        raise ToolError("service %s has no python/odoo_bin; run local_discover" % svc["id"])
    # --logfile= (empty) sends the log to stderr, which the job captures in out.log.
    argv = [svc["python"], svc["odoo_bin"], "-c", svc["conf"], "--logfile="] + extra
    cl = _clusters([svc])
    meta = {"modules": mods, "db": db, "cluster": next(iter(cl.values()))["cluster"] if cl else None,
            "action": flag}
    return _start_job(svc, "module", argv, meta, env=_venv_env(svc))


def t_job(args):
    jid = args["job_id"]
    try:
        idx = json.load(open(_job_index_path(), encoding="utf-8"))
    except (OSError, ValueError):
        idx = {}
    j = idx.get(jid)
    if not j:
        raise ToolError("unknown job %s (jobs are recorded in %s)" % (jid, _job_index_path()))
    return _call((j["runtime"], j["distro"]), {"op": "job_status", "job_id": jid, "tail": args.get("tail", 40)})


DUP_CODE = (
    "import sys, odoo\n"
    "from odoo.tools import config\n"
    "config.parse_config(['-c', sys.argv[1]])\n"
    "from odoo.service import db\n"
    "db.exp_duplicate_database(sys.argv[2], sys.argv[3])\n"
    "print('DUPLICATED', sys.argv[2], '->', sys.argv[3])\n"
)


def t_db(args):
    action = args["action"]
    svcs = registry.services()
    if action == "list":
        out = []
        for label, c in _clusters(svcs, args.get("id")).items():
            try:
                res = _call((c["runtime"], c["distro"]), {
                    "op": "db_list", "clusters": [c["cluster"]], "main_dbs": _main_dbs(svcs),
                    "rails": _rails(svcs),
                    "data_dirs": _data_dirs(svcs, c["runtime"], c["distro"]),
                    "activity": args.get("activity", True)}, timeout=300)
                out += res["clusters"]
            except ToolError as e:
                out.append({"cluster": label, "error": str(e)})
        return {"clusters": out}
    if not args.get("id"):
        raise ToolError("%s needs id (the service whose conf and cluster to use)" % action)
    svc = registry.get(args["id"])
    name = _safe_name(args.get("name"))
    if action == "create":
        mods = args.get("modules") or ["base"]
        if not all(re.fullmatch(r"[a-z0-9_]+", m) for m in mods):
            raise ToolError("module names must be technical names")
        major = int(str(svc.get("odoo_version") or "0").split(".")[0] or 0)
        demo = ["--with-demo"] if args.get("demo") and major >= 19 else ([] if args.get("demo") or major >= 19 else ["--without-demo=all"])
        argv = [svc["python"], svc["odoo_bin"], "-c", svc["conf"], "-d", name, "--db-filter=^%s$" % re.escape(name),
                "-i", ",".join(mods), "--stop-after-init", "--no-http", "--logfile="] + demo
        cl = next(iter(_clusters([svc]).values()))["cluster"]
        return _start_job(svc, "dbcreate", argv, {"modules": mods, "db": name, "cluster": cl}, env=_venv_env(svc))
    if action == "clone":
        src = _safe_name(args.get("source") or svc.get("main_db") or "")
        argv = [svc["python"], "-c", DUP_CODE, svc["conf"], src, name]
        return _start_job(svc, "dbclone", argv, {"db": name, "source": src},
                          cwd=svc.get("cwd") or (_P(svc["runtime"]).dirname(svc["odoo_bin"]) if svc.get("odoo_bin") else None),
                          env=_venv_env(svc))
    if action == "drop":
        c = next(iter(_clusters([svc]).values()))
        return _call(svc, {"op": "db_drop", "cluster": c["cluster"], "db": name, "main_dbs": _main_dbs(svcs),
                           "rails": _rails(svcs),
                           "data_dirs": _data_dirs(svcs, c["runtime"], c["distro"]),
                           "allow_roots": [_P(c["runtime"]).join(d, "filestore") for d in _data_dirs(svcs, c["runtime"], c["distro"])],
                           "backup_threshold_bytes": BACKUP_THRESHOLD}, timeout=1800)
    raise ToolError("unknown action %s" % action)


# ------------------------------------------------------------------ cleanup

def _plans_dir():
    return os.path.join(_home(), "local-plans")


def build_plan(scan: dict, distro, args) -> tuple:
    """Pure: turn an agent cleanup_scan into (public plan, private apply data)."""
    now = time.time()
    min_age = max(7, int(args.get("min_age_days", 30))) * 86400
    log_age = max(7, int(args.get("log_age_days", 30))) * 86400
    scratch = re.compile(args.get("scratch_pattern") or DEFAULT_SCRATCH, re.IGNORECASE)
    protected_name = re.compile(PROTECTED_NAME, re.IGNORECASE)
    where = distro or "local"
    items, keep, private = [], [], []
    for c in scan["databases"]:
        if "error" in c:
            continue
        for r in c.get("databases", []):
            target = "%s/%s" % (c["cluster"], r["name"])
            if r.get("keep"):
                keep.append({"target": target, "reason": r["keep"]})
                continue
            if not r.get("is_odoo"):
                keep.append({"target": target, "reason": "not an Odoo database"})
                continue
            age = (now - r["last_activity"]) if r.get("last_activity") else None
            why = []
            is_scratch = bool(scratch.search(r["name"]))
            ref_name = protected_name.search(r["name"])
            if is_scratch:
                why.append("scratch-style name")
            if age is not None and age >= min_age:
                why.append("inactive %d days" % (age // 86400))
            if ref_name and not is_scratch:
                keep.append({"target": target, "reason": "reference-copy name (%s): never dropped for inactivity alone"
                             % ref_name.group(1).lower()})
                continue
            if not why:
                keep.append({"target": target, "reason": "recent or not scratch (inactive %s days)"
                             % ("?" if age is None else int(age // 86400))})
                continue
            # Only a scratch-style name makes a DB disposable; one proposed for inactivity
            # alone, or carrying a reference-copy word, is always dumped first.
            backup = (not is_scratch) or bool(ref_name) or r["size_bytes"] >= BACKUP_THRESHOLD
            items.append({"kind": "scratch_db", "target": target, "size_bytes": r["size_bytes"],
                          "reason": ", ".join(why), "action": "drop", "backup": backup})
            private.append({"cluster_label": c["cluster"], "db": r["name"]})
    if scan.get("cluster_errors"):
        keep.append({"target": "%s:filestores" % where,
                     "reason": "a cluster could not be listed (%s); orphan filestores not judged"
                     % "; ".join(scan["cluster_errors"])[:300]})
    else:
        for f in scan["filestores"]:
            if f["db_exists"]:
                continue
            if now - f["mtime"] < 7 * 86400:
                keep.append({"target": "%s:%s" % (where, f["path"]), "reason": "orphan but modified < 7 days"})
                continue
            items.append({"kind": "orphan_filestore", "target": "%s:%s" % (where, f["path"]),
                          "size_bytes": f.get("size_bytes") or 0,
                          "reason": "database %s no longer exists on any cluster" % f["db"],
                          "action": "delete", "backup": False})
            private.append({"path": f["path"]})
    for c in scan["confs"]:
        if c["running"]:
            keep.append({"target": "%s:%s" % (where, c["conf"]), "reason": "service %s is running" % c["service"]})
        elif c["db_exists"] is False and now - c["mtime"] >= 14 * 86400:
            items.append({"kind": "dead_conf", "target": "%s:%s" % (where, c["conf"]), "size_bytes": 0,
                          "reason": "its database %s no longer exists" % c["main_db"], "action": "archive",
                          "backup": False})
            private.append({"path": c["conf"], "service": c["service"]})
    for lf in scan["logs"]:
        if now - lf["mtime"] >= log_age and not (lf["current"] and _running(scan, lf["service"])):
            items.append({"kind": "stale_log", "target": "%s:%s" % (where, lf["path"]),
                          "size_bytes": lf["size_bytes"],
                          "reason": "not written for %d days" % ((now - lf["mtime"]) // 86400),
                          "action": "delete", "backup": False})
            private.append({"path": lf["path"]})
    digest = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:10]
    plan = {"plan_id": "plan-%s-%s" % (datetime.now().strftime("%Y%m%d%H%M%S"), digest),
            "items": items, "keep": keep,
            "created_at": _now(), "expires_at": datetime.fromtimestamp(now + PLAN_TTL_S, timezone.utc)
            .replace(microsecond=0).isoformat(),
            "distro": distro, "total_bytes": sum(i["size_bytes"] or 0 for i in items)}
    return plan, private


def _running(scan, sid):
    return any(c["service"] == sid and c["running"] for c in scan["confs"])


def _keep_group(reason: str) -> str:
    r = re.sub(r"\d+(\.\d+)?", "N", reason)
    return re.split(r" of service | \(| - |: ", r, maxsplit=1)[0].strip()


def _prefix(name: str) -> str:
    return re.split(r"[_\-.]|\d", name, maxsplit=1)[0].lower() or name.lower()


def plan_view(plan: dict, plan_file: str, args: dict) -> dict:
    """What the tool returns. Default: a summary small enough to show a user, with the
    contract keys present (items / keep are the largest SUMMARY_TOP of each). detail=true
    returns one page of the full lists (offset / limit)."""
    items, keep = plan["items"], plan["keep"]
    head = {k: plan[k] for k in ("plan_id", "created_at", "expires_at", "distro", "total_bytes")}
    head.update({"items_total": len(items), "keep_total": len(keep), "plan_file": plan_file})
    if args.get("detail"):
        off = max(0, int(args.get("offset", 0)))
        lim = max(1, min(int(args.get("limit", PAGE_DEFAULT)), PAGE_MAX))
        head.update({"view": "page", "offset": off, "limit": lim,
                     "items": items[off:off + lim], "keep": keep[off:off + lim]})
        if off + lim < max(len(items), len(keep)):
            head["next_offset"] = off + lim
        return head
    by_kind, groups, reasons = {}, {}, {}
    for i in items:
        k = by_kind.setdefault(i["kind"], {"count": 0, "bytes": 0, "with_backup": 0})
        k["count"] += 1
        k["bytes"] += i["size_bytes"] or 0
        k["with_backup"] += 1 if i["backup"] else 0
        if i["kind"] == "scratch_db":
            cluster, _, name = i["target"].rpartition("/")
            g = groups.setdefault("%s %s*" % (cluster, _prefix(name)), {"count": 0, "bytes": 0})
            g["count"] += 1
            g["bytes"] += i["size_bytes"] or 0
    for k in keep:
        g = _keep_group(k["reason"])
        reasons[g] = reasons.get(g, 0) + 1
    top_groups = sorted(groups.items(), key=lambda kv: -kv[1]["bytes"])[:15]
    head.update({
        "view": "summary",
        "summary": {"by_kind": by_kind,
                    "scratch_db_groups": [dict(group=g, **v) for g, v in top_groups],
                    "scratch_db_groups_total": len(groups),
                    "keep_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1]))},
        "items": sorted(items, key=lambda i: -(i["size_bytes"] or 0))[:SUMMARY_TOP],
        "keep": [k for k in keep if k["reason"].startswith(("main", "reference", "protected"))][:SUMMARY_TOP],
        "more": "items/keep above are the largest %d drops and the first protected keeps; call "
                "local_cleanup_plan with plan_id=%s detail=true offset=0 for every item (paged), "
                "or read plan_file" % (SUMMARY_TOP, plan["plan_id"]),
    })
    return head


def _plan_file(plan_id: str) -> str:
    return os.path.join(_plans_dir(), os.path.basename(plan_id) + ".json")


def t_cleanup_plan(args):
    if args.get("plan_id"):
        try:
            stored = json.load(open(_plan_file(args["plan_id"]), encoding="utf-8"))
        except (OSError, ValueError):
            raise ToolError("unknown plan %s" % args["plan_id"])
        return plan_view(stored["plan"], _plan_file(args["plan_id"]), args)
    svcs_all = registry.services()
    plans = []
    for d in _distros(args):
        rt = "wsl" if os.name == "nt" else "linux"
        svcs = [s for s in svcs_all if s.get("runtime") == rt and s.get("wsl_distro") == d]
        if not svcs:
            continue
        clusters = [c["cluster"] for c in _clusters(svcs).values()]
        scan = _call((rt, d), {"op": "cleanup_scan", "services": svcs, "clusters": clusters,
                               "main_dbs": _main_dbs(svcs_all),
                               "rails": _rails(svcs_all, args.get("scratch_pattern"))}, timeout=600)
        plan, private = build_plan(scan, d, args)
        os.makedirs(_plans_dir(), exist_ok=True)
        stored = {"plan": plan, "private": private, "runtime": rt, "distro": d,
                  "scratch_pattern": args.get("scratch_pattern"),
                  "data_dirs": scan["data_dirs"],
                  "log_dirs": sorted({_P(rt).dirname(s["logfile"]) for s in svcs if s.get("logfile")}),
                  "clusters": {c["label"]: c for c in clusters}}
        with open(_plan_file(plan["plan_id"]), "w", encoding="utf-8") as fh:
            json.dump(stored, fh, indent=1)
        plans.append(plan_view(plan, _plan_file(plan["plan_id"]), args))
    if not plans:
        return {"plan_id": None, "items": [], "keep": [], "note": "no registered services - run local_discover"}
    if len(plans) == 1:
        return plans[0]
    return {"plans": plans, "note": "one plan per distro; apply each plan_id separately"}


def t_cleanup_apply(args):
    p = os.path.join(_plans_dir(), os.path.basename(args["plan_id"]) + ".json")
    try:
        stored = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        raise ToolError("unknown plan %s - create one with local_cleanup_plan and show it to the user first"
                        % args["plan_id"])
    plan = stored["plan"]
    if datetime.fromisoformat(plan["expires_at"]).timestamp() < time.time():
        raise ToolError("plan %s expired; make a fresh plan (state may have changed)" % plan["plan_id"])
    if stored.get("applied_at"):
        raise ToolError("plan %s was already applied at %s" % (plan["plan_id"], stored["applied_at"]))
    only = set(args.get("only") or [])
    unknown = only - {i["target"] for i in plan["items"]}
    if unknown:
        raise ToolError("not in the plan: %s" % ", ".join(sorted(unknown)))
    svcs = registry.services()
    rt, d = stored["runtime"], stored["distro"]
    allow = [_P(rt).join(x, "filestore") for x in stored["data_dirs"]] + stored["log_dirs"]
    results = []
    for item, priv in zip(plan["items"], stored["private"]):
        if only and item["target"] not in only:
            continue
        req = {"op": "apply_item", "item": dict(item, target=priv.get("path") or item["target"]),
               "allow_roots": allow, "clusters": list(stored["clusters"].values())}
        if item["kind"] == "scratch_db":
            req["drop"] = {"cluster": stored["clusters"][priv["cluster_label"]], "db": priv["db"],
                           "main_dbs": _main_dbs(svcs), "rails": _rails(svcs, stored.get("scratch_pattern")),
                           "data_dirs": stored["data_dirs"], "allow_roots": allow,
                           "backup_threshold_bytes": BACKUP_THRESHOLD}
        res = runner.call(rt, d, req, timeout=1800)
        results.append({"target": item["target"], "ok": res.get("ok", False),
                        "result": res.get("result") if res.get("ok") else res.get("error"),
                        "refused": bool(res.get("refused"))})
        if not res.get("ok") and not res.get("refused"):
            results.append({"stopped": "unexpected error - remaining items not applied"})
            break
    stored["applied_at"] = _now()
    stored["apply_results"] = results
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(stored, fh, indent=1)
    return {"plan_id": plan["plan_id"], "results": results}


def t_snapshot(args):
    out = {}
    for d in _distros(args):
        out[d or "local"] = _call(("wsl" if os.name == "nt" else "linux", d), {"op": "snapshot"})
    return out


def t_relaunch(args):
    out = {}
    for d in _distros(args):
        out[d or "local"] = _call(("wsl" if os.name == "nt" else "linux", d),
                                  {"op": "relaunch", "snapshot": args.get("snapshot")}, timeout=180)
    return out


HANDLERS = {
    "local_discover": t_discover, "local_services": t_services, "local_start": t_start, "local_stop": t_stop,
    "local_restart": t_restart, "local_logs": t_logs, "local_module": t_module, "local_job": t_job,
    "local_db": t_db, "local_cleanup_plan": t_cleanup_plan, "local_cleanup_apply": t_cleanup_apply,
    "local_snapshot": t_snapshot, "local_relaunch": t_relaunch,
}


def dispatch(name: str, args: dict):
    fn = HANDLERS.get(name)
    if fn is None:
        return "unknown tool %s" % name, True
    try:
        return json.dumps(fn(args or {}), indent=1, default=str, ensure_ascii=False), False
    except (ToolError, registry.RegistryError) as e:
        return str(e), True
