"""Connection profiles for the Odoo MCP server.

Goal: one bundled server that works for ANY developer against ANY instance, with
zero credentials in the plugin and zero per-machine edits to the plugin.

Three owners, three lifetimes (docs: .claude/docs/2026-09-27_odoo-mcp-connection-design.md):

  servers  ~/.odoo-mcp/servers.json (or legacy profiles.json)
           Developer-owned: staging, production, shared instances. This code only
           READS it. The developer sets each profile's tier, ceiling and approval.
  locals   ~/.odoo-mcp/local/<project-key>.json
           Tool-owned: one file per project checkout, written by local_profile.py,
           which Claude runs to connect to a LOCAL instance without asking.
  learned  ~/.odoo-mcp/state/learned.json
           Server-owned facts discovered at runtime (a staging database renamed by a
           rebuild). Layered over the servers file, never written into it.

Plus <project>/.odoo-mcp.json (a developer's per-project pin) and ODOO_* env vars.

Resolution order (first hit wins; odoo_status shows which rule picked it):

  1. ODOO_MCP_PROFILE         explicit name from the developer's environment
  2. <project>/.odoo-mcp.json  project pin
  3. local profile for this project checkout
  4. a server profile bound to this checkout ("projects", or legacy "project_map")
  5. the servers file "default" - ONLY when it is a local-tier profile. A remote
     profile is never selected by accident; bind it or choose it in the session.
  6. ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_API_KEY
  7. nothing -> NoProfile with setup guidance

Any string value may reference an environment variable as ${VAR}.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

PROJECT_FILE = ".odoo-mcp.json"
USER_DIR = ".odoo-mcp"
SERVERS_FILE = "servers.json"
LEGACY_FILE = "profiles.json"

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

MODES = ("read", "write", "write+unlink")
RANK = {m: i for i, m in enumerate(MODES)}
TIERS = ("local", "staging", "production")
APPROVALS = ("none", "chat", "human")
DEFAULT_APPROVAL = {"local": "none", "staging": "chat", "production": "human"}

# Kept for callers that validated the old two-value field.
VALID_MODES = MODES


class ProfileError(Exception):
    """Configuration problem. Message is user-facing and should say how to fix it."""


# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------


def home() -> Path:
    """Config root. ODOO_MCP_HOME overrides it (tests, portable setups)."""
    override = os.environ.get("ODOO_MCP_HOME", "").strip()
    if override and not override.startswith("${"):
        return Path(os.path.expanduser(override))
    return Path(os.path.expanduser("~")) / USER_DIR


def user_file() -> Path:
    """The developer's servers file. servers.json wins; profiles.json is legacy."""
    new = home() / SERVERS_FILE
    return new if new.is_file() else home() / LEGACY_FILE


def local_dir() -> Path:
    return home() / "local"


def state_dir() -> Path:
    return home() / "state"


def grants_dir() -> Path:
    return home() / "grants"


def audit_file() -> Path:
    return home() / "audit.log"


def project_dir() -> Path:
    """The directory Claude Code is working in (forwarded as ODOO_MCP_PROJECT_DIR)."""
    for var in ("ODOO_MCP_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(var, "").strip()
        if val and not val.startswith("${"):
            p = Path(val)
            if p.is_dir():
                return p
    return Path.cwd()


def project_key(path: Path) -> str:
    """Stable file name for a checkout: readable basename + short path hash."""
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    norm = resolved.replace("\\", "/").lower()
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(resolved).name or "root")[:40]
    return "%s-%s" % (base, hashlib.sha1(norm.encode("utf-8")).hexdigest()[:8])


def is_loopback(url: str) -> bool:
    """True only for hosts that cannot be another machine."""
    host = (urlparse(url).hostname or "").lower().strip("[]")
    return (
        host in ("localhost", "::1")
        or host.startswith("127.")
        or host.endswith(".localhost")
        or host.endswith(".test")
    )


def _under(child: Path, parent: Path) -> bool:
    try:
        c, p = child.resolve(), parent.resolve()
    except OSError:
        return False
    return c == p or p in c.parents


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------


