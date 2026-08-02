#!/usr/bin/env python3
"""rag-plugin /project-focus state engine (v0.10.0).

Schema v2 — per-workspace focus map + optional explicit global focus.
See `docs/decisions.md#d-028` for the design rationale and migration policy.

State file: ``~/.claude/rag-plugin/state/project-focus.json``.

v2 shape::

    {
      "schema_version": 2,
      "engine_version": "0.10.0",
      "workspaces": { "<normalized-workspace-key>": <focus-record>, ... },
      "global":     null | <focus-record>,
      "migrated_from_v1_at": null | "<iso8601>",
      "migration_log": [ "..." ]
    }

A focus record has the same field set v0.9.0 wrote, plus:

  - ``scope``:           ``"workspace"`` | ``"global"``
  - ``workspace_key``:   normalized path (workspace records); empty for global

Subcommands (all stdlib-only, no MCP):

  set  [<project-name>] [--auto] [--global]   activate workspace OR global focus
  status                                        show effective focus + drift
  clear                                         clear ONLY the current workspace
  clear --global                                clear ONLY the global record
  clear --all                                   clear both

Migration:
  - v1 state files are auto-migrated to v2 on first read.
  - The chosen workspace key is ``_norm(git_root_at_set or cwd_at_set)``.
  - If neither path is usable (empty or non-existent), focus is disabled and
    the user is asked to rerun ``/rag:project-focus``. v1 records are NEVER
    auto-migrated into ``global`` (per the v0.10.0 design decision).
  - Before the first migration, the original v1 file is copied once to
    ``project-focus.v1.bak.json`` so the user can roll back manually.

Never mutates ragtools project config. Never adds projects. Never reindexes.
Atomic state writes (tmp + ``os.replace``).

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
V1_BACKUP_NAME = "project-focus.v1.bak.json"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 21420
SCRIPT_VERSION = "0.10.0"
SCHEMA_VERSION = 2


# --------------------------------------------------------------------------- #
# Project enumeration                                                         #
# --------------------------------------------------------------------------- #


def _http_json(url: str, timeout: float = 1.5) -> Any:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"rag-plugin-focus/{SCRIPT_VERSION}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except Exception:
        return None


def fetch_configured_projects(host: str = DEFAULT_HOST,
                              port: int = DEFAULT_PORT,
                              timeout: float = 1.5,
                              hydrate_paths: bool = True) -> list[dict[str, Any]]:
    """GET /api/projects from the local ragtools service. Empty list on any error."""
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
# Path normalization + workspace key resolution                               #
# --------------------------------------------------------------------------- #


def detect_git_root(start: Path) -> Optional[Path]:
    p = start.resolve()
    for ancestor in [p] + list(p.parents):
        if (ancestor / ".git").exists():
            return ancestor
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
    """Normalize a path for comparison (resolve, posix slashes, lowercase on Windows)."""
    if not p:
        return ""
    try:
        out = str(Path(p).expanduser().resolve())
    except Exception:
        out = str(p)
    out = out.replace("\\", "/")
    while out.endswith("/") and len(out) > 1:
        out = out[:-1]
    if os.name == "nt":
        out = out.lower()
    return out


def resolve_workspace_key(cwd: Path) -> str:
    """Compute the workspace key for the given cwd: normalized git root or cwd."""
    root = detect_git_root(cwd) or cwd
    return _norm(str(root))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- #
# v1 record validity helpers                                                  #
# --------------------------------------------------------------------------- #


def _v1_pick_migration_path(record: dict[str, Any]) -> tuple[Optional[str], str]:
    """Return (chosen_normalized_key, source_label) or (None, reason).

    Prefer git_root_at_set, fall back to cwd_at_set. Both must:
      - be non-empty after stripping
      - resolve to an existing directory on disk
    """
    for field in ("git_root_at_set", "cwd_at_set"):
        raw = str(record.get(field) or "").strip()
        if not raw:
            continue
        try:
            p = Path(raw).expanduser().resolve()
        except Exception:
            continue
        if not p.exists() or not p.is_dir():
            continue
        return _norm(str(p)), field
    return None, "no usable git_root_at_set or cwd_at_set"


# --------------------------------------------------------------------------- #
# State file CRUD + migration                                                 #
# --------------------------------------------------------------------------- #


def _empty_v2_bundle() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "engine_version": SCRIPT_VERSION,
        "workspaces": {},
        "global": None,
        "migrated_from_v1_at": None,
        "migration_log": [],
    }


def _migrate_v1_to_v2(old_record: dict[str, Any]) -> dict[str, Any]:
    bundle = _empty_v2_bundle()
    chosen_key, source = _v1_pick_migration_path(old_record)
    if chosen_key is None:
        bundle["migrated_from_v1_at"] = _now_iso()
        bundle["migration_log"].append(
            f"v1->v2: focus disabled during migration ({source}); rerun /rag:project-focus to re-establish."
        )
        return bundle
    record = dict(old_record)
    record["scope"] = "workspace"
    record["workspace_key"] = chosen_key
    record.setdefault("enabled", True)
    record["engine_version"] = SCRIPT_VERSION
    bundle["workspaces"][chosen_key] = record
    bundle["migrated_from_v1_at"] = _now_iso()
    bundle["migration_log"].append(
        f"v1->v2: migrated single-record focus into workspaces[{chosen_key}] using {source}"
    )
    return bundle


def write_state(state: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def _backup_v1_once(raw_text: str) -> None:
    bak = STATE_DIR / V1_BACKUP_NAME
    if bak.exists():
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    bak.write_text(raw_text, encoding="utf-8")


def read_state() -> Optional[dict[str, Any]]:
    """Read the state file, auto-migrating v1 to v2 on first encounter.

    Returns None if the state file does not exist OR is malformed beyond
    rescue. v2 files are returned as-is. v1 files are migrated, the
    migrated bundle is persisted, and a one-time backup is written to
    ``project-focus.v1.bak.json``.
    """
    if not STATE_FILE.exists():
        return None
    try:
        raw_text = STATE_FILE.read_text(encoding="utf-8", errors="replace")
        bundle = json.loads(raw_text)
    except Exception:
        return None
    if not isinstance(bundle, dict):
        return None

    # v2+: passthrough.
    if int(bundle.get("schema_version") or 0) >= SCHEMA_VERSION:
        return bundle

    # v1 single-record shape (top-level "enabled" or "project_name").
    if "enabled" in bundle or "project_name" in bundle:
        _backup_v1_once(raw_text)
        migrated = _migrate_v1_to_v2(bundle)
        try:
            write_state(migrated)
        except Exception:
            # Even if the persistence write fails, return the in-memory
            # migrated bundle so callers see the v2 shape this run.
            pass
        return migrated

    # Unrecognized shape — treat as missing.
    return None


def clear_workspace(workspace_key: str) -> bool:
    bundle = read_state() or _empty_v2_bundle()
    if workspace_key in bundle.get("workspaces", {}):
        del bundle["workspaces"][workspace_key]
        write_state(bundle)
        return True
    # Persist the (possibly newly initialized) v2 bundle so future reads are clean.
    write_state(bundle)
    return False


def clear_global() -> bool:
    bundle = read_state() or _empty_v2_bundle()
    had = bundle.get("global") is not None
    bundle["global"] = None
    write_state(bundle)
    return had


def clear_all() -> bool:
    bundle = read_state() or _empty_v2_bundle()
    had = bool(bundle.get("workspaces")) or bundle.get("global") is not None
    bundle["workspaces"] = {}
    bundle["global"] = None
    write_state(bundle)
    return had


def clear_state_file() -> bool:
    """Remove the state file entirely. Used by ``clear --file`` and tests."""
    if not STATE_FILE.exists():
        return False
    try:
        STATE_FILE.unlink()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Effective focus resolver (workspace > global > none)                        #
# --------------------------------------------------------------------------- #


def _is_enabled(record: Optional[dict[str, Any]]) -> bool:
    return bool(record and record.get("enabled"))


def resolve_effective_focus(bundle: dict[str, Any], workspace_key: str
                            ) -> tuple[Optional[dict[str, Any]], str]:
    """Return (effective_record, source_tag).

    source_tag is one of:
      - "workspace"            — current workspace has an enabled record
      - "global"               — no workspace record; explicit global is in use
      - "other-workspace-only" — at least one OTHER workspace has an enabled
                                  record but neither this workspace nor global
                                  applies (signals the hook to inject a neutral
                                  notice without leaking the other project name)
      - "none"                 — nothing applies
    """
    workspaces = bundle.get("workspaces") or {}
    ws_record = workspaces.get(workspace_key)
    if _is_enabled(ws_record):
        return ws_record, "workspace"

    glob = bundle.get("global")
    if _is_enabled(glob):
        return glob, "global"

    # No effective focus, but check whether ANY enabled record exists for a
    # different workspace. If so, the hook should surface a neutral notice.
    for k, rec in workspaces.items():
        if k == workspace_key:
            continue
        if _is_enabled(rec):
            return None, "other-workspace-only"

    return None, "none"


# --------------------------------------------------------------------------- #
# Match scoring                                                               #
# --------------------------------------------------------------------------- #


@dataclass
class MatchResult:
    project: dict[str, Any]
    method: str
    score: int


def _candidate_paths(project: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("path", "root", "root_path", "directory", "source_path"):
        v = project.get(key)
        if isinstance(v, str) and v.strip():
            paths.append(v)
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
            if pn == cwd_n or (git_n and pn == git_n):
                candidates.append(MatchResult(proj, "exact-path", 1000 + len(pn)))
                continue
            if cwd_n.startswith(pn + "/") or cwd_n == pn:
                candidates.append(MatchResult(proj, "ancestor-path", 500 + len(pn)))
                continue
            if git_n and (git_n.startswith(pn + "/") or git_n == pn):
                candidates.append(MatchResult(proj, "ancestor-path", 500 + len(pn)))
                continue
            if pn.startswith(cwd_n + "/") or (git_n and pn.startswith(git_n + "/")):
                candidates.append(MatchResult(proj, "descendant-path", 200 + len(pn)))
                continue

    if not candidates:
        return None, []

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
    if len(unique) >= 2 and unique[0].score - unique[1].score < 10 and unique[0].method == unique[1].method:
        unique.sort(key=lambda r: -max((len(p) for p in _candidate_paths(r.project)), default=0))
        if abs(len(_candidate_paths(unique[0].project)[0] if _candidate_paths(unique[0].project) else "")
               - len(_candidate_paths(unique[1].project)[0] if _candidate_paths(unique[1].project) else "")) < 3:
            return None, unique
        best = unique[0]

    return best, unique


# --------------------------------------------------------------------------- #
# Commands                                                                    #
# --------------------------------------------------------------------------- #


def _build_record(proj: dict[str, Any], best: MatchResult,
                  cwd: Path, scope: str, workspace_key: str,
                  manual: bool) -> dict[str, Any]:
    paths = _candidate_paths(proj)
    return {
        "enabled": True,
        "mode": "strict",
        "scope": scope,
        "workspace_key": workspace_key,
        "project_id": str(proj.get("id", "")),
        "project_name": _project_name(proj),
        "project_path": paths[0] if paths else "",
        "project_paths": paths,
        "match_method": best.method,
        "cwd_at_set": str(cwd),
        "git_root_at_set": str(detect_git_root(cwd) or ""),
        "service_reachable": True,
        "created_at": _now_iso(),
        "source": ("/project-focus (manual)" if manual else "/project-focus (auto)") +
                  (" --global" if scope == "global" else ""),
        "engine_version": SCRIPT_VERSION,
    }


def cmd_set(args: argparse.Namespace) -> int:
    cwd = Path.cwd()
    is_global = bool(getattr(args, "global_", False))

    if is_global and not args.project:
        print(json.dumps({
            "ok": False,
            "reason": "global-requires-name",
            "hint": "explicit global focus must name a project: /project-focus --global <name>",
        }, indent=2))
        return 2

    projects = fetch_configured_projects(host=args.host, port=args.port)
    service_up = bool(projects)
    if not service_up:
        try:
            urllib.request.urlopen(
                f"http://{args.host}:{args.port}/health", timeout=1.0
            ).read()
            service_up = True
        except Exception:
            service_up = False

    workspace_key = resolve_workspace_key(cwd)
    manual = args.project if (args.project and not args.auto) else None
    bundle = read_state() or _empty_v2_bundle()

    if not projects:
        if manual:
            scope = "global" if is_global else "workspace"
            record = {
                "enabled": True,
                "mode": "strict",
                "scope": scope,
                "workspace_key": "" if is_global else workspace_key,
                "project_name": manual,
                "project_id": "",
                "project_path": "",
                "project_paths": [],
                "match_method": "manual-no-config",
                "warning": "ragtools service unreachable or no projects configured; "
                           "focus is set by name only and cannot be cross-checked against list_projects",
                "service_reachable": service_up,
                "cwd_at_set": str(cwd),
                "git_root_at_set": str(detect_git_root(cwd) or ""),
                "created_at": _now_iso(),
                "source": "/project-focus" + (" --global" if is_global else ""),
                "engine_version": SCRIPT_VERSION,
            }
            if is_global:
                bundle["global"] = record
            else:
                bundle["workspaces"][workspace_key] = record
            try:
                write_state(bundle)
            except Exception as e:
                print(f"error writing state: {e}", file=sys.stderr)
                return 4
            print(json.dumps({"ok": True, "set": record, "candidates": []}, indent=2))
            return 0
        print(json.dumps({
            "ok": False,
            "reason": "no-projects-available",
            "service_reachable": service_up,
            "hint": "start ragtools or configure a project, then re-run /project-focus. "
                    "Or pass a project name explicitly: /project-focus <name>.",
        }, indent=2))
        return 2

    best, candidates = match_project(cwd, projects,
                                     manual_name=manual if not is_global else (args.project or None))
    # In --global mode the workspace path doesn't matter; only manual_name is used.
    if is_global and best is None and candidates:
        best = candidates[0]

    if best is None and not candidates:
        print(json.dumps({
            "ok": False,
            "reason": "no-match",
            "cwd": str(cwd),
            "candidates": [_project_name(p) for p in projects],
            "hint": ("named project not found in list_projects. "
                     "Try /project-focus --global <name> only after running /rag:projects add.")
                    if is_global else
                    "no configured ragtools project matches this directory. "
                    "Pass an explicit name: /project-focus <name>, or run /rag:projects add.",
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
    scope = "global" if is_global else "workspace"
    key = "" if is_global else workspace_key
    record = _build_record(proj, best, cwd, scope=scope,
                           workspace_key=key, manual=bool(manual))
    if is_global:
        bundle["global"] = record
    else:
        bundle["workspaces"][workspace_key] = record
    try:
        write_state(bundle)
    except Exception as e:
        print(f"error writing state: {e}", file=sys.stderr)
        return 4

    other_candidates = [
        {"name": _project_name(c.project), "method": c.method, "score": c.score}
        for c in candidates[1:5]
    ]
    print(json.dumps({"ok": True, "set": record, "alternatives": other_candidates}, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    bundle = read_state()
    if not bundle:
        print(json.dumps({
            "ok": True, "enabled": False,
            "workspace_key": resolve_workspace_key(Path.cwd()),
            "hint": "no /project-focus active. Run /project-focus to activate."}, indent=2))
        return 0

    cwd = Path.cwd()
    workspace_key = resolve_workspace_key(cwd)
    effective, source = resolve_effective_focus(bundle, workspace_key)
    workspaces = bundle.get("workspaces") or {}
    glob = bundle.get("global")

    # Re-probe project presence to flag staleness.
    projects = fetch_configured_projects(host=args.host, port=args.port)
    project_names = {_project_name(p) for p in projects} if projects else set()

    def _staleness(rec: Optional[dict[str, Any]]) -> Optional[bool]:
        if rec is None or not project_names:
            return None
        return rec.get("project_name") in project_names

    out = {
        "ok": True,
        "schema_version": int(bundle.get("schema_version") or SCHEMA_VERSION),
        "engine_version": bundle.get("engine_version", SCRIPT_VERSION),
        "workspace_key": workspace_key,
        "workspace_focus": workspaces.get(workspace_key),
        "global_focus": glob,
        "effective_focus": effective,
        "effective_source": source,
        "all_workspaces": sorted(workspaces.keys()),
        "still_in_list_projects": {
            "workspace": _staleness(workspaces.get(workspace_key)),
            "global": _staleness(glob),
        },
        "state_file": str(STATE_FILE),
        "migrated_from_v1_at": bundle.get("migrated_from_v1_at"),
        "migration_log": bundle.get("migration_log") or [],
    }
    print(json.dumps(out, indent=2))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    if args.all:
        had = clear_all()
        print(json.dumps({"ok": True, "cleared": "all", "had_state": had,
                          "state_file": str(STATE_FILE)}, indent=2))
        return 0
    if getattr(args, "global_", False):
        had = clear_global()
        print(json.dumps({"ok": True, "cleared": "global", "had_state": had,
                          "state_file": str(STATE_FILE)}, indent=2))
        return 0
    workspace_key = resolve_workspace_key(Path.cwd())
    had = clear_workspace(workspace_key)
    print(json.dumps({"ok": True, "cleared": "workspace", "had_state": had,
                      "workspace_key": workspace_key,
                      "state_file": str(STATE_FILE)}, indent=2))
    return 0


def cmd_self_test(args: argparse.Namespace) -> int:
    """Lightweight stdlib unit-style sanity tests."""
    print("[project_focus] self-test")
    failed = 0

    cwd = Path.cwd()
    fake_projects = [
        {"name": "alpha", "path": str(cwd)},
        {"name": "beta", "path": str(cwd.parent)},
        {"name": "gamma", "path": "/totally/unrelated"},
    ]
    best, _ = match_project(cwd, fake_projects)
    if best is None or _project_name(best.project) != "alpha":
        print(f"  [FAIL] exact-path match expected 'alpha', got "
              f"{_project_name(best.project) if best else None}")
        failed += 1
    else:
        print("  [OK] exact-path match")

    deep = cwd / "subdir"
    fake_projects2 = [{"name": "outer", "path": str(cwd)}]
    best2, _ = match_project(deep, fake_projects2)
    if best2 is None or _project_name(best2.project) != "outer":
        print("  [FAIL] ancestor-path match")
        failed += 1
    else:
        print("  [OK] ancestor-path match")

    best3, _ = match_project(cwd, fake_projects, manual_name="beta")
    if best3 is None or _project_name(best3.project) != "beta":
        print("  [FAIL] manual name match")
        failed += 1
    else:
        print("  [OK] manual name match")

    best4, _ = match_project(Path("/no/such/path/here/at/all"),
                              [{"name": "x", "path": "/different/place"}])
    if best4 is not None:
        print("  [FAIL] no-match should return None")
        failed += 1
    else:
        print("  [OK] no-match returns None")

    # State-file round-trip in a temp dir.
    import tempfile
    global STATE_DIR, STATE_FILE
    saved_dir, saved_file = STATE_DIR, STATE_FILE
    try:
        with tempfile.TemporaryDirectory() as td:
            STATE_DIR = Path(td) / "state"
            STATE_FILE = STATE_DIR / "project-focus.json"
            sample = _empty_v2_bundle()
            sample["workspaces"]["/x/y"] = {"enabled": True, "project_name": "t"}
            write_state(sample)
            r = read_state()
            assert r and r.get("workspaces", {}).get("/x/y", {}).get("project_name") == "t", \
                f"round-trip mismatch: {r}"
            assert clear_workspace("/x/y") is True
            assert read_state()["workspaces"] == {}
            print("  [OK] v2 state file round-trip + clear_workspace")
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
                                 description=f"rag-plugin /project-focus state engine v{SCRIPT_VERSION}")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set", help="activate workspace OR global focus")
    s.add_argument("project", nargs="?", default=None,
                   help="optional manual project name; default = auto-detect")
    s.add_argument("--auto", action="store_true",
                   help="force auto-detection even if a project name is given")
    s.add_argument("--global", dest="global_", action="store_true",
                   help="set explicit global focus (requires a project name)")
    s.set_defaults(func=cmd_set)

    sub.add_parser("status", help="show current focus").set_defaults(func=cmd_status)

    c = sub.add_parser("clear", help="clear focus state")
    c.add_argument("--global", dest="global_", action="store_true",
                   help="clear ONLY the explicit global focus")
    c.add_argument("--all", action="store_true",
                   help="clear ALL workspace focuses AND the global focus")
    c.set_defaults(func=cmd_clear)

    sub.add_parser("self-test", help="run internal sanity checks").set_defaults(func=cmd_self_test)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
