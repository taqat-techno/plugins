#!/usr/bin/env python3
"""Scope resolution for ragtools retrieval (rag-plugin, WP-2).

Why this module exists
----------------------
ragtools ≥3.0.0 made retrieval **fail-closed**: ``search_knowledge_base`` and
``search_project_context`` return HTTP 422 ``SCOPE_UNRESOLVED`` when no project
is named. Scope stopped being an optional filter and became a precondition, so
resolving it has to be a default path rather than an opt-in feature.

The matching engine here was extracted from ``project_focus.py``, which had
carried it since v0.9.0 to power the opt-in ``/project-focus`` command. Three
defects were fixed on the way out (see below); ``project_focus.py`` now imports
from here so there is exactly one owner (ARCHITECTURE.md single-owner layering).

The three fixes
---------------
**R1 — descendant matches are no longer ranked by path length.**
The old scorer gave every descendant ``200 + len(path)``. Measured from
``C:/MY-WorkSpace/claude_plugins``, that selected ``taqat-plugins``
(``…/TR_plugins``, 241) over ``claude-plugins`` (``…/plugins``, 238) — the wrong
project for that repository, decided by three characters of path string. Its
ambiguity guard required ``abs(len0-len1) < 3`` and the difference was exactly
3, so nothing fired.

Length ranking is meaningful for *containment* (a deeper project that contains
the cwd is more specific) and meaningless for *descent* (when the cwd is a
parent of several project roots, none of them is "more correct"). So the three
relations are now separated and only the first two are ranked:

    exact       project path == cwd (or git root)        -> rank by specificity
    ancestor    cwd is INSIDE the project                -> rank by specificity
    descendant  the project is INSIDE the cwd            -> NOT ranked; 2+ is ambiguous

Ambiguity is surfaced, never guessed. ragtools supports a union search natively
(``projects=[a, b]``), so "both" is a real answer the caller can offer.

**R2 — one HTTP call instead of 1+N.**
``fetch_configured_projects`` issued ``/api/projects`` then
``/api/projects/{id}/status`` per project — 25 requests on a 24-project install.
``/api/projects/configured`` returns ``id``, ``path``, ``mode``, ``state``,
``enabled``, ``files``, ``chunks`` for every project in **one**, and carries the
two fields (``mode``, ``state``) the old path never fetched at all.

**R3 — resolution is not focus.**
``/project-focus`` remains an explicit user override. Automatic resolution is
the default and is labelled distinctly, so a user's deliberate choice is never
confused with a heuristic guess.

Stdlib only, no third-party imports: this runs inside a ``UserPromptSubmit``
hook on every qualifying prompt.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "ProjectMatch",
    "ScopeDecision",
    "resolve",
    "match_project",
    "fetch_projects",
    "detect_git_root",
    "norm",
    "resolve_workspace_key",
    "read_cache",
    "write_cache",
    "CACHE_TTL_SECONDS",
]

SCRIPT_VERSION = "1.0.0"

STATE_DIR = Path.home() / ".claude" / "rag-plugin" / "state"
CACHE_FILE = STATE_DIR / "context-cache.json"
#: Scope changes when the directory changes, not when the prompt does. Long
#: enough that a normal session never re-fetches; short enough that adding a
#: project shows up without a restart.
CACHE_TTL_SECONDS = 900

# Relation kinds, in precedence order. A closer relation always wins over a
# looser one regardless of score — an exact match is never beaten by a deep
# ancestor.
EXACT = "exact-path"
ANCESTOR = "ancestor-path"
DESCENDANT = "descendant-path"
NAME = "name"
NAME_PARTIAL = "name-partial"

_PRECEDENCE = {EXACT: 3, ANCESTOR: 2, DESCENDANT: 1}


# --------------------------------------------------------------------------- #
# Path normalisation — the single owner of path comparison                     #
# --------------------------------------------------------------------------- #


def norm(p: str) -> str:
    """Normalise a path for comparison.

    Resolves (following symlinks), converts to POSIX separators, drops trailing
    slashes, and lowercases **only on Windows**. Case-folding unconditionally
    would merge genuinely distinct paths on Linux and macOS; not folding at all
    would miss ``C:\\Work`` vs ``c:\\work`` on Windows.
    """
    if not p:
        return ""
    try:
        out = str(Path(p).expanduser().resolve())
    except (OSError, ValueError):
        out = str(p)
    out = out.replace("\\", "/")
    while out.endswith("/") and len(out) > 1:
        out = out[:-1]
    if os.name == "nt":
        out = out.lower()
    return out


def detect_git_root(start: Path) -> Optional[Path]:
    """Nearest ancestor containing ``.git``, else ``git rev-parse``, else None."""
    try:
        p = Path(start).resolve()
    except (OSError, ValueError):
        return None
    for ancestor in [p] + list(p.parents):
        try:
            if (ancestor / ".git").exists():
                return ancestor
        except OSError:
            continue
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=2, cwd=str(p),
        )
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def resolve_workspace_key(cwd: Path) -> str:
    """Stable key for a workspace: normalised git root, else normalised cwd."""
    root = detect_git_root(cwd) or Path(cwd)
    return norm(str(root))


# --------------------------------------------------------------------------- #
# Data                                                                         #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProjectMatch:
    """One project that plausibly covers the working directory.

    ``raw`` keeps the source dict from ``/api/projects/configured`` so callers
    that need a field this dataclass does not model (``files``, ``chunks``,
    ``ignore_patterns``) can reach it without a second request. It is excluded
    from ``asdict`` output used for caching — see :func:`write_cache`.
    """

    project_id: str
    path: str
    method: str
    score: int
    mode: str = "docs"
    state: str = ""
    enabled: bool = True
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @property
    def indexes_code(self) -> bool:
        """False for ``docs`` mode: an empty code search there means nothing."""
        return self.mode in ("code", "general")

    @property
    def stale(self) -> bool:
        return self.state == "indexed_stale"


@dataclass
class ScopeDecision:
    """What scope a retrieval call should use, and how confident that is."""

    project: Optional[ProjectMatch] = None
    candidates: list[ProjectMatch] = field(default_factory=list)
    ambiguous: bool = False
    source: str = "none"          # resolved | override | cache | none
    reason: str = ""

    @property
    def project_id(self) -> Optional[str]:
        return self.project.project_id if self.project else None

    @property
    def union_ids(self) -> list[str]:
        """Ids for a union search — the honest answer to an ambiguous cwd.

        ragtools accepts ``projects=[a, b]`` natively, so offering both beats
        picking one at random and beats refusing outright.
        """
        return [c.project_id for c in self.candidates]

    def describe(self) -> str:
        if self.project and not self.ambiguous:
            bits = [f"project={self.project.project_id}", f"mode={self.project.mode}"]
            if self.project.state:
                bits.append(f"state={self.project.state}")
            return " · ".join(bits)
        if self.ambiguous:
            return (
                f"ambiguous: {', '.join(self.union_ids)} — "
                f"name one, or search the union"
            )
        return f"no project resolved ({self.reason or 'cwd matches nothing indexed'})"


# --------------------------------------------------------------------------- #
# Fetching the project list                                                    #
# --------------------------------------------------------------------------- #


def _http_json(url: str, timeout: float = 1.5) -> Any:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": f"rag-plugin-scope/{SCRIPT_VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, OSError, ValueError, TimeoutError):
        return None


def fetch_projects(base_url: str, timeout: float = 1.5) -> list[dict[str, Any]]:
    """Every configured project, with ``path``, ``mode`` and ``state``.

    ``/api/projects/configured`` (ragtools 3.x) answers in ONE request. The
    pre-3.x fallback is ``/api/projects`` + one ``/status`` per project, which
    is what this replaced — kept only so the plugin still resolves scope against
    an older service.
    """
    base = base_url.rstrip("/")
    data = _http_json(f"{base}/api/projects/configured", timeout=timeout)
    if isinstance(data, dict) and isinstance(data.get("projects"), list):
        return [p for p in data["projects"] if isinstance(p, dict)]

    # Legacy path (pre-3.x): 1 + N requests.
    data = _http_json(f"{base}/api/projects", timeout=timeout)
    raw: list[dict[str, Any]] = []
    if isinstance(data, list):
        raw = [p for p in data if isinstance(p, dict)]
    elif isinstance(data, dict) and isinstance(data.get("projects"), list):
        raw = [p for p in data["projects"] if isinstance(p, dict)]
    out: list[dict[str, Any]] = []
    for proj in raw:
        pid = str(proj.get("project_id") or proj.get("id") or "").strip()
        merged = dict(proj)
        if pid:
            detail = _http_json(f"{base}/api/projects/{pid}/status", timeout=timeout)
            if isinstance(detail, dict):
                merged.update({k: v for k, v in detail.items() if v is not None})
        out.append(merged)
    return out


def _project_id(project: dict[str, Any]) -> str:
    for key in ("id", "project_id", "name", "slug"):
        v = project.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _candidate_paths(project: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("path", "root", "root_path", "directory", "source_path"):
        v = project.get(key)
        if isinstance(v, str) and v.strip():
            paths.append(v)
    extra = project.get("paths")
    if isinstance(extra, list):
        paths.extend(v for v in extra if isinstance(v, str) and v.strip())
    return paths


def _make(project: dict[str, Any], path: str, method: str, score: int) -> ProjectMatch:
    return ProjectMatch(
        project_id=_project_id(project),
        path=path,
        method=method,
        score=score,
        mode=str(project.get("mode") or "docs"),
        state=str(project.get("state") or ""),
        enabled=bool(project.get("enabled", True)),
        raw=project,
    )


def _cacheable(m: ProjectMatch) -> dict[str, Any]:
    """A match without its ``raw`` payload — caches store identity, not content."""
    d = asdict(m)
    d.pop("raw", None)
    return d


# --------------------------------------------------------------------------- #
# Resolution                                                                   #
# --------------------------------------------------------------------------- #


def _by_name(projects: list[dict[str, Any]], wanted: str) -> ScopeDecision:
    want = wanted.strip().lower()
    exact = [_make(p, (_candidate_paths(p) or [""])[0], NAME, 100)
             for p in projects if _project_id(p).lower() == want]
    if exact:
        return ScopeDecision(project=exact[0], candidates=exact, source="override",
                             reason=f"named explicitly: {wanted}")
    partial = [_make(p, (_candidate_paths(p) or [""])[0], NAME_PARTIAL, 50)
               for p in projects if want and want in _project_id(p).lower()]
    if len(partial) == 1:
        return ScopeDecision(project=partial[0], candidates=partial, source="override",
                             reason=f"partial name match: {wanted}")
    if len(partial) > 1:
        return ScopeDecision(candidates=partial, ambiguous=True, source="override",
                             reason=f"{len(partial)} projects match the name {wanted!r}")
    return ScopeDecision(reason=f"no project named {wanted!r}")


def resolve(
    cwd: Path,
    projects: list[dict[str, Any]],
    manual_name: Optional[str] = None,
) -> ScopeDecision:
    """Resolve the project scope for ``cwd``.

    Precedence is by RELATION first, then specificity within the relation:
    an exact match beats any ancestor; any ancestor beats any descendant. Only
    exact and ancestor matches are ranked by path length — see the module
    docstring for why descendants are not.
    """
    if manual_name:
        return _by_name(projects, manual_name)

    cwd_n = norm(str(cwd))
    git_root = detect_git_root(Path(cwd))
    git_n = norm(str(git_root)) if git_root else ""

    buckets: dict[str, list[ProjectMatch]] = {EXACT: [], ANCESTOR: [], DESCENDANT: []}
    seen: set[tuple[str, str]] = set()

    for proj in projects:
        pid = _project_id(proj)
        if not pid:
            continue
        for raw_path in _candidate_paths(proj):
            pn = norm(raw_path)
            if not pn or (pid, pn) in seen:
                continue
            seen.add((pid, pn))

            if pn == cwd_n or (git_n and pn == git_n):
                buckets[EXACT].append(_make(proj, raw_path, EXACT, 1000 + len(pn)))
            elif cwd_n.startswith(pn + "/") or (git_n and git_n.startswith(pn + "/")):
                # cwd lives inside the project: deeper project = more specific.
                buckets[ANCESTOR].append(_make(proj, raw_path, ANCESTOR, 500 + len(pn)))
            elif pn.startswith(cwd_n + "/") or (git_n and pn.startswith(git_n + "/")):
                # The project lives inside the cwd. Length says nothing here.
                buckets[DESCENDANT].append(_make(proj, raw_path, DESCENDANT, 200))

    for kind in sorted(buckets, key=lambda k: -_PRECEDENCE[k]):
        matches = _dedupe(buckets[kind])
        if not matches:
            continue
        if kind is DESCENDANT:
            if len(matches) == 1:
                return ScopeDecision(project=matches[0], candidates=matches,
                                     source="resolved",
                                     reason="the only indexed project under this directory")
            return ScopeDecision(
                candidates=matches, ambiguous=True, source="resolved",
                reason=(
                    f"{len(matches)} indexed projects live under this directory "
                    "and none contains it; path length does not rank them"
                ),
            )
        matches.sort(key=lambda m: -m.score)
        if len(matches) > 1 and matches[0].score == matches[1].score:
            return ScopeDecision(
                candidates=matches, ambiguous=True, source="resolved",
                reason=f"{kind}: two projects match this directory equally",
            )
        return ScopeDecision(project=matches[0], candidates=matches, source="resolved",
                             reason=kind)

    return ScopeDecision(reason="no configured project covers this directory")


def _dedupe(matches: list[ProjectMatch]) -> list[ProjectMatch]:
    """Best match per project id, preserving the strongest score."""
    best: dict[str, ProjectMatch] = {}
    for m in matches:
        prev = best.get(m.project_id)
        if prev is None or m.score > prev.score:
            best[m.project_id] = m
    return sorted(best.values(), key=lambda m: (-m.score, m.project_id))


def match_project(cwd: Path, projects: list[dict[str, Any]],
                  manual_name: Optional[str] = None):
    """Back-compat shim for ``project_focus.py``: ``(best_or_None, candidates)``.

    An ambiguous decision returns ``None`` as the best match, which is the
    contract the focus command already expects for "ask the user".
    """
    decision = resolve(cwd, projects, manual_name)
    return (None if decision.ambiguous else decision.project), decision.candidates


# --------------------------------------------------------------------------- #
# Cache                                                                        #
# --------------------------------------------------------------------------- #


def read_cache(workspace_key: str, ttl: float = CACHE_TTL_SECONDS,
               now: Optional[float] = None) -> Optional[dict[str, Any]]:
    """Cached context for a workspace, or None when absent/expired/unreadable.

    Never raises: a hook that dies on a corrupt cache is worse than one that
    re-resolves.
    """
    try:
        if not CACHE_FILE.is_file():
            return None
        blob = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        entry = (blob.get("workspaces") or {}).get(workspace_key)
        if not isinstance(entry, dict):
            return None
        stamped = float(entry.get("as_of_epoch", 0))
        current = time.time() if now is None else now
        if current - stamped > ttl:
            return None
        return entry
    except (OSError, ValueError, TypeError):
        return None


def write_cache(workspace_key: str, decision: ScopeDecision,
                service: Optional[dict[str, Any]] = None,
                now: Optional[float] = None) -> bool:
    """Persist a resolved context. Returns success; never raises."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        blob: dict[str, Any] = {"schema": 1, "workspaces": {}}
        if CACHE_FILE.is_file():
            try:
                existing = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(existing, dict) and isinstance(existing.get("workspaces"), dict):
                    blob = existing
            except (OSError, ValueError):
                pass
        blob.setdefault("workspaces", {})[workspace_key] = {
            "as_of_epoch": time.time() if now is None else now,
            "project": _cacheable(decision.project) if decision.project else None,
            "candidates": [_cacheable(c) for c in decision.candidates],
            "ambiguous": decision.ambiguous,
            "source": decision.source,
            "reason": decision.reason,
            "service": service or {},
        }
        tmp = CACHE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        tmp.replace(CACHE_FILE)
        return True
    except (OSError, ValueError, TypeError):
        return False