@dataclass
class Profile:
    name: str
    url: str
    db: str
    username: str = ""
    api_key: str = ""
    tier: str = "staging"
    ceiling: str = "read"
    start: str = "read"
    approval: str = "chat"
    mode: str = "read"            # the EFFECTIVE mode; the session sets it, default = start
    projects: tuple = ()
    allow_write_models: frozenset = frozenset()
    write_scope: frozenset = frozenset()   # session-level restriction, empty = none
    companies: tuple = ()
    lang: str = ""
    tz: str = ""
    timeout: int = 30
    verify_ssl: bool = True
    db_pattern: str = ""
    kind: str = "server"          # server | local | project | env
    source: str = ""
    configured_db: str = ""       # the db as written, before a learned override
    meta: dict = field(default_factory=dict)

    @property
    def configured(self) -> bool:
        return True

    @property
    def production(self) -> bool:
        return self.tier == "production"

    @property
    def allow_unlink(self) -> bool:
        return RANK[self.mode] >= RANK["write+unlink"]

    @property
    def allow_production_writes(self) -> bool:
        return self.production and RANK[self.ceiling] >= RANK["write"]

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

    def with_mode(self, mode: str, scope=frozenset()) -> "Profile":
        return replace(self, mode=mode, write_scope=frozenset(scope))

    def describe(self) -> dict:
        """Safe-to-display summary. Never includes the key."""
        out = {
            "profile": self.name,
            "kind": self.kind,
            "tier": self.tier,
            "url": self.url,
            "database": self.db or "(selected by host)",
            "username": self.username,
            "mode": self.mode,
            "start": self.start,
            "ceiling": self.ceiling,
            "approval_to_raise": self.approval,
            "allowed_company_ids": list(self.companies) or None,
            "api_key_set": bool(self.api_key),
            "source": self.source,
        }
        if self.write_scope:
            out["write_scope"] = sorted(self.write_scope)
        if self.configured_db and self.configured_db != self.db:
            out["configured_database"] = self.configured_db
        if self.meta.get("expires_at"):
            out["key_expires_at"] = self.meta["expires_at"]
        return out


@dataclass
class NoProfile:
    """Returned when nothing is configured. Tools turn this into setup help."""

    searched: list = field(default_factory=list)
    problem: str = ""

    name = "(none)"

    @property
    def configured(self) -> bool:
        return False

    def secrets(self) -> tuple:
        return ()


# --------------------------------------------------------------------------
# Loading helpers
# --------------------------------------------------------------------------


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProfileError("cannot read %s: %s" % (path, exc))
    if not raw.strip():
        raise ProfileError("%s is empty" % path)
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ProfileError(
            "%s is not valid JSON: %s\n"
            "Tip: trailing commas and comments are not allowed in JSON." % (path, exc)
        )
    if not isinstance(data, dict):
        raise ProfileError("%s must contain a JSON object at the top level" % path)
    return data


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _clamp(mode: str, ceiling: str) -> str:
    return mode if RANK[mode] <= RANK[ceiling] else ceiling


def _choice(raw: dict, key: str, allowed: tuple, name: str) -> Optional[str]:
    value = raw.get(key)
    if value is None or value == "":
        return None
    value = str(value).strip().lower()
    if value not in allowed:
        raise ProfileError(
            "profile %r has %s %r; expected one of %s" % (name, key, value, ", ".join(allowed))
        )
    return value


