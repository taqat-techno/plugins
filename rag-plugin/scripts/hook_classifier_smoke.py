#!/usr/bin/env python3
"""rag-plugin retrieval-reminder hook classifier smoke test (v0.4.0).

Asserts the operational-intent classifier in
hooks/prompt_retrieval_reminder.py correctly silent-passes operational
prompts and lets knowledge-shape prompts through.

Source of the classifier expectations:
  ~/.claude/LESSONS.md  ->  "Inspect the machine before asking clarifying
                            questions" (2026-04-28).

Run from the rag-plugin root:
  python scripts/hook_classifier_smoke.py [--self-test] [--verbose]

Exit code:
  0 — all fixtures pass
  1 — one or more fixtures misclassify

Stdlib only. No HTTP. Imports the hook module directly so the
classifier and its regex live in one place.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo-relative import (works when run from the plugin root)
HERE = Path(__file__).resolve().parent
HOOKS_DIR = HERE.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

import prompt_retrieval_reminder as hook  # type: ignore  # noqa: E402

# 12 operational fixtures — must classify as operational-intent
OPERATIONAL_FIXTURES: list[str] = [
    "how do I start the bot in WSL?",
    "start the ragtools service",
    "stop my langgraph worker",
    "where is openclaw installed on my machine?",
    "is rag on PATH?",
    "what's running on port 21420?",
    "fix the broken qdrant lock",
    "install ragtools",
    "set up auto-start for the service",
    "why is my service failing to boot?",
    "check if redis is reachable",
    "list the processes using port 8080",
]

# 8 knowledge-shape fixtures — must NOT classify as operational
KNOWLEDGE_FIXTURES: list[str] = [
    "what's our process for handling token rotation?",
    "how do we decide which projects to index?",
    "where did we decide on the chunk size?",
    "explain the F-001..F-012 failure catalog",
    "tell me about our deployment pipeline conventions",
    "what's the convention for naming MCP servers?",
    "summarize the rag-plugin decisions log",
    "what does our SOP for incident response look like?",
]


def run() -> int:
    failures: list[str] = []
    for prompt in OPERATIONAL_FIXTURES:
        if not hook.is_operational_intent(prompt):
            failures.append(f"FALSE-NEGATIVE (should be operational): {prompt!r}")
    for prompt in KNOWLEDGE_FIXTURES:
        if hook.is_operational_intent(prompt):
            failures.append(f"FALSE-POSITIVE (should be knowledge):   {prompt!r}")

    n_total = len(OPERATIONAL_FIXTURES) + len(KNOWLEDGE_FIXTURES)
    n_pass = n_total - len(failures)
    print(f"[hook_classifier_smoke] {n_pass}/{n_total} fixtures pass")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")
        return 1
    return 0


def run_verbose() -> int:
    print("--- operational fixtures (expect: operational=True) ---")
    for p in OPERATIONAL_FIXTURES:
        v = hook.is_operational_intent(p)
        flag = "[OK]" if v else "[FAIL]"
        print(f"  {flag}  operational={v}  {p!r}")
    print()
    print("--- knowledge fixtures (expect: operational=False) ---")
    for p in KNOWLEDGE_FIXTURES:
        v = hook.is_operational_intent(p)
        flag = "[OK]" if not v else "[FAIL]"
        print(f"  {flag}  operational={v}  {p!r}")
    print()
    return run()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true",
                    help="run the fixtures and exit 0/1")
    ap.add_argument("--verbose", action="store_true",
                    help="print every fixture's classification")
    args = ap.parse_args(argv)
    if args.verbose:
        return run_verbose()
    return run()


if __name__ == "__main__":
    sys.exit(main())
