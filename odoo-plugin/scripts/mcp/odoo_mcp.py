#!/usr/bin/env python3
"""Manage ~/.odoo-mcp/profiles.json - the one file that decides Odoo MCP connections.

  check   [--ping] [--folder PATH]   validate; show projects, instances, this folder's project
  add     PROJECT INSTANCE ...       add or change an instance (key from --key-stdin or a prompt)
  bind    PROJECT [FOLDER]           bind a folder to a project
  remove  PROJECT[/INSTANCE]         remove an instance, or a whole project
  local   [...]                      create a key on this project's LOCAL Odoo and add it
  migrate --plan | --apply PLAN      move a version-1 file (and project .mcp.json servers) to v2

Every write is validated, backed up and replaced atomically. A change that WIDENS a
remote instance - a new remote instance above read, more access, prod relabelled
stage - needs the developer's yes: run it in their own terminal, or pass
--approved-by "<their answer>". It is recorded in ~/.odoo-mcp/audit.log. Keys are
never taken from arguments and never printed. Standard library only.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

# The server package lives in <plugin>/mcp. This CLI sits outside it so the server
# itself contains no process-execution path (tests/mcp enforce that).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp"))

import config as C  # noqa: E402
from session import Session, audit  # noqa: E402

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EXIT_USAGE, EXIT_WIDEN, EXIT_ODOO = 2, 3, 4


def die(msg: str, code: int = EXIT_USAGE) -> None:
    print("odoo_mcp: %s" % msg, file=sys.stderr)
    raise SystemExit(code)


def emit(payload) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------
# File access
# --------------------------------------------------------------------------


def load_doc() -> dict:
    """The current version-2 document, or an empty one when there is no file yet."""
    path = C.config_path()
    if not path.is_file():
        return {"version": 2, "projects": {}}
    try:
        doc = json.loads(path.read_bytes().decode("utf-8-sig"))
    except ValueError as exc:
        die("%s is not valid JSON (%s) - fix it first" % (path, exc))
    if not isinstance(doc, dict) or doc.get("version") != 2:
        die("%s is not a version-2 file. Run: odoo_mcp.py migrate --plan" % path)
    if not isinstance(doc.get("projects"), dict):
        doc["projects"] = {}
    return doc


def instance_in(doc: dict, project: str, name: str):
    """The parsed instance (or None) - for comparing before and after a change."""
    try:
        cfg = C.parse(json.dumps(doc), C.config_path())
    except C.ConfigError:
        return None
    proj = cfg.projects.get(project)
    return proj.instances.get(name) if proj else None


def save(doc: dict):
    try:
        return C.save(doc)
    except C.ConfigError as exc:
        die(str(exc))


def approval(args, reasons: list) -> str:
    """The developer's yes for a widening, or exit 3 saying how to get it."""
    if not reasons:
        return ""
    given = (getattr(args, "approved_by", None) or "").strip()
    if len(given) >= 2:
        return given
    if sys.stdin.isatty() and not getattr(args, "key_stdin", False):
        return "terminal"
    die("this change widens what a remote instance may do:\n  - %s\n"
        "Ask the developer - name the instance, its url and the new access - then rerun with "
        "--approved-by \"<their answer, verbatim>\" (or let them run it in their own terminal)."
        % "\n  - ".join(reasons), EXIT_WIDEN)


def read_key(args, required: bool) -> str:
    if getattr(args, "key_stdin", False):
        key = sys.stdin.readline().strip()
    elif sys.stdin.isatty():
        key = getpass.getpass("API key for %s/%s (input hidden): " % (args.project, args.instance))
    else:
        key = ""
    if required and not key:
        die("an API key is needed: pipe it with --key-stdin, or run this in a terminal")
    return key


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def cmd_check(args) -> int:
    path = C.config_path()
    out: dict = {"file": str(path)}
    if not path.is_file():
        out["exists"] = False
        out["help"] = ("no profiles.json yet - add a local instance with `odoo_mcp.py local`, "
                       "or a remote one with `odoo_mcp.py add`")
        emit(out)
        return 0
    loader = C.Loader(path)
    try:
        cfg, warnings = loader.get()
    except C.ConfigError as exc:
        out["error"] = str(exc)
        emit(out)
        return EXIT_USAGE
    folder = Path(getattr(args, "folder", None) or os.getcwd())
    project = cfg.match(C.session_folders(folder))
    out.update({
        "version": cfg.version,
        "folder": str(folder),
        "project": project.name if project else None,
        "default": project.default_name() if project else None,
        "projects": {},
        "warnings": warnings,
    })
    sess = Session(folder, loader) if getattr(args, "ping", False) else None
    for p in cfg.projects.values():
        rows = {}
        for name, inst in p.instances.items():
            if isinstance(inst, C.BrokenInstance):
                rows[name] = {"error": inst.error}
                continue
            row = inst.describe()
            if sess is not None:
                row.update(ping(sess, inst))
            rows[name] = row
        out["projects"][p.name] = {"paths": list(p.paths), "default": p.default_name(),
                                   "instances": rows}
    emit(out)
    return 0


def ping(sess, inst) -> dict:
    from odoo_client import OdooError

    try:
        client = sess.client(inst)
        who = client.whoami()
        return {"login_ok": True, "database": client.p.db or "host-selected",
                "odoo_version": who.get("server_version") or who.get("version")}
    except (OdooError, C.ConfigError) as exc:
        return {"login_ok": False, "error": str(exc).splitlines()[0][:300]}


