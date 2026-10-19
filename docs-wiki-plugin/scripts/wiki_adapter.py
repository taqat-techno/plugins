#!/usr/bin/env python3
"""docs-wiki adapter helper: flavour detection, adapter-file validation, report paths.

Stdlib only, offline (the only subprocess is a local `git remote get-url`). Commands
call it so these answers are the same on every run instead of being re-derived by the
model each time (audit WIKI-P2-06, WIKI-P1-04).

    python wiki_adapter.py detect <wiki-path>
    python wiki_adapter.py validate [--root <project-root>]
    python wiki_adapter.py locate [--root <project-root>]
    python wiki_adapter.py report-path <audit|drift|sync-audit> --wiki <wiki-path>
                                      [--root <project-root>] [--data-dir <dir>]

Every subcommand prints one JSON object. Exit codes: 0 ok, 1 validation errors,
2 usage error.

Adapter file: `<project-root>/.claude/docs-wiki.local.json`. Versions before 0.11.0 used
`<project-root>/.docs-wiki.local.json`; it is still read when the new file is absent.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

FLAVOURS = ("github-wiki", "gitlab-wiki", "azure-devops-wiki", "mkdocs-tree")
ADAPTER_FILE = Path(".claude") / "docs-wiki.local.json"
LEGACY_ADAPTER_FILE = Path(".docs-wiki.local.json")
REPORT_KINDS = ("audit", "drift", "sync-audit")

#: key -> (type or tuple of types, allowed values or None)
SCHEMA: dict[str, tuple] = {
    "wikiPath": (str, None),
    "wikiFlavour": (str, FLAVOURS),
    "owner": (str, None),
    "repo": (str, None),
    "sourceOfTruthRoots": (list, None),
    "retiredFolders": (list, None),
    "exceptions": (list, None),
    "sidebarStyle": (str, ("explicit", "auto")),
    "reportsDir": (str, None),
    # wiki-plantuml / swimlane pipeline
    "javaExe": (str, None),
    "plantumlJar": (str, None),
    "renderMode": (str, ("local", "kroki")),
    "krokiEndpoint": (str, None),
    "org": (str, None),
    "projectGuid": (str, None),
    "wikiId": (str, None),
    "attachmentApiVersion": (str, None),
    "attachmentBodyEncoding": (str, ("base64", "raw")),
    "swimlaneNaming": (str, None),
    "palette": (dict, None),
    "knownStrays": ((list, dict), None),
}


def _emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- detect

def _git_remote(path: Path) -> str:
    try:
        out = subprocess.run(["git", "-C", str(path), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10, check=False)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _remote_flavour(remote: str):
    r = remote.lower()
    if not r:
        return None
    if "dev.azure.com" in r or "visualstudio.com" in r:
        return "azure-devops-wiki"
    if "gitlab" in r and r.rstrip("/").endswith((".wiki.git", ".wiki")):
        return "gitlab-wiki"
    if "github" in r and r.rstrip("/").endswith((".wiki.git", ".wiki")):
        return "github-wiki"
    return None


def detect(path: Path, remote: str | None = None) -> dict:
    """Best-effort flavour detection with evidence. ``flavour`` is None when the
    evidence is missing or conflicting: the caller must then ask the user."""
    evidence: list[str] = []
    votes: dict[str, int] = {}

    def vote(flavour: str, weight: int, why: str) -> None:
        votes[flavour] = votes.get(flavour, 0) + weight
        evidence.append(f"{flavour} +{weight}: {why}")

    if not path.is_dir():
        return {"path": str(path), "exists": False, "flavour": None,
                "confidence": "none", "evidence": ["path is not a directory"]}

    remote = _git_remote(path) if remote is None else remote
    rf = _remote_flavour(remote)
    remote = re.sub(r"//[^/@]+@", "//", remote)  # never echo embedded credentials
    if rf:
        vote(rf, 3, "git remote " + remote)
    if path.name.lower().endswith(".wiki"):
        vote("github-wiki", 1, "directory name ends in .wiki (GitHub/GitLab sibling clone)")
    if any(path.glob(".order")) or any(path.glob("*/.order")):
        vote("azure-devops-wiki", 2, ".order files (Azure DevOps page ordering)")
    if (path / ".attachments").is_dir():
        vote("azure-devops-wiki", 1, ".attachments/ folder")
    for parent in (path, path.parent):
        if (parent / "mkdocs.yml").is_file() or (parent / "mkdocs.yaml").is_file():
            vote("mkdocs-tree", 3, f"mkdocs.yml in {parent.name or parent}")
            break
    if (path / "_Sidebar.md").is_file() or (path / "Home.md").is_file():
        vote("github-wiki", 1, "Home.md / _Sidebar.md (GitHub/GitLab wiki convention)")
    if (path / "home.md").is_file() and not (path / "Home.md").is_file():
        vote("gitlab-wiki", 1, "lower-case home.md (GitLab convention)")

    if not votes:
        return {"path": str(path), "exists": True, "flavour": None, "confidence": "none",
                "evidence": ["no flavour signal found; ask the user"], "remote": remote}
    ranked = sorted(votes.items(), key=lambda kv: -kv[1])
    top, score = ranked[0]
    tie = len(ranked) > 1 and ranked[1][1] == score
    confidence = "none" if tie else ("high" if score >= 3 else "medium" if score == 2 else "low")
    return {"path": str(path), "exists": True, "flavour": None if tie else top,
            "confidence": confidence, "scores": dict(ranked), "evidence": evidence,
            "remote": remote}


# --------------------------------------------------------------------------- config

def locate(root: Path) -> dict:
    new, old = root / ADAPTER_FILE, root / LEGACY_ADAPTER_FILE
    if new.is_file():
        return {"path": str(new), "legacy": False, "exists": True}
    if old.is_file():
        return {"path": str(old), "legacy": True, "exists": True,
                "note": f"legacy location; move it to {ADAPTER_FILE.as_posix()}"}
    return {"path": str(new), "legacy": False, "exists": False}


def validate_data(data) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(data, dict):
        return ["the adapter file must hold a JSON object"], warnings
    for key, value in data.items():
        if key not in SCHEMA:
            close = difflib.get_close_matches(key, SCHEMA.keys(), n=1)
            hint = f" (did you mean {close[0]!r}?)" if close else ""
            errors.append(f"unknown key {key!r}{hint}")
            continue
        typ, allowed = SCHEMA[key]
        if not isinstance(value, typ):
            want = typ.__name__ if isinstance(typ, type) else " or ".join(t.__name__ for t in typ)
            errors.append(f"{key}: expected {want}, got {type(value).__name__}")
            continue
        if allowed and value not in allowed:
            errors.append(f"{key}: {value!r} is not one of {', '.join(allowed)}")
        if typ is list and not all(isinstance(v, str) for v in value):
            errors.append(f"{key}: every entry must be a string")
    if data.get("renderMode") == "kroki" and not data.get("krokiEndpoint"):
        errors.append("renderMode 'kroki' needs krokiEndpoint (a self-hosted URL)")
    endpoint = str(data.get("krokiEndpoint", ""))
    if any(h in endpoint for h in ("kroki.io", "plantuml.com")):
        errors.append("krokiEndpoint is a public service; the diagram source would leave "
                      "your network. Use a self-hosted endpoint.")
    for key in ("pat", "token", "AZDO_PAT", "password"):
        if key in data:
            errors.append(f"{key!r} looks like a secret; keep it in the environment, "
                          "never in the adapter file")
    return errors, warnings


def validate(root: Path) -> tuple[dict, int]:
    where = locate(root)
    if not where["exists"]:
        return {**where, "ok": True, "errors": [], "warnings": ["no adapter file; defaults apply"]}, 0
    try:
        data = json.loads(Path(where["path"]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {**where, "ok": False, "errors": [f"cannot parse: {exc}"], "warnings": []}, 1
    errors, warnings = validate_data(data)
    if where["legacy"]:
        warnings.append(where["note"])
    return {**where, "ok": not errors, "errors": errors, "warnings": warnings}, (1 if errors else 0)


# --------------------------------------------------------------------------- reports

def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def report_path(kind: str, wiki: Path, root: Path, data_dir: str = "",
                now: float | None = None) -> dict:
    """A unique report file path that is never inside the wiki.

    Default ``<root>/.docs-wiki/reports/<kind>-<YYYYMMDD-HHMMSS>.md``. When the project
    root is the wiki itself (or inside it), fall back to the plugin data directory, then
    the system temp directory, so a report never becomes a published wiki page.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    where = locate(root)
    configured = ""
    if where["exists"]:
        try:
            configured = json.loads(Path(where["path"]).read_text(encoding="utf-8")).get("reportsDir", "")
        except (OSError, ValueError, AttributeError):
            configured = ""
    candidates = []
    if configured:
        p = Path(configured)
        candidates.append(p if p.is_absolute() else root / p)
    candidates.append(root / ".docs-wiki" / "reports")
    if data_dir and "${" not in data_dir:
        candidates.append(Path(data_dir) / "reports")
    candidates.append(Path(tempfile.gettempdir()) / "docs-wiki-reports")
    for base in candidates:
        if _inside(base, wiki):
            continue
        target = base / f"{kind}-{stamp}.md"
        n = 2
        while target.exists():
            target = base / f"{kind}-{stamp}-{n}.md"
            n += 1
        ignored_hint = None
        if base == root / ".docs-wiki" / "reports":
            gi = root / ".gitignore"
            text = gi.read_text(encoding="utf-8", errors="replace") if gi.is_file() else ""
            if ".docs-wiki" not in text:
                ignored_hint = "add `.docs-wiki/` to .gitignore so reports are not committed"
        return {"path": str(target), "dir": str(base), "inside_wiki": False,
                "gitignore_hint": ignored_hint}
    return {"path": None, "error": "every candidate directory is inside the wiki"}


# --------------------------------------------------------------------------- cli

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("detect")
    d.add_argument("wiki_path")
    v = sub.add_parser("validate")
    v.add_argument("--root", default=".")
    lo = sub.add_parser("locate")
    lo.add_argument("--root", default=".")
    r = sub.add_parser("report-path")
    r.add_argument("kind", choices=REPORT_KINDS)
    r.add_argument("--wiki", required=True)
    r.add_argument("--root", default=".")
    r.add_argument("--data-dir", default=os.environ.get("CLAUDE_PLUGIN_DATA", ""))
    args = ap.parse_args(argv)

    if args.cmd == "detect":
        _emit(detect(Path(args.wiki_path)))
        return 0
    if args.cmd == "validate":
        result, code = validate(Path(args.root))
        _emit(result)
        return code
    if args.cmd == "locate":
        _emit(locate(Path(args.root)))
        return 0
    if args.cmd == "report-path":
        result = report_path(args.kind, Path(args.wiki), Path(args.root), args.data_dir)
        _emit(result)
        return 0 if result.get("path") else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
