"""~/.odoo-mcp/local-services.json - the only file the odoo-local server writes.

Isolation rules:
* This is NOT ~/.odoo-mcp/profiles.json. That file holds real stage/prod instances and
  is written only by scripts/mcp/odoo_mcp.py; this module refuses to touch it.
* Every entry is a loopback service: its database host must be loopback (or a unix
  socket) and any url/host must be loopback. The writer refuses anything else, so a
  stage or production instance can never appear here.
* Writes are atomic (temp file + os.replace), backed up (last 10) to
  ~/.odoo-mcp/local-backups/, and serialised with a lock file.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

VERSION = 1
KEEP_BACKUPS = 10
SERVICE_KEYS = (
    "id", "project", "odoo_version", "runtime", "wsl_distro", "cwd", "python", "odoo_bin", "conf",
    "http_port", "gevent_port", "db_host", "db_port", "main_db", "systemd_unit", "logfile", "data_dir",
    "created_by", "created_at", "discovered_at", "warnings", "pinned", "dbfilter",
)
RUNTIMES = ("wsl", "linux", "windows", "docker")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class RegistryError(Exception):
    pass


def base_dir() -> str:
    return os.environ.get("ODOO_LOCAL_HOME") or os.path.join(os.path.expanduser("~"), ".odoo-mcp")


def path() -> str:
    p = os.environ.get("ODOO_LOCAL_SERVICES_FILE") or os.path.join(base_dir(), "local-services.json")
    if os.path.basename(p).lower() == "profiles.json":
        raise RegistryError("odoo-local never reads or writes profiles.json")
    return p


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_loopback(host) -> bool:
    h = str(host or "").strip().lower().strip("[]")
    return (h in ("", "localhost", "127.0.0.1", "::1", "false", "none")
            or h.startswith("127.") or h.endswith(".localhost") or h.startswith("/"))


def validate(svc: dict) -> dict:
    if not isinstance(svc, dict):
        raise RegistryError("a service entry must be an object")
    sid = svc.get("id")
    if not isinstance(sid, str) or not ID_RE.match(sid):
        raise RegistryError("service id %r must be lowercase kebab-case" % sid)
    if svc.get("runtime") not in RUNTIMES:
        raise RegistryError("%s: runtime must be one of %s" % (sid, ", ".join(RUNTIMES)))
    if svc["runtime"] == "wsl" and not svc.get("wsl_distro"):
        raise RegistryError("%s: a wsl service needs wsl_distro" % sid)
    if not is_loopback(svc.get("db_host")):
        raise RegistryError("%s: db_host %r is not loopback - odoo-local manages local services only; "
                            "remote instances belong in profiles.json via odoo_mcp.py" % (sid, svc.get("db_host")))
    for key in ("url", "host", "http_interface"):
        val = svc.get(key)
        if val:
            host = urlparse(val).hostname if "://" in str(val) else val
            if not is_loopback(host) and str(host) != "0.0.0.0":
                raise RegistryError("%s: %s %r is not loopback" % (sid, key, val))
    for key in ("http_port", "gevent_port", "db_port"):
        v = svc.get(key)
        if v is not None and not (isinstance(v, int) and 0 < v < 65536):
            raise RegistryError("%s: %s must be a port number" % (sid, key))
    clean = {k: svc.get(k) for k in SERVICE_KEYS if k in svc}
    clean.setdefault("created_by", "odoo-local")
    clean.setdefault("created_at", now_iso())
    return clean


def load() -> dict:
    p = path()
    if not os.path.exists(p):
        return {"version": VERSION, "services": []}
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
    except ValueError as exc:
        raise RegistryError("%s is not valid JSON (%s); fix it or restore from %s"
                            % (p, exc, os.path.join(base_dir(), "local-backups")))
    if not isinstance(doc, dict) or not isinstance(doc.get("services"), list):
        raise RegistryError("%s: expected {version, services: [...]}" % p)
    return doc


def services() -> list:
    return list(load()["services"])


def get(sid: str) -> dict:
    for s in services():
        if s.get("id") == sid:
            return s
    known = ", ".join(sorted(s.get("id", "?") for s in services())) or "none - run local_discover"
    raise RegistryError("unknown service %r (known: %s)" % (sid, known))


class _Lock:
    def __init__(self, target):
        self.lock = target + ".lock"

    def __enter__(self):
        deadline = time.time() + 10
        while True:
            try:
                fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.lock) > 60:
                        os.remove(self.lock)  # stale lock from a crashed writer
                        continue
                except OSError:
                    continue
                if time.time() > deadline:
                    raise RegistryError("local-services.json is locked by another writer (%s)" % self.lock)
                time.sleep(0.1)

    def __exit__(self, *exc):
        try:
            os.remove(self.lock)
        except OSError:
            pass


def save(doc: dict) -> str:
    """Validate every entry, back up the previous file, replace atomically."""
    p = path()
    entries = [validate(s) for s in doc.get("services", [])]
    ids = [s["id"] for s in entries]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise RegistryError("duplicate service ids: %s" % ", ".join(dupes))
    out = {"version": VERSION, "updated_at": now_iso(), "services": entries}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with _Lock(p):
        if os.path.exists(p):
            bdir = os.path.join(base_dir(), "local-backups")
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(p, os.path.join(bdir, "local-services.%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S-%f")))
            old = sorted(f for f in os.listdir(bdir) if f.startswith("local-services."))
            for f in old[:-KEEP_BACKUPS]:
                try:
                    os.remove(os.path.join(bdir, f))
                except OSError:
                    pass
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, p)
    return p


def merge_discovered(found: list, distro) -> dict:
    """Add new services, refresh discovered fields of existing ones, keep user edits of
    pinned entries. Returns {added, updated, unchanged, kept_missing}."""
    doc = load()
    by_id = {s["id"]: s for s in doc["services"]}
    report = {"added": [], "updated": [], "unchanged": [], "kept_missing": []}
    seen = set()
    for f in found:
        f = dict(f)
        f.pop("running_pid", None)
        f["discovered_at"] = now_iso()
        sid = f["id"]
        seen.add(sid)
        cur = by_id.get(sid)
        if cur is None:
            f["created_by"], f["created_at"] = "odoo-local", now_iso()
            by_id[sid] = validate(f)
            report["added"].append(sid)
            continue
        if cur.get("pinned"):
            report["unchanged"].append(sid)
            continue
        changed = {k for k in SERVICE_KEYS if k not in ("created_at", "created_by", "discovered_at", "pinned")
                   and k in f and f.get(k) != cur.get(k)}
        if changed:
            cur.update({k: f[k] for k in changed})
            cur["discovered_at"] = f["discovered_at"]
            report["updated"].append("%s (%s)" % (sid, ", ".join(sorted(changed))))
        else:
            report["unchanged"].append(sid)
    for sid, s in by_id.items():
        if sid not in seen and s.get("wsl_distro") == distro:
            report["kept_missing"].append(sid)
    doc["services"] = list(by_id.values())
    report["file"] = save(doc)
    return report