def _build(name: str, raw: dict, source: str, kind: str = "server") -> Profile:
    raw = _expand(raw)

    url = str(raw.get("url") or "").strip().rstrip("/")
    if not url:
        raise ProfileError(
            "profile %r (%s) has no \"url\". Example: \"http://localhost:8069\"" % (name, source)
        )
    if not re.match(r"^https?://", url):
        raise ProfileError(
            "profile %r has url %r - it must start with http:// or https://" % (name, url)
        )
    # "db" is OPTIONAL: Odoo.sh / Odoo Online select the database from the host.
    # JSON-2 sends X-Odoo-Database only when set; XML-RPC raises at the point of need.
    db = str(raw.get("db") or raw.get("database") or "").strip()
    loopback = is_loopback(url)

    # ---- tier: explicit, else legacy "production", else inferred from the host
    tier = _choice(raw, "tier", TIERS, name)
    if tier is None:
        if _as_bool(raw.get("production")):
            tier = "production"
        else:
            tier = "local" if loopback else "staging"
    if tier == "local" and not loopback:
        raise ProfileError(
            "profile %r is tier \"local\" but its url %r is not a loopback host.\n"
            "Only localhost / 127.x / ::1 / *.localhost / *.test can be local - that is what "
            "lets local profiles skip approval. Use tier \"staging\" for this server." % (name, url)
        )

    # ---- ceiling: explicit, else derived from the legacy switches
    ceiling = _choice(raw, "ceiling", MODES, name)
    legacy_mode = _choice(raw, "mode", ("read", "write", "write+unlink"), name)
    allow_unlink = _as_bool(raw.get("allow_unlink"))
    if ceiling is None:
        if tier == "local":
            ceiling = "write+unlink"
        elif tier == "production":
            if _as_bool(raw.get("allow_production_writes")):
                ceiling = "write+unlink" if allow_unlink else "write"
            else:
                ceiling = "read"
        else:
            ceiling = "write+unlink" if allow_unlink else "write"

    # ---- start mode: explicit, else legacy "mode" (+allow_unlink), else by tier
    start = _choice(raw, "start", MODES, name)
    if start is None:
        if legacy_mode:
            start = legacy_mode
            if legacy_mode == "write" and allow_unlink:
                start = "write+unlink"
        else:
            start = "write" if tier == "local" else "read"
    start = _clamp(start, ceiling)

    # ---- approval
    approval = _choice(raw, "approval", APPROVALS, name) or DEFAULT_APPROVAL[tier]
    if tier == "production" and approval == "none":
        raise ProfileError(
            "profile %r is production with \"approval\": \"none\". Refusing: raising a "
            "production connection to write must need at least \"chat\" approval "
            "(the developer's explicit yes) - \"human\" is the default." % name
        )

    companies = raw.get("allowed_company_ids") or raw.get("companies") or []
    if isinstance(companies, int):
        companies = [companies]
    if not isinstance(companies, list) or not all(isinstance(c, int) for c in companies):
        raise ProfileError("profile %r: allowed_company_ids must be a list of integer company ids" % name)

    allow_models = raw.get("allow_write_models") or []
    if not isinstance(allow_models, list):
        raise ProfileError("profile %r: allow_write_models must be a list of model names" % name)

    projects = raw.get("projects") or []
    if isinstance(projects, str):
        projects = [projects]
    if not isinstance(projects, list):
        raise ProfileError("profile %r: projects must be a list of checkout paths" % name)

    timeout = raw.get("timeout", 30)
    try:
        timeout = max(5, min(int(timeout), 600))
    except (TypeError, ValueError):
        raise ProfileError("profile %r: timeout must be an integer number of seconds" % name)

    verify_ssl = _as_bool(raw.get("verify_ssl"), True)
    if not verify_ssl:
        if tier == "production":
            raise ProfileError(
                "profile %r is production and sets \"verify_ssl\": false.\n"
                "Refusing: that would send the API key over a connection nobody has "
                "authenticated. Install the server's certificate (or its CA) into the "
                "trust store instead." % name
            )
        import sys as _sys

        print(
            "[odoo-mcp] WARNING: profile %r disables TLS certificate verification. "
            "Use this only against a local development server." % name,
            file=_sys.stderr,
        )

    db_pattern = str(raw.get("db_pattern") or "").strip()
    if db_pattern:
        try:
            re.compile(db_pattern)
        except re.error as exc:
            raise ProfileError("profile %r: db_pattern is not a valid regex: %s" % (name, exc))

    return Profile(
        name=name,
        url=url,
        db=db,
        configured_db=db,
        username=str(raw.get("username") or raw.get("login") or "").strip(),
        api_key=str(raw.get("api_key") or raw.get("password") or "").strip(),
        tier=tier,
        ceiling=ceiling,
        start=start,
        approval=approval,
        mode=start,
        projects=tuple(str(p) for p in projects),
        allow_write_models=frozenset(str(m).strip() for m in allow_models if str(m).strip()),
        companies=tuple(companies),
        lang=str(raw.get("lang") or "").strip(),
        tz=str(raw.get("tz") or "").strip(),
        timeout=timeout,
        verify_ssl=verify_ssl,
        db_pattern=db_pattern,
        kind=kind,
        source=source,
        meta={k: raw[k] for k in ("expires_at", "created_at", "conf", "odoo_version") if k in raw},
    )


# --------------------------------------------------------------------------
# Learned facts (runtime-discovered database renames)
# --------------------------------------------------------------------------


def _learned_path() -> Path:
    return state_dir() / "learned.json"


