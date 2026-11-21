"""~/.odoo-mcp/odoo-sh.json - per-machine Odoo.sh SSH profiles.

Isolation rules:
* Separate from profiles.json (record data) and local-services.json (local services).
  This module refuses to read or write either of them.
* Lives in the user's home only. A path inside a git working tree is refused, so the file
  can never be committed with a project. Nothing here is synced by the plugin.
* Stores the PATH of a private key, never the key. Keys are never opened except to read
  the header that says whether they are passphrase-protected (in memory, never printed).
* Read-only by default: a new profile allows only "read". Widening "allow" needs the
  developer's yes (recorded verbatim in the audit log); narrowing never does.
* Writes are atomic (temp file + os.replace), backed up (last 10) to ~/.odoo-mcp/sh-backups/.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime, timezone

VERSION = 1
KEEP_BACKUPS = 10
ROLES = ("dev", "stage", "prod")
# read is always on. The rest are opt-in, each enabled separately with the developer's yes:
#   update      odoo-bin -u <modules> --stop-after-init on the build
#   restart     odoosh-restart http
#   shell       one-off shell command (not interactive; meant for read-only inspection)
#   odoo_shell  odoo-bin shell snippet, rolled back at the end; commit() is refused
ACTIONS = ("read", "update", "restart", "shell", "odoo_shell")
WRITE_ACTIONS = ("update", "restart", "shell", "odoo_shell")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,98}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,98}$")
HOST_RE = re.compile(r"^[A-Za-z0-9{}][A-Za-z0-9.{}_-]{0,252}$")
USER_RE = re.compile(r"^[A-Za-z0-9{}][A-Za-z0-9{}_.-]{0,63}$")
JUMP_RE = re.compile(r"^[A-Za-z0-9_.@:,\[\]-]{1,255}$")
DIR_RE = re.compile(r"^(~|/)[A-Za-z0-9._/~-]{0,200}$")
# Extra ssh -o options a profile may add (old servers, unusual networks). Anything that
# could run a local command, disable host checking or enable prompts is not on this list.
SSH_OPTION_KEYS = ("HostKeyAlgorithms", "PubkeyAcceptedAlgorithms", "PubkeyAcceptedKeyTypes",
                   "KexAlgorithms", "Ciphers", "MACs", "AddressFamily", "IPQoS",
                   "ServerAliveInterval", "ServerAliveCountMax", "Compression", "IdentityAgent",
                   "CertificateFile")
SSH_OPTION_RE = re.compile(r"^(%s)=[A-Za-z0-9@.,+:/\\~_ -]{1,300}$" % "|".join(SSH_OPTION_KEYS))
PROFILE_KEYS = ("project", "branch", "role", "url", "key", "ssh_user", "host", "port",
                "proxy_jump", "allow", "paths", "ssh_binary", "ssh_options", "connect_timeout",
                "command_timeout", "src_dir", "logs_dir", "created_at", "updated_at")


class ConfigError(Exception):
    pass


def base_dir() -> str:
    return os.environ.get("ODOO_SH_HOME") or os.path.join(os.path.expanduser("~"), ".odoo-mcp")


def _inside_git_tree(p: str) -> bool:
    d = os.path.dirname(os.path.abspath(p))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


def path() -> str:
    p = os.environ.get("ODOO_SH_FILE") or os.path.join(base_dir(), "odoo-sh.json")
    if os.path.basename(p).lower() in ("profiles.json", "local-services.json"):
        raise ConfigError("odoo-sh never reads or writes %s" % os.path.basename(p))
    if _inside_git_tree(p):
        raise ConfigError("%s is inside a git working tree; Odoo.sh SSH profiles live only in "
                          "~/.odoo-mcp/ so they can never be committed" % p)
    return p


def audit_path() -> str:
    return os.path.join(base_dir(), "odoo-sh-audit.log")


def known_hosts_dir() -> str:
    return os.path.join(base_dir(), "odoo-sh-known_hosts")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def audit(event: dict) -> None:
    """One JSON line per change or write action. Never records keys or log content."""
    try:
        os.makedirs(base_dir(), exist_ok=True)
        entry = {"ts": now_iso(), "pid": os.getpid()}
        entry.update(event)
        with open(audit_path(), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def validate(name: str, prof: dict) -> dict:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ConfigError("profile name %r must be lowercase letters, digits, - or _" % name)
    if not isinstance(prof, dict):
        raise ConfigError("%s: a profile must be an object" % name)
    project = prof.get("project")
    if not isinstance(project, str) or not SLUG_RE.match(project):
        raise ConfigError("%s: project must be the Odoo.sh project slug (lowercase, digits, -)" % name)
    branch = prof.get("branch")
    if branch not in (None, "") and (not isinstance(branch, str) or not BRANCH_RE.match(branch)):
        raise ConfigError("%s: branch %r is not a valid Odoo.sh branch name" % (name, branch))
    role = prof.get("role") or "prod"   # unknown role = treated as production
    if role not in ROLES:
        raise ConfigError("%s: role must be one of %s" % (name, ", ".join(ROLES)))
    url = prof.get("url")
    if not isinstance(url, str) or not re.match(r"^https://[A-Za-z0-9.-]+(:\d+)?/?$", url):
        raise ConfigError("%s: url must be the build's https URL, e.g. https://<project>-<branch>.odoo.com" % name)
    key = prof.get("key")   # absent = use whatever key ssh-agent offers
    if key not in (None, ""):
        if not isinstance(key, str) or "PRIVATE KEY" in key or "\n" in key or len(key) > 500:
            raise ConfigError("%s: key must be a file path (private key, or its .pub when the agent "
                              "holds the private half), never key material" % name)
    sb = prof.get("ssh_binary")
    if sb not in (None, "") and (not isinstance(sb, str) or "\n" in sb or len(sb) > 500):
        raise ConfigError("%s: ssh_binary must be a path to the ssh executable" % name)
    opts = prof.get("ssh_options") or []
    if not isinstance(opts, list) or not all(isinstance(o, str) and SSH_OPTION_RE.match(o) for o in opts):
        raise ConfigError("%s: ssh_options entries must be Key=Value with Key one of %s"
                          % (name, ", ".join(SSH_OPTION_KEYS)))
    for k, lo, hi in (("connect_timeout", 3, 120), ("command_timeout", 5, 600)):
        v = prof.get(k)
        if v not in (None, "") and not (isinstance(v, int) and lo <= v <= hi):
            raise ConfigError("%s: %s must be %d-%d seconds" % (name, k, lo, hi))
    for k in ("src_dir", "logs_dir"):
        v = prof.get(k)
        if v not in (None, "") and (not isinstance(v, str) or not DIR_RE.match(v) or ".." in v):
            raise ConfigError("%s: %s must be an absolute or ~/ path on the build" % (name, k))
    for k, rx in (("ssh_user", USER_RE), ("host", HOST_RE)):
        v = prof.get(k)
        if v not in (None, "") and (not isinstance(v, str) or not rx.match(v)):
            raise ConfigError("%s: %s %r has characters ssh would misread" % (name, k, v))
    port = prof.get("port")
    if port not in (None, "") and not (isinstance(port, int) and 0 < port < 65536):
        raise ConfigError("%s: port must be a number 1-65535" % name)
    jump = prof.get("proxy_jump")
    if jump not in (None, "") and (not isinstance(jump, str) or not JUMP_RE.match(jump) or jump.startswith("-")):
        raise ConfigError("%s: proxy_jump must look like user@host[:port]" % name)
    allow = prof.get("allow") or ["read"]
    if not isinstance(allow, list) or any(a not in ACTIONS for a in allow):
        raise ConfigError("%s: allow must list actions from %s" % (name, ", ".join(ACTIONS)))
    if "read" not in allow:
        allow = ["read"] + list(allow)
    paths = prof.get("paths") or []
    if not isinstance(paths, list) or not all(isinstance(x, str) for x in paths):
        raise ConfigError("%s: paths must be a list of folders" % name)
    clean = {k: prof.get(k) for k in PROFILE_KEYS if prof.get(k) not in (None, "", [])}
    clean.update({"project": project, "role": role, "url": url.rstrip("/"),
                  "allow": [a for a in ACTIONS if a in allow]})
    clean.setdefault("created_at", now_iso())
    return clean


_SSH_ADDR_RE = re.compile(
    r"^(?:ssh\s+)?(?:(?:-p\s*(?P<p1>\d+)|-o\s*\S+|-[A-Za-z]\s+\S+)\s+)*"
    r"(?:ssh://)?(?P<user>[A-Za-z0-9_.-]+)@(?P<host>[A-Za-z0-9.-]+)(?::(?P<p2>\d+))?"
    r"(?:\s+-p\s*(?P<p3>\d+))?\s*$")


def parse_ssh_address(text: str) -> dict:
    """The SSH address Odoo.sh shows for a build ("ssh 1234@acme-erp-stage-1234.dev.odoo.com",
    "1234@host", "ssh -p 2222 1234@host", "ssh://1234@host:2222") -> {ssh_user, host, port}."""
    m = _SSH_ADDR_RE.match((text or "").strip())
    if not m:
        raise ConfigError("cannot read an ssh address from %r; paste it as shown, e.g. "
                          "ssh 1234567@<project>-<branch>-1234567.dev.odoo.com" % text)
    port = m.group("p1") or m.group("p2") or m.group("p3")
    return {"ssh_user": m.group("user"), "host": m.group("host"), "port": int(port) if port else None}


def load() -> dict:
    p = path()
    if not os.path.exists(p):
        return {"version": VERSION, "profiles": {}}
    try:
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
    except ValueError as exc:
        raise ConfigError("%s is not valid JSON (%s); restore it from %s"
                          % (p, exc, os.path.join(base_dir(), "sh-backups")))
    if not isinstance(doc, dict) or not isinstance(doc.get("profiles"), dict):
        raise ConfigError("%s: expected {version, profiles: {...}}" % p)
    return doc


def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p)).rstrip("\\/")


def pick(name=None, project_dir=None):
    """(name, profile) for a call. Order: explicit name, a profile whose `paths` contain
    the project folder, the file's `default`, the only profile."""
    doc = load()
    profs = doc["profiles"]
    if not profs:
        raise ConfigError("no Odoo.sh profiles yet - run /odoo:sh-setup (it lists your SSH keys, "
                          "writes the profile and tests the connection)")
    if name:
        if name not in profs:
            raise ConfigError("unknown Odoo.sh profile %r (known: %s)" % (name, ", ".join(sorted(profs))))
        return name, profs[name]
    pd = project_dir or os.environ.get("ODOO_SH_PROJECT_DIR") or ""
    if pd:
        here = _norm(pd)
        for n, pr in sorted(profs.items()):
            for folder in pr.get("paths") or []:
                f = _norm(folder)
                if here == f or here.startswith(f + os.sep):
                    return n, pr
    d = doc.get("default")
    if d in profs:
        return d, profs[d]
    if len(profs) == 1:
        return next(iter(profs.items()))
    raise ConfigError("several Odoo.sh profiles (%s) and none is the default for this folder; "
                      "pass profile=<name> or run odoo_sh.py default <name>" % ", ".join(sorted(profs)))


