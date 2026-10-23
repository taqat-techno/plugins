"""Connection configuration for the Odoo MCP server: one file per Windows account.

    ~/.odoo-mcp/profiles.json   ("version": 2)

    {"version": 2,
     "projects": {
       "acme": {"paths": ["C:/work/acme"], "default": "stage",
                "instances": {
                  "stage": {"url": "https://acme-stage.odoo.com", "db": "auto",
                            "username": "admin", "api_key": "...", "tier": "stage", "access": "write"},
                  "prod":  {"url": "https://acme.odoo.com", "db": "acme-main-1",
                            "username": "admin", "api_key": "...", "tier": "prod", "access": "read"}}}}}

A session belongs to the project whose "paths" contain its folder (or, for a git
worktree, its main checkout). Each tool call names an instance or gets the
project's default. Nothing else decides the connection: no project pins, no local
store, no learned overlay, no environment profile.

Rules that are never inferred:
  - a remote url must say "tier": "stage" or "prod";
  - "local" is accepted only for a loopback url;
  - a prod instance names its database ("auto" is for local and stage only).

A problem in one instance breaks only that instance (BrokenInstance). Problems
with the file's structure raise ConfigError.

Design: .claude/docs/2026-10-23_odoo-mcp-one-file-design.md
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

CONFIG_FILE = "profiles.json"
USER_DIR = ".odoo-mcp"

TIERS = ("local", "stage", "prod")
ACCESS = ("read", "write", "full")
ACCESS_RANK = {"read": 0, "write": 1, "full": 2}
DEFAULT_ACCESS = {"local": "full", "stage": "write", "prod": "read"}
ACCESS_TO_MODE = {"read": "read", "write": "write", "full": "write+unlink"}
NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ConfigError(Exception):
    """Configuration problem. The message is user-facing and says how to fix it."""


class _InstanceError(Exception):
    """A problem confined to one instance; becomes a BrokenInstance."""


# --------------------------------------------------------------------------
# Paths and hosts
# --------------------------------------------------------------------------


def home() -> Path:
    """The store folder. ODOO_MCP_HOME relocates it (tests, portable setups)."""
    override = os.environ.get("ODOO_MCP_HOME", "").strip()
    if override and not override.startswith("${"):
        return Path(os.path.expanduser(override))
    return Path(os.path.expanduser("~")) / USER_DIR


def config_path() -> Path:
    return home() / CONFIG_FILE


def project_folder() -> Path:
    """The folder Claude Code works in (forwarded as ODOO_MCP_PROJECT_DIR)."""
    for var in ("ODOO_MCP_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(var, "").strip()
        if val and not val.startswith("${"):
            p = Path(val)
            if p.is_dir():
                return p
    return Path.cwd()


def norm_path(p) -> str:
    """Comparable spelling of a folder: absolute, `/`-separated, no trailing `/`,
    lowercase. Not resolve()d, so a mapped or network drive is never touched."""
    s = os.path.abspath(os.path.expanduser(str(p)))
    return s.replace("\\", "/").rstrip("/").lower()


def is_loopback(url: str) -> bool:
    """True only for hosts that cannot be another machine."""
    host = (urlparse(url).hostname or "").lower().strip("[]")
    return (
        host in ("localhost", "::1")
        or host.startswith("127.")
        or host.endswith(".localhost")
        or host.endswith(".test")
    )


# --------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Instance:
    project: str
    name: str
    url: str
    db: str
    db_auto: bool
    username: str
    api_key: str
    tier: str
    access: str
    db_pattern: str = ""
    companies: tuple = ()
    lang: str = ""
    tz: str = ""
    timeout: int = 30
    verify_ssl: bool = True
    allow_write_models: frozenset = frozenset()
    legacy: bool = False
    mode: str = "read"          # the EFFECTIVE mode; the session sets it

    @property
    def qualified(self) -> str:
        return "%s/%s" % (self.project, self.name)

    def base_context(self) -> dict:
        ctx: dict = {}
        if self.companies:
            ctx["allowed_company_ids"] = list(self.companies)
        if self.lang:
            ctx["lang"] = self.lang
        if self.tz:
            ctx["tz"] = self.tz
        return ctx

    def secrets(self) -> tuple:
        return (self.api_key,)

    def describe(self) -> dict:
        """Safe-to-display summary. Never includes the key."""
        return {
            "instance": self.qualified,
            "tier": self.tier,
            "access": self.access,
            "mode": self.mode,
            "url": self.url,
            "database": self.db or ("auto" if self.db_auto else "host-selected"),
            "username": self.username,
            "api_key_set": bool(self.api_key),
            "legacy": self.legacy,
        }

    def fingerprint(self) -> str:
        """Identity of the definition, for the client cache. Ignores `mode`."""
        parts = {}
        for f in fields(self):
            if f.name == "mode":
                continue
            value = getattr(self, f.name)
            if isinstance(value, (frozenset, set)):
                value = sorted(value)
            elif isinstance(value, tuple):
                value = list(value)
            parts[f.name] = value
        return hashlib.sha1(json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BrokenInstance:
    project: str
    name: str
    error: str

    @property
    def qualified(self) -> str:
        return "%s/%s" % (self.project, self.name)


@dataclass
class Project:
    name: str
    paths: tuple
    default: Optional[str]
    instances: dict

    def default_name(self) -> Optional[str]:
        """The instance a call gets when it names none. A prod instance is only
        ever the default when the developer wrote it as "default"."""
        if self.default:
            return self.default
        for tier in ("local", "stage"):
            names = [n for n, i in self.instances.items()
                     if isinstance(i, Instance) and i.tier == tier]
            if len(names) == 1:
                return names[0]
            if names:
                return None
        return None


@dataclass
class Config:
    version: int
    projects: dict
    source: Path
    warnings: list = field(default_factory=list)

    def match(self, folders: list) -> Optional[Project]:
        """The project whose paths contain one of `folders` - longest path wins.
        Two projects tied at that length match nothing: never a guess."""
        best, best_len, tied = None, -1, False
        normed = [norm_path(f) for f in folders]
        for project in self.projects.values():
            for p in project.paths:
                if any(f == p or f.startswith(p + "/") for f in normed):
                    if len(p) > best_len:
                        best, best_len, tied = project, len(p), False
                    elif len(p) == best_len and project is not best:
                        tied = True
        return None if tied else best

    def describe_projects(self) -> str:
        return "; ".join("%s (%s)" % (p.name, ", ".join(p.paths) or "no folders")
                         for p in self.projects.values()) or "none"

    def lookup(self, ref: Optional[str], current: Optional[Project]) -> Instance:
        """Resolve "", "name" or "project/name" to an Instance, or explain why not."""
        ref = (ref or "").strip()
        if "/" in ref:
            pname, iname = ref.split("/", 1)
            project = self.projects.get(pname)
            if project is None:
                raise ConfigError("unknown project %r. Projects: %s"
                                  % (pname, self.describe_projects()))
        else:
            if current is None:
                raise ConfigError(
                    "this folder is not part of any project in %s%s. Projects: %s. "
                    'Pass instance="project/instance" or run odoo_mcp.py bind <project>.'
                    % (self.source, " (asked for %r)" % ref if ref else "",
                       self.describe_projects()))
            project, iname = current, ref
            if not iname:
                iname = project.default_name()
                if iname is None:
                    raise ConfigError(
                        'project %r has %s and no "default"; name one: %s'
                        % (project.name,
                           "several instances" if project.instances else "no instances",
                           ", ".join(sorted(project.instances)) or "(add one)"))
        inst = project.instances.get(iname)
        if inst is None:
            raise ConfigError("project %r has no instance %r. Its instances: %s"
                              % (project.name, iname, ", ".join(sorted(project.instances)) or "none"))
        if isinstance(inst, BrokenInstance):
            raise ConfigError(inst.error)
        return inst


def session_folders(start) -> list:
    """[start] - plus the main checkout when `start` is inside a git worktree.

    A worktree's `.git` is a FILE: "gitdir: <main>/.git/worktrees/<name>". It is
    trusted only when git's own back-pointer, <main>/.git/worktrees/<name>/gitdir,
    names this `.git` file - so a cloned folder cannot claim another project (and its
    production instances) by writing a `.git` file. Reading files only: the server's
    no-process guarantee holds."""
    start = Path(start)
    folder = start
    while True:
        dot_git = folder / ".git"
        if dot_git.is_file():
            try:
                line = dot_git.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                return [start]
            if line.startswith("gitdir:"):
                gitdir = Path(os.path.normpath(os.path.join(str(folder), line[7:].strip())))
                if (gitdir.parent.name == "worktrees" and gitdir.parent.parent.name == ".git"
                        and _points_back(gitdir, dot_git)):
                    return [start, gitdir.parent.parent.parent]
            return [start]
        if dot_git.is_dir() or folder.parent == folder:
            return [start]
        folder = folder.parent


def _points_back(admin_dir: Path, dot_git: Path) -> bool:
    """git's consistency check: the worktree admin dir's `gitdir` file names this
    worktree's `.git` file."""
    try:
        target = (admin_dir / "gitdir").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return False
    return bool(target) and norm_path(os.path.join(str(admin_dir), target)) == norm_path(dot_git)


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        def sub(m):
            got = os.environ.get(m.group(1), "")
            if not got:
                raise _InstanceError(
                    "environment variable %s is not set in the MCP server's environment "
                    "(variables set after the app started are not seen until it restarts). "
                    "Put the key in profiles.json instead, or set the variable and restart."
                    % m.group(1))
            return got
        return _ENV_REF.sub(sub, value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _build_instance(project: str, name: str, raw: Any) -> Instance:
    if not isinstance(raw, dict):
        raise _InstanceError("must be an object")
    raw = _expand(raw)

    url = str(raw.get("url") or "").strip().rstrip("/")
    if not url:
        raise _InstanceError('has no "url", e.g. "http://localhost:8069"')
    if not re.match(r"^https?://", url):
        raise _InstanceError("url %r must start with http:// or https://" % url)
    loopback = is_loopback(url)

    tier = str(raw.get("tier") or "").strip().lower()
    if not tier:
        if not loopback:
            raise _InstanceError(
                'url %s is remote, so it needs "tier": "stage" or "tier": "prod". '
                "The tier of a remote instance is never guessed." % url)
        tier = "local"
    if tier not in TIERS:
        raise _InstanceError('"tier" %r is not one of local, stage, prod' % tier)
    if tier == "local" and not loopback:
        raise _InstanceError(
            '"tier": "local" needs a loopback url (localhost, 127.x, ::1, *.localhost, '
            "*.test); %s is not one. Use \"stage\" or \"prod\"." % url)

    access = str(raw.get("access") or DEFAULT_ACCESS[tier]).strip().lower()
    if access not in ACCESS:
        raise _InstanceError('"access" %r is not one of read, write, full' % access)

    db = str(raw.get("db") or raw.get("database") or "").strip()
    db_auto = db.lower() == "auto" or not db
    if tier == "prod" and db_auto:
        raise _InstanceError(
            'a prod instance needs an explicit "db" - production databases are never '
            "picked or followed automatically")
    if db_auto:
        db = ""

    api_key = str(raw.get("api_key") or "").strip()
    if not api_key:
        raise _InstanceError('has no "api_key"')

    verify_ssl = _as_bool(raw.get("verify_ssl"), True)
    if not verify_ssl and tier == "prod":
        raise _InstanceError(
            '"verify_ssl": false is refused on prod: it would send the API key over a '
            "connection nobody authenticated. Install the server's certificate instead.")

    try:
        timeout = max(5, min(int(raw.get("timeout", 30)), 600))
    except (TypeError, ValueError):
        raise _InstanceError('"timeout" must be a number of seconds')

    companies = raw.get("companies", raw.get("allowed_company_ids")) or []
    if isinstance(companies, int) and not isinstance(companies, bool):
        companies = [companies]
    if not isinstance(companies, list) or not all(
            isinstance(c, int) and not isinstance(c, bool) for c in companies):
        raise _InstanceError('"companies" must be a list of integer company ids')

    allow = raw.get("allow_write_models") or []
    if not isinstance(allow, list):
        raise _InstanceError('"allow_write_models" must be a list of model names')

    db_pattern = str(raw.get("db_pattern") or "").strip()
    if db_pattern:
        try:
            re.compile(db_pattern)
        except re.error as exc:
            raise _InstanceError('"db_pattern" is not a valid regex: %s' % exc)

    return Instance(
        project=project, name=name, url=url, db=db, db_auto=db_auto,
        username=str(raw.get("username") or "").strip(), api_key=api_key,
        tier=tier, access=access, db_pattern=db_pattern, companies=tuple(companies),
        lang=str(raw.get("lang") or "").strip(), tz=str(raw.get("tz") or "").strip(),
        timeout=timeout, verify_ssl=verify_ssl,
        allow_write_models=frozenset(str(m).strip() for m in allow if str(m).strip()),
    )


def _instance(project: str, name: str, raw: Any):
    try:
        return _build_instance(project, name, raw)
    except _InstanceError as exc:
        return BrokenInstance(project, name, "instance %s/%s: %s" % (project, name, exc))


def _check_name(kind: str, name: Any, where: str) -> str:
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise ConfigError(
            "%s: %s name %r is not allowed - use letters, digits, '.', '_' and '-' only"
            % (where, kind, name))
    return name


def parse(text: str, source: Path) -> Config:
    """Parse a version-2 document. Raises ConfigError for problems with the file's
    structure; a problem inside one instance yields a BrokenInstance instead."""
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.strip():
        raise ConfigError("%s is empty" % source)
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            "%s is not valid JSON: %s at line %d col %d. JSON allows no trailing commas "
            "and no comments." % (source, exc.msg, exc.lineno, exc.colno))
    if not isinstance(doc, dict):
        raise ConfigError("%s must contain a JSON object at the top level" % source)
    if doc.get("version") != 2:
        raise ConfigError(
            "%s has \"version\": %r; this server reads version 2."
            % (source, doc.get("version")))

    raw_projects = doc.get("projects") or {}
    if not isinstance(raw_projects, dict):
        raise ConfigError('%s: "projects" must be an object' % source)

    projects: dict = {}
    owner: dict = {}
    for pname, raw in raw_projects.items():
        _check_name("project", pname, str(source))
        where = "%s project %r" % (source, pname)
        if not isinstance(raw, dict):
            raise ConfigError("%s must be an object" % where)
        paths = raw.get("paths")
        if isinstance(paths, str):
            paths = [paths]
        if not isinstance(paths, list) or not paths or not all(
                isinstance(p, str) and p.strip() for p in paths):
            raise ConfigError('%s needs "paths": a non-empty list of folders' % where)
        normed = []
        for p in paths:
            n = norm_path(p)
            if n in owner and owner[n] != pname:
                raise ConfigError("folder %s is listed by both projects %r and %r in %s"
                                  % (p, owner[n], pname, source))
            owner[n] = pname
            if n not in normed:
                normed.append(n)

        raw_instances = raw.get("instances") or {}
        if not isinstance(raw_instances, dict):
            raise ConfigError('%s: "instances" must be an object' % where)
        instances = {}
        for iname, iraw in raw_instances.items():
            _check_name("instance", iname, where)
            instances[iname] = _instance(pname, iname, iraw)

        default = raw.get("default")
        if default is not None and default not in instances:
            raise ConfigError('%s: "default" %r is not one of its instances (%s)'
                              % (where, default, ", ".join(sorted(instances)) or "none"))
        projects[pname] = Project(pname, tuple(normed), default, instances)

    return Config(version=2, projects=projects, source=Path(source))


