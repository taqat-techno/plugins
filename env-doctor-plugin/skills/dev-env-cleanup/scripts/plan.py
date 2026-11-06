#!/usr/bin/env python3
"""env-doctor dev-env-cleanup planner. Pure decision logic: reads records, writes a plan.

It never touches databases or files it is not told to write. `build` turns the
read-only inventory (inventory.sh, optional host_probe.py, optional odoo-local
`local_cleanup_plan` JSON) into a plan with a content-derived id; `show` prints it;
`emit` re-verifies an APPROVED plan id and writes the action lists that the apply
scripts consume. Stdlib only; runs on Windows, Linux, macOS or inside WSL.

    python plan.py build --inventory inv.tsv [--host host.tsv] [--odoo-plan odoo.json]
                         [--scope all|db|files|docker|wsl-disk] [--keep-days 7]
                         [--backup-threshold-gb 1] [--out-dir DIR]
    python plan.py show  --plan DIR/<plan_id>.json
    python plan.py emit  --plan DIR/<plan_id>.json --approve <plan_id> --out-dir DIR [--max-age-hours 24]

Plan shape (a superset of the odoo-local `local_cleanup_plan` contract):
    {plan_id, created_at, host, user, scope, items:[{id, kind, target, size_bytes, reason,
     action: drop|delete|archive|command|report, backup, source, ...}], keep:[{target, reason}],
     notes:[...], clusters:{port: conn}}
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
import time

DAY = 86400
GIB = 1024 ** 3
MIB = 1024 ** 2
CANONICAL_CONFS = ("odoo.wsl.conf", "odoo.conf")
SYSTEM_DBS = ("postgres", "template0", "template1")
PURE_CACHES = (".cache/pip", ".cache/uv", ".npm/_cacache", ".cache/yarn", ".cache/pnpm", ".cache/go-build")
JUDGMENT_CACHES = {
    ".cache/JetBrains": "IDE backend caches; delete only the folders of IDE versions you no longer run",
    ".cache/ms-playwright": "browser binaries; deleting forces a re-download on the next Playwright run",
    ".cache/ms-playwright-mcp": "Playwright MCP browser profile/cache; close the MCP server first",
    ".cache/odoo-src": "derived source clones; delete only after proving each is a clean clone of a source still on disk",
}
PLAN_FIELDS = ("kind", "target", "size_bytes", "reason", "action", "backup")


# --------------------------------------------------------------------------- parsing

def parse_records(text: str) -> dict:
    inv = {k: [] for k in ("conf", "cluster", "db", "datadir", "filestore", "path", "journal", "docker",
                           "proc", "ref", "keep", "note", "vhdx", "hostdisk", "df")}
    inv["meta"] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        f = line.rstrip("\r").split("\t")
        kind, rest = f[0], f[1:]
        if kind == "meta" and len(rest) >= 2:
            inv["meta"][rest[0]] = rest[1]
        elif kind in inv and isinstance(inv[kind], list):
            inv[kind].append(rest)
    return inv


def _int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def human(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(n) < 1024 or unit == "TiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TiB"


def parse_size(text: str) -> int:
    m = re.match(r"^\s*([0-9.]+)\s*([KMGT]?)i?B?\s*$", text or "", re.I)
    if not m:
        return 0
    return int(float(m.group(1)) * {"": 1, "K": 1024, "M": MIB, "G": GIB, "T": GIB * 1024}[m.group(2).upper()])


# --------------------------------------------------------------------------- planning

class Planner:
    def __init__(self, inv, now=None, keep_days=7, backup_threshold=GIB, scope="all", backup_all=False):
        self.inv, self.scope, self.backup_all = inv, scope, backup_all
        self.now = now if now is not None else _int(inv["meta"].get("now"), int(time.time()))
        self.cutoff = self.now - keep_days * DAY
        self.keep_days, self.threshold = keep_days, backup_threshold
        self.items, self.keep, self.notes = [], [], [r[0] for r in inv["note"] if r]
        self.patterns = [r[0].strip() for r in inv["keep"] if r and r[0].strip()]
        self.confs = [self._conf(r) for r in inv["conf"] if r]
        self.clusters = {}
        for r in inv["cluster"]:
            if len(r) >= 5:
                self.clusters[r[2]] = r[4]
        self.unreachable = [p for p, c in self.clusters.items() if c == "unreachable"]
        self.dbs = [self._db(r) for r in inv["db"] if len(r) >= 7]
        self.db_names = {d["name"] for d in self.dbs}
        self.refs = {r[0]: r[1] for r in inv["ref"] if len(r) >= 2}
        self.procs = [r[2] for r in inv["proc"] if len(r) >= 3]
        self.filestores = [{"data_dir": r[0], "name": r[1], "size": _int(r[2]), "mtime": _int(r[3]),
                            "path": r[0].rstrip("/") + "/filestore/" + r[1]} for r in inv["filestore"] if len(r) >= 4]

    # --- helpers
    @staticmethod
    def _conf(r):
        r = r + [""] * (9 - len(r))
        return {"path": r[0], "mtime": _int(r[1]), "db": r[2], "port": r[3], "host": r[4], "user": r[5],
                "data_dir": r[6].rstrip("/"), "logfile": r[7], "dbfilter": r[8],
                "canonical": os.path.basename(r[0]) in CANONICAL_CONFS}

    @staticmethod
    def _db(r):
        return {"port": r[0], "name": r[1], "size": _int(r[2]), "conns": _int(r[3]),
                "last_stats": _int(r[4]), "last_login": _int(r[5]), "odoo": r[6] == "1"}

    def pinned(self, *names) -> str | None:
        for n in names:
            for p in self.patterns:
                if n and (fnmatch.fnmatchcase(n, p) or fnmatch.fnmatchcase(os.path.basename(n.rstrip("/")), p)):
                    return p
        return None

    def add_keep(self, target, reason):
        self.keep.append({"target": target, "reason": reason})

    def add(self, **item):
        item.setdefault("backup", False)
        item.setdefault("source", "env-doctor")
        self.items.append(item)
        return item

    def days_ago(self, ts) -> str:
        return f"{max(0, (self.now - ts) // DAY)} days ago" if ts else "never recorded"

    # --- databases
    def _db_keep_reason(self, d) -> str | None:
        name = d["name"]
        if name in SYSTEM_DBS:
            return "system database"
        if d["conns"] > 0:
            return f"{d['conns']} open connection(s) now"
        for c in self.confs:
            if c["db"] == name and c["port"] in ("", d["port"]) and (c["canonical"] or self.pinned(c["path"])):
                return f"main database of {c['path']}"
        for c in self.confs:
            flt = c["dbfilter"]
            if c["canonical"] and flt and "%" not in flt and c["port"] in ("", d["port"]):
                try:
                    if re.match(flt, name):
                        return f"matches dbfilter {flt} of {c['path']}"
                except re.error:
                    pass
        for args in self.procs:
            if re.search(r"(?:^|\s)(?:-d|--database)(?:=|\s+)" + re.escape(name) + r"(?:\s|$)", args):
                return "used by a running process"
            for c in self.confs:
                if c["db"] == name and c["path"] and c["path"] in args:
                    return f"its conf {c['path']} is used by a running process"
        if name in self.refs:
            return f"named in tool state file {self.refs[name]} (a fast-test template or similar)"
        p = self.pinned(name)
        if p:
            return f"pinned in keep.txt ({p})"
        last, signal = self.activity(d)
        if last >= self.cutoff:
            return f"active {self.days_ago(last)} ({signal}); in-flight work is never offered"
        return None

    def activity(self, d):
        signals = [(d["last_stats"], "table statistics"), (d["last_login"], "last Odoo login")]
        signals += [(f["mtime"], "filestore write") for f in self.filestores if f["name"] == d["name"]]
        signals += [(c["mtime"], f"conf {os.path.basename(c['path'])} edited") for c in self.confs if c["db"] == d["name"]]
        return max(signals, key=lambda s: s[0]) if signals else (0, "none")

    def plan_dbs(self):
        dropped = {}
        for d in sorted(self.dbs, key=lambda x: -x["size"]):
            target = f"{d['name']}@{d['port']}"
            reason = self._db_keep_reason(d)
            if reason:
                self.add_keep(target, reason)
                continue
            last, signal = self.activity(d)
            lanes = [os.path.basename(c["path"]) for c in self.confs if c["db"] == d["name"]]
            why = (f"no activity for {self.keep_days}+ days (last: {signal}, {self.days_ago(last)})" if last
                   else "no activity signal at all (statistics reset or never used)")
            if lanes:
                why += "; referenced only by non-main conf(s) " + ", ".join(lanes)
            # Dump first when it is big (>= threshold), when it is not an Odoo database (origin
            # unknown), or when nothing says when it was last used. A small, inactive Odoo dev
            # copy is dropped without a dump unless --backup-all.
            backup = bool(self.backup_all or d["size"] >= self.threshold or not d["odoo"] or not last)
            item = self.add(kind="db", target=target, db=d["name"], port=d["port"], size_bytes=d["size"],
                            reason=why, action="drop", backup=backup, conn=self.clusters.get(d["port"], ""))
            dropped[d["name"]] = item
        return dropped

    # --- files
    def plan_files(self, dropped):
        conf_dirs = {c["data_dir"] for c in self.confs if c["data_dir"]}
        orphan_ok = bool(self.clusters) and not self.unreachable and self.scope in ("all", "db", "files") \
            and self.inv["db"] is not None
        if self.unreachable:
            self.notes.append("orphan-filestore and dead-data-dir checks are off: port(s) "
                              + ", ".join(self.unreachable) + " could not be inventoried")
        if not self.clusters:
            self.notes.append("no database cluster was inventoried, so no filestore is called orphaned")
        dead_dirs = set()
        if orphan_ok:
            for r in self.inv["datadir"]:
                if len(r) < 3:
                    continue
                path, size, mtime = r[0].rstrip("/"), _int(r[1]), _int(r[2])
                live = [f for f in self.filestores if f["data_dir"].rstrip("/") == path and
                        (f["name"] in self.db_names and f["name"] not in dropped)]
                if path in conf_dirs:
                    continue
                if live or mtime >= self.cutoff or self.pinned(path):
                    self.add_keep(path, "data dir holding live filestores" if live else
                                  ("pinned in keep.txt" if self.pinned(path) else f"modified {self.days_ago(mtime)}"))
                    continue
                dead_dirs.add(path)
                self.add(kind="datadir", target=path, size_bytes=size, action="delete",
                         reason="Odoo data dir no conf points at, with no filestore of an existing database")
        for f in self.filestores:
            parent = f["data_dir"].rstrip("/")
            if parent in dead_dirs:
                continue
            if f["name"] in dropped:
                db_item = dropped[f["name"]]
                self.add(kind="filestore", target=f["path"], size_bytes=f["size"], action="delete",
                         backup=db_item["backup"], depends_on=db_item["target"],
                         reason=f"filestore of {f['name']}, dropped in this plan")
                if db_item["backup"]:
                    db_item["filestore"] = f["path"]
                continue
            if not orphan_ok or f["name"] in self.db_names:
                continue
            if f["mtime"] >= self.cutoff or self.pinned(f["path"], f["name"]):
                self.add_keep(f["path"], "orphan filestore but recently written" if f["mtime"] >= self.cutoff
                              else "pinned in keep.txt")
                continue
            self.add(kind="filestore", target=f["path"], size_bytes=f["size"], action="delete",
                     reason="orphan filestore: no database of that name on any inventoried cluster")
        if self.scope not in ("all", "files"):
            return
        for r in self.inv["path"]:
            if len(r) < 4:
                continue
            cat, path, size, mtime = r[0], r[1], _int(r[2]), _int(r[3])
            home = self.inv["meta"].get("home", "")
            rel = path[len(home):].lstrip("/") if home and path.startswith(home) else path
            if self.pinned(path):
                self.add_keep(path, "pinned in keep.txt")
            elif cat == "tmp":
                if mtime >= self.cutoff:
                    self.add_keep(path, f"scratch entry modified {self.days_ago(mtime)}")
                else:
                    self.add(kind="tmp", target=path, size_bytes=size, action="delete",
                             reason=f"scratch entry last modified {self.days_ago(mtime)}")
            elif cat == "cache" and rel in PURE_CACHES and size >= 100 * MIB:
                self.add(kind="cache", target=path, size_bytes=size, action="delete",
                         reason="package-manager download cache; rebuilt on demand")
            elif cat == "cache" and rel in JUDGMENT_CACHES and size >= 100 * MIB:
                self.add(kind="cache", target=path, size_bytes=size, action="report", reason=JUDGMENT_CACHES[rel])
            elif cat == "log" and size >= 512 * MIB:
                self.add(kind="log", target=path, size_bytes=size, action="report",
                         reason="large server log; rotate or truncate it while its server is stopped")
        for r in self.inv["journal"]:
            size = parse_size(r[0]) if r else 0
            if size >= 500 * MIB:
                self.add(kind="journal", target="systemd journal", size_bytes=size, action="command",
                         command="sudo journalctl --vacuum-size=100M", needs_root=True,
                         reason="journal is larger than it needs to be")

    def plan_confs(self, dropped):
        if self.unreachable:
            return
        for c in self.confs:
            if c["canonical"] or self.pinned(c["path"]) or not c["db"]:
                continue
            gone = c["db"] in dropped or (c["port"] in self.clusters and c["db"] not in self.db_names)
            if gone and c["mtime"] < self.cutoff:
                stamp = time.strftime("%Y%m%d", time.gmtime(self.now))
                self.add(kind="conf", target=c["path"], size_bytes=0, action="archive",
                         dest=os.path.dirname(c["path"]) + f"/_archive_{stamp}",
                         reason=f"points at database {c['db']}, which " +
                         ("is dropped in this plan" if c["db"] in dropped else "no longer exists"))

    def plan_docker(self):
        for r in self.inv["docker"]:
            if len(r) >= 3:
                rec = parse_size(r[2].split(" ")[0])
                if rec >= GIB:
                    self.add(kind="docker", target=f"docker {r[0]}", size_bytes=rec, action="command",
                             command={"Images": "docker image prune -a", "Containers": "docker container prune",
                                      "Local Volumes": "docker volume prune",
                                      "Build Cache": "docker builder prune"}.get(r[0], "docker system df -v"),
                             reason=f"{r[2]} reclaimable; check what is unused before pruning (volumes hold data)")

    def plan_vhdx(self, planned_bytes):
        used = None
        for r in self.inv["df"]:
            if r and r[0] == "/":
                used = _int(r[1])
        images = [r for r in self.inv["vhdx"] if len(r) >= 3]
        this = self.inv["meta"].get("distro")
        for r in images:
            distro, path, size = r[0], r[1], _int(r[2])
            # the df figure belongs to the distro the inventory ran in; without its name, only
            # a single image can be matched safely
            u = used if (this == distro or (this is None and len(images) == 1)) else None
            if not u:
                continue
            after = max(u - planned_bytes, 0)
            if size > 1.5 * after and size - after >= 10 * GIB:
                self.add(kind="vhdx", target=path, size_bytes=size - after, action="command", needs_admin=True,
                         command=f"compact-wsl.ps1 -Distro {distro} -Mode run   (elevated PowerShell, after the idle gate)",
                         reason=f"image is {human(size)} for {human(after)} of data after this plan; "
                                "it never shrinks by itself")

    def plan_host(self):
        for r in self.inv["hostdisk"]:
            if len(r) >= 3 and _int(r[2]) and _int(r[1]) / _int(r[2]) < 0.10:
                self.notes.append(f"drive {r[0]} has {human(r[1])} free (under 10%); Windows may shrink the "
                                  "pagefile and WSL can fail to boot with Wsl/0x8007000e")

    def build(self):
        dropped = self.plan_dbs() if self.scope in ("all", "db") else {}
        if self.scope in ("all", "files", "db"):
            self.plan_files(dropped)
            self.plan_confs(dropped)
        if self.scope in ("all", "docker"):
            self.plan_docker()
        if self.scope in ("all", "wsl-disk"):
            planned = sum(i["size_bytes"] for i in self.items if i["action"] in ("drop", "delete"))
            self.plan_vhdx(planned)
        self.plan_host()
        return self


ODOO_KINDS = {"scratch_db": "db", "orphan_filestore": "filestore", "dead_conf": "conf", "stale_log": "log"}
_ODOO_DB = re.compile(r"^(?P<runtime>[^:/]+):(?P<port>\d+)/(?P<db>[^/]+)$")
_ODOO_PATH = re.compile(r"^(?P<runtime>[^:/]+):(?P<path>/.*)$")


def odoo_target(target: str):
    """odoo-local target -> (env-doctor target, runtime). `Ubuntu:5434/db` -> `db@5434`;
    `Ubuntu:/home/u/x` -> `/home/u/x`; anything else is kept as it is."""
    m = _ODOO_DB.match(target)
    if m:
        return f"{m['db']}@{m['port']}", m["runtime"]
    m = _ODOO_PATH.match(target)
    if m:
        return m["path"], m["runtime"]
    return target, None


def merge_odoo(planner: Planner, odoo: dict):
    """Fold odoo-local `local_cleanup_plan` output in (one plan, or {"plans": [...]} for several
    runtimes). env-doctor's keep-list always wins; unknown keys and actions are ignored."""
    plans = odoo.get("plans") if isinstance(odoo.get("plans"), list) else [odoo]
    this = planner.inv["meta"].get("distro")
    kept = {k["target"] for k in planner.keep}
    have = {(i["kind"], i["target"]) for i in planner.items}
    for op in (p for p in plans if isinstance(p, dict)):
        runtime = op.get("distro")
        if this and runtime and runtime != this:
            planner.notes.append(f"odoo-local plan {op.get('plan_id')} is for {runtime}, not {this}; not merged")
            continue
        for k in op.get("keep", []) or []:
            if isinstance(k, dict) and k.get("target"):
                t, _ = odoo_target(str(k["target"]))
                if t not in kept:
                    planner.add_keep(t, f"odoo-local: {k.get('reason', '')}".strip())
                    kept.add(t)
        for it in op.get("items", []) or []:
            if not isinstance(it, dict) or not it.get("target") or it.get("action") not in ("drop", "archive", "delete"):
                continue
            raw = str(it["target"])
            target, _ = odoo_target(raw)
            kind = ODOO_KINDS.get(str(it.get("kind")), str(it.get("kind", "item")))
            bare = target.split("@")[0]
            if target in kept or any(k.split("@")[0] == bare for k in kept) or planner.pinned(bare, target):
                planner.notes.append(f"odoo-local proposed {it['action']} of {raw}; kept by env-doctor's keep-list")
                continue
            if (kind, target) in have:
                continue  # env-doctor already plans it; applied once, by env-doctor's scripts
            planner.add(kind=kind, target=target, size_bytes=_int(it.get("size_bytes")), action=it["action"],
                        backup=bool(it.get("backup")), reason=str(it.get("reason", "")), source="odoo-local",
                        odoo_plan_id=op.get("plan_id"), odoo_target=raw)
            have.add((kind, target))
        if op.get("plan_id"):
            planner.notes.append(f"Odoo items from odoo-local local_cleanup_plan {op['plan_id']}: apply them with "
                                 f"local_cleanup_apply {{plan_id: {op['plan_id']}, only: [their odoo_target]}}; "
                                 "the rest with this skill's scripts")


