#!/usr/bin/env python3
"""
rag-plugin UserPromptSubmit retrieval-reminder hook (v0.3.0).

Reads stdin JSON from Claude Code on every user prompt submission. Decides
whether to inject a system reminder that tells Claude to call the ragtools
`search_knowledge_base` MCP tool before answering.

Design (Tier 2, guided enforcement — see docs/decisions.md#d-017):

  Phase A — shape gate (cheap, no network):
    - Exclude prompts that reference the current conversation context
      (e.g., "explain this file", "look above", "the code I just pasted").
      These are NOT retrieval questions — silent-pass immediately.
    - Match question-shaped prompts (contains "?", or leads with a wh-word,
      or uses imperative retrieval verbs like "explain / tell me / find").
    - Match statements that assert ownership of a domain
      (e.g., "our deployment pipeline", "my runbook for X") — these may
      have answers in the user's notes even without a question mark.
    - Pass shape gate if (question OR possessive) AND NOT current-context.

  Phase B — domain probe (one local HTTP call, ~30-50ms warm):
    - First probe `/health` with a 500ms timeout. If the service is down,
      silent-pass with reason `service-down`.
    - Then GET /api/search?query=<urlencoded>&top_k=1&compact=true with a
      1-second timeout. Parse JSON, extract results[0].score.
    - If score >= PROBE_THRESHOLD (default 0.5, the ragtools MODERATE
      confidence boundary), PROBE PASSED: inject reminder.
    - If score < threshold or results is empty: silent-pass.
    - Any HTTP error, timeout, or parse failure: silent-pass with reason.

  Hook contract:
    - Injects `hookSpecificOutput.additionalContext` with a ~10-line reminder
      when both phases pass. No permissionDecision field — the hook does
      not block, deny, or ask. It only provides context (D-007 spirit).
    - Silent-pass on any error or mismatch. The hook never crashes the turn.
    - Prints a single JSON object to stdout on match; nothing on silent-pass.
    - Exit 0 in all cases. Never non-zero.

Observability:

  Every decision is appended as one JSON line to
  ~/.claude/rag-plugin/hook-decisions.log unless a disable marker exists
  at ~/.claude/rag-plugin/.hook-observability-disabled. The log contains
  decision metadata only — timestamp, shape_match, probe_match, probe score,
  action, prompt_length, hook_version. It NEVER contains the prompt text,
  the search query, or any result content. This aligns with D-012 (local-
  only, no networked telemetry, no user content persisted).

Environment variable overrides (for testing and runtime tuning):

  RAG_PLUGIN_HOOK_PROBE_THRESHOLD  -- float 0.0-1.0, default 0.5
  RAG_PLUGIN_HOOK_HEALTH_URL       -- override health endpoint (testing)
  RAG_PLUGIN_HOOK_SEARCH_URL       -- override search endpoint base (testing)
  RAG_PLUGIN_HOOK_HEALTH_TIMEOUT   -- float seconds, default 0.5
  RAG_PLUGIN_HOOK_SEARCH_TIMEOUT   -- float seconds, default 1.0

Python 3 stdlib only. No third-party dependencies. Cross-platform.

Related decisions:
  D-001  ops-only, never search (this hook REGISTERS a reminder, not a search)
  D-007  hooks ask, never deny (this hook injects context, does not block)
  D-008  compact-by-default outputs (~200 token reminder, ~50 byte log lines)
  D-012  no networked telemetry, local-only logs, zero user content
  D-015  plugin-level .mcp.json auto-wiring
  D-016  CLAUDE.md retrieval rule (this hook complements, does not replace)
  D-017  Tier 2 guided enforcement + observability-first escalation path
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- configuration ---------------------------------------------------------

HOOK_VERSION = "0.3.0"

HEALTH_URL = os.environ.get(
    "RAG_PLUGIN_HOOK_HEALTH_URL",
    "http://127.0.0.1:21420/health",
)
SEARCH_URL = os.environ.get(
    "RAG_PLUGIN_HOOK_SEARCH_URL",
    "http://127.0.0.1:21420/api/search",
)
HEALTH_TIMEOUT = float(os.environ.get("RAG_PLUGIN_HOOK_HEALTH_TIMEOUT", "0.5"))
SEARCH_TIMEOUT = float(os.environ.get("RAG_PLUGIN_HOOK_SEARCH_TIMEOUT", "1.0"))
PROBE_THRESHOLD = float(os.environ.get("RAG_PLUGIN_HOOK_PROBE_THRESHOLD", "0.5"))

# Observability log lives under ~/.claude/rag-plugin/
# (same directory as the telemetry log from D-012).
_CLAUDE_HOME = os.path.expanduser("~/.claude")
OBS_DIR = os.path.join(_CLAUDE_HOME, "rag-plugin")
OBS_LOG = os.path.join(OBS_DIR, "hook-decisions.log")
OBS_DISABLE_MARKER = os.path.join(OBS_DIR, ".hook-observability-disabled")


# --- shape heuristic (Phase A) ---------------------------------------------

# If the prompt mentions the current conversation context, it's NOT a
# retrieval question — silent-pass. Order: case-insensitive, word boundaries.
_CURRENT_CONTEXT_HINTS = re.compile(
    r"\b(this file|this code|the code|current file|current code|the file above|"
    r"above|below|just now|last turn|you just|the last (turn|message|response)|"
    r"what you said|what i said|this conversation|the snippet|the output above)\b",
    re.IGNORECASE,
)

# Question-shaped prompts: a trailing "?", or a leading/embedded wh-word,
# or an imperative retrieval verb.
_QUESTION_MARK = re.compile(r"\?")
_QUESTION_SHAPE = re.compile(
    r"(?:^|\s)(what|how|where|when|why|who|which|whose|"
    r"is|are|can|could|does|do|did|should|would|will|has|have|had|"
    r"tell me|explain|describe|show me|find|search|look up|look for|"
    r"give me|list|summarize|summarise)\b",
    re.IGNORECASE,
)

# Possessive domain signal: the user is asserting ownership of a domain that
# might have an answer in their notes even without a question mark.
# Examples that pass: "our deployment pipeline uses blue-green",
# "the emergency assistance procedure", "my runbook for backups".
_POSSESSIVE_DOMAIN = re.compile(
    r"\b(my|our|the|your)\s+"
    r"(process|policy|procedure|sop|runbook|playbook|"
    r"docs?|notes?|wiki|"
    r"project|convention|standard|workflow|pipeline|"
    r"decision|design|architecture|setup|config(?:uration)?|"
    r"service|system|deployment|release|incident|"
    r"team|org(?:anization)?|customer|client|"
    r"api|endpoint|schema|contract|"
    r"rule|guideline|checklist)\b",
    re.IGNORECASE,
)


def shape_match(prompt: str) -> bool:
    """Phase A. Does the prompt look like a question/statement that might
    have an answer in the user's indexed knowledge base?"""
    if not prompt or not prompt.strip():
        return False
    # Current-context references are NOT retrieval questions.
    if _CURRENT_CONTEXT_HINTS.search(prompt):
        return False
    # Question-shaped prompts pass.
    if _QUESTION_MARK.search(prompt):
        return True
    if _QUESTION_SHAPE.search(prompt):
        return True
    # Possessive domain statements pass.
    if _POSSESSIVE_DOMAIN.search(prompt):
        return True
    return False