def invalidate_cache(workspace_key: Optional[str] = None) -> bool:
    """Drop one workspace's entry, or the whole cache. Never raises."""
    try:
        if workspace_key is None:
            if CACHE_FILE.is_file():
                CACHE_FILE.unlink()
            return True
        if not CACHE_FILE.is_file():
            return True
        blob = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(blob, dict):
            (blob.get("workspaces") or {}).pop(workspace_key, None)
            CACHE_FILE.write_text(json.dumps(blob, indent=2), encoding="utf-8")
        return True
    except (OSError, ValueError, TypeError):
        return False


if __name__ == "__main__":  # pragma: no cover - manual smoke aid
    import argparse

    ap = argparse.ArgumentParser(description="Resolve the ragtools project scope for a directory")
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--base-url", default="http://127.0.0.1:21420")
    ap.add_argument("--name", default=None, help="resolve by project name instead of path")
    args = ap.parse_args()

    projs = fetch_projects(args.base_url)
    print(f"projects fetched: {len(projs)}")
    decision = resolve(Path(args.cwd), projs, args.name)
    print(f"cwd           : {args.cwd}")
    print(f"workspace key : {resolve_workspace_key(Path(args.cwd))}")
    print(f"decision      : {decision.describe()}")
    for c in decision.candidates:
        print(f"   - {c.project_id:24s} {c.method:16s} score={c.score:5d} "
              f"mode={c.mode:8s} state={c.state} path={c.path}")
