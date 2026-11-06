#!/usr/bin/env python3
"""odoo-local MCP server - stdio, standard library only.

The second MCP server of the odoo plugin. The first (mcp/server.py, "odoo") is pure
data access to instances in ~/.odoo-mcp/profiles.json and never starts processes.
This one manages LOCAL services only (~/.odoo-mcp/local-services.json): start, stop,
logs, module jobs, local databases, cleanup plans. See mcp_local/README.md.

Protocol: newline-delimited JSON-RPC 2.0 (MCP stdio transport). stdout carries
protocol messages only; diagnostics go to stderr.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import local_tools as tools  # noqa: E402

SERVER_NAME = "odoo-local"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
PREFERRED_PROTOCOL = "2025-06-18"
INSTRUCTIONS = (
    "Local Odoo services only (loopback processes and Postgres clusters registered in "
    "~/.odoo-mcp/local-services.json). Run local_discover first. Start/stop/restart/status/logs/"
    "module jobs need no confirmation. Long work (module install/upgrade, DB create/clone) returns a "
    "job id: continue other work and call local_job later instead of waiting. Cleanup is plan-first: "
    "show the local_cleanup_plan output to the user, then local_cleanup_apply with its plan_id. "
    "Never use these tools for stage or production; record data goes through the 'odoo' server."
)


def log(msg):
    print("[odoo-local] %s" % msg, file=sys.stderr, flush=True)


def send(msg):
    line = json.dumps(msg, ensure_ascii=False, default=str).replace("\r", "").replace("\n", " ")
    try:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except BrokenPipeError:
        raise SystemExit(0)


def handle(msg):
    method, req_id, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    note = "id" not in msg
    if not isinstance(method, str):
        if not note:
            send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "missing method"}})
        return
    if method == "initialize":
        wanted = params.get("protocolVersion")
        send({"jsonrpc": "2.0", "id": req_id, "result": {
            "protocolVersion": wanted if wanted in SUPPORTED_PROTOCOLS else PREFERRED_PROTOCOL,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": INSTRUCTIONS}})
        return
    if method in ("notifications/initialized", "initialized", "notifications/cancelled"):
        return
    if method == "ping":
        send({"jsonrpc": "2.0", "id": req_id, "result": {}})
        return
    if method in ("shutdown", "exit"):
        if not note:
            send({"jsonrpc": "2.0", "id": req_id, "result": {}})
        raise SystemExit(0)
    if method == "tools/list":
        send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools.TOOLS}})
        return
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if not isinstance(name, str) or not isinstance(args, dict):
            send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "bad tools/call params"}})
            return
        text, is_error = tools.dispatch(name, args)
        send({"jsonrpc": "2.0", "id": req_id,
              "result": {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}})
        return
    if method in ("resources/list", "resources/templates/list", "prompts/list"):
        key = {"resources/list": "resources", "resources/templates/list": "resourceTemplates",
               "prompts/list": "prompts"}[method]
        send({"jsonrpc": "2.0", "id": req_id, "result": {key: []}})
        return
    if not note:
        send({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "method not found: %s" % method}})


def main():
    for stream in (sys.stdout, sys.stdin, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", newline="\n" if stream is sys.stdout else None)
        except (AttributeError, TypeError):
            pass
    log("started (pid %d)" % os.getpid())
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except ValueError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "invalid JSON"}})
            continue
        for m in (msg if isinstance(msg, list) else [msg]):
            if not isinstance(m, dict):
                continue
            try:
                handle(m)
            except SystemExit:
                raise
            except Exception as exc:
                log(traceback.format_exc())
                if "id" in m:
                    send({"jsonrpc": "2.0", "id": m.get("id"),
                          "error": {"code": -32603, "message": "%s: %s" % (type(exc).__name__, exc)}})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
