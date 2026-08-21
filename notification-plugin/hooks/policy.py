#!/usr/bin/env python3
"""notification plugin - configuration and suppression rules.

Answers one question: given this payload, should a notification be sent at all?
Every rule is deterministic and reads only fields the payload already carries.

Config lives at ${CLAUDE_PLUGIN_DATA}/config.json and is entirely optional -
absent means every category is on. ${CLAUDE_PLUGIN_ROOT} is version-pinned and
wiped on every plugin upgrade, so nothing is ever written there.

Hard guarantees:
  - Never raises. A missing, unreadable or malformed config yields DEFAULTS.
  - Read-only. This module never writes; only the doctor command does.
"""

import json
import os

CONFIG_FILENAME = "config.json"

DEFAULTS = {
    "enabled": True,
    "categories": {
        "question": True,
        "permission": True,
        "task": True,
        "turn": True,
        "failure": True,
    },
    "sound": {"attention": True, "informational": False},
    "suppress_teammate_tasks": True,
}


def data_dir():
    """The plugin's persistent directory, which survives plugin upgrades."""
    path = os.environ.get("CLAUDE_PLUGIN_DATA")
    if path:
        return path
    # Only reached when the plugin runs outside a hook context, e.g. a manual
    # invocation for testing.
    return os.path.join(os.path.expanduser("~"), ".claude", "notification")


def config_path():
    return os.path.join(data_dir(), CONFIG_FILENAME)


def _merge(base, override):
    """Shallow-merge one level of nested dicts; ignore keys we do not know."""
    result = dict(base)
    if not isinstance(override, dict):
        return result
    for key, value in override.items():
        if key not in result:
            continue
        if isinstance(result[key], dict) and isinstance(value, dict):
            merged = dict(result[key])
            for inner_key, inner_value in value.items():
                if inner_key in merged:
                    merged[inner_key] = inner_value
            result[key] = merged
        else:
            result[key] = value
    return result


def load():
    """Effective configuration. Any failure returns DEFAULTS unchanged."""
    try:
        with open(config_path(), "r", encoding="utf-8") as handle:
            return _merge(DEFAULTS, json.load(handle))
    except Exception:
        return dict(DEFAULTS)


def suppression_reason(category, payload, config):
    """Return why this event must not notify, or None to proceed.

    The reasons are the deterministic filters from the architecture decisions:
      D-007  subagent and teammate events are not signals for the human
      D-008  a turn that ends with background work still in flight is not "done"
    """
    try:
        if not config.get("enabled", True):
            return "notifications disabled in config"

        categories = config.get("categories") or {}
        if not categories.get(category, True):
            return "category '{0}' disabled in config".format(category)

        # D-007 - these fields are present only inside a subagent / --agent run.
        if payload.get("agent_id"):
            return "event came from a subagent"

        if category == "task":
            if config.get("suppress_teammate_tasks", True) and payload.get("teammate_name"):
                return "task was completed by a teammate"

        if category == "turn":
            # D-008 - Claude Code populates these when the task registry is
            # reachable; non-empty means the session will wake itself back up.
            if payload.get("background_tasks"):
                return "background tasks still in flight"
            if payload.get("session_crons"):
                return "scheduled wakeups still pending"
            if payload.get("stop_hook_active"):
                return "another Stop hook is driving the turn"

        return None
    except Exception:
        # A broken policy must never silently start notifying; stay quiet.
        return "policy evaluation failed"


def wants_sound(klass, config):
    try:
        return bool((config.get("sound") or {}).get(klass, False))
    except Exception:
        return False
