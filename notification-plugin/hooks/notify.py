#!/usr/bin/env python3
"""notification plugin - the single hook entry point.

Reads one Claude Code hook payload from stdin and, if policy allows, hands a
title/body to the platform's native notifier. Seven registrations route here,
all with `async: true`, all with the verb as the first argument:

    notify.py question     PreToolUse        matcher AskUserQuestion
    notify.py answered     PostToolUse       matcher AskUserQuestion   never notifies
    notify.py prompted     UserPromptSubmit                            never notifies
    notify.py permission   Notification      matcher permission_prompt
    notify.py task         TaskCompleted
    notify.py turn         Stop
    notify.py failure      StopFailure

Waiting-for-you notifications stay on screen until closed (D-015). They never
replace each other, and the plugin withdraws them only when the user acts:
`answered` removes the answered question, and `prompted` removes the session's
waiting toasts when the user types again.

One question, one notification (D-013): Claude Code presents AskUserQuestion
through its permission-prompt path, so every question also raises a generic
permission_prompt a few seconds later. `question` leaves a short-lived marker,
`permission` is suppressed while it stands, and `answered`, `turn` and `failure`
clear it.

Hard guarantees (see docs/decisions.md):
  D-001  Every hook is async, so this script structurally cannot block Claude.
         Five of the seven events are blocking events where exit 2 would
         suppress a question, feed an error back to Claude, block and erase the
         user's prompt, trap a turn, or refuse a task completion.
  D-002  In hook mode this script writes NOTHING to stdout. Before Claude Code
         v2.1.202 malformed async JSON could crash the session and re-crash it
         on resume; emitting nothing is safe on every version.
  D-003  No shell, ever. Backends are argument vectors run with shell=False.
  D-006  No model, prompt, agent or transcript read on any runtime path.
  Exit code is ALWAYS 0.

Stdlib only. Python 3.8+. Windows, macOS, Linux.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import backends      # noqa: E402
import identity      # noqa: E402
import policy        # noqa: E402
import render        # noqa: E402
import state         # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def read_payload(stream=None):
    """Parse the hook payload as UTF-8. Any failure yields an empty dict, never a raise.

    Claude Code writes UTF-8, but on Windows Python decodes a PIPED stdin with the
    ANSI code page (cp1252, surrogateescape). Every non-ASCII question - Arabic,
    emoji, box-drawing previews - then arrives as mojibake or lone surrogates,
    which no backend can deliver. Decoding the raw bytes explicitly is the only
    path that does not depend on the machine's locale.
    """
    stream = sys.stdin if stream is None else stream
    try:
        buffer = getattr(stream, "buffer", None)
        raw = buffer.read() if buffer is not None else stream.read()
    except Exception:
        return {}
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not raw:
        return {}
    try:
        data = json.loads(raw.lstrip("﻿"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def deliver(category, payload, config):
    """Render and send one notification. Returns a short outcome string."""
    session = payload.get("session_id")

    if category == state.ANSWERED:
        return _answered(payload, config)
    if category == state.PROMPTED:
        return _prompted(payload, config)

    # A turn that ended - normally or on an error - closes any open question.
    if category in ("turn", "failure"):
        state.clear_question(session)

    reason = policy.suppression_reason(category, payload, config)
    if reason:
        return "suppressed: " + reason

    built = render.build(
        category, payload,
        project=identity.project_name(payload.get("cwd")),
        tag=identity.session_tag(session),
    )
    if built is None:
        return "suppressed: nothing to say"

    klass, title, body, attribution = built

    if category == "question":
        # Marked before sending: the permission_prompt this question raises
        # arrives a few seconds later and must find the marker already there.
        state.mark_question(session)

    sent = backends.send(
        title=title,
        body=body,
        attribution=attribution,
        attention=klass == render.ATTENTION,
        persistent=policy.wants_persistent(category, config),
        silent=not policy.wants_sound(klass, config),
        key=identity.group_key(payload, category),
    )
    return "sent" if sent else "no backend"


def _answered(payload, config):
    """PostToolUse(AskUserQuestion): the question is closed. Never notifies."""
    if payload.get("agent_id"):
        return "ignored: event came from a subagent"
    state.clear_question(payload.get("session_id"))
    categories = config.get("categories") or {}
    if config.get("enabled", True) and categories.get("question", True):
        # An answered question should not linger in Notification Center.
        backends.remove([identity.group_key(payload, "question")])
    return "cleared"


# Every notification that can still be on screen when the user types again.
_WAITING_CATEGORIES = ("question", "permission", "turn", "failure")


def _prompted(payload, config):
    """UserPromptSubmit: the user is back at the terminal. Never notifies.

    Waiting-for-you notifications stay until closed, so without this they would
    remain on screen after the user has already replied in the terminal. It also
    closes a question dismissed with Esc, where PostToolUse never fires.
    """
    if payload.get("agent_id"):
        return "ignored: event came from a subagent"
    state.clear_question(payload.get("session_id"))
    if config.get("enabled", True):
        backends.remove([identity.group_key(payload, name) for name in _WAITING_CATEGORIES])
    return "cleared"


def run_hook(category):
    """Hook mode. Silent on every path, including success."""
    payload = read_payload()
    deliver(category, payload, policy.load())


# --------------------------------------------------------------------------
# doctor - runs only from /notification:doctor, never from a hook
# --------------------------------------------------------------------------

_SETUP_HINTS = {
    backends.MACOS: (
        "macOS: notifications route through Script Editor, and the command fails\n"
        "  SILENTLY if it lacks permission. Run this once in Terminal:\n"
        "      osascript -e 'display notification \"test\"'\n"
        "  then open System Settings > Notifications, find Script Editor, and turn\n"
        "  on Allow Notifications. Set its style to Alerts if you want attention\n"
        "  notifications to wait for you instead of auto-dismissing."
    ),
    backends.LINUX: (
        "Linux: notifications need libnotify and a running notification daemon.\n"
        "  If notify-send is missing:  sudo apt install libnotify-bin"
    ),
    backends.WINDOWS: (
        "Windows: toasts appear under \"Claude Code\", an app identity registered\n"
        "  per user (HKCU, no admin) on first use. They respect Focus Assist / Do\n"
        "  Not Disturb. If nothing appears, check Settings > System > Notifications\n"
        "  and confirm Claude Code - or Windows PowerShell, the fallback identity -\n"
        "  is allowed to send notifications."
    ),
}

_UNSUPPORTED_HINTS = {
    backends.UNSUPPORTED_WSL: (
        "WSL detected. Desktop notifications are not supported in v1 and every\n"
        "  event is skipped silently - Claude is completely unaffected. A\n"
        "  WSL-to-Windows-host adapter is planned."
    ),
    backends.UNSUPPORTED_SSH: (
        "SSH session detected. There is no local desktop to notify, so every\n"
        "  event is skipped silently."
    ),
    backends.UNSUPPORTED_HEADLESS: (
        "No DISPLAY or WAYLAND_DISPLAY. This looks like a headless host, so every\n"
        "  event is skipped silently."
    ),
    backends.UNSUPPORTED_MISSING: (
        "No usable notifier was found on this system. Every event is skipped\n"
        "  silently. See the platform note above."
    ),
}

_DOCTOR_SESSION = "doctor-test"

_TEST_PAYLOADS = [
    ("question", {"tool_input": {"questions": [
        {"header": "Test", "question": "Notification test - can you see this attention toast?"}]}}),
    ("task", {"task_subject": "Notification test - this one disappears on its own"}),
]


def plugin_version():
    try:
        manifest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                ".claude-plugin", "plugin.json")
        with open(manifest, "r", encoding="utf-8") as handle:
            return json.load(handle).get("version") or "?"
    except Exception:
        return "?"


def _print_config(config):
    print("Configuration")
    print("  file      {0}".format(policy.config_path()))
    exists = os.path.isfile(policy.config_path())
    print("  status    {0}".format("present" if exists else "absent (built-in defaults in use)"))
    categories = config.get("categories") or {}
    enabled = [name for name in render.CATEGORIES if categories.get(name, True)]
    disabled = [name for name in render.CATEGORIES if not categories.get(name, True)]
    print("  enabled   {0}".format(", ".join(enabled) or "none"))
    if disabled:
        print("  disabled  {0}".format(", ".join(disabled)))
    sound = config.get("sound") or {}
    print("  sound     attention={0} informational={1}".format(
        bool(sound.get("attention")), bool(sound.get("informational"))))
    persistent = config.get("persistent") or {}
    print("  persist   {0}".format(
        ", ".join(name for name in render.CATEGORIES if persistent.get(name)) or "none"))


def _print_tasks():
    print("Task notifications")
    opted_in = os.environ.get("CLAUDE_CODE_ENABLE_TODO_TOOLS") == "1"
    print("  CLAUDE_CODE_ENABLE_TODO_TOOLS={0}".format(
        os.environ.get("CLAUDE_CODE_ENABLE_TODO_TOOLS") or "(unset)"))
    if not opted_in:
        print("  Since Claude Code v2.1.233 the Task tools (TaskCreate / TaskUpdate /")
        print("  TaskList / TodoWrite) are NOT provided on Opus 4.8, Sonnet 5, Fable 5,")
        print("  Mythos 5 or later families unless you opt in. Without them the task")
        print("  list stays empty, so the TaskCompleted event never fires and")
        print("  '☑️ ... finished a task' will never appear. To enable it:")
        print("      CLAUDE_CODE_ENABLE_TODO_TOOLS=1 claude")
        print("  On older families such as Opus 4.7 the Task tools are on by default.")


def write_default_config():
    try:
        os.makedirs(policy.data_dir(), exist_ok=True)
        path = policy.config_path()
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(policy.DEFAULTS, handle, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
        return path
    except Exception as exc:
        return "failed: {0}".format(exc)


def run_doctor(send_tests=True, as_json=False):
    info = backends.describe()
    config = policy.load()

    if as_json:
        info["version"] = plugin_version()
        info["config"] = config
        info["config_path"] = policy.config_path()
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return

    print("notification v{0} - capability report".format(plugin_version()))
    print("")
    print("Environment")
    print("  system    {0} {1}".format(info["system"], info["release"]))
    print("  python    {0} ({1})".format(info["python_version"], info["python"]))
    print("  wsl       {0}".format(info["wsl"]))
    print("  ssh       {0}".format(info["ssh"]))
    print("  backend   {0}".format(info["backend"]))
    print("  resolved  {0}".format(info["detail"]))
    print("  plugin    {0}".format(os.environ.get("CLAUDE_PLUGIN_ROOT") or "(not running as a hook)"))
    print("")
    _print_config(config)
    print("")
    _print_tasks()
    print("")

    backend_name = info["backend"]
    if backend_name == "unsupported":
        print("Notifications are DISABLED on this host.")
        hint = _UNSUPPORTED_HINTS.get(info["detail"])
        if hint:
            print("  " + hint)
        print("")
        print("  This is a supported outcome, not an error: every hook exits 0 and")
        print("  Claude behaves exactly as it would without the plugin installed.")
        return

    hint = _SETUP_HINTS.get(backend_name)
    if hint:
        print("Platform notes")
        print("  " + hint)
        print("")

    if not send_tests:
        return

    print("Test notifications")
    for category, payload in _TEST_PAYLOADS:
        payload = dict(payload)
        payload.setdefault("cwd", os.getcwd())
        payload.setdefault("session_id", _DOCTOR_SESSION)
        outcome = deliver(category, payload, config)
        print("  {0:<11} {1}".format(category, outcome))
    state.clear_question(_DOCTOR_SESSION)
    print("")
    print("  Two notifications should have appeared: a question that stays on screen")
    print("  until you close it, and a task completion that disappears on its own.")
    print("  If nothing appeared, re-read the platform notes above.")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--doctor":
        run_doctor(send_tests="--no-test" not in args, as_json="--json" in args)
        return
    if args and args[0] == "--write-config":
        print(write_default_config())
        return
    if not args:
        return
    run_hook(args[0])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # D-001/D-002: a notifier must never disturb the session it observes.
        pass
    sys.exit(0)