# --- domain probe (Phase B) ------------------------------------------------


def _service_is_up() -> bool:
    """500ms health probe. True if service is reachable; False on any
    exception. Never raises."""
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=HEALTH_TIMEOUT) as resp:
            return resp.status == 200
    except Exception:
        return False


def domain_probe(prompt: str) -> tuple[bool, float, str]:
    """Phase B. Run a top_k=1 search via the ragtools /api/search endpoint.
    Returns (matched, top_score, error_reason). error_reason is empty on
    success. Never raises."""
    try:
        query = urllib.parse.urlencode(
            {
                "query": prompt[:500],  # cap the query to avoid pathological sizes
                "top_k": "1",
                "compact": "true",
            }
        )
        url = f"{SEARCH_URL}?{query}"
        with urllib.request.urlopen(url, timeout=SEARCH_TIMEOUT) as resp:
            if resp.status != 200:
                return (False, 0.0, f"probe-error:http-{resp.status}")
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return (False, 0.0, f"probe-error:http-{e.code}")
    except urllib.error.URLError:
        return (False, 0.0, "probe-error:network")
    except TimeoutError:
        return (False, 0.0, "probe-error:timeout")
    except json.JSONDecodeError:
        return (False, 0.0, "probe-error:json")
    except Exception:
        return (False, 0.0, "probe-error:unknown")

    results = body.get("results") if isinstance(body, dict) else None
    if not results or not isinstance(results, list):
        return (False, 0.0, "")

    top = results[0]
    score = 0.0
    if isinstance(top, dict):
        raw = top.get("score", 0.0)
        try:
            score = float(raw)
        except (TypeError, ValueError):
            score = 0.0

    matched = score >= PROBE_THRESHOLD
    return (matched, score, "")


