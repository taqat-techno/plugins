# lessons-to-plugins — residual report

Regenerated every run. Current state, not a log.

**Run:** 2026-08-22 · corpus 423 lessons · ledger 135 · candidates 288 · batch 40

---

## Absorbed this run (5)

| Lesson | Owner | Disposition |
|---|---|---|
| Verify intended deliverables are staged, not just written | `git-safety/git-safety` | absorbed |
| A push's own output is not the verdict — confirm with `ls-remote` | `git-safety/git-safety` | absorbed |
| `grep -c $'\r'` reports every line as CRLF — count raw bytes | `claude-env-doctor/windows-script-and-task-authoring` | absorbed |
| Inherited cwd drifts across calls — absolute paths; no heredocs | `claude-env-doctor/windows-script-and-task-authoring` | partial |
| `.stignore` comments are `//`; `(?d)`; workspace-root scope | `claude-env-doctor/env-doctor` | absorbed |

`partial` because it qualified an existing shipped workaround rather than replacing it.

## Needs human decision (0)

No conflicts with shipped behavior were found this run. One near-conflict was resolved
without escalation: shipped workaround #3 in `shell-boundary-hazards.md` ("relative paths
after `cd`") appeared to contradict the new cwd-drift rule. It does not — the shipped rule
is about MSYS *path translation* inside one command, the new one about cwd drift *across*
calls. The shipped rule was qualified, not overturned.

## New-plugin candidates (0)

No cluster this run met the threshold (≥ 8 lessons, ≥ 3 dates, ≥ 2 projects, no existing
owner). Not expected to change until the corpus is drained further.

## Deferred (0 recorded)

35 of the 40 in this batch were left unrecorded rather than marked `deferred`. Recording a
disposition for a lesson that was never evaluated would be dishonest bookkeeping; absent a
ledger entry they simply remain candidates and will be picked up by a later run.

## Rejected (0)

## Tooling defects found on first real use

Both are in `lib/lessons_index.py` and affect P1 coverage. Neither blocks the pipeline;
both make it noisier than it should be.

1. **Coverage produced 5 leads, 0 of which survived verification.** `min_terms=2` with
   common tokens (`.gitignore`, `<record>`, `__init__.py`, `/docs`) matches unrelated
   files. The grep needs rarity weighting — a term appearing in many files should not count
   toward a hit — or a higher floor for short/common terms. Until then P1 is a ranking aid
   only, exactly as the skill says: *a lead, not a verdict*.
2. **`candidates` and `coverage` do not operate on the same batch.** `candidates` sorts by
   date descending; `coverage` walks corpus file order. `--limit 40` therefore selects two
   different sets of 40. They should share one ordering.