_V1_TIERS = {"staging": "stage", "stage": "stage", "production": "prod", "prod": "prod",
             "local": "local"}
_V1_ONLY_KEYS = ("tier", "access", "ceiling", "start", "approval", "mode", "allow_unlink",
                 "allow_production_writes", "production", "projects", "password")
V1_WARNING = ("profiles.json is the old (v1) format: every connection is READ-ONLY and "
              "reachable only as legacy/<name>. Run: python <plugin>/scripts/mcp/odoo_mcp.py "
              "migrate")


def _legacy_instance(name: str, raw: Any):
    """A v1 profile, read-only. Its tier is taken from what it says, never guessed
    toward a weaker tier: a remote profile that does not say otherwise is prod."""
    try:
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise _InstanceError("name is not allowed in version 2; migrate renames it")
        if not isinstance(raw, dict):
            raise _InstanceError("must be an object")
        tier = _V1_TIERS.get(str(raw.get("tier") or "").strip().lower())
        if tier is None:
            if _as_bool(raw.get("production"), False):
                tier = "prod"
            elif is_loopback(str(raw.get("url") or "")):
                tier = "local"
            else:
                tier = "prod"
        clean = {k: v for k, v in raw.items() if k not in _V1_ONLY_KEYS}
        clean["api_key"] = raw.get("api_key") or raw.get("password")
        # Build as stage so a missing prod db stays loadable (host-selected, read-only).
        inst = _build_instance("legacy", name, dict(clean, tier="local" if tier == "local" else "stage",
                                                    access="read"))
        if tier == "prod" and not inst.verify_ssl:
            raise _InstanceError('"verify_ssl": false is refused on prod')
        return replace(inst, tier=tier, legacy=True, db_auto=False)
    except _InstanceError as exc:
        return BrokenInstance("legacy", str(name), "instance legacy/%s: %s" % (name, exc))


