"""
Remotion Plugin - Prerequisites Checker

Checks that all required tools are installed and reports missing dependencies
with platform-specific install commands.

Usage:
    python3 setup_check.py      (or `python` / `py -3` where there is no python3)
"""

import os
import platform
import shutil
import subprocess
import sys


def get_platform():
    """Detect the current platform."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "macos"
    return "linux"


def resolve_command(cmd):
    """Full path of `cmd` on PATH, or None.

    shutil.which honours PATHEXT on Windows, so `npm` / `npx` resolve to `npm.cmd` /
    `npx.cmd`. Running the bare name instead fails there with FileNotFoundError,
    because CreateProcess does not try PATHEXT extensions.
    """
    return shutil.which(cmd)


def check_command(cmd, version_flag="--version"):
    """Check if a command is available and return its version.

    The resolved path is executed directly (never through shell=True); Windows runs
    a resolved `.cmd` / `.bat` path through cmd.exe on its own.
    """
    path = resolve_command(cmd)
    if not path:
        return False, None
    try:
        result = subprocess.run(
            [path, version_flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    output = result.stdout.strip() or result.stderr.strip()
    return True, output.split("\n")[0] if output else ""


def check_python_package(package_name):
    """Check if a Python package is installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return True, line.split(":")[1].strip()
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def parse_version(version_str):
    """Extract version numbers from a version string."""
    import re
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if match:
        return tuple(int(x) for x in match.groups())
    return (0, 0, 0)


def main():
    plat = get_platform()
    all_ok = True

    print("=" * 60)
    print("Remotion Plugin - Prerequisites Check")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Interpreter for the plugin scripts: {sys.executable}")
    print("  (run generate_voice.py, concat_audio.py and measure_audio.py with this same")
    print("   interpreter, so the edge-tts / mutagen checks below apply to them)")
    print("=" * 60)

    # ── Node.js ──────────────────────────────────────────────────
    print("\n[1/6] Node.js (>= 18.0.0)")
    found, version = check_command("node")
    if found:
        ver = parse_version(version)
        if ver[0] >= 18:
            print(f"  PASS  {version}")
        else:
            print(f"  FAIL  {version} (need >= 18.0.0)")
            all_ok = False
    else:
        print("  FAIL  Not installed")
        if plat == "windows":
            print("  Install: winget install OpenJS.NodeJS.LTS")
        elif plat == "macos":
            print("  Install: brew install node@20")
        else:
            print("  Install: your distribution's package (e.g. sudo apt install nodejs - check it is >= 18)")
            print("       or: nvm (https://github.com/nvm-sh/nvm), then: nvm install --lts")
        all_ok = False

    # ── npm ──────────────────────────────────────────────────────
    print("\n[2/6] npm")
    found, version = check_command("npm")
    if found:
        print(f"  PASS  {version}")
    else:
        print("  FAIL  Not installed (comes with Node.js)")
        all_ok = False

    # ── Python (>= 3.8) ─────────────────────────────────────────
    print("\n[3/6] Python (>= 3.8.0)")
    py_ver = sys.version_info
    if py_ver >= (3, 8):
        print(f"  PASS  Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    else:
        print(f"  FAIL  Python {py_ver.major}.{py_ver.minor}.{py_ver.micro} (need >= 3.8)")
        all_ok = False

    # ── edge-tts ─────────────────────────────────────────────────
    print("\n[4/6] edge-tts (free voice generation)")
    found, version = check_python_package("edge-tts")
    if found:
        print(f"  PASS  edge-tts {version}")
    else:
        print("  FAIL  Not installed")
        print(f"  Install: {sys.executable} -m pip install edge-tts")
        all_ok = False

    # ── mutagen ──────────────────────────────────────────────────
    print("\n[5/6] mutagen (audio duration measurement)")
    found, version = check_python_package("mutagen")
    if found:
        print(f"  PASS  mutagen {version}")
    else:
        print("  FAIL  Not installed")
        print(f"  Install: {sys.executable} -m pip install mutagen")
        all_ok = False

    # ── pydub (optional) ─────────────────────────────────────────
    print("\n[6/6] pydub (audio concatenation - optional)")
    found, version = check_python_package("pydub")
    if found:
        print(f"  PASS  pydub {version}")
    else:
        print("  SKIP  Not installed (optional, uses ffmpeg fallback)")
        print(f"  Install: {sys.executable} -m pip install pydub")

    # ── FFmpeg (optional) ────────────────────────────────────────
    print("\n[bonus] FFmpeg (optional, for advanced audio/video)")
    found, version = check_command("ffmpeg", "-version")
    if found:
        print(f"  PASS  {version}")
    else:
        print("  SKIP  Not installed (optional)")
        if plat == "windows":
            print("  Install: winget install Gyan.FFmpeg")
        elif plat == "macos":
            print("  Install: brew install ffmpeg")
        else:
            print("  Install: sudo apt install ffmpeg")

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if all_ok:
        print("All prerequisites satisfied! You're ready to go.")
        print("\nNext steps:")
        print("  1. /remotion:init my-video   (in Claude Code)")
        print("  2. cd my-video && npm run dev")
    else:
        print("Some prerequisites are missing. Install them and run again.")
        print(f"\nQuick install all Python deps:")
        print(f"  {sys.executable} -m pip install edge-tts mutagen pydub")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
