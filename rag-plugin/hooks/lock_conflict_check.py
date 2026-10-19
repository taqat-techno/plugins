#!/usr/bin/env python3
"""
rag-plugin lock-conflict PreToolUse hook (Bash and PowerShell tools).

Reads the hook payload, takes ``tool_input.command`` and decides whether the
command would fight the Qdrant single-process file lock that the ragtools
service holds while it is up.

It returns ``permissionDecision: "ask"`` only when BOTH conditions hold:

  1. A command that will actually run matches a known lock-conflicting CLI
     shape: ``rag index`` / ``rag rebuild`` / ``rag watch`` / standalone
     ``rag-mcp`` / ``rag.exe`` variants, or Python opening Qdrant directly
     (``QdrantClient(path=...)``).
  2. A ragtools service answers ``/health`` within one second (the likely ports
     are probed: installed 21420, source 21421, or the one named by the
     ``service_port`` plugin option / ``RAG_PLUGIN_SERVICE_PORT`` /
     ``RAG_SERVICE_PORT``).

In every other case (no match, service not reachable, malformed input, any
unexpected error) the hook prints nothing and exits 0.

  - Never DENY (D-007). Always ASK, and print no override token: the user
    answers the prompt.
  - Match the command that runs, not text that mentions it. ``echo``,
    ``grep``/``rg``/``Select-String`` patterns, ``git commit -m`` messages,
    comments and quoted strings never trigger the guard. Quoted text counts
    only as the code argument of a ``python -c`` call, because that code runs.
  - HTTP API calls (``curl -X POST .../api/rebuild``) and ``/projects rebuild``
    go through the service on purpose and do not match.

Python 3 stdlib only, plus the vendored ``hooks/_vendor/hooklib.py``.
"""
from __future__ import annotations

import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "_vendor"))
import hooklib  # noqa: E402

GUARDED_TOOLS = ("Bash", "PowerShell")


def _env_port() -> str:
    for var in ("CLAUDE_PLUGIN_OPTION_SERVICE_PORT", "RAG_PLUGIN_SERVICE_PORT",
                "RAG_SERVICE_PORT"):
        value = os.environ.get(var, "").strip()
        if value.isdigit() and int(value) > 0:
            return value
    return ""


_ENV_PORT = _env_port()
HEALTH_URLS = (
    [f"http://127.0.0.1:{_ENV_PORT}/health"]
    if _ENV_PORT
    else ["http://127.0.0.1:21420/health", "http://127.0.0.1:21421/health"]
)
#: Back-compat alias: some docs refer to the single-URL name.
HEALTH_URL = HEALTH_URLS[0]
HEALTH_TIMEOUT_SECONDS = 1.0

# CLI shapes, matched against the UNQUOTED text of one command segment.
CLI_PATTERNS = [
    re.compile(r"(?<![\w.-])rag(?:\.exe)?\s+(?:index|rebuild|watch)(?:\s|$)"),
    re.compile(r"(?<![\w.-])rag-mcp(?:\.exe)?(?:\s|$)"),
]
# Direct Qdrant access from Python. Matched against the whole segment, but only
# when the segment runs a Python interpreter (the code is usually quoted).
PYTHON_PATTERNS = [
    re.compile(r"QdrantClient\s*\(\s*path\s*="),
    re.compile(r"from\s+qdrant_client\s+import\s+QdrantClient"),
]
#: Back-compat: the full list some docs refer to.
LOCK_CONFLICT_PATTERNS = CLI_PATTERNS + PYTHON_PATTERNS

# Programs whose arguments are text, not commands to run.
_TEXT_PROGRAMS = {
    "echo", "printf", "grep", "egrep", "fgrep", "rg", "ag", "ack", "cat", "less",
    "more", "head", "tail", "sed", "awk", "findstr", "select-string", "sls",
    "write-output", "write-host", "write-verbose", "write-information", "man",
    "help", "type", "which", "where", "get-command", "gcm",
}
_PYTHON_PROGRAMS = re.compile(r"^(?:python(?:\d+(?:\.\d+)?)?|py|pythonw|uv|poetry|pipx)(?:\.exe)?$")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_WRAPPERS = {"sudo", "env", "nohup", "time", "exec", "command", "&", "call", "start"}


