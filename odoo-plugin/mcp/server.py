#!/usr/bin/env python3
"""Odoo MCP server - stdio transport, standard library only.

Bundled with odoo-plugin. No pip install, no npm, no uv: if `python` runs, this
runs. That is deliberate - a plugin distributed to a team cannot assume any
particular package manager is present.

Protocol: newline-delimited JSON-RPC 2.0 on stdin/stdout, per the MCP stdio
transport. We implement the `initialize` handshake used by current clients. The
newer `server/discover` probe is answered with "method not found", which the
specification's own backward-compatibility rule tells a modern client to treat
as a legacy server and fall back to `initialize` - so both client generations
work.

Two rules this file must never break:
  1. stdout carries protocol messages only. Every diagnostic goes to stderr.
  2. one message per line, no embedded newlines.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tools  # noqa: E402
from tools import Session  # noqa: E402

SERVER_NAME = "odoo"
SERVER_VERSION = "1.0.0"

# Revisions this server is happy to speak. We echo the client's choice when we
# know it, otherwise we answer with PREFERRED and let the client decide.
SUPPORTED_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
PREFERRED_PROTOCOL = "2025-06-18"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def log(msg: str) -> None:
    print("[odoo-mcp] %s" % msg, file=sys.stderr, flush=True)


def _setup_streams():
    """UTF-8 both ways, and stop Windows translating \\n into \\r\\n on stdout,
    which would corrupt the newline framing."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:  # pragma: no cover - Python < 3.7
        pass


def send(msg: dict) -> None:
    try:
        line = json.dumps(msg, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        line = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": msg.get("id"),
                "error": {"code": INTERNAL_ERROR, "message": "result was not serialisable"},
            }
        )
    # Defensive: a stray newline would split one message into two frames.
    line = line.replace("\r", "").replace("\n", " ")
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        raise SystemExit(0)


def reply(req_id, result) -> None:
    send({"jsonrpc": "2.0", "id": req_id, "result": result})


def fail(req_id, code: int, message: str) -> None:
    send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def handle(session: Session, msg: dict) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}
    is_notification = "id" not in msg

    if not isinstance(method, str):
        if not is_notification:
            fail(req_id, INVALID_REQUEST, "missing or invalid 'method'")
        return

    # ---- lifecycle ----
    if method == "initialize":
        wanted = params.get("protocolVersion")
        negotiated = wanted if wanted in SUPPORTED_PROTOCOLS else PREFERRED_PROTOCOL
        client = (params.get("clientInfo") or {}).get("name", "unknown")
        log("initialize from %s (requested %s, using %s)" % (client, wanted, negotiated))
        reply(
            req_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
        return

    if method in ("notifications/initialized", "initialized", "notifications/cancelled"):
        return  # notifications carry no response

    if method == "ping":
        reply(req_id, {})
        return

    if method in ("shutdown", "exit"):
        if not is_notification:
            reply(req_id, {})
        raise SystemExit(0)

    # ---- tools ----
    if method == "tools/list":
        reply(req_id, {"tools": tools.TOOLS})
        return

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if not isinstance(name, str):
            fail(req_id, INVALID_PARAMS, "tools/call requires a string 'name'")
            return
        if not isinstance(args, dict):
            fail(req_id, INVALID_PARAMS, "'arguments' must be an object")
            return
        text, is_error = tools.dispatch(session, name, args)
        reply(
            req_id,
            {"content": [{"type": "text", "text": text}], "isError": bool(is_error)},
        )
        return

    # Empty lists rather than errors: some clients probe these regardless of
    # advertised capabilities, and an error shows up as a scary red line.
    if method == "resources/list":
        reply(req_id, {"resources": []})
        return
    if method == "resources/templates/list":
        reply(req_id, {"resourceTemplates": []})
        return
    if method == "prompts/list":
        reply(req_id, {"prompts": []})
        return

    if not is_notification:
        # Includes server/discover: answering "method not found" is exactly what
        # tells a 2026-07-28 client to fall back to the initialize handshake.
        fail(req_id, METHOD_NOT_FOUND, "method not found: %s" % method)


def main() -> int:
    _setup_streams()
    session = Session()
    log("started (pid %d, python %s)" % (os.getpid(), sys.version.split()[0]))

    try:
        prof, err = session.load()
        if err:
            log("configuration problem: %s" % err.splitlines()[0])
        elif prof is not None and getattr(prof, "configured", False):
            log("profile %r -> %s [%s]" % (prof.name, prof.url, prof.mode))
        else:
            log("no connection profile found yet; call odoo_status for setup help")
    except Exception as exc:  # never prevent startup
        log("profile resolution failed: %s" % exc)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            fail(None, PARSE_ERROR, "invalid JSON")
            continue

        if isinstance(msg, list):
            # Batching was removed from MCP in 2025-06-18; be lenient anyway.
            for item in msg:
                if isinstance(item, dict):
                    _guarded(session, item)
            continue
        if not isinstance(msg, dict):
            fail(None, INVALID_REQUEST, "expected a JSON-RPC object")
            continue
        _guarded(session, msg)

    log("stdin closed, exiting")
    return 0


def _guarded(session: Session, msg: dict) -> None:
    """A failure in one message must never take down the server."""
    try:
        handle(session, msg)
    except SystemExit:
        raise
    except Exception as exc:
        log("unhandled error on %s: %s" % (msg.get("method"), exc))
        log(traceback.format_exc())
        if "id" in msg:
            fail(msg.get("id"), INTERNAL_ERROR, "%s: %s" % (type(exc).__name__, exc))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