# --- observability ---------------------------------------------------------


def _observability_enabled() -> bool:
    """Default is enabled. Disabled only if an explicit marker file exists."""
    return not os.path.isfile(OBS_DISABLE_MARKER)


def log_decision(
    shape: bool,
    probe_match: bool,
    probe_score: float,
    action: str,
    prompt_length: int,
) -> None:
    """Append one JSONL decision record. NEVER contains user content.
    Logging failures are swallowed — they must never affect the hook outcome."""
    if not _observability_enabled():
        return
    try:
        os.makedirs(OBS_DIR, exist_ok=True)
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shape_match": bool(shape),
            "probe_match": bool(probe_match),
            "probe_top_score": round(float(probe_score), 3) if probe_score else 0.0,
            "action": action,
            "prompt_length": int(prompt_length),
            "hook_version": HOOK_VERSION,
        }
        with open(OBS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # never fail the hook due to logging


# --- hook outputs ----------------------------------------------------------


def silent_pass(
    reason: str,
    shape: bool = False,
    probe_match: bool = False,
    probe_score: float = 0.0,
    prompt_length: int = 0,
) -> None:
    """Emit nothing to stdout, log the decision, exit 0."""
    log_decision(
        shape=shape,
        probe_match=probe_match,
        probe_score=probe_score,
        action=f"silent-pass:{reason}",
        prompt_length=prompt_length,
    )
    sys.exit(0)


def inject_reminder(
    probe_score: float,
    prompt_length: int,
) -> None:
    """Emit the reminder JSON and exit 0."""
    confidence = "HIGH" if probe_score >= 0.7 else "MODERATE"
    reminder = (
        f"REMINDER (rag-plugin v{HOOK_VERSION} retrieval-reminder hook):\n\n"
        f"The ragtools MCP is loaded and your current prompt has a likely "
        f"match in the indexed knowledge base (probe score: {probe_score:.2f}, "
        f"confidence: {confidence}).\n\n"
        f"Before answering, call:\n"
        f"  mcp__plugin_rag-plugin_ragtools__search_knowledge_base(query=<...>)\n\n"
        f"Do NOT say \"I don't have information about X\" without searching first. "
        f"See ~/.claude/CLAUDE.md Section 0 for the full retrieval rule. "
        f"This reminder fires because the CLAUDE.md rule alone is advisory — "
        f"the hook is the harness-enforced layer that guarantees you see this "
        f"instruction at the moment of answering."
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": reminder,
        }
    }
    log_decision(
        shape=True,
        probe_match=True,
        probe_score=probe_score,
        action="reminder-injected",
        prompt_length=prompt_length,
    )
    print(json.dumps(output))
    sys.exit(0)


# --- main ------------------------------------------------------------------


def main() -> None:
    # Parse stdin. Any malformed JSON → silent-pass.
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
    except (json.JSONDecodeError, ValueError):
        silent_pass("stdin-parse-error")
        return
    except Exception:
        silent_pass("stdin-parse-error")
        return

    if not isinstance(payload, dict):
        silent_pass("stdin-not-object")
        return

    # The UserPromptSubmit stdin field is `user_prompt` per the official
    # plugin-dev hook schema (claude-plugins-official-main/.../hook-development/SKILL.md
    # line 317). Accept `prompt` as a fallback for compatibility with older
    # runtimes or custom harnesses.
    prompt = payload.get("user_prompt") or payload.get("prompt") or ""
    if not isinstance(prompt, str):
        silent_pass("prompt-not-string")
        return

    prompt_length = len(prompt)
    if not prompt.strip():
        silent_pass("empty-prompt", prompt_length=prompt_length)
        return

    # Phase A: shape gate
    if not shape_match(prompt):
        silent_pass("shape-mismatch", shape=False, prompt_length=prompt_length)
        return

    # Phase B: health probe (fast fail if service is down)
    if not _service_is_up():
        silent_pass(
            "service-down",
            shape=True,
            prompt_length=prompt_length,
        )
        return

    # Phase B: domain probe (actual search)
    matched, score, err = domain_probe(prompt)
    if err:
        silent_pass(
            err,
            shape=True,
            probe_score=score,
            prompt_length=prompt_length,
        )
        return

    if not matched:
        silent_pass(
            "probe-below-threshold",
            shape=True,
            probe_match=False,
            probe_score=score,
            prompt_length=prompt_length,
        )
        return

    # Both phases passed. Inject the reminder.
    inject_reminder(probe_score=score, prompt_length=prompt_length)


if __name__ == "__main__":
    main()
