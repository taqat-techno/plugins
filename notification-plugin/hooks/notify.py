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
import subprocess
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


def read_raw(stream=None):
    """The payload's raw bytes, or b"" on any failure."""
    stream = sys.stdin if stream is None else stream
    try:
        buffer = getattr(stream, "buffer", None)
        raw = buffer.read() if buffer is not None else stream.read()
    except Exception:
        return b""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", errors="replace")
    return raw or b""


def parse_payload(raw):
    """Parse payload bytes as UTF-8 JSON. Any failure yields an empty dict, never a raise.

    Claude Code writes UTF-8, but on Windows Python decodes a PIPED stdin with the
    ANSI code page (cp1252, surrogateescape). Every non-ASCII question - Arabic,
    emoji, box-drawing previews - then arrives as mojibake or lone surrogates,
    which no backend can deliver. Decoding the raw bytes explicitly is the only
    path that does not depend on the machine's locale.
    """
    try:
        text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
    except Exception:
        return {}
    if not text:
        return {}
    try:
        data = json.loads(text.lstrip("﻿"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_payload(stream=None):
    """Read and parse the hook payload from `stream` (stdin by default)."""
    return parse_payload(read_raw(stream))


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
        title_only=policy.title_only(config),
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
    """Hook mode. Silent on every path, including success.

    Each event is registered once per interpreter name (D-016); only the first
    process to claim it delivers.
    """
    raw = read_raw()
    if not state.claim(category, raw):
        return
    state.record_run(category)
    deliver(category, parse_payload(raw), policy.load())


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
    print("  content   {0}".format(
        "title only - no question, message or error text on screen" if policy.title_only(config)
        else "full - bodies show up to {0} characters of payload text (secrets masked)".format(
            render.BODY_LIMIT)))


# The names hooks.json launches, in order (D-016). `py` is called as `py -3`.
HOOK_INTERPRETERS = ("python3", "python", "py")


def probe_interpreter(path, name):
    """Run the interpreter the way the hooks would. Returns "" when it is usable,
    otherwise why not. Only the doctor calls this; hooks never probe."""
    argv = [path] + (["-3"] if name == "py" else []) + [
        "-c", "import sys; print('%d.%d' % sys.version_info[:2]); sys.exit(0 if sys.version_info >= (3, 8) else 3)"]
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                timeout=15, shell=False)
    except Exception as exc:
        return "does not start ({0})".format(exc.__class__.__name__)
    if result.returncode == 0:
        return ""
    if result.returncode == 3:
        return "Python {0} is older than 3.8".format(result.stdout.strip())
    if result.returncode in (9009, 49):
        return "starts no Python (Microsoft Store alias without Store Python installed)"
    return "exits {0} instead of running Python".format(result.returncode)


def hook_interpreters(probe=None):
    """[(name, path or None, problem)] for every interpreter name the hooks try."""
    import shutil
    probe = probe or probe_interpreter
    rows = []
    for name in HOOK_INTERPRETERS:
        path = shutil.which(name)
        rows.append((name, path, probe(path, name) if path else ""))
    return rows


def _print_interpreters():
    import datetime
    print("Hook interpreters (each event is registered for all three; the first that")
    print("starts handles it)")
    usable = False
    for name, path, note in hook_interpreters():
        launcher = "py -3" if name == "py" else name
        print("  {0:<8}  {1}{2}".format(launcher, path or "not on PATH",
                                       " - " + note if note else ""))
        usable = usable or (path is not None and not note)
    last = state.last_run()
    if last:
        when = datetime.datetime.fromtimestamp(last.get("time", 0)).strftime("%Y-%m-%d %H:%M:%S")
        print("  last run  {0} ({1}) handled '{2}' at {3}".format(
            last.get("python"), last.get("version"), last.get("verb"), when))
    else:
        print("  last run  none recorded yet - no hook has run since install or since")
        print("            the data directory was reset")
    if not usable:
        print("  WARNING   no usable interpreter found: every notification hook fails")
        print("            silently. Install Python 3.8+ (python.org, not the Store alias)")
        print("            so that python3, python or py is on PATH, then restart Claude Code.")


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
        info["title_only"] = policy.title_only(config)
        info["hook_interpreters"] = [
            {"name": name, "path": path, "note": note} for name, path, note in hook_interpreters()]
        info["last_hook_run"] = state.last_run()
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
    _print_interpreters()
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


WINDOWS_IDENTITY_KEY = r"Software\Classes\AppUserModelId\TaqaTechno.ClaudeCode.Notifications"


def uninstall_windows_identity(winreg_module=None):
    """Remove the HKCU app identity win_toast.ps1 registers (D-014). Returns a message."""
    try:
        if winreg_module is None:
            if os.name != "nt":
                return "nothing to do: the app identity exists only on Windows"
            import winreg as winreg_module
        winreg_module.DeleteKey(winreg_module.HKEY_CURRENT_USER, WINDOWS_IDENTITY_KEY)
        return "removed HKCU\\" + WINDOWS_IDENTITY_KEY
    except FileNotFoundError:
        return "nothing to do: HKCU\\" + WINDOWS_IDENTITY_KEY + " does not exist"
    except Exception as exc:
        return "failed: {0}".format(exc)


def main():
    args = sys.argv[1:]
    if not args:
        return
    if args[0].startswith("--"):
        # Doctor mode. The flags may arrive in any order after --doctor, because
        # /notification:doctor passes its arguments straight through.
        if "--uninstall-windows-identity" in args:
            print(uninstall_windows_identity())
        elif "--write-config" in args:
            print(write_default_config())
        elif "--doctor" in args:
            run_doctor(send_tests="--no-test" not in args, as_json="--json" in args)
        return
    run_hook(args[0])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # D-001/D-002: a notifier must never disturb the session it observes.
        pass
    sys.exit(0)