def parse_v1(doc: dict, source: Path) -> Config:
    """The old profiles.json, loaded READ-ONLY under project "legacy" with no folders,
    so nothing is chosen automatically and nothing can be written."""
    profiles = doc.get("profiles")
    if not isinstance(profiles, dict):
        raise ConfigError('%s: "profiles" must be an object' % source)
    instances = {}
    for name, raw in profiles.items():
        if str(name).startswith("//"):
            continue
        instances[str(name)] = _legacy_instance(name, raw)
    return Config(version=1, projects={"legacy": Project("legacy", (), None, instances)},
                  source=Path(source), warnings=[V1_WARNING])


def load_text(text: str, source: Path) -> Config:
    """Version 2, or a v1 document (no "version", has "profiles")."""
    if text.startswith("\ufeff"):
        text = text[1:]
    try:
        doc = json.loads(text) if text.strip() else None
    except ValueError:
        doc = None
    if isinstance(doc, dict) and "version" not in doc and "profiles" in doc:
        return parse_v1(doc, source)
    return parse(text, source)


class Loader:
    """Re-reads profiles.json whenever its modification time or size changes.

    A broken edit never takes connections away: the last valid version keeps
    serving, with a warning, until the file is fixed."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else config_path()
        self._stamp = None
        self._good = None           # (Config, "HH:MM:SS")
        self._error = None

    def get(self):
        try:
            st = self.path.stat()
        except OSError:
            self._stamp, self._error = None, None
            return None, []
        stamp = (st.st_mtime_ns, st.st_size)
        if stamp != self._stamp:
            self._stamp = stamp
            try:
                cfg = load_text(self.path.read_bytes().decode("utf-8-sig", errors="replace"),
                                self.path)
                self._good, self._error = (cfg, time.strftime("%H:%M:%S")), None
            except ConfigError as exc:
                self._error = str(exc)
            except OSError as exc:
                self._error = "cannot read %s: %s" % (self.path, exc)
        if self._error:
            if self._good is None:
                raise ConfigError(self._error)
            cfg, at = self._good
            return cfg, ["%s is invalid (%s) - still using the last valid version loaded at %s"
                         % (self.path.name, self._error, at)] + list(cfg.warnings)
        cfg = self._good[0]
        return cfg, list(cfg.warnings)


_BACKUP_RE = re.compile(r"^profiles-(\d{8}-\d{6})(?:-(\d+))?\.json$")


def save(doc: dict, path: Optional[Path] = None, keep: int = 10) -> Optional[Path]:
    """Validate, back up the current file, then replace it atomically (UTF-8, LF).

    Returns the backup path, or None when there was no file. Refuses a document
    with a broken instance, unless the only problem is an environment variable
    this process cannot see."""
    path = Path(path) if path else config_path()
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    cfg = parse(text, path)
    broken = [i.error for p in cfg.projects.values() for i in p.instances.values()
              if isinstance(i, BrokenInstance) and "environment variable" not in i.error]
    if broken:
        raise ConfigError("refusing to write %s:\n  %s" % (path, "\n  ".join(broken)))

    backup = None
    _private(path.parent, 0o700, folder=True)
    if path.is_file():
        bdir = path.parent / "backups"
        _private(bdir, 0o700, folder=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup, n = bdir / ("profiles-%s.json" % stamp), 1
        while backup.exists():
            backup, n = bdir / ("profiles-%s-%d.json" % (stamp, n)), n + 1
        shutil.copyfile(path, backup)
        _private(backup, 0o600)
        ordered = sorted(
            (p for p in bdir.iterdir() if _BACKUP_RE.match(p.name)),
            key=lambda p: (_BACKUP_RE.match(p.name).group(1),
                           int(_BACKUP_RE.match(p.name).group(2) or 0)))
        for old in ordered[:-keep] if keep > 0 else []:
            old.unlink(missing_ok=True)

    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(text.encode("utf-8"))
    _private(tmp, 0o600)
    os.replace(tmp, path)
    return backup


def _private(p: Path, mode: int, folder: bool = False) -> None:
    """Keys live here: folders 0700, files 0600. On Windows chmod only toggles the
    read-only flag; the user-profile ACL is what keeps the store private there."""
    if folder:
        p.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p, mode)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Bootstrap assist (proposes a local instance; never connects by itself)
# --------------------------------------------------------------------------


def discover(start) -> dict:
    """Look around a project folder for hints to PROPOSE a local instance."""
    root = Path(start)
    out: dict = {
        "project_dir": str(root),
        "conf_files": [],
        "compose_files": [],
        "suggested": {},
        "notes": [],
    }

    try:
        for pattern in ("*.conf", "conf/*.conf", "config/*.conf", "etc/*.conf", "*/odoo.conf"):
            for p in sorted(root.glob(pattern))[:20]:
                if p.is_file():
                    out["conf_files"].append(str(p))
        for pattern in ("docker-compose.y*ml", "*/docker-compose.y*ml", "compose.y*ml"):
            for p in sorted(root.glob(pattern))[:10]:
                if p.is_file():
                    out["compose_files"].append(str(p))
    except OSError:
        pass

    port, db = None, None
    for cf in out["conf_files"]:
        try:
            import configparser

            cp = configparser.ConfigParser(strict=False, interpolation=None)
            cp.read(cf, encoding="utf-8")
            if cp.has_section("options"):
                port = port or cp.get("options", "http_port", fallback=None) \
                    or cp.get("options", "xmlrpc_port", fallback=None)
                db = db or cp.get("options", "db_name", fallback=None)
        except Exception:  # a malformed conf must never break discovery
            out["notes"].append("could not parse %s" % cf)

    if db in ("False", "false", ""):
        db = None

    out["suggested"] = {
        "url": "http://localhost:%s" % (port or 8069),
        "db": db or "<database name>",
    }
    if out["conf_files"] or out["compose_files"]:
        out["notes"].append(
            "For a LOCAL instance, connect automatically: run "
            "`python <plugin>/scripts/mcp/odoo_mcp.py local` - it creates the key and adds "
            "the instance to profiles.json without asking.")
    if out["compose_files"] and not out["conf_files"]:
        out["notes"].append(
            "Containerised setup detected and no odoo.conf on the host - pass --url and --db "
            "(and --odoo-cmd for the container) to odoo_mcp.py local.")
    return out
