"""Read-only host-pressure probes shared by the SessionStart hook and the cleanup skill.

Single owner of: system-drive free space, WSL distro -> ext4.vhdx discovery, VHDX
allocated size vs the distro's own `df` used bytes, the installed WSL version, and the
"is WSL running" check. Stdlib only. Every function fails soft (returns None / [])
instead of raising, so a caller in a hook can never crash on it.

It never starts the WSL VM: `wsl_used_bytes` refuses to run unless `running_distros`
already lists the distro.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

GIB = 1024 ** 3

# WSL releases with a known crash or corruption problem, and what to do about it.
# Keep the reason short and factual; the SessionStart hook prints it verbatim.
KNOWN_BAD_WSL = {
    (2, 6, 3): "wsl.exe 2.6.3 has crashed with 0xc00000fd (stack overflow) mid-run and taken the VM down; "
               "`wsl --update` (3.0.3 or later) fixed it. Run it when WSL is idle; it applies on the next WSL start.",
}

_LXSS = r"Software\Microsoft\Windows\CurrentVersion\Lxss"
_LXSS_MSI = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Lxss\MSI"


def is_windows() -> bool:
    return sys.platform == "win32"


def drive_usage(path: str | None = None):
    """(free_bytes, total_bytes) of the system drive (or `path`), or None."""
    try:
        target = path or (os.environ.get("SystemDrive", "C:") + "\\" if is_windows() else "/")
        usage = shutil.disk_usage(target)
        return usage.free, usage.total
    except OSError:
        return None


def wsl_distros():
    """[(name, vhdx_path_or_None)] from the per-user Lxss registry key. Windows only."""
    if not is_windows():
        return []
    try:
        import winreg
    except ImportError:
        return []
    out = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _LXSS)
    except OSError:
        return []
    with root:
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(root, sub) as key:
                    name = winreg.QueryValueEx(key, "DistributionName")[0]
                    base = winreg.QueryValueEx(key, "BasePath")[0]
            except OSError:
                continue
            base = base[4:] if base.startswith("\\\\?\\") else base
            vhdx = os.path.join(base, "ext4.vhdx")
            out.append((name, vhdx if os.path.isfile(vhdx) else None))
    return out


def file_size(path: str | None):
    try:
        return os.path.getsize(path) if path else None
    except OSError:
        return None


def wsl_version():
    """Installed WSL version as a tuple of ints, read from the registry (no wsl.exe call)."""
    if not is_windows():
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _LXSS_MSI) as key:
            raw = winreg.QueryValueEx(key, "Version")[0]
    except (ImportError, OSError):
        return None
    parts = re.findall(r"\d+", str(raw))
    return tuple(int(p) for p in parts[:3]) if len(parts) >= 3 else None


def known_bad_wsl(version):
    return KNOWN_BAD_WSL.get(tuple(version[:3])) if version else None


def _wsl(args, timeout):
    env = dict(os.environ, WSL_UTF8="1", MSYS_NO_PATHCONV="1")
    try:
        proc = subprocess.run(["wsl.exe", *args], capture_output=True, timeout=timeout, env=env,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    raw = proc.stdout
    if b"\x00" in raw:  # UTF-16LE when WSL_UTF8 is not honoured
        raw = raw.replace(b"\x00", b"")
    return proc.returncode, raw.decode("utf-8", "replace")


def running_distros(timeout: float = 1.5):
    """Names of running distros. `wsl -l --running` does not boot the VM. None on error."""
    if not is_windows() or not shutil.which("wsl.exe"):
        return None
    res = _wsl(["--list", "--running", "--quiet"], timeout)
    if res is None or res[0] not in (0, 1):  # exit 1 = "no running distributions" on some builds
        return None
    return [ln.strip() for ln in res[1].splitlines() if ln.strip()]


def wsl_used_bytes(distro: str, timeout: float = 2.0, running=None):
    """Bytes used on the distro's root filesystem, only if that distro is already running."""
    running = running if running is not None else running_distros()
    if not running or distro not in running:
        return None
    res = _wsl(["-d", distro, "--", "df", "-B1", "--output=used", "/"], timeout)
    if res is None or res[0] != 0:
        return None
    nums = re.findall(r"^\s*(\d+)\s*$", res[1], re.M)
    return int(nums[-1]) if nums else None


def vhdx_bloat(size_bytes, used_bytes, ratio: float = 1.5, min_slack: int = 10 * GIB):
    """True when the image holds much more than the distro uses (it never shrinks by itself)."""
    if not size_bytes or not used_bytes:
        return False
    return size_bytes > ratio * used_bytes and size_bytes - used_bytes >= min_slack
