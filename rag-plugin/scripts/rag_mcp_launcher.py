#!/usr/bin/env python3
"""Resolve and exec the canonical ragtools MCP stdio entrypoint.

Why this launcher exists:
  Plugin-level .mcp.json has to pick one command, but the canonical command
  differs across install modes (packaged Windows ships `rag.exe`, dev pip
  installs ship `rag-mcp`, macOS tarball installs ship `rag` on a PATH the
  user adds manually). Hardcoding either name breaks the other.

Resolution order:
  1. GET http://127.0.0.1:21420/api/mcp-config (1s timeout) — the running
     service is the authoritative source of truth for this install mode.
  2. `rag` on PATH → exec `rag serve`  (packaged binary installs).
  3. `rag-mcp` on PATH → exec `rag-mcp`  (dev pip installs).
  4. Fail loudly to stderr so Claude Code surfaces it in /mcp.

This is a stdio MCP server, so the launcher must exec-replace itself with
the real binary. No subprocess wrapping — Claude Code pipes stdin/stdout
directly into the child.
"""

import json
import os
import shutil
import sys
import urllib.error
import urllib.request

SERVICE_CONFIG_URL = "http://127.0.0.1:21420/api/mcp-config"
SERVICE_TIMEOUT_SEC = 1.0


def _log(msg: str) -> None:
    sys.stderr.write(f"[rag-mcp-launcher] {msg}\n")
    sys.stderr.flush()


def _from_service() -> tuple[str, list[str]] | None:
    """Ask the running ragtools service for the canonical command.

    Returns (command, args) on success, None on any failure (service down,
    malformed response, network error, timeout).
    """
    try:
        with urllib.request.urlopen(SERVICE_CONFIG_URL, timeout=SERVICE_TIMEOUT_SEC) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    try:
        entry = payload["config"]["mcpServers"]["ragtools"]
        command = entry["command"]
        args = list(entry.get("args", []))
    except (KeyError, TypeError):
        return None

    if not isinstance(command, str) or not command:
        return None
    return command, args


def _from_path() -> tuple[str, list[str]] | None:
    """Probe PATH for a ragtools binary, in preferred order."""
    rag = shutil.which("rag")
    if rag:
        return rag, ["serve"]
    rag_mcp = shutil.which("rag-mcp")
    if rag_mcp:
        return rag_mcp, []
    return None


def resolve() -> tuple[str, list[str]]:
    """Return (command, args) or exit non-zero with a clear message."""
    for source_name, source in (("service", _from_service), ("path", _from_path)):
        resolved = source()
        if resolved is not None:
            command, args = resolved
            _log(f"resolved via {source_name}: {command} {' '.join(args)}".rstrip())
            return command, args

    _log(
        "ragtools not found. Tried GET "
        f"{SERVICE_CONFIG_URL} (service down or unreachable) and PATH probes "
        "for `rag` and `rag-mcp` (neither on PATH). Install ragtools or run /rag-setup."
    )
    sys.exit(127)


def main() -> None:
    command, args = resolve()

    if "--dry-run" in sys.argv[1:]:
        print(json.dumps({"command": command, "args": args}))
        return

    try:
        os.execvp(command, [command, *args])
    except OSError as exc:
        _log(f"exec failed for {command}: {exc}")
        sys.exit(127)


if __name__ == "__main__":
    main()
