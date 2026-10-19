"""Shared helpers for sprint-recap.

Deliberately dependency-free: collect / build / publish must run on a bare
Python 3.9+. Only the capture stage needs a third-party package (Playwright),
and it fails with an actionable message rather than an ImportError traceback.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

RECAP_DIRNAME = ".sprint-recap"
CONFIG_FILENAME = ".sprint-recap.local.json"

# Selectors / captions that must never be clicked unless a step explicitly
# opts in AND the target is not production. Mirrors qa-browser's discipline.
DESTRUCTIVE_PATTERN = re.compile(
    r"\b(delete|destroy|remove|drop|wipe|purge|truncate|revoke|deactivate|"
    r"terminate|cancel\s+subscription|reset\s+password|حذف|إلغاء)\b",
    re.IGNORECASE,
)

# Hostname labels that mark production. Matched against whole labels of the host
# (split on "." and "-"), so staging.delivery-app.io is not "live" and
# app-prod.example.com is "prod". `www` counts only as the first label.
PRODUCTION_HINTS = ("prod", "production", "live", "www")

# Hosts that are always the developer's own machine or a reserved test name.
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")
LOCAL_SUFFIXES = (".localhost", ".test", ".local")


# --------------------------------------------------------------------------- #
# paths + config
# --------------------------------------------------------------------------- #
def project_root(start: Path | None = None) -> Path:
    """Repo root if we are inside a git work tree, else the cwd."""
    start = start or Path.cwd()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return start


def recap_dir(root: Path | None = None) -> Path:
    return (root or project_root()) / RECAP_DIRNAME


def run_dir(sprint_id: str, root: Path | None = None) -> Path:
    return recap_dir(root) / "runs" / slugify(sprint_id)


def config_path(root: Path | None = None) -> Path:
    return (root or project_root()) / CONFIG_FILENAME


def load_config(root: Path | None = None) -> dict:
    path = config_path(root)
    if not path.exists():
        die(
            f"No {CONFIG_FILENAME} found at {path}.\n"
            "Run /sprint-recap:target set to create it."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"{path} is not valid JSON: {exc}")


def resolve_target(config: dict, target: str) -> dict:
    targets = config.get("targets", {})
    if target not in targets:
        die(
            f"Target '{target}' is not defined in {CONFIG_FILENAME}. "
            f"Known targets: {', '.join(sorted(targets)) or '(none)'}"
        )
    entry = targets[target]
    if not entry.get("base_url"):
        die(f"Target '{target}' has no base_url.")
    return entry


def resolve_role(config: dict, target: str, role: str) -> dict:
    """Return {username, password} for a role, or die with a clear message."""
    roles = resolve_target(config, target).get("roles", {})
    if role not in roles:
        die(
            f"Role '{role}' is not defined for target '{target}'. "
            f"Known roles: {', '.join(sorted(roles)) or '(none)'}"
        )
    creds = roles[role]
    if creds.get("storage_state") and not creds.get("password"):
        # SSO / MFA: the user supplies a logged-in Playwright storage state.
        return creds
    missing = [k for k in ("username", "password") if not creds.get(k)]
    if missing:
        die(f"Role '{role}' is missing: {', '.join(missing)}")
    return creds


def host_of(url: str) -> str:
    try:
        return (urlsplit(url or "").hostname or "").lower()
    except ValueError:
        return ""


def is_local_host(url: str) -> bool:
    host = host_of(url)
    return host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES)


def is_production(url: str, config: dict) -> bool:
    """True when the URL looks like production.

    `production_markers` in the config (substrings, matched anywhere in the URL)
    replace the default. The default matches whole hostname labels, never
    substrings, so "staging.delivery-app.io" is not mistaken for "live".
    """
    custom = config.get("production_markers")
    if custom:
        lowered = (url or "").lower()
        return any(str(marker).lower() in lowered for marker in custom)
    host = host_of(url)
    if not host:
        return False
    labels = re.split(r"[.-]", host)
    if labels and labels[0] == "www":
        return True
    return any(label in PRODUCTION_HINTS for label in labels)


def capture_refusal(url: str, target_cfg: dict, config: dict,
                    allow_production: bool = False, name: str = "") -> str | None:
    """Why capture must not run against this target, or None when it may.

    A browser run logs in with real credentials and clicks through the app, so
    the default is to refuse anything that is not provably a test environment:
      * a production-looking URL is refused unless --allow-production is given;
      * any other host must be local, or the target must opt in with
        `"allow_capture": true` in .sprint-recap.local.json.
    """
    if is_production(url, config) and not allow_production:
        return ("Refusing to capture against a production-looking URL: " + str(url)
                + ". Point `target` at staging, or pass --allow-production if you "
                "are certain this data is disposable.")
    if is_local_host(url) or target_cfg.get("allow_capture") is True:
        return None
    return ("Target " + repr(name) + " (" + str(url) + ") is not a "
            "local host and does not set \"allow_capture\": true. Confirm it is a "
            "disposable test environment, then add that key to the target in "
            ".sprint-recap.local.json.")


def same_host(url: str, base_url: str) -> bool:
    """True when an absolute URL stays on the base URL's host."""
    return host_of(url) == host_of(base_url)


