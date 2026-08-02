#!/usr/bin/env python3
"""rag-plugin UserPromptSubmit context injector (v1.0.0, WP-7).

Merges the two previous UserPromptSubmit hooks — ``prompt_retrieval_reminder``
(D-017/D-027) and ``project_focus_inject`` (D-025/D-028) — into one decision.

Why they had to merge
---------------------
One of them knew the project and the other needed it.

``prompt_retrieval_reminder.domain_probe()`` issued
``GET /api/search?query=…&top_k=1&compact=true`` with **no project**. From
ragtools v3.0.0 that is a hard ``HTTP 422 SCOPE_UNRESOLVED``, so the probe
always returned an error, ``main()`` took the ``if err: silent_pass(err)``
branch, and ``inject_reminder()`` became unreachable.

The hook's own log recorded it precisely::

    reminder-injected                  380   last  2026-07-28T08:23:16Z
    silent-pass:probe-error:http-422   105   first 2026-07-29T07:55:59Z

Zero injections in the four days after, on 105 consecutive probes. The flagship
answer to under-retrieval had been silently dead, and the failure was invisible
because an advisory hook fails open — "the probe errored" and "nothing matched"
produce the same silence.

Meanwhile ``project_focus_inject`` was resolving the workspace's project from a
cheap state-file read on every prompt and never told the other hook.

What changed
------------
* **Phase A.6** — a prompt with no resolvable repository context exits before
  any network call. "Rewrite this email" now costs zero HTTP.
* **Phase B** — scope comes from the focus override, else the resolver cache,
  else a single resolution. Warm path: **zero** HTTP calls.
* **Phase C** — the relevance probe is **scoped**, so it measures the index
  Claude will actually search instead of returning 422 forever.
* **Phase D** — one compact block: scope, mode, freshness, and the probe verdict.

A 422 after Phase C is now a real defect and is logged distinctly
(``probe-error:http-422-after-scope``) rather than swallowed as noise.

D-031 is preserved without exception: this file is registered **advisory**, so
``hook_launcher`` normalises every exit to 0. It cannot block a prompt.
D-028 §5's anti-leak rule is preserved: a foreign workspace's project name is
never injected.

Python 3 stdlib only.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import NamedTuple

HOOK_VERSION = "1.0.0"

# --- endpoint -------------------------------------------------------------

_ENV_PORT = next(
    (os.environ[v] for v in ("RAG_PLUGIN_SERVICE_PORT", "RAG_SERVICE_PORT")
     if os.environ.get(v, "").strip().isdigit()),
    "",
)
#: Installed defaults to 21420, a SOURCE install to 21421, and both can run at
#: once. Full discovery (rules/service-discovery.md) is too expensive for a
#: per-prompt hook, so the likely pair is probed and the winner cached.
CANDIDATE_PORTS = [int(_ENV_PORT)] if _ENV_PORT else [21420, 21421]

HEALTH_TIMEOUT = float(os.environ.get("RAG_PLUGIN_HOOK_HEALTH_TIMEOUT", "0.5"))
SEARCH_TIMEOUT = float(os.environ.get("RAG_PLUGIN_HOOK_SEARCH_TIMEOUT", "1.5"))
PROBE_THRESHOLD = float(os.environ.get("RAG_PLUGIN_HOOK_PROBE_THRESHOLD", "0.65"))

_CLAUDE_HOME = os.path.expanduser("~/.claude")
OBS_DIR = os.path.join(_CLAUDE_HOME, "rag-plugin")
OBS_LOG = os.path.join(OBS_DIR, "hook-decisions.log")
OBS_DISABLE_MARKER = os.path.join(OBS_DIR, ".hook-observability-disabled")

_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts")


# --- Phase A: shape heuristic (carried over unchanged) ---------------------

_CURRENT_CONTEXT_HINTS = re.compile(
    r"\b(this file|this code|the code|current file|current code|the file above|"
    r"above|below|just now|last turn|you just|the last (turn|message|response)|"
    r"what you said|what i said|this conversation|the snippet|the output above)\b",
    re.IGNORECASE,
)
_QUESTION_SHAPE = re.compile(
    r"(\?|^\s*(what|where|when|who|why|how|which|is|are|does|do|did|can|could|"
    r"should|would|list|show|find|explain|describe|summar|tell me|remind))",
    re.IGNORECASE,
)
_POSSESSIVE = re.compile(
    r"\b(our|my|we|us|the team|the company|the client|the project|internal|"
    r"the process|the procedure|the convention|the standard|the requirement|"
    r"the decision|the spec|the policy)\b",
    re.IGNORECASE,
)


def shape_match(prompt: str) -> bool:
    """Question-like, domain-possessive, and not about the current context."""
    if not prompt or not prompt.strip():
        return False
    if _CURRENT_CONTEXT_HINTS.search(prompt):
        return False
    if not _QUESTION_SHAPE.search(prompt):
        return False
    return bool(_POSSESSIVE.search(prompt)) or len(prompt.split()) >= 6


# --- Phase A.5: operational-intent classifier (D-027, byte-compatible) -----

_OPERATIONAL_INTENT = re.compile(
    r"\b(?:(?:please\s+|can\s+you\s+|could\s+you\s+|i\s+need\s+to\s+|i\s+want\s+to\s+|"
    r"help\s+me\s+|how\s+(?:do\s+i|can\s+i|to|do\s+you|would\s+i)\s+)?"
    r"(start|stop|restart|run|launch|kill|spawn|"
    r"fix|repair|debug|troubleshoot|"
    r"set\s*up|setup|install|uninstall|reinstall|upgrade|update|configure|"
    r"where\s+is|where\s+are|what'?s\s+(?:running|listening|installed|configured|in)|"
    r"is\s+\w+\s+(?:installed|running|on\s+path|reachable|up)|"
    r"why\s+is\s+(?:\w+\s+){1,4}?(?:failing|crashing|broken|down|not\s+running|"
    r"not\s+working|not\s+starting|not\s+booting)|"
    r"check\s+(?:if|whether|the)\s+|inspect\s+(?:the|my)\s+|"
    r"auto[- ]?start|wire\s+up|enable|disable|"
    r"open\s+(?:the\s+)?(?:wsl|terminal|shell|ide|browser)|"
    r"clear\s+(?:the\s+)?(?:cache|log|state)|delete\s+(?:the\s+)?(?:cache|log|file|state)|"
    r"list\s+(?:the\s+)?(?:files|processes|tasks|services)|"
    r"show\s+(?:me\s+)?(?:the\s+)?(?:status|process|log|tail)"
    r")\b)",
    re.IGNORECASE,
)


def is_operational_intent(prompt: str) -> bool:
    """Machine-state questions answer from the filesystem, not the index."""
    if not prompt or not prompt.strip():
        return False
    return bool(_OPERATIONAL_INTENT.search(prompt[:120]))


# --- Phase B: scope ---------------------------------------------------------


def _load(module_name: str, filename: str):
    """Import a plugin script by path. None on any failure — the hook degrades
    to 'no scope' rather than dying."""
    try:
        import importlib.util

        path = os.path.join(_SCRIPTS_DIR, filename)
        if not os.path.isfile(path):
            return None
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        return None


def _point_focus_engine_at_state_file(engine) -> bool:
    """Honour ``RAG_PLUGIN_FOCUS_STATE_FILE``.

    The retired ``project_focus_inject`` hook supported this override and its
    test suite drives the hook through it. Preserving a working test seam
    across a merge is not optional — dropping it would have left the focus
    behaviour untested rather than untestable.
    """
    override = os.environ.get("RAG_PLUGIN_FOCUS_STATE_FILE")
    if not override:
        return True
    try:
        from pathlib import Path

        path = Path(override)
        engine.STATE_FILE = path
        engine.STATE_DIR = path.parent
        return True
    except Exception:
        return False


def _focus_override(engine, workspace_key: str):
    """The user's explicit /project-focus, if it applies here.

    Returns ``(project_name_or_None, source)`` where source is one of
    ``workspace`` / ``global`` / ``other-workspace-only`` / ``none``.
    D-028 precedence: workspace > global > none.
    """
    try:
        bundle = engine.read_state()
        if not bundle:
            return None, "none"
        record, source = engine.resolve_effective_focus(bundle, workspace_key)
        if record and source in ("workspace", "global"):
            name = str(record.get("project_name", "")).strip()
            return (name or None), source
        return None, source
    except Exception:
        return None, "none"


class Scope(NamedTuple):
    """What scope the injector resolved, and where it came from.

    ``focus_note`` carries D-028 §5's "focus exists for a DIFFERENT workspace"
    fact separately from the scope itself, because that case still needs a
    notice even when no project resolves — and the notice must never name the
    foreign project.
    """

    project: str = ""
    mode: str = ""
    state: str = ""
    source: str = "none"          # override-workspace | override-global |
                                  # cache | resolved | none
    ambiguous: tuple = ()
    focus_note: str = ""          # "" | "other-workspace-only"


def resolve_scope(cwd: str) -> Scope:
    """Resolve the retrieval scope for ``cwd``.

    Order: explicit focus override -> resolver cache -> one live resolution.
    Every failure degrades to "no scope", never to an unscoped search.
    """
    scope = _load("rp_scope_resolve", "scope_resolve.py")
    if scope is None:
        return Scope()

    try:
        from pathlib import Path

        workspace_key = scope.resolve_workspace_key(Path(cwd))
    except Exception:
        return Scope()

    focus_note = ""
    focus = _load("rp_project_focus", "project_focus.py")
    if focus is not None and _point_focus_engine_at_state_file(focus):
        name, source = _focus_override(focus, workspace_key)
        if name:
            # D-028 §6: a global override fires because the user asked for it,
            # NOT because it matches this directory. It must say so.
            return Scope(project=name,
                         source="override-global" if source == "global"
                         else "override-workspace")
        if source == "other-workspace-only":
            # D-028 §5: never leak the foreign project's name. Remember the
            # fact, then try to resolve THIS workspace on its own merits.
            focus_note = "other-workspace-only"

    cached = scope.read_cache(workspace_key)
    if cached:
        proj = cached.get("project") or {}
        if cached.get("ambiguous"):
            ids = tuple(c.get("project_id", "")
                        for c in (cached.get("candidates") or []))
            return Scope(source="cache", ambiguous=ids, focus_note=focus_note)
        if proj.get("project_id"):
            return Scope(proj["project_id"], proj.get("mode", ""),
                         proj.get("state", ""), "cache", (), focus_note)
        return Scope(source="cache", focus_note=focus_note)

    base = _first_live_base_url()
    if not base:
        return Scope(focus_note=focus_note)
    try:
        from pathlib import Path

        projects = scope.fetch_projects(base, timeout=SEARCH_TIMEOUT)
        decision = scope.resolve(Path(cwd), projects)
        scope.write_cache(workspace_key, decision, service={"base_url": base})
        if decision.ambiguous:
            return Scope(source="resolved", ambiguous=tuple(decision.union_ids),
                         focus_note=focus_note)
        if decision.project:
            return Scope(decision.project.project_id, decision.project.mode,
                         decision.project.state, "resolved", (), focus_note)
    except Exception:
        return Scope(focus_note=focus_note)
    return Scope(source="resolved", focus_note=focus_note)


# --- HTTP -------------------------------------------------------------------

_live_base_url_cache: list = []


def _first_live_base_url():
    """The first candidate port whose /health answers. Cached per process."""
    if _live_base_url_cache:
        return _live_base_url_cache[0]
    for port in CANDIDATE_PORTS:
        url = f"http://127.0.0.1:{port}"
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=HEALTH_TIMEOUT) as resp:
                if resp.status == 200:
                    _live_base_url_cache.append(url)
                    return url
        except Exception:
            continue
    return None


def domain_probe(prompt: str, project: str):
    """Phase C. A **scoped** top_k=1 search. ``(matched, score, error_reason)``.

    The scope argument is the whole fix. Without it this returned
    ``probe-error:http-422`` on every prompt from 2026-07-29 onward.
    """
    base = _first_live_base_url()
    if not base:
        return False, 0.0, "service-down"
    try:
        query = urllib.parse.urlencode({
            "query": prompt[:500],
            "project": project,
            "top_k": "1",
            "compact": "true",
        })
        with urllib.request.urlopen(f"{base}/api/search?{query}",
                                    timeout=SEARCH_TIMEOUT) as resp:
            if resp.status != 200:
                return False, 0.0, f"probe-error:http-{resp.status}"
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 422:
            # Scope WAS passed and the service still refused. That is a real
            # defect, not the ambient noise the old unscoped probe produced.
            return False, 0.0, "probe-error:http-422-after-scope"
        return False, 0.0, f"probe-error:http-{e.code}"
    except urllib.error.URLError:
        return False, 0.0, "probe-error:network"
    except TimeoutError:
        return False, 0.0, "probe-error:timeout"
    except json.JSONDecodeError:
        return False, 0.0, "probe-error:json"
    except Exception:
        return False, 0.0, "probe-error:unknown"

    results = body.get("results") if isinstance(body, dict) else None
    if not results or not isinstance(results, list):
        return False, 0.0, ""
    top = results[0] if isinstance(results[0], dict) else {}
    try:
        score = float(top.get("score", 0.0))
    except (TypeError, ValueError):
        score = 0.0
    return score >= PROBE_THRESHOLD, score, ""


# --- observability ----------------------------------------------------------


def log_decision(**fields) -> None:
    """One JSONL record. Never user content; never fails the hook (D-012)."""
    if os.path.isfile(OBS_DISABLE_MARKER):
        return
    try:
        os.makedirs(OBS_DIR, exist_ok=True)
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "hook_version": HOOK_VERSION}
        entry.update(fields)
        with open(OBS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def silent_pass(reason: str, **fields) -> None:
    log_decision(action=f"silent-pass:{reason}", **fields)
    sys.exit(0)


# --- Phase D: the injected block --------------------------------------------


def build_block(scope, probe_score=0.0, probe_matched=False):
    """Three to six lines. This loads on every qualifying prompt."""
    project, mode, state = scope.project, scope.mode, scope.state
    source, ambiguous = scope.source, scope.ambiguous
    lines = [f"REMINDER (rag-plugin v{HOOK_VERSION} context injector):", ""]

    # D-028 §5: focus exists for a DIFFERENT workspace. Say so without ever
    # naming it — a leaked name is a name Claude can pass as project=.
    foreign = (
        "Project focus exists for another workspace, but it is NOT applied here. "
        "Do NOT carry that project filter into searches from this directory."
        if scope.focus_note == "other-workspace-only" else ""
    )

    if ambiguous:
        if foreign:
            lines += [foreign, ""]
        lines += [
            "RAG scope is AMBIGUOUS for this directory: " + ", ".join(ambiguous) + ".",
            "Name one — search_knowledge_base(query=..., project=\"<id>\") — or search "
            "the union with projects=[" + ", ".join(f'"{p}"' for p in ambiguous) + "]. "
            "An unscoped call is refused (HTTP 422 SCOPE_UNRESOLVED).",
        ]
        return "\n".join(lines)

    if not project:
        if foreign:
            lines += [foreign, ""]
        lines += [
            "No RAG project is resolved for this directory.",
            "If you need the knowledge base, call list_projects() and pass an explicit "
            "project= — an unscoped search_knowledge_base / search_project_context call "
            "is refused with HTTP 422 SCOPE_UNRESOLVED and returns nothing.",
        ]
        return "\n".join(lines)

    bits = [f"project={project}"]
    if mode:
        bits.append(f"mode={mode}")
    if state:
        bits.append(f"state={state}")
    if source == "override-global":
        # D-028 §6: a global override fires because the user ran
        # `--global`, NOT because it matches this directory. Label it, or a
        # reader assumes the cwd was matched.
        label = ("EXPLICIT GLOBAL FOCUS via /project-focus --global — this does NOT "
                 "match the current working directory")
    elif source == "override-workspace":
        label = "explicit /project-focus for this workspace"
    else:
        label = f"resolved ({source})"
    lines.append(f"RAG scope: {' · '.join(bits)} — {label}.")
    lines.append(
        f'Pass project="{project}" on every search_knowledge_base and '
        "search_project_context call; unscoped is refused (HTTP 422)."
    )

    if mode == "docs":
        lines.append(
            "This project is in DOCS mode — its source code is NOT indexed. An empty "
            "find_definition / search_project_context result means nothing here; say so "
            "and use Grep/LSP for code."
        )
    if state == "indexed_stale":
        lines.append(
            "The index for this project is STALE — verify anything load-bearing against "
            "the working tree before relying on it."
        )
    if probe_matched:
        confidence = "HIGH" if probe_score >= 0.7 else "MODERATE"
        lines.append(
            f"A scoped probe suggests this prompt has a {confidence} match "
            f"(score {probe_score:.2f}) — search before answering."
        )
    return "\n".join(lines)


def inject(block: str, **fields) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": block,
        }
    }))
    log_decision(action="context-injected", **fields)
    sys.exit(0)


# --- main -------------------------------------------------------------------


def main() -> None:
    try:
        raw = sys.stdin.read()
    except Exception:
        silent_pass("stdin-read-error")
        return
    if not raw.strip():
        silent_pass("empty-stdin")
        return
    try:
        payload = json.loads(raw)
    except Exception:
        silent_pass("stdin-parse-error")
        return
    if not isinstance(payload, dict):
        silent_pass("stdin-not-object")
        return

    prompt = payload.get("user_prompt") or payload.get("prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        silent_pass("empty-prompt")
        return
    prompt_length = len(prompt)
    cwd = payload.get("cwd") or os.getcwd()

    # Phase A — shape
    if not shape_match(prompt):
        silent_pass("shape-mismatch", shape_match=False, prompt_length=prompt_length,
                    http_calls=0)
        return

    # Phase A.5 — operational intent (D-027)
    if is_operational_intent(prompt):
        silent_pass("operational-intent", shape_match=True,
                    prompt_length=prompt_length, http_calls=0)
        return

    # Phase A.6 — repo context. NEW: exits before any network call.
    scope = resolve_scope(str(cwd))
    if (not scope.project and not scope.ambiguous and scope.source == "none"
            and not scope.focus_note):
        silent_pass("no-repo-context", shape_match=True,
                    prompt_length=prompt_length, scope_source="none", http_calls=0)
        return

    http_calls = 0 if scope.source.startswith(("cache", "override")) else 1

    # Ambiguous or unresolved scope: say so; never probe unscoped.
    if scope.ambiguous or not scope.project:
        inject(build_block(scope),
               shape_match=True, prompt_length=prompt_length,
               scope_source=scope.source, ambiguous=bool(scope.ambiguous),
               focus_note=scope.focus_note, http_calls=http_calls)
        return

    # Phase C — SCOPED probe
    matched, score, err = domain_probe(prompt, scope.project)
    if err:
        # Still inject the scope block: knowing the project and its mode is
        # useful even when relevance could not be measured.
        inject(build_block(scope),
               shape_match=True, prompt_length=prompt_length,
               scope_source=scope.source, project_id=scope.project,
               project_mode=scope.mode, project_state=scope.state,
               probe_error=err, http_calls=http_calls + 1)
        return

    inject(build_block(scope, score, matched),
           shape_match=True, prompt_length=prompt_length, scope_source=scope.source,
           project_id=scope.project, project_mode=scope.mode,
           project_state=scope.state, probe_match=matched,
           probe_top_score=round(score, 3), http_calls=http_calls + 1)


if __name__ == "__main__":
    main()