def plan_id_for(items) -> str:
    canon = json.dumps([{k: i.get(k) for k in PLAN_FIELDS} for i in items], sort_keys=True, ensure_ascii=True)
    return "envdoc-" + hashlib.sha256(canon.encode("utf-8")).hexdigest()[:10]


def to_plan(planner: Planner) -> dict:
    items = planner.items
    for n, it in enumerate(items, 1):
        it["id"] = f"i{n:03d}"
    meta = planner.inv["meta"]
    return {"plan_id": plan_id_for(items), "created_at": planner.now, "host": meta.get("host"),
            "user": meta.get("user"), "home": meta.get("home"), "scope": planner.scope,
            "keep_days": planner.keep_days, "items": items, "keep": planner.keep, "notes": planner.notes,
            "clusters": planner.clusters}


def render(plan: dict) -> str:
    items = plan["items"]
    reclaim = sum(i["size_bytes"] for i in items if i["action"] in ("drop", "delete"))
    other = sum(i["size_bytes"] for i in items if i["action"] in ("command", "report"))
    out = [f"CLEANUP PLAN {plan['plan_id']}  (host {plan.get('host')}, scope {plan.get('scope')}, nothing changed yet)",
           f"  Applying it frees about {human(reclaim)}; another {human(other)} needs a command you run or a judgment call.",
           ""]
    order = ("db", "filestore", "datadir", "conf", "tmp", "cache", "log", "journal", "docker", "vhdx")
    for kind in order + tuple(sorted({i["kind"] for i in items} - set(order))):
        group = [i for i in items if i["kind"] == kind]
        if not group:
            continue
        out.append(f"  {kind} ({len(group)}, {human(sum(i['size_bytes'] for i in group))})")
        for i in group[:60]:
            flag = " [backup first]" if i.get("backup") else ""
            extra = f"  -> {i['command']}" if i.get("command") else ""
            out.append(f"    {i['id']} {i['action']:<7} {human(i['size_bytes']):>10}  {i['target']}{flag}")
            out.append(f"         {i['reason']}{extra}")
        if len(group) > 60:
            out.append(f"    ... {len(group) - 60} more in the plan file")
    out.append("")
    out.append(f"  Kept ({len(plan['keep'])}), never offered:")
    for k in plan["keep"][:80]:
        out.append(f"    {k['target']}: {k['reason']}")
    if len(plan["keep"]) > 80:
        out.append(f"    ... {len(plan['keep']) - 80} more in the plan file")
    if plan["notes"]:
        out.append("")
        out.append("  Notes:")
        out.extend(f"    - {n}" for n in plan["notes"])
    out.append("")
    out.append(f"  To apply: approve plan id {plan['plan_id']} exactly (all items, or name the item ids to leave out).")
    return "\n".join(out)