def save(doc: dict) -> str:
    p = path()
    profs = {n: validate(n, pr) for n, pr in (doc.get("profiles") or {}).items()}
    out = {"version": VERSION, "updated_at": now_iso(), "profiles": profs}
    if doc.get("default") in profs:
        out["default"] = doc["default"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        bdir = os.path.join(base_dir(), "sh-backups")
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(p, os.path.join(bdir, "odoo-sh.%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S-%f")))
        old = sorted(f for f in os.listdir(bdir) if f.startswith("odoo-sh."))
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
    for _ in range(20):
        try:
            os.replace(tmp, p)
            break
        except PermissionError:   # Windows: a reader holds the file for a moment
            time.sleep(0.05)
    else:
        os.replace(tmp, p)
    return p


def upsert(name: str, fields: dict) -> dict:
    """Add or change a profile. `allow` is never widened here (see set_allow)."""
    doc = load()
    cur = dict(doc["profiles"].get(name) or {})
    old_allow = cur.get("allow") or ["read"]
    for k, v in fields.items():
        if k == "allow":
            continue
        if v is None:
            continue
        if v == "":
            cur.pop(k, None)
        else:
            cur[k] = v
    cur["allow"] = old_allow
    cur["updated_at"] = now_iso()
    doc["profiles"][name] = validate(name, cur)
    if not doc.get("default") or doc.get("default") not in doc["profiles"]:
        doc["default"] = name
    save(doc)
    audit({"action": "profile_upsert", "profile": name,
           "fields": sorted(k for k, v in fields.items() if v is not None and k != "allow")})
    return doc["profiles"][name]


