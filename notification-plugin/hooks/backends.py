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
  - Stateless: replace-in-place uses server-side hints and toast tags, so
    nothing is written to disk on the notification path.
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


def _send_windows(shell, title, body, attribution, sticky, silent, key):
    """WinRT toast via the bundled script. Payload travels in the environment."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "win_toast.ps1")
    if not os.path.isfile(script):
        return False
    env = dict(os.environ)
    env["CCN_TITLE"] = title
    env["CCN_BODY"] = body
    env["CCN_ATTRIB"] = attribution
    env["CCN_STICKY"] = "1" if sticky else "0"
    env["CCN_SILENT"] = "1" if silent else "0"
    env["CCN_TAG"] = key[:60]
    argv = [
        shell,
        "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-File", script,
    ]
    return _run(argv, env=env, creationflags=_CREATE_NO_WINDOW)


def _send_macos(osascript, title, body, attribution, _sticky, silent, _key):
    """AppleScript via `on run argv`.

    The text is NEVER interpolated into the script source. AppleScript string
    literals have no escape for a literal newline, so interpolation is the
    classic way these scripts break on real input; passing argv sidesteps
    escaping entirely.

    `_sticky` and `_key` are unused on purpose: `display notification` offers no
    programmatic persistence and no replace-in-place. Persistence on macOS is a
    user setting (System Settings > Notifications > Script Editor > Alerts).
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


def _send_linux(notify_send, title, body, attribution, sticky, silent, key):
    """libnotify. Critical urgency is the only reliable route to persistence.

    The freedesktop spec says critical notifications should not automatically
    expire; GNOME Shell and KDE Plasma both honour that. `-t` is unreliable -
    GNOME Shell ignores expire-time entirely.
    """
    full_body = "{0}\n{1}".format(attribution, body) if attribution else body
    # notify-send renders a small HTML subset, so these three would otherwise
    # mangle or drop the body.
    full_body = full_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    argv = [notify_send, "-a", "Claude Code"]
    if sticky:
        argv += ["-u", "critical"]
    else:
        argv += ["-u", "low", "-t", "6000", "--hint=string:transient:1"]
    if silent:
        argv += ["--hint=int:suppress-sound:1"]
    # Server-side replace-in-place, so a burst updates one notification instead
    # of stacking. Servers that do not know these hints ignore them harmlessly.
    argv += [
        "--hint=string:x-canonical-private-synchronous:{0}".format(key),
        "--hint=string:x-dunst-stack-tag:{0}".format(key),
        "--", title, full_body,
    ]
    return _run(argv)


_SENDERS = {
    WINDOWS: _send_windows,
    MACOS: _send_macos,
    LINUX: _send_linux,
}


def send(title, body, attribution, sticky, silent, key):
    """Deliver one notification. Returns True only when the backend was run."""
    try:
        name, detail = detect()
        if name is None:
            return False
        sender = _SENDERS.get(name)
        if sender is None:
            return False
        return sender(detail, title, body, attribution, sticky, silent, key)
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