# --------------------------------------------------------------------------- emit

def emit(plan: dict, approve: str, out_dir: str, now=None, max_age_hours=24, exclude=()):
    if approve != plan.get("plan_id"):
        raise SystemExit(f"refused: approved id {approve!r} is not this plan's id {plan.get('plan_id')!r}")
    if plan_id_for(plan["items"]) != plan["plan_id"]:
        raise SystemExit("refused: the plan file was edited after it was built (its id no longer matches)")
    age = (now if now is not None else time.time()) - plan["created_at"]
    if age > max_age_hours * 3600:
        raise SystemExit(f"refused: the plan is {age / 3600:.0f} h old; re-run the inventory (state may have changed)")
    os.makedirs(out_dir, exist_ok=True)
    items = [i for i in plan["items"] if i["id"] not in set(exclude)]
    skipped_dbs = {i["target"] for i in plan["items"] if i["kind"] == "db" and i["id"] in set(exclude)}
    lines = {"confs.tsv": [], "dbs.tsv": [], "files.tsv": [], "commands.txt": []}
    for i in items:
        if i.get("source") == "odoo-local":
            continue  # applied through odoo-local's own local_cleanup_apply
        if i["action"] == "archive":
            lines["confs.tsv"].append(f"archive\t{i['target']}\t{i['dest']}")
        elif i["action"] == "drop" and i["kind"] == "db":
            conn = i.get("conn", "socket")
            host, user = ("", "") if conn in ("", "socket") else tuple((conn.split(":", 2) + ["", ""])[1:3])
            lines["dbs.tsv"].append("\t".join([i["port"], i["db"], "1" if i.get("backup") else "0",
                                               host or "-", user or "-", i.get("filestore") or "-"]))
        elif i["action"] == "delete":
            if i.get("depends_on") in skipped_dbs:
                continue
            lines["files.tsv"].append(f"delete\t{i['target']}")
        elif i["action"] == "command":
            lines["commands.txt"].append(f"{i['id']}: {i['command']}    # {i['reason']}")
    written = {}
    for name, rows in lines.items():
        path = os.path.join(out_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("".join(r + "\n" for r in rows))
        written[name] = len(rows)
    return written


# --------------------------------------------------------------------------- cli

def _read(path):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--inventory", required=True)
    b.add_argument("--host")
    b.add_argument("--odoo-plan")
    b.add_argument("--scope", default="all", choices=("all", "db", "files", "docker", "wsl-disk"))
    b.add_argument("--keep-days", type=int, default=7)
    b.add_argument("--backup-threshold-gb", type=float, default=1.0)
    b.add_argument("--backup-all", action="store_true", help="pg_dump every database before its drop")
    b.add_argument("--out-dir", default=os.path.join(os.path.expanduser("~"), ".claude", "env-doctor", "plans"))
    b.add_argument("--now", type=int)
    s = sub.add_parser("show")
    s.add_argument("--plan", required=True)
    e = sub.add_parser("emit")
    e.add_argument("--plan", required=True)
    e.add_argument("--approve", required=True)
    e.add_argument("--out-dir", required=True)
    e.add_argument("--exclude", default="", help="comma-separated item ids to leave out")
    e.add_argument("--max-age-hours", type=float, default=24)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if a.cmd == "build":
        text = _read(a.inventory) + ("\n" + _read(a.host) if a.host else "")
        planner = Planner(parse_records(text), now=a.now, keep_days=a.keep_days,
                          backup_threshold=int(a.backup_threshold_gb * GIB), scope=a.scope,
                          backup_all=a.backup_all).build()
        if a.odoo_plan:
            merge_odoo(planner, json.loads(_read(a.odoo_plan)))
        plan = to_plan(planner)
        os.makedirs(a.out_dir, exist_ok=True)
        path = os.path.join(a.out_dir, plan["plan_id"] + ".json")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(plan, fh, indent=1, ensure_ascii=False)
        print(render(plan))
        print(f"\n  Plan file: {path}")
        return 0
    plan = json.loads(_read(a.plan))
    if a.cmd == "show":
        print(render(plan))
        return 0
    written = emit(plan, a.approve, a.out_dir, max_age_hours=a.max_age_hours,
                   exclude=[x.strip() for x in a.exclude.split(",") if x.strip()])
    for name, n in written.items():
        print(f"{name}: {n} line(s) -> {os.path.join(a.out_dir, name)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
