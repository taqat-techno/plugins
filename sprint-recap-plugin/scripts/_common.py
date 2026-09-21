"""Shared helpers for sprint-recap.

Deliberately dependency-free: collect / build / publish must run on a bare
Python 3.9+. Only the capture stage needs a third-party package (Playwright),
and it fails with an actionable message rather than an ImportError traceback.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RECAP_DIRNAME = ".sprint-recap"
CONFIG_FILENAME = ".sprint-recap.local.json"

# Selectors / captions that must never be clicked unless a step explicitly
# opts in AND the target is not production. Mirrors qa-browser's discipline.
DESTRUCTIVE_PATTERN = re.compile(
    r"\b(delete|destroy|remove|drop|wipe|purge|truncate|revoke|deactivate|"
    r"terminate|cancel\s+subscription|reset\s+password|حذف|إلغاء)\b",
    re.IGNORECASE,
)

PRODUCTION_HINTS = ("prod", "production", "live", "www.")


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
            "Run /sprint-recap-target set to create it."
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
    missing = [k for k in ("username", "password") if not creds.get(k)]
    if missing:
        die(f"Role '{role}' is missing: {', '.join(missing)}")
    return creds


def is_production(url: str, config: dict) -> bool:
    lowered = (url or "").lower()
    markers = config.get("production_markers") or list(PRODUCTION_HINTS)
    return any(marker.lower() in lowered for marker in markers)


# --------------------------------------------------------------------------- #
# secrets
# --------------------------------------------------------------------------- #
def mask(secret: str) -> str:
    """Mask a secret for display. Never returns the original value."""
    if not secret:
        return ""
    if len(secret) <= 4:
        return "*" * len(secret)
    return f"{secret[0]}{'*' * (len(secret) - 2)}{secret[-1]}"


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


def git(args: list[str], cwd: Path, timeout: int = 60) -> str:
    """Run a read-only git command. Returns '' on any failure."""
    try:
        out = subprocess.run(
            ["git", "-c", f"safe.directory={cwd.as_posix()}", *args],
            cwd=cwd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def which(binary: str) -> bool:
    from shutil import which as _which
    return _which(binary) is not None
