#!/usr/bin/env python3
"""One entry point for every rag-plugin check (WP-13).

    python tests/run_all.py                 # live tree — everything must pass
    python tests/run_all.py --baseline      # v0.17.0 snapshot — gates must FAIL
    python tests/run_all.py --quick         # skip the slow subprocess suites

Why a runner rather than "just use unittest discover"
-----------------------------------------------------
The plugin's checks live in four places for good reasons — structural gates in
``tests/``, unit suites beside the code they test, and a smoke harness that is
not a unittest module at all. Running three of the four and calling it green is
how a regression ships.

It also makes the **negative control** a first-class command. The repository's
standing rule is that a source-scanning test is worthless until it has been
shown to FAIL against the version it is meant to catch; ``--baseline`` is that
demonstration, and it *inverts* the exit code so "the gates correctly failed"
reports as success.

**Skips are printed, never hidden.** ragtools itself shipped two E2E suites that
had never executed, because a skip and a pass look identical from outside.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = PLUGIN_ROOT / "tests"

#: Suites that live beside the code they test. Each is a standalone script.
SIDECAR_SUITES = [
    ("hook fail-open (D-031)", PLUGIN_ROOT / "hooks" / "test_hook_launcher.py", False),
    ("project focus", PLUGIN_ROOT / "scripts" / "test_project_focus.py", False),
    ("report engine", PLUGIN_ROOT / "scripts" / "test_rag_report.py", True),
    ("operational-intent classifier",
     PLUGIN_ROOT / "scripts" / "hook_classifier_smoke.py", False),
]


def _run_structural(baseline: bool) -> tuple[int, int, int]:
    """Run tests/. Returns (run, failures+errors, skipped)."""
    env_key = "RAG_PLUGIN_TEST_ROOT"
    previous = os.environ.get(env_key)
    if baseline:
        os.environ[env_key] = str(TESTS_DIR / "baseline_v0.17.0")
    else:
        os.environ.pop(env_key, None)
    try:
        sys.path.insert(0, str(TESTS_DIR))
        loader = unittest.TestLoader()
        suite = loader.discover(str(TESTS_DIR), top_level_dir=str(TESTS_DIR))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        return (result.testsRun,
                len(result.failures) + len(result.errors),
                len(result.skipped))
    finally:
        if previous is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = previous


def _run_sidecars(quick: bool) -> list[tuple[str, bool]]:
    results = []
    for label, path, slow in SIDECAR_SUITES:
        if quick and slow:
            print(f"  SKIPPED (--quick): {label}")
            results.append((label, True))
            continue
        if not path.is_file():
            print(f"  MISSING: {label} ({path.name})")
            results.append((label, False))
            continue
        proc = subprocess.run([sys.executable, str(path)],
                              capture_output=True, text=True, timeout=300)
        ok = proc.returncode == 0
        tail = (proc.stdout or proc.stderr).strip().splitlines()
        summary = tail[-1] if tail else "(no output)"
        print(f"  {'OK  ' if ok else 'FAIL'}  {label:34s} {summary}")
        results.append((label, ok))
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--baseline", action="store_true",
                    help="run the structural gates against tests/baseline_v0.17.0; "
                         "they are EXPECTED to fail, so the exit code is inverted")
    ap.add_argument("--quick", action="store_true", help="skip the slow suites")
    args = ap.parse_args(argv)

    mode = "BASELINE (v0.17.0 snapshot)" if args.baseline else "LIVE"
    print(f"=== rag-plugin checks — {mode} ===\n")

    print("--- structural gates (tests/) ---")
    run, bad, skipped = _run_structural(args.baseline)
    print(f"    {run} run, {bad} failed, {skipped} skipped")
    if skipped:
        print("    NOTE: skips above are real. A suite that skips is a suite that "
              "did not run — do not read this as coverage.")

    if args.baseline:
        print()
        if bad > 0:
            print(f"NEGATIVE CONTROL PASSED: {bad} gate(s) correctly failed against "
                  "v0.17.0.\nThe gates can see the defects they were written for.")
            return 0
        print("NEGATIVE CONTROL FAILED: every gate passed against the PRE-FIX tree.\n"
              "The gates are not detecting the defects they exist for — treat them "
              "as decoration until this is explained.")
        return 1

    print("\n--- sidecar suites ---")
    sidecars = _run_sidecars(args.quick)
    failed = [name for name, ok in sidecars if not ok]

    print()
    if bad == 0 and not failed:
        print(f"ALL CHECKS PASSED ({run} structural + {len(sidecars)} sidecar suites).")
        print("Run `python tests/run_all.py --baseline` to confirm the gates still bite.")
        return 0
    if bad:
        print(f"FAILED: {bad} structural gate(s).")
    for name in failed:
        print(f"FAILED: sidecar suite {name!r}.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
