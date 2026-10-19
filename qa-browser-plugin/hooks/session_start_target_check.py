#!/usr/bin/env python3
"""
qa-browser SessionStart hook - config and evidence safety check.

Runs only when `.qa-browser.local.json` exists in the project root
($CLAUDE_PROJECT_DIR, else the cwd). Silent otherwise, and silent when every
check passes. Checks:

  1. the config is tracked by git                      -> DANGER
  2. the config is not git-ignored                     -> WARNING
  3. the config holds inline credential values
     (`password` / `totp` / `totpSecret` strings) instead of env-var
     references (`passwordEnv` / `totpEnv`)            -> WARNING
  4. a `qa-evidence/` directory exists and is not git-ignored -> WARNING
  5. `targetUrl` is a production host under the gate's rules  -> WARNING
  6. a role's `passwordEnv` / `totpEnv` is outside the credential
     allow-list (QA_* or the credential_env_allowlist option)  -> WARNING

Output: SessionStart hook JSON on stdout (`additionalContext` for Claude,
`systemMessage` for the user). Always exit 0; any error fails open.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

CONFIG_FILENAME = ".qa-browser.local.json"
EVIDENCE_DIR = "qa-evidence"
INLINE_SECRET_KEYS = ("password", "totp", "totpSecret")


def project_root() -> Path:
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project and Path(project).is_dir():
        return Path(project)
    return Path.cwd()


def inline_secret_roles(data: dict) -> list[str]:
    """Roles whose entry stores a credential value directly in the file."""
    roles = data.get("roles")
    if not isinstance(roles, dict):
        return []
    hits = []
    for name, entry in roles.items():
        if isinstance(entry, dict) and any(
                isinstance(entry.get(k), str) and entry.get(k).strip()
                for k in INLINE_SECRET_KEYS):
            hits.append(str(name))
    return sorted(hits)


def main() -> int:
    hooklib.watchdog(4.5)
    root = project_root()
    config_path = root / CONFIG_FILENAME
    if not config_path.is_file():
        return 0  # first-time user or a project that does not use qa-browser

    issues: list[str] = []
    in_git = _is_git_repo(root)

    if in_git and _is_tracked(root, CONFIG_FILENAME):
        issues.append(
            f"DANGER: {CONFIG_FILENAME} is tracked by git. Run:\n"
            f"    git rm --cached {CONFIG_FILENAME}\n"
            f"    echo '{CONFIG_FILENAME}' >> .gitignore\n"
            f"  then commit the .gitignore change. If the file ever held a password, "
            f"rotate it: it is in the git history."
        )
    if in_git and not _is_ignored(root, CONFIG_FILENAME):
        issues.append(
            f"WARNING: {CONFIG_FILENAME} is not in .gitignore. Add it:\n"
            f"    echo '{CONFIG_FILENAME}' >> .gitignore"
        )

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except Exception:
        data = None
        issues.append(f"WARNING: could not parse {CONFIG_FILENAME} (invalid JSON?).")

    if data is not None:
        roles = inline_secret_roles(data)
        if roles:
            issues.append(
                f"WARNING: {CONFIG_FILENAME} stores credential values inline for "
                f"role(s) {', '.join(roles)}. Replace them with env-var references "
                f"(\"passwordEnv\": \"QA_<ROLE>_PASSWORD\", \"totpEnv\": ...) set "
                f"before launching Claude Code; see /qa-browser:target."
            )
        target_url = data.get("targetUrl", "")
        hit = _production_hit(target_url, data) if isinstance(target_url, str) else None
        if hit:
            issues.append(
                f"WARNING: targetUrl ({target_url}) matches {hit}. "
                f"The production gate will block navigation to it unless Claude Code "
                f"was launched with QA_BROWSER_ALLOW_PRODUCTION=1."
            )

        bad_envs = _disallowed_envs(data)
        if bad_envs:
            issues.append(
                f"WARNING: {CONFIG_FILENAME} names credential variable(s) "
                f"{', '.join(bad_envs)} that are outside the allow-list. Credential "
                f"variables must start with QA_ or be listed in the qa-browser "
                f"credential_env_allowlist option; the gate refuses to read them and "
                f"totp.py refuses them. If you did not write this config, check it: it "
                f"may be trying to read an unrelated secret."
            )

    if in_git and (root / EVIDENCE_DIR).is_dir() and not _is_ignored(root, EVIDENCE_DIR + "/"):
        issues.append(
            f"WARNING: {EVIDENCE_DIR}/ is not git-ignored. Screenshots and network "
            f"captures can contain personal data. Add it:\n"
            f"    echo '{EVIDENCE_DIR}/' >> .gitignore"
        )

    if issues:
        text = "[qa-browser] safety check found issues:\n" + "\n".join(
            "  - " + issue for issue in issues)
        # systemMessage reaches the user; additionalContext reaches Claude.
        sys.stdout.write(json.dumps({
            "systemMessage": text,
            "hookSpecificOutput": {"hookEventName": "SessionStart",
                                   "additionalContext": text},
        }))
        sys.stdout.flush()
    return 0


def _git(root: Path, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                              text=True, timeout=3)
    except Exception:
        return None


def _is_git_repo(root: Path) -> bool:
    r = _git(root, "rev-parse", "--is-inside-work-tree")
    return bool(r) and r.returncode == 0 and r.stdout.strip() == "true"


def _is_tracked(root: Path, name: str) -> bool:
    r = _git(root, "ls-files", "--error-unmatch", name)
    return bool(r) and r.returncode == 0


def _is_ignored(root: Path, name: str) -> bool:
    # --no-index: answer from the ignore rules even for a tracked path.
    r = _git(root, "check-ignore", "-q", "--no-index", name)
    return bool(r) and r.returncode == 0


def _gate():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import pre_navigate_prod_gate as gate
    finally:
        sys.path.pop(0)
    return gate


def _disallowed_envs(config: dict) -> list[str]:
    """Credential env names the gate (single owner of the rule) would refuse."""
    return _gate().disallowed_credential_envs(config)


def _production_hit(url: str, config: dict) -> str | None:
    """Ask the navigation gate (single owner of the host rules) about `url`."""
    gate = _gate()
    host = gate.hostname_of(url)
    return gate.production_match(host, gate.effective_config(config)) if host else None


if __name__ == "__main__":
    hooklib.run(main)