def set_allow(name: str, actions: list, approved_by=None) -> dict:
    """Replace a profile's allowed actions. Adding a write action needs the developer's
    verbatim yes; removing never does."""
    doc = load()
    if name not in doc["profiles"]:
        raise ConfigError("unknown profile %r" % name)
    prof = doc["profiles"][name]
    bad = [a for a in actions if a not in ACTIONS]
    if bad:
        raise ConfigError("unknown action(s) %s; choose from %s" % (", ".join(bad), ", ".join(ACTIONS)))
    new = ["read"] + [a for a in WRITE_ACTIONS if a in actions]
    added = [a for a in new if a not in (prof.get("allow") or ["read"])]
    answer = approved_by.strip() if isinstance(approved_by, str) else ""
    if added and len(answer) < 2:
        raise ConfigError(
            "allowing %s on %s (role %s, %s) needs the developer's explicit yes. Ask them, naming the "
            "profile and the actions, and pass their answer verbatim as --approved-by."
            % (", ".join(added), name, prof.get("role"), prof.get("url")))
    prof["allow"] = new
    prof["updated_at"] = now_iso()
    doc["profiles"][name] = validate(name, prof)
    save(doc)
    audit({"action": "allow", "profile": name, "allow": new, "added": added,
           "approved_by": answer if added else None})
    return doc["profiles"][name]


def remove(name: str) -> None:
    doc = load()
    if doc["profiles"].pop(name, None) is None:
        raise ConfigError("unknown profile %r" % name)
    if doc.get("default") == name:
        doc.pop("default", None)
    save(doc)
    audit({"action": "profile_remove", "profile": name})


def set_default(name: str) -> None:
    doc = load()
    if name not in doc["profiles"]:
        raise ConfigError("unknown profile %r" % name)
    doc["default"] = name
    save(doc)
