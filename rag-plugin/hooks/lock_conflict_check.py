#!/usr/bin/env python3
"""
rag-plugin lock-conflict PreToolUse hook.

Reads stdin JSON from Claude Code, extracts tool_input.command, and decides
whether the command would fight the Qdrant single-process file lock that the
ragtools service holds when it is up.

Returns hookSpecificOutput.permissionDecision: "ask" only when BOTH conditions
hold:

  1. The command matches one of the known lock-conflicting CLI patterns
     (rag index / rag rebuild / rag watch / rag-mcp standalone / direct
      QdrantClient access).
  2. a ragtools service answers /health inside a 1-second timeout (the likely
     ports are probed — installed 21420, source 21421 — or the one named by
     RAG_SERVICE_PORT / RAG_PLUGIN_SERVICE_PORT) —
     i.e. the service is currently up and holding the lock.

In every other case (no pattern match, or service not reachable, or stdin
malformed, or any unexpected error) the hook prints nothing and exits 0,
which is a silent pass-through. This is deliberate:

  - Never DENY (D-007). Always ASK.
  - Both conditions must hold — false positives erode trust.
  - The hook never blocks. Worst case: the user gets one extra confirmation
    prompt for a command that turns out to be safe.

Design notes:

  - Python stdlib only (json, sys, re, urllib.request, socket). No curl,
    no jq, no third-party deps. Cross-platform.
  - The matcher does NOT match HTTP API calls (curl POST /api/rebuild),
    /projects rebuild, or /rag-status — those go through the service
    on purpose and do not fight the lock.
  - The matcher requires a whole-word "rag" boundary so it does not
    false-match other commands that happen to contain the substring "rag".
  - The health probe uses urllib.request.urlopen with a 1-second timeout;
    any exception (timeout, connection refused, DNS error, JSON parse fail)
    is treated as "service down" and the hook silently passes.

This hook is the security-guidance equivalent of the F-003 "Storage folder
data/qdrant is already accessed by another instance" failure mode. It
exists because the v2.4.1 incident showed that the lock-contention failure
class is the single most common operational footgun for ragtools users.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error

# Resolvable, not hardcoded. The installed service defaults to 21420 and a
# SOURCE install to 21421 (ragtools `config._default_service_port`), and both
# can be running at once. This hook only needs "is a service up right now", so
# it probes the likely ports rather than running full discovery — a guard that
# costs a scan on every Bash call would be worse than the guard is worth.
#
# The override existed on the sibling UserPromptSubmit hook and not here (N-06);
# the two now honour the same variables.
_ENV_PORT = next(
    (os.environ[v] for v in ("RAG_PLUGIN_SERVICE_PORT", "RAG_SERVICE_PORT")
     if os.environ.get(v, "").strip().isdigit()),
    "",
)
HEALTH_URLS = (
    [f"http://127.0.0.1:{_ENV_PORT}/health"]
    if _ENV_PORT
    else ["http://127.0.0.1:21420/health", "http://127.0.0.1:21421/health"]
)
#: Back-compat alias — some tests and docs refer to the single-URL name.
HEALTH_URL = HEALTH_URLS[0]
HEALTH_TIMEOUT_SECONDS = 1.0

# Pattern list. Each pattern is a compiled regex applied to the literal
# tool_input.command string with re.search (not re.match) so the command
# can have leading whitespace, environment-variable prefixes, etc.
#
# Anchoring rules:
#   - "rag" patterns require a word boundary before "rag" so they do not
#     match commands like "fragrag" or paths containing "ragtools" inside
#     a longer word.
#   - Each pattern ends with either a whitespace boundary or end-of-string
#     so that "rag rebuild" matches but "rag rebuilder" does not.
#   - The matcher MUST NOT match HTTP API curl invocations even when they
#     contain the substring "rebuild" — those go through /api/rebuild on
#     the service. The patterns specifically look for the CLI shape:
#     "rag <subcommand>", not "curl ... /api/...".
LOCK_CONFLICT_PATTERNS = [
    # rag index — direct CLI indexing, takes the Qdrant lock
    re.compile(r"(?<![\w.-])rag\s+index(?:\s|$)"),
    # rag rebuild — direct CLI rebuild, takes the Qdrant lock
    re.compile(r"(?<![\w.-])rag\s+rebuild(?:\s|$)"),
    # rag watch — direct CLI watcher, takes the Qdrant lock
    re.compile(r"(?<![\w.-])rag\s+watch(?:\s|$)"),
    # rag-mcp standalone — direct MCP server invocation, takes the Qdrant lock
    re.compile(r"(?<![\w.-])rag-mcp(?:\s|$)"),
    # rag.exe variants on Windows
    re.compile(r"(?<![\w.-])rag\.exe\s+(index|rebuild|watch)(?:\s|$)"),
    # Direct QdrantClient(path=...) python access — fights the lock
    re.compile(r"QdrantClient\s*\(\s*path\s*="),
    # python -c "from qdrant_client import QdrantClient; ..."
    re.compile(r"from\s+qdrant_client\s+import\s+QdrantClient"),
]


def matches_lock_conflict(command: str) -> str | None:
    """Return the matched pattern source if any pattern matches, else None."""
    if not command:
        return None
    for pattern in LOCK_CONFLICT_PATTERNS:
        if pattern.search(command):
            return pattern.pattern
    return None


def service_is_up() -> bool:
    """Probe the candidate /health endpoints with a 1-second timeout each.

    Any exception (connection refused, timeout, DNS error, etc.) is treated
    as "service down" and we return False. We do not parse the response body
    because /health may return JSON or plain text depending on the version;
    a 200 is sufficient evidence *a* service is holding the lock — and for a
    lock-conflict guard, any running service is reason enough to ask.

    Both likely ports are probed (installed 21420, source 21421) unless an
    explicit override names one. The first 200 wins; a closed loopback port
    refuses immediately, so the second probe costs nothing when the first
    succeeds and almost nothing when it does not.
    """
    for url in HEALTH_URLS:
        try:
            with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                OSError, ValueError):
            continue
        except Exception:
            # Any other unexpected error → treat this URL as down and move on.
            # We never want this hook to blow up Claude Code's tool call.
            continue
    return False


def emit_silent_pass() -> None:
    """Print nothing and exit 0. Claude Code interprets this as 'no decision'
    and proceeds with the tool call as normal."""
    sys.exit(0)


def emit_ask(command: str, matched_pattern: str) -> None:
    """Emit a hookSpecificOutput JSON with permissionDecision: ask."""
    reason = (
        "About to run a Bash command that opens Qdrant in direct mode while "
        "the ragtools service is up at http://127.0.0.1:21420.\n\n"
        "Both processes would compete for the Qdrant single-process file lock — "
        "the most common ragtools failure mode (F-003 in references/known-failures.md). "
        "Either stop the service first (`rag service stop`) or use the HTTP API "
        "equivalent (e.g. `curl -X POST http://127.0.0.1:21420/api/rebuild` for rebuild, "
        "`/projects rebuild` for project management).\n\n"
        f"matched pattern: {matched_pattern}\n"
        f"command: {command[:200]}"
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def main() -> None:
    # Parse stdin. If anything is malformed, silent pass.
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            emit_silent_pass()
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        emit_silent_pass()
        return  # unreachable, for type checkers
    except Exception:
        emit_silent_pass()
        return

    # Extract the command. If it's not a Bash tool call, silent pass.
    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        emit_silent_pass()
        return

    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        emit_silent_pass()
        return

    command = tool_input.get("command", "")
    if not isinstance(command, str):
        emit_silent_pass()
        return

    # Pattern check first (cheap). If no match, silent pass without
    # touching the network.
    matched = matches_lock_conflict(command)
    if matched is None:
        emit_silent_pass()
        return

    # Pattern matched. Now check if the service is up. If not, silent pass —
    # there's no lock contention to warn about when the service is down.
    if not service_is_up():
        emit_silent_pass()
        return

    # Both conditions hold. Ask the user to confirm.
    emit_ask(command, matched)


if __name__ == "__main__":
    main()
