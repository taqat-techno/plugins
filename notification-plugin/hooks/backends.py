#!/usr/bin/env python3
"""notification plugin - platform detection and native delivery.

One backend per desktop. Each `send` builds an ARGUMENT VECTOR and runs it with
shell=False, so notification text - which is untrusted input from a question, a
task subject or an API error - can never be interpreted as a command. On Windows
the text does not even reach the command line: it travels in environment
variables that the bundled PowerShell script reads.

Hosts with no desktop notifier (WSL, headless Linux, SSH, a machine without
libnotify) resolve to None and the caller exits silently. That is a supported
outcome, not an error.

Hard guarantees:
  - Never raises. Every entry point returns a value or False.
  - Bounded: every subprocess runs under a hard timeout.
  - Notifications never replace each other: every toast gets a unique tag,
    and nothing is written to disk by a backend. On Windows the toast script keeps one
    per-user app identity ("Claude Code") registered under HKCU (D-014).
"""

import os
import platform
import shutil
import subprocess
import sys

SEND_TIMEOUT = 8

WINDOWS = "windows"
MACOS = "macos"
LINUX = "linux"

UNSUPPORTED_WSL = "wsl"
UNSUPPORTED_SSH = "ssh"
UNSUPPORTED_HEADLESS = "headless"
UNSUPPORTED_MISSING = "missing-notifier"

_CREATE_NO_WINDOW = 0x08000000


# --------------------------------------------------------------------------
# detection
# --------------------------------------------------------------------------

def is_wsl():
    """True inside any WSL distribution.

    WSL2 with WSLg exposes a display but usually has no notification daemon, so
    notify-send there fails or silently no-ops - the worst outcome, because it
    looks like it worked. Detecting it turns a silent lie into a documented skip.
    """
    try:
        if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
            return True
        if os.path.exists("/mnt/wslg"):
            return True
        for probe in ("/proc/sys/kernel/osrelease", "/proc/version"):
            try:
                with open(probe, "r", encoding="utf-8", errors="replace") as handle:
                    if "microsoft" in handle.read().lower():
                        return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def is_ssh():
    try:
        return bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))
    except Exception:
        return False


def _powershell():
    """Windows PowerShell 5.1 - NOT pwsh, which cannot load WinRT types."""
    found = shutil.which("powershell.exe") or shutil.which("powershell")
    if found:
        return found
    fallback = os.path.join(
        os.environ.get("SystemRoot", r"C:\Windows"),
        "System32", "WindowsPowerShell", "v1.0", "powershell.exe",
    )
    return fallback if os.path.isfile(fallback) else None


def detect():
    """Return (backend_name, detail). backend_name is None when unsupported."""
    try:
        if is_wsl():
            return None, UNSUPPORTED_WSL
        if is_ssh():
            return None, UNSUPPORTED_SSH

        system = platform.system()

        if system == "Windows":
            shell = _powershell()
            if not shell:
                return None, UNSUPPORTED_MISSING
            return WINDOWS, shell

        if system == "Darwin":
            found = shutil.which("osascript")
            if not found:
                return None, UNSUPPORTED_MISSING
            return MACOS, found

        if system == "Linux":
            if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                return None, UNSUPPORTED_HEADLESS
            found = shutil.which("notify-send")
            if not found:
                return None, UNSUPPORTED_MISSING
            return LINUX, found

        return None, UNSUPPORTED_MISSING
    except Exception:
        return None, UNSUPPORTED_MISSING


# --------------------------------------------------------------------------
# delivery
# --------------------------------------------------------------------------

def _run(argv, env=None, creationflags=0):
    """Run a backend command with no shell and a hard timeout.

    `creationflags` is accepted on every platform as long as it stays 0 off
    Windows, so one call site serves all three backends.
    """
    try:
        subprocess.run(
            argv,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SEND_TIMEOUT,
            shell=False,
            creationflags=creationflags,
        )
        return True
    except Exception:
        return False


_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))


def _unique_tag():
    """A fresh toast tag, so a new notification never replaces an older one."""
    return "n" + os.urandom(8).hex()


def _toast_keys(keys):
    return ";".join(key[:60] for key in keys if isinstance(key, str) and key)


