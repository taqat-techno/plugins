#!/usr/bin/env python3
"""Hooks that connect the env-doctor mechanic (hooks/mechanic.py) to the agent.

Three modes, all fail-open (any error exits 0 with no output):

  start   PostToolUse, asyncRewake. Runs when the agent starts a local service (a Bash or
          PowerShell command matching the `if` filters in hooks.json, or the odoo-local
          start / restart / relaunch tools). Registers this session as a driver, starts the
          watcher if none is running, then listens like `listen`.
  listen  PostToolUse, asyncRewake. Waits in the background (at most LISTEN_MAX) for a
          finding this session has not had. On one, it prints it to stderr and exits 2,
          which wakes the agent with it as a system reminder. One listener per session;
          the next tool call re-arms it. The shell gate in hooks.json skips Python
          entirely unless the watcher is active.
  prompt  UserPromptSubmit. Hands any finding the listener has not delivered (for example
          one that came while the agent was idle) to the agent as additionalContext.

Only sessions that started a service get findings. Silence with ENV_DOCTOR_MECHANIC=off
or the `mechanic` plugin option.
"""
from __future__ import annotations

import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "_vendor"))
sys.path.insert(0, HERE)
import hooklib  # noqa: E402
import mechanic  # noqa: E402

LISTEN_MAX = 3 * 3600
POLL = 5.0
# Commands that only read or search; a service word inside them is not a service start.
_READ_ONLY = re.compile(r"^\s*(?:grep|rg|cat|ls|which|where|ps|head|tail|less|more|find|echo|git|type|"
                        r"Get-Content|Select-String|Get-ChildItem|Get-Process)\b", re.I)
_SERVICE = re.compile(r"odoo-bin|runserver|\brun\s+dev\b|compose\s+up|\buvicorn\b|\bgunicorn\b|systemd-run", re.I)


def starts_service(payload) -> bool:
    tool = str(payload.get("tool_name") or "")
    if tool.startswith("mcp__"):
        return bool(re.search(r"local_(?:start|restart|relaunch)$", tool))
    command = str(hooklib.tool_input(payload).get("command") or "")
    return bool(_SERVICE.search(command)) and not _READ_ONLY.match(command)


def _say(text: str) -> None:
    data = text.encode("utf-8", "replace")
    try:
        sys.stderr.buffer.write(data)
    except AttributeError:
        sys.stderr.write(text)
    sys.stderr.flush()


def listen(sd, sid, env=os.environ, max_wait=LISTEN_MAX, poll=POLL) -> int:
    if mechanic.armed(sd, sid):
        return 0
    beat = os.path.join(sd, "sessions", sid + ".listen")
    started = time.time()
    try:
        while time.time() - started < max_wait:
            mechanic._touch(beat, str(os.getpid()))
            if mechanic.silenced(env):
                return 0
            if not mechanic.daemon_alive(sd, env=env) and time.time() - started > 3 * mechanic.interval(env) + 15:
                return 0
            fresh = [f for f in mechanic.pending(sd, sid) if mechanic.claim(sd, sid, f["id"])]
            if fresh:
                mechanic.seen(sd, sid)
                _say(mechanic.message(fresh))
                return 2
            time.sleep(poll)
    finally:
        mechanic._rm(beat)
    return 0


def main(mode: str) -> int:
    env = os.environ
    if mechanic.silenced(env):
        return 0
    payload = hooklib.read_payload()
    if payload is None:
        return 0
    sid = mechanic.safe_id(payload.get("session_id"))
    if not sid:
        return 0
    sd = mechanic.state_dir(env)

    if mode == "start":
        if not starts_service(payload):
            return 0
        mechanic.register(sd, sid)
        if not mechanic.ensure_daemon(env):
            return 0
        return listen(sd, sid, env)

    if mechanic.registered_at(sd, sid) is None:
        return 0
    if not mechanic.daemon_alive(sd, env=env):
        age = mechanic._age(os.path.join(sd, "daemon.beat"))
        if age is None or age > 3 * mechanic.interval(env) + 60:
            mechanic._rm(os.path.join(sd, "active"))  # a killed watcher left its marker behind
        return 0
    mechanic.seen(sd, sid)

    if mode == "listen":
        return listen(sd, sid, env)
    if mode == "prompt":
        fresh = [f for f in mechanic.pending(sd, sid) if mechanic.claim(sd, sid, f["id"])]
        if fresh:
            hooklib.context("UserPromptSubmit", mechanic.message(fresh))
        return 0
    return 0


if __name__ == "__main__":
    _mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if _mode == "prompt":
        hooklib.watchdog(4)
    hooklib.run(lambda: main(_mode))
