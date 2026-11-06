#!/usr/bin/env python3
"""Local Odoo provisioning for `odoo_mcp.py local` - no questions asked.

Finds the project's Odoo conf, confirms Odoo answers on a LOOPBACK url, creates an
expiring API key for the local admin through the project's own `odoo-bin shell`,
and verifies the key authenticates. odoo_mcp.py then writes the result as instance
"local" of the folder's project in ~/.odoo-mcp/profiles.json.

Refuses any non-loopback target: only localhost / *.localhost / 127.x.x.x / ::1.
Standard library only. `--self-test` checks the pure helpers.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
import xmlrpc.client
from datetime import datetime, timedelta, timezone
from pathlib import Path

# The server package lives in <plugin>/mcp. These CLIs sit outside it so the server
# itself contains no process-execution path (tests/mcp enforce that).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp"))

import config as C  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SHELL_CODE = r'''
from datetime import timedelta
from odoo import fields, release
login = %(login)r
user = env['res.users'].with_context(active_test=False).search([('login', '=', login)], limit=1) if login else None
if not user:
    user = env.ref('base.user_admin')
keys = env['res.users.apikeys'].with_user(user)
exp = fields.Datetime.now() + timedelta(days=%(days)d)
try:
    key = keys._generate('rpc', 'claude-mcp-local', exp)
except TypeError:
    key = keys._generate('rpc', 'claude-mcp-local')
env.cr.commit()
print('MCP_LOGIN=' + user.login)
print('MCP_VERSION=' + release.version)
print('MCP_KEY=' + key)
'''


def _die(msg: str, code: int = 2) -> None:
    print("odoo_mcp local: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


def _now_iso(delta_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=delta_days)).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Odoo probes (unauthenticated)
# --------------------------------------------------------------------------


def _jsonrpc(url: str, path: str, params=None, timeout: int = 10):
    body = json.dumps({"jsonrpc": "2.0", "method": "call", "params": params or {}}).encode()
    req = urllib.request.Request(url + path, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(str(data["error"])[:300])
    return data.get("result") if isinstance(data, dict) else None


def server_version(url: str):
    try:
        info = _jsonrpc(url, "/web/webclient/version_info")
        if isinstance(info, dict):
            return info
    except Exception:
        pass
    try:
        info = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common").version()
        return info if isinstance(info, dict) else None
    except Exception:
        return None


def list_databases(url: str):
    try:
        res = _jsonrpc(url, "/web/database/list")
        return [str(d) for d in res] if isinstance(res, list) else None
    except Exception:
        return None


def verify_key(url: str, db: str, login: str, key: str, major: int) -> bool:
    try:
        if major >= 19:
            req = urllib.request.Request(
                url + "/json/2/res.users/context_get", data=b"{}", method="POST",
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                         "X-Odoo-Database": db})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status == 200
        uid = xmlrpc.client.ServerProxy(url + "/xmlrpc/2/common").authenticate(db, login, key, {})
        if isinstance(uid, dict):
            uid = uid.get("uid")
        return isinstance(uid, int) and not isinstance(uid, bool) and uid > 0
    except Exception:
        return False


# --------------------------------------------------------------------------
# Conf helpers
# --------------------------------------------------------------------------


def read_conf(path: Path) -> dict:
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.read(path, encoding="utf-8")
    opt = cp["options"] if cp.has_section("options") else {}
    port = opt.get("http_port") or opt.get("xmlrpc_port") or "8069"
    db = opt.get("db_name") or ""
    return {
        "port": str(port).strip(),
        "db": "" if db.strip() in ("", "False", "false") else db.strip(),
        "dbfilter": (opt.get("dbfilter") or "").strip(),
    }


def find_odoo_bin(*roots: Path):
    for root in roots:
        for depth in ("odoo-bin", "*/odoo-bin", "*/*/odoo-bin"):
            for hit in sorted(root.glob(depth)):
                if hit.is_file():
                    return hit
    return None


def pick_database(conf: dict, found):
    if conf.get("db"):
        return conf["db"], None
    if not found:
        return None, "the server does not list databases and the conf pins none - pass --db"
    cands = list(found)
    flt = conf.get("dbfilter") or ""
    if flt and "%" not in flt:
        try:
            cands = [d for d in cands if re.match(flt, d)]
        except re.error:
            pass
    if len(cands) == 1:
        return cands[0], None
    return None, "several databases match (%s) - pass --db <name> for the one this task needs" % (
        ", ".join(cands))


def _expired(raw: dict) -> bool:
    exp = raw.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) \
            <= datetime.now(timezone.utc)
    except ValueError:
        return False


# --------------------------------------------------------------------------
# Project and provisioning
# --------------------------------------------------------------------------


def project_for(folder: Path, cfg):
    """(project name, paths, created) for a local instance in `folder`.

    A bound folder keeps its project. An unbound one gets a new project named after
    its MAIN checkout (never a worktree path), so every worktree of it matches later."""
    folders = C.session_folders(folder)
    if cfg is not None:
        project = cfg.match(folders)
        if project is not None:
            return project.name, list(project.paths), False
    main = Path(os.path.abspath(str(folders[-1])))
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", main.name) or "project"
    if cfg is not None and name in cfg.projects:
        _die("project %s exists for other folders; pass --project" % name)
    return name, [str(main)], True


def provision(project: Path, args) -> dict:
    """Create and verify a key on the local Odoo. Returns the instance values (with the
    key), or with --dry-run what it would connect to (no key)."""
    conf_path = Path(args.conf).resolve() if args.conf else None
    if conf_path is None and not args.url:
        confs = C.discover(project).get("conf_files") or []
        if not confs:
            _die("no Odoo conf found under %s - pass --conf, or --url and --db" % project)
        conf_path = Path(confs[0]).resolve()
    conf = read_conf(conf_path) if conf_path else {"port": "8069", "db": "", "dbfilter": ""}

    url = (args.url or "http://127.0.0.1:%s" % conf["port"]).rstrip("/")
    if not C.is_loopback(url):
        _die("%s is not a loopback address. `local` only connects to this machine; add remote "
             "instances with `odoo_mcp.py add`." % url)

    info = server_version(url)
    if not info:
        _die("Odoo is not answering at %s. Start the local server first, then re-run." % url, 4)
    ver = str(info.get("server_version") or "")
    try:
        major = int((info.get("server_version_info") or [0])[0])
    except (TypeError, ValueError, IndexError):
        major = 0

    conf_for_pick = dict(conf)
    if args.db:
        conf_for_pick["db"] = args.db
    db, why = pick_database(conf_for_pick, list_databases(url))
    if not db:
        _die(why)

    if args.dry_run:
        return {"dry_run": True, "would_connect": url, "db": db, "odoo_version": ver,
                "conf": str(conf_path) if conf_path else None}

    if args.odoo_cmd:
        base_cmd = shlex.split(args.odoo_cmd, posix=os.name != "nt")
    else:
        roots = [project] + ([conf_path.parent, conf_path.parent.parent] if conf_path else [])
        odoo_bin = find_odoo_bin(*roots)
        if not odoo_bin:
            _die("cannot find odoo-bin near %s. Pass --odoo-cmd with the command you use to start "
                 "Odoo, e.g. --odoo-cmd \"/path/venv/bin/python /path/odoo-bin\" or "
                 "--odoo-cmd \"docker compose exec -T odoo odoo\"." % project)
        base_cmd = [args.python or sys.executable, str(odoo_bin)]
    shell_conf = args.shell_conf or (str(conf_path) if conf_path else None)
    cmd = base_cmd + ["shell", "-d", db, "--no-http", "--log-level=warn"]
    if shell_conf:
        cmd[len(base_cmd):len(base_cmd)] = ["-c", shell_conf]

    code = SHELL_CODE % {"login": args.login or "", "days": args.expire_days}
    try:
        proc = subprocess.run(cmd, input=code, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=args.timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        _die("could not run odoo shell (%s): %s" % (" ".join(cmd[:3]), exc), 4)
    values = {}
    for line in proc.stdout.splitlines():
        if line.startswith("MCP_") and "=" in line:
            k, v = line.split("=", 1)
            values[k] = v.strip()
    key = values.get("MCP_KEY")
    if not key:
        tail = "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-8:])
        _die("odoo shell did not return a key (exit %s). Last lines:\n%s" % (proc.returncode, tail), 4)
    login = values.get("MCP_LOGIN", "admin")

    if not verify_key(url, db, login, key, major):
        _die("the new key did not authenticate against %s / %s - nothing was written." % (url, db), 4)

    return {
        "url": url,
        "db": db,
        "username": login,
        "api_key": key,
        "tier": "local",
        "access": "full",
        "conf": str(conf_path) if conf_path else None,
        "odoo_version": values.get("MCP_VERSION", ver),
        "created_at": _now_iso(),
        "expires_at": _now_iso(args.expire_days),
    }


def prune_expired(doc: dict, keep: str = "") -> list:
    """Drop local instances whose key has expired, in every project. Returns their names."""
    removed = []
    for pname, proj in (doc.get("projects") or {}).items():
        instances = proj.get("instances") or {}
        for iname in list(instances):
            raw = instances[iname]
            q = "%s/%s" % (pname, iname)
            if q != keep and isinstance(raw, dict) and str(raw.get("tier") or "local") == "local" \
                    and C.is_loopback(str(raw.get("url") or "")) and _expired(raw):
                del instances[iname]
                if proj.get("default") == iname:
                    del proj["default"]
                removed.append(q)
    return removed


def self_test() -> int:
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    check("loopback ok", C.is_loopback("http://127.0.0.1:8069") and C.is_loopback("http://acme.localhost"))
    check("remote refused", not C.is_loopback("https://acme-stage.example.com"))
    check("conf db wins", pick_database({"db": "x"}, ["a", "b"]) == ("x", None))
    check("single db picked", pick_database({"db": ""}, ["only"]) == ("only", None))
    check("dbfilter narrows", pick_database({"db": "", "dbfilter": "^c2_.*$"}, ["c1_a", "c2_b"])[0] == "c2_b")
    check("ambiguous refuses", pick_database({"db": ""}, ["a", "b"])[0] is None)
    check("expired detects", _expired({"expires_at": "2000-01-01T00:00:00Z"}))
    doc = {"projects": {"p": {"default": "local", "instances": {
        "local": {"url": "http://127.0.0.1:1", "expires_at": "2000-01-01T00:00:00Z"},
        "stage": {"url": "https://s.example.com", "tier": "stage", "expires_at": "2000-01-01T00:00:00Z"}}}}}
    check("prune drops only expired locals", prune_expired(doc) == ["p/local"]
          and list(doc["projects"]["p"]["instances"]) == ["stage"])
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true", help="check the pure helpers")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