def _run_toast_script(shell, values):
    """Run the bundled toast script. The payload travels in the environment."""
    script = os.path.join(_HOOKS_DIR, "win_toast.ps1")
    if not os.path.isfile(script):
        return False
    env = dict(os.environ)
    env.update(values)
    argv = [
        shell,
        "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", script,
    ]
    return _run(argv, env=env, creationflags=_CREATE_NO_WINDOW)


def _send_windows(shell, title, body, attribution, attention, persistent, silent, key, remove_keys):
    """WinRT toast under the plugin's own "Claude Code" app identity."""
    icon = os.path.join(_HOOKS_DIR, "icon.png")
    return _run_toast_script(shell, {
        "CCN_MODE": "show",
        "CCN_TITLE": title,
        "CCN_BODY": body,
        "CCN_ATTRIB": attribution,
        "CCN_ATTENTION": "1" if attention else "0",
        "CCN_PERSISTENT": "1" if persistent else "0",
        "CCN_SILENT": "1" if silent else "0",
        "CCN_TAG": _unique_tag(),
        "CCN_GROUP": key[:60],
        "CCN_REMOVE": _toast_keys(remove_keys),
        "CCN_ICON": icon if os.path.isfile(icon) else "",
    })


def _send_macos(osascript, title, body, attribution, attention, persistent, silent, key, remove_keys):
    """AppleScript via `on run argv`.

    The text is NEVER interpolated into the script source. AppleScript string
    literals have no escape for a literal newline, so interpolation is the
    classic way these scripts break on real input; passing argv sidesteps
    escaping entirely.

    `attention`, `persistent`, `key` and `remove_keys` are unused on purpose:
    `display notification` offers no programmatic persistence, no
    replace-in-place and no withdrawal. Persistence on macOS is a user setting
    (System Settings > Notifications > Script Editor > Alerts).
    """
    display = 'display notification (item 1 of argv) with title (item 2 of argv) subtitle (item 3 of argv)'
    if not silent:
        display += ' sound name "Ping"'
    argv = [
        osascript,
        "-e", "on run argv",
        "-e", display,
        "-e", "end run",
        "--", body, title, attribution,
    ]
    return _run(argv)


def _send_linux(notify_send, title, body, attribution, attention, persistent, silent, key, remove_keys):
    """libnotify. Critical urgency is the only reliable route to persistence.

    The freedesktop spec says critical notifications should not automatically
    expire; GNOME Shell and KDE Plasma both honour that. `-t` is unreliable -
    GNOME Shell ignores expire-time entirely, and critical adds no buttons.
    """
    full_body = "{0}\n{1}".format(body, attribution) if attribution else body
    # notify-send renders a small HTML subset, so these three would otherwise
    # mangle or drop the body.
    full_body = full_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    argv = [notify_send, "-a", "Claude Code"]
    if persistent:
        argv += ["-u", "critical"]
    elif attention:
        argv += ["-u", "normal"]
    else:
        argv += ["-u", "low", "-t", "6000", "--hint=string:transient:1"]
    if silent:
        argv += ["--hint=int:suppress-sound:1"]
    # No replace-in-place hints: every notification stands on its own.
    argv += ["--", title, full_body]
    return _run(argv)


_SENDERS = {
    WINDOWS: _send_windows,
    MACOS: _send_macos,
    LINUX: _send_linux,
}


def send(title, body, attribution, attention, persistent, silent, key, remove_keys=()):
    """Deliver one notification. Returns True only when the backend was run.

    `key` is the notification's group (session + category); `remove_keys` names
    groups of earlier notifications to withdraw, in the same process.
    """
    try:
        name, detail = detect()
        if name is None:
            return False
        sender = _SENDERS.get(name)
        if sender is None:
            return False
        return sender(detail, title, body, attribution, attention, persistent, silent, key,
                      tuple(remove_keys or ()))
    except Exception:
        return False


def remove(keys):
    """Withdraw earlier notifications by group. Windows only; a no-op elsewhere."""
    try:
        name, detail = detect()
        if name != WINDOWS or not keys:
            return False
        return _run_toast_script(detail, {"CCN_MODE": "remove", "CCN_REMOVE": _toast_keys(keys)})
    except Exception:
        return False


def describe():
    """Human-readable capability report for /notification:doctor."""
    name, detail = detect()
    return {
        "system": platform.system(),
        "release": platform.release(),
        "python": sys.executable or "?",
        "python_version": platform.python_version(),
        "wsl": is_wsl(),
        "ssh": is_ssh(),
        "backend": name or "unsupported",
        "detail": detail,
    }
