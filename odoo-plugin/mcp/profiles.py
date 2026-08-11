"""Connection-profile resolution for the Odoo MCP server.

Goal: one bundled server that works for ANY developer against ANY instance,
with zero credentials in the plugin and zero per-machine edits to the plugin.

Resolution order (first hit wins):

  1. ODOO_MCP_PROFILE           -- explicit profile name, looked up in the
                                   project file then the user file.
  2. <project>/.odoo-mcp.json   -- project-local. Git-ignore this.
  3. ~/.odoo-mcp/profiles.json  -- user-wide, with an optional project_map so
                                   one file serves many checkouts.
  4. ODOO_URL / ODOO_DB / ODOO_USERNAME / ODOO_API_KEY environment variables.
  5. Nothing -> a NoProfile object carrying actionable setup guidance.

Any string value may reference an environment variable as ${VAR}, so the
profile file can be committed-safe by keeping the secret in the environment:

    {"profiles": {"local": {"api_key": "${MY_ODOO_KEY}"}}}
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

PROJECT_FILE = ".odoo-mcp.json"
USER_DIR = ".odoo-mcp"
USER_FILE = "profiles.json"

_ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

VALID_MODES = ("read", "write")


class ProfileError(Exception):
    """Configuration problem. Message is user-facing and should say how to fix it."""


@dataclass
class Profile:
    name: str
    url: str
    db: str
    username: str = ""
    api_key: str = ""
    mode: str = "read"
    production: bool = False
    allow_unlink: bool = False
    allow_production_writes: bool = False
    allow_write_models: frozenset = frozenset()
    companies: tuple = ()
    lang: str = ""
    tz: str = ""
    timeout: int = 30
    verify_ssl: bool = True
    source: str = ""

    @property
    def configured(self) -> bool:
        return True

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
            "profile": self.name,
            "url": self.url,
            "database": self.db,
            "username": self.username,
            "mode": self.mode,
            "production": self.production,
            "allow_unlink": self.allow_unlink,
            "allow_production_writes": self.allow_production_writes,
            "allow_write_models": sorted(self.allow_write_models),
            "allowed_company_ids": list(self.companies) or None,
            "api_key_set": bool(self.api_key),
            "source": self.source,
        }


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
# Loading
# --------------------------------------------------------------------------


def _expand(value: Any) -> Any:
    """Expand ${VAR} references in strings, recursively through containers."""
    if isinstance(value, str):
        def sub(m):
            return os.environ.get(m.group(1), "")
        return _ENV_REF.sub(sub, value)
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


def _build(name: str, raw: dict, source: str) -> Profile:
    raw = _expand(raw)

    url = str(raw.get("url") or "").strip().rstrip("/")
    db = str(raw.get("db") or raw.get("database") or "").strip()
    if not url:
        raise ProfileError(
            "profile %r (%s) has no \"url\". Example: \"http://localhost:8069\"" % (name, source)
        )
    if not re.match(r"^https?://", url):
        raise ProfileError(
            "profile %r has url %r - it must start with http:// or https://" % (name, url)
        )
    if not db:
        raise ProfileError(
            "profile %r (%s) has no \"db\". This is the Odoo database name." % (name, source)
        )

    mode = str(raw.get("mode") or "read").strip().lower()
    if mode not in VALID_MODES:
        raise ProfileError(
            "profile %r has mode %r; expected one of %s" % (name, mode, ", ".join(VALID_MODES))
        )

    companies = raw.get("allowed_company_ids") or raw.get("companies") or []
    if isinstance(companies, int):
        companies = [companies]
    if not isinstance(companies, list) or not all(isinstance(c, int) for c in companies):
        raise ProfileError(
            "profile %r: allowed_company_ids must be a list of integer company ids" % name
        )

    allow_models = raw.get("allow_write_models") or []
    if not isinstance(allow_models, list):
        raise ProfileError("profile %r: allow_write_models must be a list of model names" % name)

    timeout = raw.get("timeout", 30)
    try:
        timeout = max(5, min(int(timeout), 600))
    except (TypeError, ValueError):
        raise ProfileError("profile %r: timeout must be an integer number of seconds" % name)

    production = _as_bool(raw.get("production"))
    verify_ssl = _as_bool(raw.get("verify_ssl"), True)
    if not verify_ssl:
        # Turning off certificate verification exposes the connection - and the API
        # key travelling on it - to interception. Tolerated only for local development.
        if production:
            raise ProfileError(
                "profile %r sets both \"production\": true and \"verify_ssl\": false.\n"
                "Refusing: that would send the API key over a connection nobody has "
                "authenticated. Install the server's certificate (or its CA) into the "
                "trust store instead." % name
            )
        import sys as _sys

        print(
            "[odoo-mcp] WARNING: profile %r disables TLS certificate verification. "
            "The connection can be intercepted. Use this only against a local "
            "development server, and prefer trusting the dev CA instead." % name,
            file=_sys.stderr,
        )

    return Profile(
        name=name,
        url=url,
        db=db,
        username=str(raw.get("username") or raw.get("login") or "").strip(),
        api_key=str(raw.get("api_key") or raw.get("password") or "").strip(),
        mode=mode,
        production=production,
        allow_unlink=_as_bool(raw.get("allow_unlink")),
        allow_production_writes=_as_bool(raw.get("allow_production_writes")),
        allow_write_models=frozenset(str(m).strip() for m in allow_models if str(m).strip()),
        companies=tuple(companies),
        lang=str(raw.get("lang") or "").strip(),
        tz=str(raw.get("tz") or "").strip(),
        timeout=timeout,
        verify_ssl=verify_ssl,
        source=source,
    )


def project_dir() -> Path:
    """The directory Claude Code is working in.

    Plugin-provided MCP configs get ${CLAUDE_PROJECT_DIR} substituted directly,
    which we forward as ODOO_MCP_PROJECT_DIR.
    """
    for var in ("ODOO_MCP_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(var, "").strip()
        # An unexpanded "${VAR}" means the client did not substitute it; ignore.
        if val and not val.startswith("${"):
            p = Path(val)
            if p.is_dir():
                return p
    return Path.cwd()


def user_file() -> Path:
    return Path(os.path.expanduser("~")) / USER_DIR / USER_FILE


def _select(doc: dict, path: Path, wanted: Optional[str], proj: Path) -> Optional[Profile]:
    """Pull a profile out of a loaded config document."""
    profiles = doc.get("profiles")

    # Shorthand: the file itself is a single profile.
    if not isinstance(profiles, dict):
        if doc.get("url"):
            name = str(doc.get("name") or path.stem.lstrip(".") or "default")
            if wanted and wanted != name:
                return None
            return _build(name, doc, str(path))
        return None

    if not profiles:
        return None

    name = wanted
    if not name:
        mapping = doc.get("project_map")
        if isinstance(mapping, dict):
            try:
                here = proj.resolve()
            except OSError:
                here = proj
            best, best_len = None, -1
            for key, prof_name in mapping.items():
                try:
                    kp = Path(os.path.expanduser(str(key))).resolve()
                except OSError:
                    continue
                # longest matching prefix wins, so a subdir can override a parent
                if (here == kp or kp in here.parents) and len(str(kp)) > best_len:
                    best, best_len = str(prof_name), len(str(kp))
            name = best
    if not name:
        name = doc.get("default")
    if not name and len(profiles) == 1:
        name = next(iter(profiles))
    if not name:
        raise ProfileError(
            "%s defines %d profiles (%s) but no \"default\" and no \"project_map\" entry "
            "matching this directory.\n"
            "Add \"default\": \"<name>\", or set ODOO_MCP_PROFILE."
            % (path, len(profiles), ", ".join(sorted(profiles)))
        )

    raw = profiles.get(name)
    if raw is None:
        raise ProfileError(
            "profile %r not found in %s. Available: %s"
            % (name, path, ", ".join(sorted(profiles)) or "(none)")
        )
    if not isinstance(raw, dict):
        raise ProfileError("profile %r in %s must be an object" % (name, path))
    return _build(str(name), raw, "%s [%s]" % (path, name))


def _from_env() -> Optional[Profile]:
    url = os.environ.get("ODOO_URL", "").strip()
    if not url or url.startswith("${"):
        return None
    raw = {
        "url": url,
        "db": os.environ.get("ODOO_DB", "").strip(),
        "username": os.environ.get("ODOO_USERNAME", os.environ.get("ODOO_USER", "")).strip(),
        "api_key": os.environ.get("ODOO_API_KEY", os.environ.get("ODOO_PASSWORD", "")).strip(),
        "mode": os.environ.get("ODOO_MCP_MODE", "read").strip() or "read",
        "production": os.environ.get("ODOO_MCP_PRODUCTION", ""),
    }
    return _build("env", raw, "environment variables")


def resolve():
    """Return a Profile or a NoProfile. Raises ProfileError only on a broken config."""
    wanted = os.environ.get("ODOO_MCP_PROFILE", "").strip() or None
    if wanted and wanted.startswith("${"):
        wanted = None

    proj = project_dir()
    searched = []

    for path in (proj / PROJECT_FILE, user_file()):
        searched.append(str(path))
        if not path.is_file():
            continue
        prof = _select(_read_json(path), path, wanted, proj)
        if prof is not None:
            return prof

    searched.append("environment (ODOO_URL/ODOO_DB/ODOO_USERNAME/ODOO_API_KEY)")
    prof = _from_env()
    if prof is not None:
        return prof

    problem = ""
    if wanted:
        problem = "ODOO_MCP_PROFILE=%r was set, but no config file defining it was found." % wanted
    return NoProfile(searched=searched, problem=problem)


# --------------------------------------------------------------------------
# Bootstrap assist (used by the /odoo-mcp setup flow, never at runtime)
# --------------------------------------------------------------------------


def discover(start: Optional[Path] = None) -> dict:
    """Look around the project for hints to PROPOSE a profile.

    Deliberately advisory. Odoo config layouts vary widely between projects
    (config/ vs conf/, arbitrary file names, containerised setups with no conf
    on disk at all), so this suggests values for a human to confirm - it is
    never used to auto-connect.
    """
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
        "username": "<odoo login for a dedicated, least-privilege MCP user>",
        "api_key": "${ODOO_MCP_API_KEY}",
        "mode": "read",
    }
    if out["compose_files"] and not out["conf_files"]:
        out["notes"].append(
            "Containerised setup detected and no odoo.conf on the host - confirm the "
            "published port and database name from the compose file."
        )
    if not out["conf_files"] and not out["compose_files"]:
        out["notes"].append(
            "No Odoo config discovered here. Fill the values in manually; discovery is "
            "only a convenience."
        )
    return out