def _segments(command: str):
    """Split ``command`` into segments at ; && || | & and newlines that sit
    outside quotes. Yields ``(full_text, unquoted_text)`` per segment, where
    ``unquoted_text`` has quoted strings blanked and comments removed."""
    segs = []
    full, bare = [], []
    quote = ""
    i, n = 0, len(command)
    while i < n:
        ch = command[i]
        if quote:
            full.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < n:
                full.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
            bare.append(" ")
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            full.append(ch)
            bare.append(" ")
            i += 1
            continue
        if ch == "#" and (i == 0 or command[i - 1].isspace()):
            while i < n and command[i] not in "\r\n":
                i += 1
            continue
        if ch in ";|&\r\n":
            segs.append(("".join(full), "".join(bare)))
            full, bare = [], []
            i += 1
            continue
        full.append(ch)
        bare.append(ch)
        i += 1
    segs.append(("".join(full), "".join(bare)))
    return [(f, b) for f, b in segs if b.strip() or f.strip()]


def _program(full: str, bare: str) -> tuple[str, str]:
    """The program a segment runs (lower-case basename) and the segment's
    unquoted text rebuilt as ``<program> <unquoted args>``. The program may be a
    quoted path (PowerShell ``& "C:\\Tools\\rag.exe" index``)."""
    import shlex

    try:
        tokens = shlex.split(full, posix=False)
    except ValueError:
        tokens = full.split()
    words = bare.split()
    while tokens and (_ENV_ASSIGN.match(tokens[0]) or tokens[0].lower() in _WRAPPERS):
        tokens = tokens[1:]
        if words:
            words = words[1:]
    if not tokens:
        return "", ""
    first = tokens[0]
    quoted = first[:1] in ("'", '"')
    prog = re.split(r"[\\/]", first.strip("'\""))[-1].lower()
    if not quoted and words:
        words = words[1:]
    return prog, " ".join([prog] + words)


def matches_lock_conflict(command: str) -> str | None:
    """Return the matched pattern source if a segment that runs matches, else None."""
    if not command or not isinstance(command, str):
        return None
    for full, bare in _segments(command):
        prog, text = _program(full, bare)
        if not prog or prog in _TEXT_PROGRAMS:
            continue
        if prog == "git":
            # git commit -m "...", git log --grep ... : the text is a message.
            continue
        for pattern in CLI_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
        if _PYTHON_PROGRAMS.match(prog):
            for pattern in PYTHON_PATTERNS:
                if pattern.search(full):
                    return pattern.pattern
    return None


def service_is_up() -> bool:
    """True when any candidate /health answers 200 within one second."""
    for url in HEALTH_URLS:
        try:
            with urllib.request.urlopen(url, timeout=HEALTH_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        except Exception:
            continue
    return False


def ask_reason(command: str, matched_pattern: str) -> str:
    base = HEALTH_URL.rsplit("/health", 1)[0]
    return (
        "This command opens Qdrant in direct mode while the ragtools service is up "
        f"at {base}.\n\n"
        "Both processes would compete for the Qdrant single-process file lock, the "
        "most common ragtools failure (F-003 in references/known-failures.md). Stop "
        "the service first (`rag service stop`) or use the HTTP API "
        f"(`curl -X POST {base}/api/rebuild` to rebuild, `/projects rebuild` to "
        "manage projects).\n\n"
        f"matched pattern: {matched_pattern}\n"
        f"command: {hooklib.redact(command[:200])}"
    )


def main() -> int:
    hooklib.watchdog(8.0)
    payload = hooklib.read_payload()
    if payload is None or payload.get("tool_name", "") not in GUARDED_TOOLS:
        return 0
    command = hooklib.tool_input(payload).get("command", "")
    matched = matches_lock_conflict(command) if isinstance(command, str) else None
    if matched is None:
        return 0  # cheap path: no network
    if not service_is_up():
        return 0
    hooklib.ask(ask_reason(command, matched))
    return 0


if __name__ == "__main__":
    hooklib.run(main)
