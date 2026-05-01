#!/usr/bin/env python3
"""rag-plugin /project-focus state engine (v0.9.0).

Manages a single local state file at:

  ~/.claude/rag-plugin/state/project-focus.json

Subcommands (all stdlib-only, no MCP, no HTTP except the optional
`set --auto` matcher which calls `GET /api/projects` to enumerate
configured ragtools projects):

  set [<project-name-or-id>] [--auto]   activate focus
  status                                  show current focus
  clear                                   remove the state file

`set` with no args is equivalent to `set --auto`. The auto matcher
detects the current project from the working directory + git root
and matches against `list_projects` by:
  1. exact path
  2. closest parent path (longest match)
  3. project name
  4. case-insensitive comparison on Windows

Never mutates ragtools project config. Never adds projects.
Never reindexes. Atomic state writes (tmp + os.replace).

Exit codes:
  0  success
  2  no current-project candidate could be matched (set/auto)
  3  ambiguity — multiple equally-specific candidates
  4  state file write error
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

STATE_DIR = Path.home() / ".claude" / "rag-plugin" / "state"
STATE_FILE = STATE_DIR / "project-focus.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 21420
SCRIPT_VERSION = "0.9.0"


# --------------------------------------------------------------------------- #
# Project enumeration                                                         #
# --------------------------------------------------------------------------- #


def _http_json(url: str, timeout: float = 1.5) -> Any:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rag-plugin-focus/0.9.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except Exception:
        return None


def fetch_configured_projects(host: str = DEFAULT_HOST,
                              port: int = DEFAULT_PORT,
                              timeout: float = 1.5,
                              hydrate_paths: bool = True) -> list[dict[str, Any]]:
    """GET /api/projects from the local ragtools service. Empty list on any error.

    The list endpoint returns lean records: {project_id, files, chunks}. To get
    paths for path-based matching, call /api/projects/<id>/status per project
    (only if hydrate_paths=True).
    """
    data = _http_json(f"http://{host}:{port}/api/projects", timeout=timeout)
    raw: list[dict[str, Any]] = []
    if isinstance(data, list):
        raw = [p for p in data if isinstance(p, dict)]
    elif isinstance(data, dict) and "projects" in data and isinstance(data["projects"], list):
        raw = [p for p in data["projects"] if isinstance(p, dict)]
    if not raw or not hydrate_paths:
        return raw
    out: list[dict[str, Any]] = []
    for proj in raw:
        pid = str(proj.get("project_id") or proj.get("id") or proj.get("name") or "").strip()
        if not pid:
            out.append(proj)
            continue
        detail = _http_json(
            f"http://{host}:{port}/api/projects/{urllib.parse.quote(pid)}/status",
            timeout=timeout,
        )
        merged = dict(proj)
        if isinstance(detail, dict):
            merged.update({k: v for k, v in detail.items() if v is not None})
        out.append(merged)
    return out


# --------------------------------------------------------------------------- #
# Current-directory + git-root detection                                      #
# --------------------------------------------------------------------------- #


def detect_git_root(start: Path) -> Optional[Path]:
    p = start.resolve()
    for ancestor in [p] + list(p.parents):
        if (ancestor / ".git").exists():
            return ancestor
    # Fallback: try `git rev-parse --show-toplevel` if available
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2,
            cwd=str(p),
        )
        if r.returncode == 0:
            top = r.stdout.strip()
            if top:
                return Path(top)
    except Exception:
        return None
    return None


def _norm(p: str) -> str:
    """Normalize path for comparison (resolve, posix slashes, lowercase on Windows)."""
    try:
        out = str(Path(p).expanduser().resolve())
    except Exception:
        out = str(p)
    out = out.replace("\\", "/")
    if os.name == "nt":
        out = out.lower()
    return out


@dataclass
class MatchResult:
    project: dict[str, Any]
    method: str  # "exact-path" | "ancestor-path" | "name" | "manual"
    score: int    # higher = better; used for tie-breaking


def _candidate_paths(project: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("path", "root", "root_path", "directory", "source_path"):
        v = project.get(key)
        if isinstance(v, str) and v.strip():
            paths.append(v)
    # Some ragtools shapes store `paths` as a list
    plist = project.get("paths")
    if isinstance(plist, list):
        for v in plist:
            if isinstance(v, str) and v.strip():
                paths.append(v)
    return paths


def _project_name(project: dict[str, Any]) -> str:
    for key in ("project_id", "id", "name", "slug"):
        v = project.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def match_project(cwd: Path, projects: list[dict[str, Any]],
                  manual_name: Optional[str] = None) -> tuple[Optional[MatchResult], list[MatchResult]]:
    """Return (best_match, all_candidates). Caller decides on ambiguity."""
    candidates: list[MatchResult] = []
    if manual_name:
        wanted = manual_name.strip().lower()
        for proj in projects:
            n = _project_name(proj).lower()
            pid = str(proj.get("id", "")).lower()
            if n == wanted or pid == wanted:
                candidates.append(MatchResult(proj, "name", 100))
        if candidates:
            return candidates[0], candidates
        # Allow substring match as last resort
        for proj in projects:
            n = _project_name(proj).lower()
            if wanted and wanted in n:
                candidates.append(MatchResult(proj, "name-partial", 50))
        return (candidates[0] if candidates else None), candidates

    cwd_n = _norm(str(cwd))
    git_root = detect_git_root(cwd)
    git_n = _norm(str(git_root)) if git_root else ""

    for proj in projects:
        for raw_path in _candidate_paths(proj):
            pn = _norm(raw_path)
            if not pn:
                continue
            # Exact match
            if pn == cwd_n or (git_n and pn == git_n):
                candidates.append(MatchResult(proj, "exact-path", 1000 + len(pn)))
                continue
            # Ancestor match — project path is ancestor of CWD or git_root
            if cwd_n.startswith(pn + "/") or cwd_n == pn:
                candidates.append(MatchResult(proj, "ancestor-path", 500 + len(pn)))
                continue
            if git_n and (git_n.startswith(pn + "/") or git_n == pn):
                candidates.append(MatchResult(proj, "ancestor-path", 500 + len(pn)))
                continue
            # CWD/git_root is ancestor of project path (less common but valid)
            if pn.startswith(cwd_n + "/") or (git_n and pn.startswith(git_n + "/")):
                candidates.append(MatchResult(proj, "descendant-path", 200 + len(pn)))
                continue

    if not candidates:
        return None, []

    # Sort by score desc, dedupe by project name
    candidates.sort(key=lambda r: -r.score)
    seen: set[str] = set()
    unique: list[MatchResult] = []
    for c in candidates:
        n = _project_name(c.project)
        if n in seen:
            continue
        seen.add(n)
        unique.append(c)

    best = unique[0]
    # Ambiguity check: if top two are within 10 score points of each other AND same method, ambiguous
    if len(unique) >= 2 and unique[0].score - unique[1].score < 10 and unique[0].method == unique[1].method:
        # Tie-break by longest path
        unique.sort(key=lambda r: -max((len(p) for p in _candidate_paths(r.project)), default=0))
        if abs(len(_candidate_paths(unique[0].project)[0] if _candidate_paths(unique[0].project) else "")
               - len(_candidate_paths(unique[1].project)[0] if _candidate_paths(unique[1].project) else "")) < 3:
            return None, unique  # ambiguous
        best = unique[0]

    return best, unique


# --------------------------------------------------------------------------- #
# State file CRUD                                                             #
# --------------------------------------------------------------------------- #


def write_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def read_state() -> Optional[dict[str, Any]]:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None


def clear_state() -> bool:
    if not STATE_FILE.exists():
        return False
    try:
        STATE_FILE.unlink()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Commands                                                                    #
# --------------------------------------------------------------------------- #


def cmd_set(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    projects = fetch_configured_projects(host=args.host, port=args.port)

    service_up = bool(projects)
    if not service_up:
        # Try a hard probe so we can distinguish "down" from "no projects"
        try:
            urllib.request.urlopen(
                f"http://{args.host}:{args.port}/health", timeout=1.0
            ).read()
            service_up = True
        except Exception:
            service_up = False

    manual = args.project if (args.project and not args.auto) else None
    if not projects:
        # Service down or no projects configured — still allow a manual name with a warning
        if manual:
            state = {
                "enabled": True,
                "mode": "strict",
                "project_name": manual,
                "project_path": "",
                "project_id": "",
                "match_method": "manual-no-config",
                "warning": "ragtools service unreachable or no projects configured; "
                           "focus is set by name only and cannot be cross-checked against list_projects",
                "service_reachable": service_up,
                "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": "/project-focus",
            }
            try:
                write_state(state)
            except Exception as e:
                print(f"error writing state: {e}", file=sys.stderr)
                return 4
            print(json.dumps({"ok": True, "set": state, "candidates": []}, indent=2))
            return 0
        print(json.dumps({
            "ok": False,
            "reason": "no-projects-available",
            "service_reachable": service_up,
            "hint": "start ragtools or configure a project, then re-run /project-focus. "
                    "Or pass a project name explicitly: /project-focus <name>.",
        }, indent=2))
        return 2

    best, candidates = match_project(cwd, projects, manual_name=manual)
    if best is None and not candidates:
        print(json.dumps({
            "ok": False,
            "reason": "no-match",
            "cwd": str(cwd),
            "candidates": [_project_name(p) for p in projects],
            "hint": "no configured ragtools project matches this directory. "
                    "Pass an explicit name: /project-focus <name>, or run /rag:rag-projects add.",
        }, indent=2))
        return 2

    if best is None:
        print(json.dumps({
            "ok": False,
            "reason": "ambiguous",
            "cwd": str(cwd),
            "candidates": [
                {"name": _project_name(c.project), "method": c.method, "score": c.score}
                for c in candidates[:5]
            ],
            "hint": "more than one project matches equally well. "
                    "Disambiguate with /project-focus <name>.",
        }, indent=2))
        return 3

    proj = best.project
    paths = _candidate_paths(proj)
    state = {
        "enabled": True,
        "mode": "strict",
        "project_id": str(proj.get("id", "")),
        "project_name": _project_name(proj),
        "project_path": paths[0] if paths else "",
        "project_paths": paths,
        "match_method": best.method,
        "cwd_at_set": str(cwd),
        "git_root_at_set": str(detect_git_root(cwd) or ""),
        "service_reachable": True,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "/project-focus" + (" (manual)" if manual else " (auto)"),
        "engine_version": SCRIPT_VERSION,
    }
    try:
        write_state(state)
    except Exception as e:
        print(f"error writing state: {e}", file=sys.stderr)
        return 4

    other_candidates = [
        {"name": _project_name(c.project), "method": c.method, "score": c.score}
        for c in candidates[1:5]
    ]
    print(json.dumps({"ok": True, "set": state, "alternatives": other_candidates}, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = read_state()
    if not state:
        print(json.dumps({"ok": True, "enabled": False,
                          "hint": "no /project-focus active. Run /project-focus to activate."}, indent=2))
        return 0
    # Re-probe project presence to flag staleness
    projects = fetch_configured_projects(host=args.host, port=args.port)
    name = state.get("project_name", "")
    still_present = any(_project_name(p) == name for p in projects) if projects else None
    out = dict(state)
    out["still_in_list_projects"] = still_present
    out["state_file"] = str(STATE_FILE)
    print(json.dumps({"ok": True, "focus": out}, indent=2))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    existed = clear_state()
    print(json.dumps({"ok": True, "cleared": existed,
                      "state_file": str(STATE_FILE)}, indent=2))
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    """Lightweight stdlib unit-style sanity tests."""
    print("[project_focus] self-test")
    failed = 0

    # match_project: exact + ancestor path
    cwd = Path.cwd()
    fake_projects = [
        {"name": "alpha", "path": str(cwd)},
        {"name": "beta", "path": str(cwd.parent)},
        {"name": "gamma", "path": "/totally/unrelated"},
    ]
    best, all_c = match_project(cwd, fake_projects)
    if best is None or _project_name(best.project) != "alpha":
        print(f"  [FAIL] exact-path match expected 'alpha', got "
              f"{_project_name(best.project) if best else None}")
        failed += 1
    else:
        print("  [OK] exact-path match")

    # ancestor wins over descendant: cwd is `.../foo/bar`, project=`.../foo` should match
    deep = cwd / "subdir"
    fake_projects2 = [{"name": "outer", "path": str(cwd)}]
    best2, _ = match_project(deep, fake_projects2)
    if best2 is None or _project_name(best2.project) != "outer":
        print("  [FAIL] ancestor-path match")
        failed += 1
    else:
        print("  [OK] ancestor-path match")

    # manual name match
    best3, _ = match_project(cwd, fake_projects, manual_name="beta")
    if best3 is None or _project_name(best3.project) != "beta":
        print("  [FAIL] manual name match")
        failed += 1
    else:
        print("  [OK] manual name match")

    # no-match
    best4, _ = match_project(Path("/no/such/path/here/at/all"),
                              [{"name": "x", "path": "/different/place"}])
    if best4 is not None:
        print("  [FAIL] no-match should return None")
        failed += 1
    else:
        print("  [OK] no-match returns None")

    # state file round-trip (use temp dir so we don't clobber real state)
    import tempfile
    global STATE_DIR, STATE_FILE
    saved_dir, saved_file = STATE_DIR, STATE_FILE
    try:
        with tempfile.TemporaryDirectory() as td:
            STATE_DIR = Path(td) / "state"
            STATE_FILE = STATE_DIR / "project-focus.json"
            sample = {"enabled": True, "project_name": "test"}
            write_state(sample)
            r = read_state()
            assert r == sample, f"round-trip mismatch: {r}"
            assert clear_state() is True
            assert read_state() is None
            print("  [OK] state file round-trip + clear")
    except AssertionError as e:
        print(f"  [FAIL] state file: {e}")
        failed += 1
    finally:
        STATE_DIR, STATE_FILE = saved_dir, saved_file

    if failed:
        print(f"[project_focus] FAIL — {failed} check(s) failed")
        return 1
    print("[project_focus] self-test OK")
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="project_focus.py",
                                 description="rag-plugin /project-focus state engine")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set", help="activate focus")
    s.add_argument("project", nargs="?", default=None,
                   help="optional manual project name; default = auto-detect")
    s.add_argument("--auto", action="store_true",
                   help="force auto-detection even if a project name is given")
    s.set_defaults(func=cmd_set)

    sub.add_parser("status", help="show current focus").set_defaults(func=cmd_status)
    sub.add_parser("clear", help="remove the state file").set_defaults(func=cmd_clear)
    sub.add_parser("self-test", help="run internal sanity checks").set_defaults(func=cmd_self_test)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