def cmd_add(args) -> int:
    doc = load_doc()
    projects = doc["projects"]
    proj = projects.get(args.project)
    created = proj is None
    if created:
        proj = {"paths": [str(Path(args.path or os.getcwd()).resolve())], "instances": {}}
    elif args.path:
        bind_folder(doc, args.project, proj, Path(args.path))
    instances = proj.setdefault("instances", {})
    old = instance_in(doc, args.project, args.instance) if not created else None
    raw = dict(instances.get(args.instance) or {})
    for key in ("url", "tier", "db", "username", "access", "db_pattern"):
        value = getattr(args, key, None)
        if value is not None:
            raw[key] = value
    key = read_key(args, required=not raw.get("api_key"))
    if key:
        raw["api_key"] = key
    instances[args.instance] = raw
    projects[args.project] = proj

    new = instance_in(doc, args.project, args.instance)
    if new is None:
        die("the result is not a valid profiles.json; nothing was written")
    if isinstance(new, C.BrokenInstance):
        die(new.error)
    reasons = C.widenings(old, new)
    approved = approval(args, reasons)
    backup = save(doc)
    if reasons:
        audit({"action": "widen", "instance": new.qualified, "url": new.url,
               "reasons": reasons, "approved_by": approved[:200]})
    audit({"action": "config", "op": "add", "instance": new.qualified})
    emit({"saved": new.qualified, "project_created": created, "instance": new.describe(),
          "backup": str(backup) if backup else None})
    return 0


def bind_folder(doc: dict, name: str, proj: dict, folder: Path) -> bool:
    """Add `folder` to project `name`; refuse a folder another project owns."""
    folder = folder.resolve()
    n = C.norm_path(folder)
    for other, p in doc["projects"].items():
        if other != name and n in [C.norm_path(x) for x in (p.get("paths") or [])]:
            die("folder %s is already bound to project %r" % (folder, other))
    paths = proj.setdefault("paths", [])
    if n in [C.norm_path(x) for x in paths]:
        return False
    paths.append(str(folder))
    return True


def cmd_bind(args) -> int:
    doc = load_doc()
    proj = doc["projects"].get(args.project)
    if proj is None:
        die("there is no project %r - create it with `odoo_mcp.py add %s <instance> ...` or "
            "`odoo_mcp.py local --project %s`" % (args.project, args.project, args.project))
    folder = Path(args.folder or os.getcwd())
    added = bind_folder(doc, args.project, proj, folder)
    backup = save(doc) if added else None
    audit({"action": "config", "op": "bind", "project": args.project, "folder": str(folder)})
    emit({"project": args.project, "paths": proj["paths"], "changed": added,
          "backup": str(backup) if backup else None})
    return 0


def cmd_remove(args) -> int:
    doc = load_doc()
    projects = doc["projects"]
    pname, _, iname = args.target.partition("/")
    proj = projects.get(pname)
    if proj is None:
        die("there is no project %r" % pname)
    instances = proj.get("instances") or {}
    if iname:
        if iname not in instances:
            die("project %r has no instance %r" % (pname, iname))
        del instances[iname]
        if proj.get("default") == iname:
            del proj["default"]
    else:
        prods = sorted(n for n, i in instances.items()
                       if isinstance(i, dict) and str(i.get("tier") or "").lower() == "prod")
        approval(args, ["remove project %s, which holds production instance(s) %s"
                        % (pname, ", ".join(prods))] if prods else [])
        del projects[pname]
    backup = save(doc)
    audit({"action": "config", "op": "remove", "target": args.target})
    emit({"removed": args.target, "backup": str(backup) if backup else None})
    return 0


# --------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")

    ck = sub.add_parser("check", help="validate and show the connections (default)")
    ck.add_argument("--ping", action="store_true", help="also log in to every instance")
    ck.add_argument("--folder", help="resolve this folder instead of the current one")

    ad = sub.add_parser("add", help="add or change an instance")
    ad.add_argument("project")
    ad.add_argument("instance")
    ad.add_argument("--url")
    ad.add_argument("--tier", choices=C.TIERS)
    ad.add_argument("--db", help='database name, or "auto" (local/stage only)')
    ad.add_argument("--username")
    ad.add_argument("--access", choices=C.ACCESS)
    ad.add_argument("--db-pattern", dest="db_pattern")
    ad.add_argument("--key-stdin", action="store_true", help="read the API key from stdin")
    ad.add_argument("--path", help="folder of a new project / a folder to bind to it")
    ad.add_argument("--approved-by", dest="approved_by",
                    help="the developer's verbatim yes, for a change that widens access")

    bd = sub.add_parser("bind", help="bind a folder to a project")
    bd.add_argument("project")
    bd.add_argument("folder", nargs="?")

    rm = sub.add_parser("remove", help="remove PROJECT/INSTANCE or a whole PROJECT")
    rm.add_argument("target")
    rm.add_argument("--approved-by", dest="approved_by")
    return ap


COMMANDS = {"check": cmd_check, "add": cmd_add, "bind": cmd_bind, "remove": cmd_remove}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return COMMANDS[args.cmd or "check"](args)


if __name__ == "__main__":
    sys.exit(main())
