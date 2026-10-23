"""Version-1 profiles.json and project .mcp.json Odoo servers -> version 2.

Two steps, so a human reviews before anything changes:

  build_plan(v1, scan_roots)   a JSON plan that names every source but holds NO key:
                               projects, instances (tier / access / db proposed, safe side
                               first), servers to retire, pins to remove, notes, and the
                               questions only the developer can answer ("unresolved").
  apply_plan(plan, v1, ...)    refuses while anything is unresolved; pulls usernames and keys
                               from the sources; needs the developer's yes for every remote
                               instance above read; backs up everything it touches.

Tiers are never guessed toward the weaker side: a remote profile becomes "prod" unless it
says otherwise or its name says stage, and every prod instance is proposed read-only.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp"))

import config as C  # noqa: E402
from session import audit  # noqa: E402

_V1_TIER = {"staging": "stage", "stage": "stage", "production": "prod", "prod": "prod",
            "local": "local"}
_V1_CEILING = {"write+unlink": "full", "write": "write", "read": "read"}
_PROD_NAME = re.compile(r"(?i)(prod|production|-ro$)")
_REBUILD_DB = re.compile(r"-\d+$")
_EXPORT = re.compile(r"export\s+((?:[A-Za-z_][A-Za-z0-9_]*=\S+\s*)+)")
_SKIP_DIRS = ("/.claude/worktrees/", "/node_modules/", "/.git/")


def _die(msg: str, code: int) -> None:
    print("odoo_mcp migrate: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


def _url(url) -> str:
    return str(url or "").strip().rstrip("/")


def _odoo_sh_stage_db(url: str, db: str) -> bool:
    host = (C.origin(url)[1] or "")
    return host.endswith(".odoo.com") and bool(_REBUILD_DB.search(db or ""))


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def _v1_tier(name: str, raw: dict) -> str:
    tier = _V1_TIER.get(str(raw.get("tier") or "").strip().lower())
    if tier:
        return tier
    if str(raw.get("production") or "").lower() in ("1", "true", "yes", "on") or raw.get("production") is True:
        return "prod"
    if _PROD_NAME.search(name):
        return "prod"
    if C.is_loopback(_url(raw.get("url"))):
        return "local"
    return "stage"


def _v1_stage_access(raw: dict) -> str:
    ceiling = str(raw.get("ceiling") or "").strip().lower()
    if ceiling in _V1_CEILING:
        return _V1_CEILING[ceiling]
    allow = raw.get("allow_unlink")
    if allow is True or str(allow).lower() in ("1", "true", "yes", "on"):
        return "full"
    return "write"


def _server_settings(spec: dict) -> dict:
    """ODOO_* settings of a project .mcp.json server: its env, plus `export K=V`
    segments inside a `bash -lc` argument."""
    out = {}
    for arg in spec.get("args") or []:
        for m in _EXPORT.finditer(str(arg)):
            for pair in m.group(1).split():
                k, _, v = pair.partition("=")
                out[k] = v
    env = spec.get("env") or {}
    if isinstance(env, dict):
        out.update({str(k): str(v) for k, v in env.items()})
    return out


def _is_odoo_server(spec: dict) -> bool:
    text = " ".join([str(spec.get("command") or "")] + [str(a) for a in spec.get("args") or []])
    text += json.dumps(spec.get("env") or {})
    return "odoo_xmlrpc_mcp.py" in text or "ODOO_URL" in text


def _windows_path(p: str) -> str:
    m = re.match(r"^/mnt/([a-zA-Z])/(.*)$", p)
    return "%s:/%s" % (m.group(1).upper(), m.group(2)) if m else p


def _find(roots: list, filename: str) -> list:
    found = []
    for root in roots:
        root = Path(root)
        for pattern in (filename, "*/" + filename, "*/*/" + filename, "*/*/*/" + filename):
            for hit in sorted(root.glob(pattern)):
                if hit.is_file() and not any(s in hit.as_posix() for s in _SKIP_DIRS):
                    found.append(hit)
    return found


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name) or "project"


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------


def build_plan(v1, scan_roots: list) -> dict:
    plan: dict = {"version": 2, "projects": {}, "retire": [], "remove_pins": [],
                  "notes": [], "unresolved": []}
    seen: dict = {}          # (url, db) -> "project/instance" kept

    def add(pname: str, paths: list, iname: str, spec: dict):
        key = (_url(spec["url"]).lower(), spec.get("db") or "")
        if key in seen:
            plan["notes"].append("merged %s into %s (same url and db)" % (spec["from"], seen[key]))
            return
        project = plan["projects"].setdefault(pname, {"paths": [], "default": None, "instances": {}})
        for p in paths:
            if p not in project["paths"]:
                project["paths"].append(p)
        project["instances"][iname] = spec
        seen[key] = "%s/%s" % (pname, iname)

    profiles = (v1 or {}).get("profiles") or {}
    project_map = (v1 or {}).get("project_map") or {}
    for name, raw in profiles.items():
        if str(name).startswith("//") or not isinstance(raw, dict):
            continue
        url = _url(raw.get("url"))
        tier = _v1_tier(name, raw)
        db = str(raw.get("db") or raw.get("database") or "").strip()
        if tier == "stage" and _odoo_sh_stage_db(url, db):
            db = "auto"
        access = {"prod": "read", "local": "full"}.get(tier) or _v1_stage_access(raw)
        paths = list(raw.get("projects") or [])
        if isinstance(raw.get("projects"), str):
            paths = [raw["projects"]]
        paths += [str(k) for k, v in project_map.items() if v == name and not str(k).startswith("//")]
        stem = _safe_name(str(name).split("-", 1)[0].lower())
        add(stem, paths, _safe_name(str(name)),
            {"from": "v1:%s" % name, "url": url, "db": db, "tier": tier, "access": access})

    for mcp_json in _find(scan_roots, ".mcp.json"):
        try:
            servers = json.loads(mcp_json.read_text(encoding="utf-8-sig")).get("mcpServers") or {}
        except (OSError, ValueError, AttributeError):
            plan["notes"].append("could not read %s" % mcp_json)
            continue
        names = [n for n, s in servers.items() if isinstance(s, dict) and _is_odoo_server(s)]
        if not names:
            continue
        folder = mcp_json.parent
        pname = _safe_name(folder.name)
        for sname in names:
            settings = _server_settings(servers[sname])
            url = _url(settings.get("ODOO_URL"))
            db = settings.get("ODOO_DB", "")
            if C.is_loopback(url):
                tier, access = "local", "full"
            elif _PROD_NAME.search(sname):
                tier, access = "prod", "read"
            else:
                tier = "stage"
                access = "write" if settings.get("ODOO_ALLOW_WRITE", "").lower() in ("1", "true") \
                    else "read"
                if _odoo_sh_stage_db(url, db):
                    db = "auto"
            iname = _safe_name(re.sub(r"^odoo[-_]", "", sname) or sname)
            add(pname, [str(folder)], iname,
                {"from": "mcp:%s#%s" % (mcp_json, sname), "url": url, "db": db,
                 "tier": tier, "access": access})
        settings_local = folder / ".claude" / "settings.local.json"
        mcp_dir = folder / ".claude" / "mcp"
        plan["retire"].append({
            "mcp_json": str(mcp_json), "servers": names,
            "settings_local": str(settings_local) if settings_local.is_file() else None,
            "mcp_dir": str(mcp_dir) if mcp_dir.is_dir() else None,
        })

    plan["remove_pins"] = [str(p) for p in _find(scan_roots, ".odoo-mcp.json")]

    prod_dbs: dict = {}
    for pname, project in plan["projects"].items():
        if not project["paths"]:
            plan["unresolved"].append(
                "project '%s' has no paths - fill \"paths\" with its folder(s)" % pname)
        stages = [n for n, s in project["instances"].items() if s["tier"] == "stage"]
        project["default"] = stages[0] if len(stages) == 1 else None
        for iname, spec in project["instances"].items():
            if spec["tier"] != "prod":
                continue
            if not spec.get("db") or spec["db"] == "auto":
                plan["unresolved"].append(
                    "instance %s/%s is prod and has no db - fill \"db\" (production is never "
                    "picked automatically)" % (pname, iname))
            else:
                prod_dbs.setdefault(spec["db"], []).append("%s/%s" % (pname, iname))
    for db, owners in prod_dbs.items():
        projects = {o.split("/")[0] for o in owners}
        if len(projects) > 1:
            plan["unresolved"].append(
                "prod instances %s share database %s - check which one is right"
                % (", ".join(owners), db))
    return plan


# --------------------------------------------------------------------------
# Apply
# --------------------------------------------------------------------------


_V1_OPTIONAL = ("lang", "tz", "timeout", "verify_ssl", "companies", "allowed_company_ids",
                "allow_write_models", "db_pattern")


def _source_values(source: str, v1) -> dict:
    """username + api_key (and optional keys) from where an instance came from."""
    kind, _, ref = source.partition(":")
    if kind == "v1":
        raw = ((v1 or {}).get("profiles") or {}).get(ref)
        if not isinstance(raw, dict):
            _die("plan source %s is not in the version-1 file" % source, 2)
        out = {"url": _url(raw.get("url")), "db": str(raw.get("db") or raw.get("database") or ""),
               "username": str(raw.get("username") or raw.get("login") or ""),
               "api_key": str(raw.get("api_key") or raw.get("password") or "")}
        out.update({k: raw[k] for k in _V1_OPTIONAL if k in raw})
        return out
    if kind == "mcp":
        path, _, server = ref.rpartition("#")
        if Path(path).name != ".mcp.json":
            _die("plan source %s is not a .mcp.json server" % source, 2)
        try:
            spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))["mcpServers"][server]
        except (OSError, ValueError, KeyError, TypeError):
            _die("plan source %s cannot be read" % source, 2)
        s = _server_settings(spec)
        key = s.get("ODOO_API_KEY") or s.get("ODOO_PASSWORD") or ""
        project = C.norm_path(Path(path).parent)
        for var in ("ODOO_API_KEY_FILE", "ODOO_PASSWORD_FILE"):
            if not key and s.get(var):
                key_file = Path(_windows_path(s[var]))
                # A cloned repo's .mcp.json must not turn any file on this machine into
                # the password sent to the url it names.
                if not C.norm_path(key_file).startswith(project + "/"):
                    _die("%s names key file %s, outside its project folder - not read. Add this "
                         "instance's key with odoo_mcp.py add after migrating." % (source, key_file), 2)
                try:
                    key = key_file.read_text(encoding="utf-8").strip()
                except OSError:
                    _die("cannot read %s for %s" % (s[var], source), 2)
        return {"url": _url(s.get("ODOO_URL")), "db": s.get("ODOO_DB", ""),
                "username": s.get("ODOO_USERNAME", ""), "api_key": key}
    _die("unknown plan source %r" % source, 2)


def _backup_dir() -> Path:
    bdir = C.home() / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(bdir, 0o700)
    except OSError:
        pass
    return bdir


def _copy(src: Path, dst: Path) -> None:
    shutil.copyfile(src, dst)
    try:
        os.chmod(dst, 0o600)
    except OSError:
        pass


def _write_json(path: Path, doc: dict) -> None:
    path.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def _retire(entry: dict, bdir: Path, stamp: str) -> dict:
    done: dict = {"mcp_json": entry["mcp_json"]}
    mj = Path(entry["mcp_json"])
    remaining = set()
    if mj.is_file():
        tag = _safe_name(mj.parent.name)
        _copy(mj, bdir / ("mcp-json-%s-%s.json" % (tag, stamp)))
        doc = json.loads(mj.read_text(encoding="utf-8-sig"))
        servers = doc.get("mcpServers") or {}
        for name in entry["servers"]:
            servers.pop(name, None)
        remaining = set(servers)
        _write_json(mj, doc)
        done["removed_servers"] = entry["servers"]
    sl = entry.get("settings_local")
    if sl and Path(sl).is_file():
        p = Path(sl)
        _copy(p, bdir / ("settings-local-%s-%s.json" % (_safe_name(mj.parent.name), stamp)))
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        enabled = doc.get("enabledMcpjsonServers")
        if isinstance(enabled, list):
            doc["enabledMcpjsonServers"] = [n for n in enabled
                                            if n not in entry["servers"] and n in remaining]
            _write_json(p, doc)
    md = entry.get("mcp_dir")
    if md and Path(md).is_dir():
        target = Path(md).with_name("mcp.retired-%s" % stamp[:8])
        n = 2
        while target.exists():
            target = Path(md).with_name("mcp.retired-%s-%d" % (stamp[:8], n))
            n += 1
        Path(md).rename(target)
        done["mcp_dir_renamed_to"] = str(target)
    return done


def _check_plan_paths(plan: dict) -> None:
    """A plan is a file anyone can edit: it may only touch what migration owns -
    .odoo-mcp.json pins, .mcp.json files, and the .claude/settings.local.json and
    .claude/mcp beside them."""
    for pin in plan.get("remove_pins") or []:
        if Path(pin).name != ".odoo-mcp.json":
            _die("remove_pins may only name .odoo-mcp.json files, not %s" % pin, 2)
    for entry in plan.get("retire") or []:
        mj = Path(entry.get("mcp_json") or "")
        if mj.name != ".mcp.json":
            _die("retire may only edit .mcp.json files, not %s" % mj, 2)
        claude = mj.parent / ".claude"
        sl, md = entry.get("settings_local"), entry.get("mcp_dir")
        if sl and C.norm_path(sl) != C.norm_path(claude / "settings.local.json"):
            _die("retire may only edit %s, not %s" % (claude / "settings.local.json", sl), 2)
        if md and C.norm_path(md) != C.norm_path(claude / "mcp"):
            _die("retire may only rename %s, not %s" % (claude / "mcp", md), 2)


def apply_plan(plan: dict, v1, approved_by) -> dict:
    if plan.get("unresolved"):
        _die("the plan still has open questions - answer them in the plan, empty "
             "\"unresolved\", then apply:\n  - %s" % "\n  - ".join(plan["unresolved"]), 2)
    _check_plan_paths(plan)

    doc: dict = {"version": 2, "projects": {}}
    for pname, project in (plan.get("projects") or {}).items():
        out: dict = {"paths": list(project.get("paths") or []), "instances": {}}
        if project.get("default"):
            out["default"] = project["default"]
        for iname, spec in (project.get("instances") or {}).items():
            raw = _source_values(spec["from"], v1)
            if spec.get("url") and C.origin(_url(spec["url"])) != C.origin(raw["url"]):
                _die("the plan moves %s/%s from %s to %s. A key is only ever sent where it came "
                     "from: migrate it unchanged, then point it elsewhere with odoo_mcp.py add "
                     "and that host's key." % (pname, iname, raw["url"], spec["url"]), 2)
            raw.update({k: spec[k] for k in ("url", "db", "tier", "access", "db_pattern")
                        if spec.get(k) not in (None, "")})
            out["instances"][iname] = raw
        doc["projects"][pname] = out

    try:
        cfg = C.parse(json.dumps(doc), C.config_path())
    except C.ConfigError as exc:
        _die(str(exc), 2)
    reasons = []
    for project in cfg.projects.values():
        for inst in project.instances.values():
            if isinstance(inst, C.BrokenInstance):
                _die(inst.error, 2)
            reasons += C.widenings(None, inst)
    given = (approved_by or "").strip()
    if reasons and len(given) < 2 and not sys.stdin.isatty():
        _die("these instances can write once migrated - the developer's yes is needed "
             "(--approved-by \"<their answer>\"):\n  - %s" % "\n  - ".join(reasons), 3)

    bdir = _backup_dir()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    current = C.config_path()
    if current.is_file() and not (bdir / "profiles-v1.json").exists():
        _copy(current, bdir / "profiles-v1.json")
    try:
        C.save(doc)
    except C.ConfigError as exc:
        _die(str(exc), 2)

    retired = [_retire(entry, bdir, stamp) for entry in plan.get("retire") or []]
    pins = []
    for pin in plan.get("remove_pins") or []:
        p = Path(pin)
        if p.is_file():
            _copy(p, bdir / ("pin-%s-%s.json" % (_safe_name(p.parent.name), stamp)))
            p.unlink()
            pins.append(str(p))
    audit({"action": "migrate", "projects": sorted(doc["projects"]),
           "retired": [r["mcp_json"] for r in retired], "pins_removed": pins,
           "widenings": reasons, "approved_by": (given or "terminal")[:200]})
    return {"migrated": sorted(doc["projects"]), "file": str(current), "retired": retired,
            "pins_removed": pins, "backups": str(bdir)}