def load_learned() -> dict:
    try:
        data = json.loads(_learned_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember_db(profile: Profile, new_db: str) -> dict:
    """Record that a profile's database moved. Keyed by profile name + url, so a
    developer editing the url invalidates the learned value automatically."""
    data = load_learned()
    entry = {
        "url": profile.url,
        "db": new_db,
        "previous_db": profile.db,
        "configured_db": profile.configured_db,
        "learned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data[profile.name] = entry
    path = _learned_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return entry


def _apply_learned(prof: Profile, learned: dict) -> Profile:
    entry = learned.get(prof.name)
    if isinstance(entry, dict) and entry.get("url") == prof.url and "db" in entry:
        return replace(prof, db=str(entry["db"]))
    return prof


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------


@dataclass
class Catalog:
    profiles: dict = field(default_factory=dict)     # name -> Profile
    chosen: Optional[str] = None
    reason: str = ""
    warnings: list = field(default_factory=list)
    searched: list = field(default_factory=list)
    problem: str = ""


def _profiles_in(doc: dict, path: Path) -> dict:
    """name -> raw dict for a config document (full or single-profile shorthand)."""
    profiles = doc.get("profiles")
    if isinstance(profiles, dict):
        out = {}
        for name, raw in profiles.items():
            if str(name).startswith("//"):
                continue
            if not isinstance(raw, dict):
                raise ProfileError("profile %r in %s must be an object" % (name, path))
            out[str(name)] = raw
        return out
    if doc.get("url"):
        return {str(doc.get("name") or path.stem.lstrip(".") or "default"): doc}
    return {}


def _local_files(proj: Path) -> list:
    """(path, doc) for local-profile files that belong to this checkout, deepest first."""
    folder = local_dir()
    found = []
    if not folder.is_dir():
        return found
    for path in sorted(folder.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        pdir = doc.get("project_dir") if isinstance(doc, dict) else None
        if pdir and _under(proj, Path(pdir)):
            found.append((len(str(pdir)), path, doc))
    return [(p, d) for _, p, d in sorted(found, key=lambda t: -t[0])]


def load_catalog(wanted: Optional[str] = None, proj: Optional[Path] = None) -> Catalog:
    """Every profile visible from this checkout, plus which one to use and why.

    Raises ProfileError for a broken developer-owned file (servers / project), since
    the developer must fix it. A broken tool-owned local file is skipped with a warning.
    """
    proj = proj or project_dir()
    cat = Catalog()
    learned = load_learned()

    def add(prof: Profile):
        if prof.name in cat.profiles:
            cat.warnings.append(
                "profile name %r is defined twice; %s wins over %s"
                % (prof.name, cat.profiles[prof.name].source, prof.source)
            )
            return
        cat.profiles[prof.name] = prof

    # --- project pin
    pfile = proj / PROJECT_FILE
    cat.searched.append(str(pfile))
    project_doc = None
    if pfile.is_file():
        project_doc = _read_json(pfile)
        for name, raw in _profiles_in(project_doc, pfile).items():
            add(_apply_learned(_build(name, raw, "%s [%s]" % (pfile, name), "project"), learned))

    # --- locals for this checkout
    cat.searched.append(str(local_dir()))
    local_names = []
    for path, doc in _local_files(proj):
        label = Path(str(doc.get("project_dir"))).name or "project"
        for db, raw in (doc.get("profiles") or {}).items():
            name = "local:%s/%s" % (label, db)
            try:
                prof = _build(name, dict(raw, tier="local"), "%s [%s]" % (path, db), "local")
            except ProfileError as exc:
                cat.warnings.append("skipped local profile %s: %s" % (name, exc))
                continue
            add(prof)
            local_names.append((db == doc.get("active"), str(raw.get("created_at") or ""), name))

    # --- servers (developer-owned)
    sfile = user_file()
    cat.searched.append(str(sfile))
    servers_doc = None
    if sfile.is_file():
        servers_doc = _read_json(sfile)
        for name, raw in _profiles_in(servers_doc, sfile).items():
            add(_apply_learned(_build(name, raw, "%s [%s]" % (sfile, name), "server"), learned))

    # --- env
    cat.searched.append("environment (ODOO_URL/ODOO_DB/ODOO_USERNAME/ODOO_API_KEY)")
    env_prof = _from_env()
    if env_prof is not None:
        add(env_prof)

    # ---------------- choose ----------------
    def pick(name, reason):
        cat.chosen, cat.reason = name, reason
        return cat

    if wanted:
        if wanted in cat.profiles:
            return pick(wanted, "explicitly selected (ODOO_MCP_PROFILE / session)")
        cat.problem = "profile %r was requested but is not defined in %s" % (
            wanted, ", ".join(cat.searched[:3]))
        return cat

    if project_doc is not None:
        names = list(_profiles_in(project_doc, pfile))
        mapped = _map_lookup(project_doc.get("project_map"), proj)
        name = mapped or project_doc.get("default") or (names[0] if len(names) == 1 else None)
        if name:
            if name not in cat.profiles:
                raise ProfileError("profile %r not found in %s. Available: %s"
                                   % (name, pfile, ", ".join(sorted(names)) or "(none)"))
            return pick(name, "project pin (%s)" % pfile)
        raise ProfileError(
            "%s defines %d profiles (%s) but no \"default\".\nAdd \"default\": \"<name>\"."
            % (pfile, len(names), ", ".join(sorted(names)))
        )

    if local_names:
        local_names.sort(reverse=True)   # active first, then newest
        return pick(local_names[0][2], "local profile for this checkout")

    if servers_doc is not None:
        best, best_len = None, -1
        for prof in cat.profiles.values():
            if prof.kind != "server":
                continue
            for p in prof.projects:
                kp = Path(os.path.expanduser(p))
                if _under(proj, kp) and len(str(kp)) > best_len:
                    best, best_len = prof.name, len(str(kp))
        mapped = _map_lookup(servers_doc.get("project_map"), proj)
        if mapped and mapped in cat.profiles and best is None:
            best = mapped
        if best:
            return pick(best, "server profile bound to this checkout")

        default = servers_doc.get("default")
        if default:
            prof = cat.profiles.get(str(default))
            if prof is None:
                cat.warnings.append("servers file default %r is not a defined profile" % default)
            elif prof.tier == "local":
                return pick(prof.name, "servers file default (local tier)")
            else:
                cat.warnings.append(
                    "servers file default %r is a %s profile and was NOT auto-selected: a remote "
                    "instance is only used when bound to the project (\"projects\") or chosen with "
                    "odoo_session action=use." % (prof.name, prof.tier)
                )

    if env_prof is not None:
        return pick(env_prof.name, "environment variables")

    return cat


def _map_lookup(mapping: Any, proj: Path) -> Optional[str]:
    if not isinstance(mapping, dict):
        return None
    best, best_len = None, -1
    for key, prof_name in mapping.items():
        if str(key).startswith("//"):
            continue
        kp = Path(os.path.expanduser(str(key)))
        if _under(proj, kp) and len(str(kp)) > best_len:
            best, best_len = str(prof_name), len(str(kp))
    return best


def _from_env() -> Optional[Profile]:
    url = os.environ.get("ODOO_URL", "").strip()
    if not url or url.startswith("${"):
        return None
    raw = {
        "url": url,
        "db": os.environ.get("ODOO_DB", "").strip(),
        "username": os.environ.get("ODOO_USERNAME", os.environ.get("ODOO_USER", "")).strip(),
        "api_key": os.environ.get("ODOO_API_KEY", os.environ.get("ODOO_PASSWORD", "")).strip(),
        "mode": os.environ.get("ODOO_MCP_MODE", "").strip() or None,
        "production": os.environ.get("ODOO_MCP_PRODUCTION", ""),
    }
    return _build("env", raw, "environment variables", "env")


def wanted_from_env() -> Optional[str]:
    wanted = os.environ.get("ODOO_MCP_PROFILE", "").strip() or None
    if wanted and wanted.startswith("${"):
        wanted = None
    return wanted


def resolve():
    """Return the chosen Profile or a NoProfile. Raises ProfileError on a broken config."""
    cat = load_catalog(wanted_from_env())
    if cat.chosen:
        return cat.profiles[cat.chosen]
    return NoProfile(searched=cat.searched, problem=cat.problem)


# --------------------------------------------------------------------------
# Bootstrap assist (used by setup flows and local provisioning, never to auto-connect)
# --------------------------------------------------------------------------


def discover(start: Optional[Path] = None) -> dict:
    """Look around the project for hints to PROPOSE a profile."""
    root = Path(start or project_dir())
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
            "`python <plugin>/scripts/mcp/local_profile.py provision` - it creates the key and the "
            "profile without editing any developer file."
        )
    if out["compose_files"] and not out["conf_files"]:
        out["notes"].append(
            "Containerised setup detected and no odoo.conf on the host - pass --url and --db "
            "(and --odoo-cmd for the container) to local_profile.py."
        )
    return out
