#!/usr/bin/env python3
"""Inspect the sprint-recap local config without ever printing a secret.

Used by /sprint-recap:target check. Verifies the things that matter:
  1. the config parses
  2. git is not tracking it
  3. .gitignore covers it, the credentials directory, run data (evidence,
     screenshots, clips) and any .auth/ session state left by versions < 0.4
  4. no target points at something that looks like production, and each
     non-local target has opted in to capture with "allow_capture": true
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _common import (
    CONFIG_FILENAME, RECAP_DIRNAME, config_path, is_local_host, is_production, mask,
    project_root,
)


def git_flag(args: list[str], root: Path) -> bool:
    try:
        out = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=10)
        return out.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check sprint-recap configuration.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args()

    root = project_root()
    path = config_path(root)
    report = {"config": str(path), "exists": path.exists(), "problems": [],
              "warnings": [], "targets": {}}

    if not path.exists():
        report["problems"].append(
            CONFIG_FILENAME + " does not exist. Run /sprint-recap:target set."
        )
        return emit(report, args.json)

    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["problems"].append("Config is not valid JSON: " + str(exc))
        return emit(report, args.json)

    # Outside a git work tree there is nothing to leak into, and check-ignore
    # always fails -- reporting "not gitignored" there is a false alarm.
    in_git = git_flag(["git", "rev-parse", "--is-inside-work-tree"], root)
    report["git_repo"] = in_git
    creds_rel = RECAP_DIRNAME + "/credentials/"
    # Representative paths; check-ignore matches patterns, so they need not exist.
    # Versions before 0.4 cached session cookies at <run>/<capture>/.auth/<role>.json.
    auth_probe = RECAP_DIRNAME + "/runs/example/capture/.auth/role.json"
    runs_probe = RECAP_DIRNAME + "/runs/example/01-collect/evidence.json"

    if not in_git:
        report["warnings"].append(
            "Not inside a git work tree, so ignore rules were not checked. "
            "If this project becomes a repo, gitignore " + CONFIG_FILENAME
            + ", " + creds_rel + " and " + RECAP_DIRNAME + "/**/.auth/ before "
            "the first commit."
        )
    else:
        if git_flag(["git", "ls-files", "--error-unmatch", CONFIG_FILENAME], root):
            report["problems"].append(
                CONFIG_FILENAME + " is TRACKED by git. Run: git rm --cached "
                + CONFIG_FILENAME + "  (and rotate anything it contains)"
            )
        if not git_flag(["git", "check-ignore", "-q", CONFIG_FILENAME], root):
            report["problems"].append(CONFIG_FILENAME + " is not gitignored.")
        if not git_flag(["git", "check-ignore", "-q", creds_rel], root):
            report["warnings"].append(
                creds_rel + " is not gitignored; publish --with-credentials would "
                "write a plaintext page into a tracked path."
            )
        if not git_flag(["git", "check-ignore", "-q", auth_probe], root):
            report["warnings"].append(
                RECAP_DIRNAME + "/**/.auth/ is not gitignored; versions before 0.4 "
                "cached each role's session cookies there. Add `" + RECAP_DIRNAME
                + "/` (or at least `" + RECAP_DIRNAME + "/**/.auth/`) to .gitignore."
            )
        if not git_flag(["git", "check-ignore", "-q", runs_probe], root):
            report["warnings"].append(
                RECAP_DIRNAME + "/runs/ is not gitignored; it holds evidence, "
                "screenshots and clips of the app. Ignore the whole `" + RECAP_DIRNAME
                + "/` folder and commit only the guide you mean to share."
            )

    for name, target in (config.get("targets") or {}).items():
        base = target.get("base_url", "")
        roles = target.get("roles") or {}
        report["targets"][name] = {
            "base_url": base,
            "roles": {
                role: {
                    "username": creds.get("username", ""),
                    "password": mask(creds.get("password", "")) or (
                        "(storage_state)" if creds.get("storage_state") else ""),
                }
                for role, creds in roles.items()
            },
        }
        if not base:
            report["problems"].append("Target '" + name + "' has no base_url.")
        if is_production(base, config):
            report["warnings"].append(
                "Target '" + name + "' (" + base + ") looks like production; "
                "capture will refuse it unless --allow-production is passed."
            )
        elif base and not is_local_host(base) and target.get("allow_capture") is not True:
            report["warnings"].append(
                "Target '" + name + "' (" + base + ") is not local and does not set "
                "\"allow_capture\": true; capture will refuse it until you confirm "
                "it is a disposable test environment."
            )
        if not roles:
            report["warnings"].append("Target '" + name + "' defines no roles.")
        for role, creds in roles.items():
            if creds.get("storage_state") and not creds.get("password"):
                continue
            missing = [k for k in ("username", "password") if not creds.get(k)]
            if missing:
                report["problems"].append(
                    "Target '" + name + "' role '" + role + "' is missing: "
                    + ", ".join(missing)
                )

    return emit(report, args.json)


def emit(report: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("config : " + report["config"])
        for name, target in report["targets"].items():
            print("  target " + name + " -> " + target["base_url"])
            for role, creds in target["roles"].items():
                print("    " + role + ": " + creds["username"]
                      + " / " + creds["password"] + "  (masked)")
        for warning in report["warnings"]:
            print("WARN  : " + warning, file=sys.stderr)
        for problem in report["problems"]:
            print("ERROR : " + problem, file=sys.stderr)
        if not report["problems"]:
            print("OK    : configuration is usable.")
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
