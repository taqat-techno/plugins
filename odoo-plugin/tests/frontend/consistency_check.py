#!/usr/bin/env python3
"""Deprecated standalone entry point, kept for one release: the checks it used to run
against the pre-merge odoo-frontend layout now live in test_plugin_structure.py and
test_data_consistency.py. This runs those with pytest.

Usage:
    python tests/frontend/consistency_check.py [-v]
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(here)]
    if "-v" in sys.argv or "--verbose" in sys.argv:
        args.append("-v")
    sys.exit(subprocess.call(args))
