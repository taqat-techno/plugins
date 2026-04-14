#!/usr/bin/env python3
"""
rag-plugin hook-decisions analyzer (v0.3.0).

Reads ~/.claude/rag-plugin/hook-decisions.log (JSONL, written by
hooks/prompt_retrieval_reminder.py) and prints aggregate statistics for the
Tier 2 retrieval-reminder hook. Read-only. Python 3 stdlib only.

Purpose: after the hook has been running for a while, this tool lets you
(and future plugin maintainers) measure false-positive / false-negative
rates so the Tier-2-vs-Tier-3 escalation decision is data-driven, not
guess-driven. See docs/decisions.md#d-017.

What you get:
  - Total decisions
  - Breakdown by action tag (shape-mismatch, service-down, probe-error,
    probe-below-threshold, reminder-injected, ...)
  - Probe score histogram (only for decisions that ran the probe)
  - Average prompt length by action class
  - Hook version distribution (for cross-release comparison)

What this tool does NOT do:
  - It NEVER reads the prompt text (not stored in the log).
  - It NEVER calls the MCP or the HTTP API.
  - It NEVER writes to the log or to any other file.
  - It does not take arguments. The log path is fixed.

Usage:
  python3 scripts/analyze_hook_decisions.py

Exit code:
  0 always (even if the log is missing — it just prints a "no data" banner).
"""

import json
import os
import sys
from collections import Counter

LOG_PATH = os.path.expanduser("~/.claude/rag-plugin/hook-decisions.log")


def main() -> None:
    if not os.path.isfile(LOG_PATH):
        print(f"no hook-decisions log at {LOG_PATH}")
        print("(the hook has not run yet, or observability is disabled)")
        sys.exit(0)

    total = 0
    actions: Counter = Counter()
    action_prompt_lengths: dict[str, list[int]] = {}
    probe_scores: list[float] = []
    hook_versions: Counter = Counter()
    malformed_lines = 0

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    malformed_lines += 1
                    continue

                total += 1
                action = str(entry.get("action", "unknown"))
                actions[action] += 1

                plen = entry.get("prompt_length", 0)
                try:
                    plen = int(plen)
                except (TypeError, ValueError):
                    plen = 0
                action_prompt_lengths.setdefault(action, []).append(plen)

                score = entry.get("probe_top_score", 0.0)
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = 0.0
                # Only include in histogram if the probe actually ran (score > 0)
                # or the action tag indicates the probe was invoked.
                if score > 0.0 or "probe" in action or action == "reminder-injected":
                    probe_scores.append(score)

                hv = str(entry.get("hook_version", "unknown"))
                hook_versions[hv] += 1
    except Exception as e:
        print(f"error reading {LOG_PATH}: {e}")
        sys.exit(0)

    if total == 0:
        print(f"log at {LOG_PATH} exists but contains no valid records")
        print(f"malformed lines: {malformed_lines}")
        sys.exit(0)

    # --- render report ---
    print("=" * 64)
    print(f" rag-plugin hook-decisions analyzer ")
    print("=" * 64)
    print(f"log: {LOG_PATH}")
    print(f"total decisions: {total}")
    if malformed_lines:
        print(f"malformed lines skipped: {malformed_lines}")
    print()

    print("--- by action ---")
    for action, count in actions.most_common():
        pct = 100.0 * count / total
        plens = action_prompt_lengths.get(action, [])
        avg_plen = sum(plens) / len(plens) if plens else 0
        print(f"  {action:36s} {count:6d}  ({pct:5.1f}%)   avg prompt len: {avg_plen:.0f}")
    print()

    # A simple summary: reminder-injected rate vs shape-passed rate
    injected = actions.get("reminder-injected", 0)
    shape_passed = sum(
        count
        for action, count in actions.items()
        if action == "reminder-injected"
        or action.startswith("silent-pass:probe-")
        or action == "silent-pass:service-down"
    )
    shape_mismatches = actions.get("silent-pass:shape-mismatch", 0)
    shape_pass_rate = 100.0 * shape_passed / total if total else 0.0
    injection_rate_of_shape_passed = 100.0 * injected / shape_passed if shape_passed else 0.0
    injection_rate_overall = 100.0 * injected / total if total else 0.0

    print("--- summary ---")
    print(f"  shape gate pass rate:            {shape_pass_rate:5.1f}%  ({shape_passed}/{total})")
    print(f"  shape gate mismatch rate:        {100.0 * shape_mismatches / total:5.1f}%  ({shape_mismatches}/{total})")
    print(f"  reminder injection rate overall: {injection_rate_overall:5.1f}%  ({injected}/{total})")
    print(f"  reminder injection rate (of prompts that passed shape gate): {injection_rate_of_shape_passed:5.1f}%")
    print()

    if probe_scores:
        print("--- probe score histogram (when probe ran) ---")
        bins = [(0.0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5),
                (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]
        for lo, hi in bins:
            n = sum(1 for s in probe_scores if lo <= s < hi)
            bar = "#" * min(40, n)
            label = f"{lo:.1f}-{hi:.1f}" if hi <= 1.0 else f"{lo:.1f}-1.0"
            # Normalize the 0.9-1.0 label
            if lo == 0.9:
                label = "0.9-1.0"
            print(f"  {label:9s} {n:5d}  {bar}")
        print()

        # Probe stats
        if probe_scores:
            avg_score = sum(probe_scores) / len(probe_scores)
            min_score = min(probe_scores)
            max_score = max(probe_scores)
            print(f"  probe-ran count: {len(probe_scores)}")
            print(f"  avg probe score: {avg_score:.3f}")
            print(f"  min / max:       {min_score:.3f} / {max_score:.3f}")
            print()

    print("--- hook version distribution ---")
    for version, count in hook_versions.most_common():
        pct = 100.0 * count / total
        print(f"  v{version:8s} {count:6d}  ({pct:5.1f}%)")
    print()

    print("--- tuning hints ---")
    if injection_rate_overall > 25:
        print("  [WARN] high overall injection rate (>25%). the hook is firing on a")
        print("    lot of prompts. if you see false positives in the transcripts,")
        print("    consider raising RAG_PLUGIN_HOOK_PROBE_THRESHOLD to 0.6.")
    elif injection_rate_overall < 2 and shape_pass_rate > 20:
        print("  [WARN] low overall injection rate (<2%) despite frequent shape passes.")
        print("    the probe is filtering out most shape-matched prompts. consider")
        print("    lowering RAG_PLUGIN_HOOK_PROBE_THRESHOLD to 0.4, or escalating")
        print("    to Tier 3 (pre-fetch) so Claude sees results inline.")
    else:
        print("  [OK] injection rate looks reasonable. no action needed.")

    probe_errors = actions.get("silent-pass:probe-error:timeout", 0) + \
                   sum(c for a, c in actions.items() if a.startswith("silent-pass:probe-error"))
    if probe_errors > 0:
        pct = 100.0 * probe_errors / total
        print(f"  [WARN] {probe_errors} probe errors ({pct:.1f}%). check the ragtools service logs.")

    service_down = actions.get("silent-pass:service-down", 0)
    if service_down > 0:
        pct = 100.0 * service_down / total
        print(f"  [WARN] {service_down} service-down events ({pct:.1f}%). the hook could")
        print(f"    not probe because /health was unreachable. start the service to")
        print(f"    restore reminder injection coverage.")

    print()
    print("=" * 64)
    print("to disable observability logging:")
    print("  /rag-config hook-observability off")
    print("to clear the log:")
    print(f"  rm {LOG_PATH}")
    print("(the plugin never deletes this file for you — user owns it)")


if __name__ == "__main__":
    main()
