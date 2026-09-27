#!/usr/bin/env python3
"""Create, list and prune LOCAL Odoo MCP connection profiles - no questions asked.

Local profiles are tool-owned: one file per project checkout in
~/.odoo-mcp/local/<project-key>.json. Claude runs this script itself when it needs
a live local instance; nothing here touches the developer's servers file.

  provision  Find the project's Odoo conf, confirm Odoo answers on a LOOPBACK url,
             create an API key for the local admin through the project's own
             `odoo-bin shell`, verify the key authenticates, then write the profile.
  list       Show local profiles (never the keys).
  prune      Remove profiles whose project is gone, whose key expired, or whose
             database no longer exists; delete files left empty.

Refuses any non-loopback target: only localhost / 127.x / ::1 / *.localhost / *.test.
Standard library only. `--self-test` checks the pure helpers.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
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

import profiles as P  # noqa: E402

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
    print("local_profile: %s" % msg, file=sys.stderr)
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
# Conf + store helpers
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


def store_path(project: Path) -> Path:
    return P.local_dir() / (P.project_key(project) + ".json")


def load_store(path: Path) -> dict:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def save_store(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


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
        import re

        try:
            cands = [d for d in cands if re.match(flt, d)]
        except re.error:
            pass
    if len(cands) == 1:
        return cands[0], None
    return None, "several databases match (%s) - pass --db <name> for the one this task needs" % (
        ", ".join(cands))


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_provision(args) -> int:
    project = Path(args.project or os.getcwd()).resolve()

    conf_path = Path(args.conf).resolve() if args.conf else None
    if conf_path is None and not args.url:
        confs = P.discover(project).get("conf_files") or []
        if not confs:
            _die("no Odoo conf found under %s - pass --conf, or --url and --db" % project)
        conf_path = Path(confs[0]).resolve()
    conf = read_conf(conf_path) if conf_path else {"port": "8069", "db": "", "dbfilter": ""}

    url = (args.url or "http://127.0.0.1:%s" % conf["port"]).rstrip("/")
    if not P.is_loopback(url):
        _die("%s is not a loopback address. Local provisioning only connects to this machine; "
             "remote instances are defined by the developer in servers.json." % url)

    info = server_version(url)
    if not info:
        _die("Odoo is not answering at %s. Start the local server first, then re-run." % url, 3)
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
        print(json.dumps({"would_connect": url, "db": db, "odoo_version": ver,
                          "conf": str(conf_path) if conf_path else None,
                          "store": str(store_path(project))}, indent=2))
        return 0

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
        _die("the new key did not authenticate against %s / %s - nothing was written." % (url, db), 5)

    path = store_path(project)
    doc = load_store(path)
    doc["version"] = 1
    doc["project_dir"] = str(project)
    doc["active"] = db
    doc.setdefault("profiles", {})[db] = {
        "url": url,
        "db": db,
        "username": login,
        "api_key": key,
        "tier": "local",
        "conf": str(conf_path) if conf_path else None,
        "odoo_version": values.get("MCP_VERSION", ver),
        "created_at": _now_iso(),
        "expires_at": _now_iso(args.expire_days),
    }
    save_store(path, doc)
    print(json.dumps({
        "provisioned": "local:%s/%s" % (project.name, db),
        "url": url, "database": db, "login": login,
        "odoo_version": values.get("MCP_VERSION", ver),
        "key_expires_at": doc["profiles"][db]["expires_at"],
        "store": str(path),
        "next": "call odoo_status - the MCP server picks this up without a restart",
    }, indent=2))
    return 0


def _iter_stores():
    folder = P.local_dir()
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            yield path, load_store(path)


def cmd_list(args) -> int:
    project = Path(args.project or os.getcwd()).resolve()
    rows = []
    for path, doc in _iter_stores():
        pdir = doc.get("project_dir")
        if not args.all and not (pdir and P._under(project, Path(pdir))):
            continue
        for db, prof in (doc.get("profiles") or {}).items():
            rows.append({"profile": "local:%s/%s" % (Path(str(pdir)).name, db),
                         "active": db == doc.get("active"), "url": prof.get("url"),
                         "login": prof.get("username"), "odoo_version": prof.get("odoo_version"),
                         "expires_at": prof.get("expires_at"), "project_dir": pdir,
                         "file": str(path)})
    print(json.dumps({"local_profiles": rows}, indent=2))
    return 0


def _expired(prof: dict) -> bool:
    exp = prof.get("expires_at")
    if not exp:
        return False
    try:
        return datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) \
            <= datetime.now(timezone.utc)
    except ValueError:
        return False


def cmd_prune(args) -> int:
    removed, kept = [], 0
    for path, doc in _iter_stores():
        pdir = doc.get("project_dir")
        if not pdir or not Path(pdir).is_dir():
            if not args.dry_run:
                path.unlink(missing_ok=True)
            removed.append({"file": str(path), "why": "project directory is gone"})
            continue
        profiles = doc.get("profiles") or {}
        live = {}
        for db, prof in profiles.items():
            if _expired(prof):
                removed.append({"profile": db, "project": pdir, "why": "key expired"})
                continue
            if args.check_db:
                found = list_databases(str(prof.get("url", "")).rstrip("/"))
                if found is not None and db not in found:
                    removed.append({"profile": db, "project": pdir, "why": "database no longer exists"})
                    continue
            live[db] = prof
        if not live:
            if not args.dry_run:
                path.unlink(missing_ok=True)
            continue
        kept += len(live)
        if len(live) != len(profiles) and not args.dry_run:
            doc["profiles"] = live
            if doc.get("active") not in live:
                doc["active"] = sorted(live, key=lambda d: live[d].get("created_at", ""))[-1]
            save_store(path, doc)
    print(json.dumps({"removed": removed, "kept": kept, "dry_run": bool(args.dry_run)}, indent=2))
    return 0


def self_test() -> int:
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(("PASS " if ok else "FAIL ") + name)
        fails += 0 if ok else 1

    check("loopback ok", P.is_loopback("http://127.0.0.1:8069") and P.is_loopback("http://acme.localhost"))
    check("remote refused", not P.is_loopback("https://acme-stage.example.com"))
    check("conf db wins", pick_database({"db": "x"}, ["a", "b"]) == ("x", None))
    check("single db picked", pick_database({"db": ""}, ["only"]) == ("only", None))
    check("dbfilter narrows", pick_database({"db": "", "dbfilter": "^c2_.*$"}, ["c1_a", "c2_b"])[0] == "c2_b")
    check("ambiguous refuses", pick_database({"db": ""}, ["a", "b"])[0] is None)
    check("expired detects", _expired({"expires_at": "2000-01-01T00:00:00Z"}))
    return 1 if fails else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    pv = sub.add_parser("provision", help="create a local profile for this project")
    pv.add_argument("--project", help="project checkout (default: current directory)")
    pv.add_argument("--conf", help="Odoo conf file (default: discovered in the project)")
    pv.add_argument("--url", help="override url; must be loopback (default http://127.0.0.1:<http_port>)")
    pv.add_argument("--db", help="database (default: conf db_name, or the single listed database)")
    pv.add_argument("--login", help="Odoo login to key (default: the local admin, base.user_admin)")
    pv.add_argument("--odoo-cmd", help="how to launch Odoo, e.g. \"/venv/bin/python /src/odoo-bin\"")
    pv.add_argument("--python", help="python used with the discovered odoo-bin (default: this one)")
    pv.add_argument("--shell-conf", help="conf path as seen by the odoo command (containers)")
    pv.add_argument("--expire-days", type=int, default=30)
    pv.add_argument("--timeout", type=int, default=300)
    pv.add_argument("--dry-run", action="store_true")

    ls = sub.add_parser("list", help="show local profiles (no keys)")
    ls.add_argument("--project")
    ls.add_argument("--all", action="store_true")

    pr = sub.add_parser("prune", help="remove stale local profiles")
    pr.add_argument("--check-db", action="store_true", help="also drop databases the server no longer lists")
    pr.add_argument("--dry-run", action="store_true")

    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.cmd == "provision":
        rc = cmd_provision(args)
        if rc == 0:
            cmd_prune(argparse.Namespace(check_db=False, dry_run=False))
        return rc
    if args.cmd == "list":
        return cmd_list(args)
    if args.cmd == "prune":
        return cmd_prune(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
