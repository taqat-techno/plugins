#!/usr/bin/env python3
"""Windows-side READ-ONLY host probe for the cleanup plan and the WSL performance branch.

Prints inventory records (same TSV format as inventory.sh) on stdout:
    hostdisk <drive> <free_bytes> <total_bytes>
    vhdx     <distro> <path> <allocated_bytes>
    meta     wsl_version <x.y.z>
    meta     wsl_running <comma-separated distros>
    note     <text>

It reads the registry and file sizes and calls `wsl.exe --list --running`, which does not
start the VM. It never runs anything inside a distro. The probe logic lives in the
plugin's hooks/host_pressure.py (shared with the SessionStart check).

    python host_probe.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "hooks")))
import host_pressure as hp  # noqa: E402


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = []
    usage = hp.drive_usage()
    drive = os.environ.get("SystemDrive", "C:") if hp.is_windows() else "/"
    if usage:
        out.append(("hostdisk", drive, str(usage[0]), str(usage[1])))
    if not hp.is_windows():
        out.append(("note", "not Windows: no WSL disk images to inspect"))
    else:
        version = hp.wsl_version()
        if version:
            out.append(("meta", "wsl_version", ".".join(map(str, version))))
            bad = hp.known_bad_wsl(version)
            if bad:
                out.append(("note", bad))
        running = hp.running_distros()
        out.append(("meta", "wsl_running", ",".join(running or [])))
        for name, vhdx in hp.wsl_distros():
            size = hp.file_size(vhdx)
            if vhdx and size:
                out.append(("vhdx", name, vhdx, str(size)))
    for rec in out:
        print("\t".join(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
