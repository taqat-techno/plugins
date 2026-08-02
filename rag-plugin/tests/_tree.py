"""Shared test helper: which plugin tree is under test.

Every structural test in this directory scans plugin files. To make a test a
real gate rather than decoration, it must be runnable against the PRE-FIX tree
as well as the live one — the repo's standing lesson is that a source-scanning
test is worthless until it has been shown to FAIL against the version it is
meant to catch.

    python -m unittest discover tests            # live tree  -> must pass
    RAG_PLUGIN_TEST_ROOT=tests/baseline_v0.17.0 \
        python -m unittest discover tests        # baseline   -> must fail

``tests/baseline_v0.17.0/`` holds byte copies of the v0.17.0 files the tests
scan. It is a fixture, not a backup: never edit it to make a test pass.
"""

from __future__ import annotations

import os
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
BASELINE_MARKER = "baseline_v0.17.0"


def tree_root() -> Path:
    """Root of the tree under test (live plugin root unless overridden)."""
    override = os.environ.get("RAG_PLUGIN_TEST_ROOT")
    if not override:
        return PLUGIN_ROOT
    p = Path(override)
    return p if p.is_absolute() else (PLUGIN_ROOT / p)


def is_baseline() -> bool:
    """True when running against the pre-fix snapshot."""
    return BASELINE_MARKER in str(tree_root())


def read(relative: str) -> str:
    """Read a file from the tree under test. Missing file -> empty string.

    Empty rather than raising: the baseline snapshot deliberately holds only
    the files the tests scan, so a test for a file that does not exist yet in
    the baseline should FAIL on content, not ERROR on IO.
    """
    path = tree_root() / relative
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def scan_files(patterns=("rules/*.md", "hooks/*.py", "commands/*.md",
                         "skills/*/SKILL.md", "skills/*/references/*.md")):
    """Yield (relative_path, text) for every plugin artefact a rule applies to.

    Excludes the baseline snapshot itself and this directory's own tests —
    a test that asserts "no artefact contains X" must not trip over the test
    that spells X out.
    """
    root = tree_root()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            rel = path.relative_to(root).as_posix()
            if BASELINE_MARKER in rel or rel.startswith("tests/"):
                continue
            try:
                yield rel, path.read_text(encoding="utf-8")
            except OSError:
                continue