# --------------------------------------------------------------------------- #
# secrets
# --------------------------------------------------------------------------- #
def mask(secret: str) -> str:
    """Mask a secret for display. Reveals neither characters nor the length."""
    return "********" if secret else ""


def redact(text: str, secrets: list[str]) -> str:
    """Strip known secret values out of arbitrary text before it is written."""
    for secret in secrets:
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    return text


# --------------------------------------------------------------------------- #
# misc
# --------------------------------------------------------------------------- #
def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip("-")
    return slug.lower() or "sprint"


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def warn(message: str) -> None:
    print(f"WARN: {message}", file=sys.stderr)


def info(message: str) -> None:
    print(message, file=sys.stderr)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_run(args: list[str], cwd: Path, timeout: int = 60) -> tuple[int, str, str]:
    """Run a read-only git command: (returncode, stdout, stderr).

    git's safe.directory check is left on: a repository owned by another user
    can run programs through its own config (core.fsmonitor, ...), so such a
    repo is reported as a degraded source instead of being forced open.
    """
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)
    return out.returncode, out.stdout or "", out.stderr or ""


def git(args: list[str], cwd: Path, timeout: int = 60) -> str:
    """Run a read-only git command. Returns '' on any failure."""
    code, stdout, _ = git_run(args, cwd, timeout)
    return stdout if code == 0 else ""


def which(binary: str) -> bool:
    return shutil.which(binary) is not None


# cmd.exe interprets these even inside the quotes Python adds for a .cmd/.bat shim.
CMD_UNSAFE = re.compile(r'["%!^&|<>\r\n]')


class UnsafeArgument(ValueError):
    """An argument cannot be passed safely to a Windows batch shim."""


def tool_argv(argv: list[str]) -> list[str]:
    """Resolve argv[0] on PATH and return a list to run WITHOUT a shell.

    On Windows, npm, npx and az are .cmd shims. Windows runs those through
    cmd.exe even with shell=False, and cmd.exe does not honour the quoting
    Python adds, so an argument containing `"`, `%`, `&`, `|` ... would become
    shell syntax. Such an argument is refused (UnsafeArgument) instead.
    Raises FileNotFoundError when the program is not on PATH.
    """
    exe = shutil.which(argv[0])
    if not exe:
        raise FileNotFoundError(argv[0] + " is not on PATH")
    if Path(exe).suffix.lower() in (".cmd", ".bat"):
        for arg in argv[1:]:
            if CMD_UNSAFE.search(str(arg)):
                raise UnsafeArgument(
                    argv[0] + " is a batch shim on this system and an argument "
                    "contains a character cmd.exe would interpret: " + repr(arg)[:80]
                )
    return [exe, *[str(a) for a in argv[1:]]]
