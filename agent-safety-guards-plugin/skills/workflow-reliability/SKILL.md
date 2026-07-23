---
name: workflow-reliability
description: Lightweight reliability discipline for multi-agent / subagent fan-out workflows. Owns running fan-outs in SMALL sequential waves (not one big burst that trips transient rate limits), making the reduce/aggregation NULL-SAFE (a failed agent returns null — degrade, do not crash the run), designing long workflows to be journaled + idempotent (byte-identical prompts resume from cache; additive or sentinel-guarded edits never double-apply), giving each agent DISJOINT file ownership plus a single central canonical vocabulary, treating a subagent "done" as a CLAIM to be verified by deterministic main-thread scans (grep / JSON-validate / reachability), dispatching ONE subagent per long-form item, keeping policy/knowledge in skills with bounded read-only execution in subagents, treating an all-clear / zero-corrections reduce as trustworthy ONLY when every producer actually completed (a crashed finder's empty result is unverified, not clean) and reconciling only the current run's artifacts (never a prior run's stale checkpoint), and the investigation-first audit shape (read-only survey, then parallel single-concern subagents, then cited synthesis, then live verification). Activates when planning or running a subagent fan-out, an orchestrated multi-step pipeline, a parallel audit, or any long workflow that must resume and verify reliably.
version: 0.2.0
last_reviewed: 2026-07-23
owns:
  - small-sequential-wave fan-out (avoid one big burst that trips transient rate limits)
  - null-safe reduce / aggregation (a failed agent returns null; degrade, do not crash)
  - journaled + idempotent long-run design (byte-identical resume; additive / sentinel-guarded edits)
  - disjoint file ownership per agent + a single central canonical vocabulary
  - treat a subagent "done" as a CLAIM; verify with deterministic main-thread scans
  - one subagent per long-form item; policy in skills, bounded read-only execution in subagents
  - the investigation-first audit shape (survey -> parallel single-concern -> cited synthesis -> verify)
  - budget-aware waves + per-item disk checkpoint (a burst over the token budget can zero out the whole batch)
  - main-thread fallback when a session/usage limit halts subagents mid-run
  - trust the on-disk output over the workflow's own completion-report counts
  - an all-clear / zero-corrections reduce is trustworthy only when every producer COMPLETED (a crashed finder's empty result is unverified, not clean); reconcile only the current run's artifacts, never a prior run's stale checkpoint
  - workflow-script footguns (literal work-list not args; array-join not template literals; assemble mega-output on disk)
defers_to:
  - agent-safety skill for per-session safety primitives (secrets, read-only immutability, authorization, no-fabrication)
  - the orchestrator / user for wave size, retry budget, and final apply decisions
user_invocable: false
---

# workflow-reliability

## Purpose

A multi-agent run is reliable when a single flaky agent cannot sink it, when re-running it is safe, and when no agent's self-report is trusted without a check. This skill encodes the small set of patterns that make fan-out workflows survive transient failures and resume cleanly: sequential waves, null-safe reduce, journaled idempotency, disjoint ownership, and verify-the-claim. It is advisory — it shapes how a workflow is planned and checked; it never auto-mutates state.

## When to use

Activate when:

- Planning or running a subagent fan-out (several agents working in parallel on related items).
- Orchestrating a multi-step pipeline that must be resumable after an interruption.
- Running a parallel audit or review across many files, roles, or modules.
- Designing any long workflow where partial failure and re-run safety matter.

## The reliability patterns

### 1. Fan out in SMALL sequential waves

Do not dispatch one large burst of subagents at once:

- A big simultaneous burst is the classic trigger for transient rate-limit / overload errors that fail otherwise-fine work.
- Dispatch a small wave, let it settle, then dispatch the next. Keep wave size conservative and bounded.
- Sequential waves also make journaling and partial-resume tractable (you always know which wave completed).

### 2. Make the reduce NULL-SAFE

The aggregation step that combines subagent results must tolerate failure:

- A failed or timed-out agent returns **null** (or a typed "failed" marker), not a crash.
- The reduce **degrades** — it folds in the successes, records which items are missing, and keeps going.
- One agent's failure must never abort the whole run or corrupt the partial result.
- Surface the missing items explicitly in the final output so the user knows what to re-run.

### 3. Journal + design for idempotency

Long workflows must be safe to resume and safe to re-run:

- **Journal** progress (which items / waves are done) so a resumed run skips completed work.
- Make subagent prompts **byte-identical** across runs where possible so prompt caching can resume cheaply.
- Make edits **idempotent**: additive (append-only) or **sentinel-guarded** (check for a marker before applying) so a second run never double-applies. "Insert if not already present" beats "insert".
- A re-run of the whole workflow should converge to the same end state, not stack duplicate changes.

### 4. Disjoint file ownership + one canonical vocabulary

When several agents write or analyze in parallel:

- Give each agent a **disjoint set of files** to own. No two agents write the same file in the same wave — that is how races and lost writes happen.
- Maintain **one central canonical vocabulary** (names, terms, IDs, conventions) that every agent references, so independently produced outputs stitch together cleanly instead of inventing conflicting names.

### 5. A subagent "done" is a CLAIM — verify it

Never trust a subagent's self-report as proof:

- A subagent saying "done" or "edited the file" is a **claim**, not verified fact.
- Verify fan-out edits with **deterministic main-thread scans**: grep for the expected change, JSON-validate produced config, check reachability / that a referenced file exists, re-parse the artifact.
- The main thread, running cheap deterministic checks, is the source of truth — not the agent's narration.

### 6. One subagent per long-form item

For substantial per-item work (a long document, a complex file, a deep analysis):

- Dispatch **one subagent per item** rather than asking a single agent to produce many long outputs in one shot.
- This keeps each agent's context focused, bounds failure to one item, and makes per-item verification and re-run clean.

### 7. Policy in skills, bounded read-only execution in subagents

- Keep durable **policy and knowledge in skills** (the rules, conventions, taxonomies) — they are read and reused, not re-derived per run.
- Keep **execution bounded and read-only in subagents** where the task is investigation: a subagent surveys and reports; it does not mutate shared state (see the agent-safety skill).

### 8. A zero / all-clear reduce is trustworthy only if the producers COMPLETED

Pattern 2 degrades a failed agent to `null` so one flake can't crash the run — but that leaves a trap at the *aggregation* step. An agent that **ran clean and found nothing** and an agent that **died before it reported** both contribute an empty result. Reading the roll-up as "0 findings / `corrections: 0` = all clear" silently converts every dead finder into a green light.

- **Carry completion separately from payload.** Each slot records two facts: did the agent *finish*, and what did it *find*. A `corrections: 0` / "all pass" verdict is a clean bill of health **only if every verifier actually completed**. If any finder crashed, timed out, or hit its quota, its zero is **unknown**, not clean.
- **Gate the aggregate closed, not open.** A verdict computed over an incomplete fan-out is "unverified", not "pass"; name the crashed / missing verifiers and re-run them before the zero is trusted. An all-green summary over N-of-M completed finders is an N/M result, never M/M.
- **Keep "found nothing" and "never looked" distinguishable in the data** — a typed failed / incomplete marker per item (pattern 2), never a bare empty list that collapses the two.

**Discard stale per-run artifacts before reconciling.** When each agent checkpoints its verdict to its own file (the budget-aware pattern below), a resumed or re-run fan-out still finds **the previous run's files on disk**. Reconciling over them counts an *earlier* run's verdict as *this* run's:

- **Clear or namespace the artifact directory at the start of each run** (a per-run subdir, or a run-id / timestamp prefix) so reconciliation only ever sees files this run produced.
- **Reconcile by identity, not by presence** — a file existing is not proof this run wrote it; check its run-id / mtime, or write into a freshly-cleared location. A green verdict inherited from a prior run is the stale-artifact form of the empty-equals-clean trap.

Before any green aggregate is allowed to drive an apply / commit / mutation, **adversarially refute it first** — see the agent-safety skill ("refute a pass before you let it mutate state").

## Surviving session/usage limits + workflow-script footguns

The wave + journal patterns above assume agents fail *individually*. Two failure modes hit the WHOLE run at once and need their own discipline.

### Budget-aware waves + checkpoint each item to disk

- **Size the wave to the remaining session/token budget, not just to the rate limit.** A burst that exceeds the budget does not degrade gracefully — *every* agent in it can die at the quota ("You've hit your session limit") with zero output, losing the entire batch.
- **Checkpoint each item's output to disk the moment that agent finishes** (one file per item), on top of journaling which-item-is-done. A quota hit or a resume then re-does only the missing files, never the completed work.

### Main-thread fallback when the limit halts every subagent

- When a session/usage limit halts *all* subagents mid-run, the **main conversation loop usually still has capacity**. Switch to authoring the remaining items directly in-thread, to the **identical structure**, rather than idling until the limit resets. Keep the canonical item structure handy so the hand-off is seamless.

### Trust on-disk reality over the completion report

- A fan-out's reported result can **undercount** what actually landed: a retry wave may write more files *after* the summary was emitted (observed: report said 40/221, disk had 51/285). This is distinct from "verify a done-claim" — the aggregate count itself is stale. Before finalizing, **re-glob and re-count the output directory**; never assemble the final result from the summary field.

### Workflow-script authoring footguns

- **Embed the work-list as a literal in the script.** Passing it through `args` can arrive stringified or `undefined`, yielding a silent **0-agent run** that wastes the whole launch.
- **Build emitted strings with array `.join('\n')`, not template literals** — large template-literal blocks are a recurring source of script parse errors.
- **Assemble mega-outputs (200k+ chars of JSON-wrapped markdown) on disk** with a small helper that strips agent preambles and reports counts. Never inline-read a giant aggregate into context.

## The investigation-first audit shape

For an audit or review across a codebase or system, use this shape:

```
1. Read-only survey        — map the territory; list the items/files/roles in scope (no mutation)
2. Parallel single-concern — one subagent per concern or item, each read-only, disjoint ownership
   subagents                 (small sequential waves; null-safe reduce)
3. Cited synthesis         — main thread aggregates results with source citations (file:line)
4. Live verification       — deterministic main-thread scans confirm each claimed finding
```

Each stage gates the next. The synthesis cites evidence; the verification proves the synthesis. No applied change happens inside the audit — fixes are proposed for the user to apply.

## Decision framework

```
many parallel items?      --> small sequential waves, not one burst
an agent failed?          --> null result, degrade the reduce, record the gap; do not crash
will this run again?       --> journal progress + make edits additive / sentinel-guarded (idempotent)
agents writing files?      --> disjoint ownership + one canonical vocabulary
agent reports "done"?      --> treat as a claim; verify with grep / JSON-validate / reachability
long per-item output?      --> one subagent per item
audit / review?            --> survey -> parallel single-concern -> cited synthesis -> live verify
burst near the budget?     --> size to remaining budget; checkpoint each item to disk
session limit hit mid-run? --> finish remaining items in-thread to the same structure
reading the final count?   --> re-glob the output dir; do not trust the summary field
authoring a workflow script? --> literal work-list (not args); array-join strings; assemble on disk
all-pass / zero result?    --> trustworthy only if every producer COMPLETED; a crashed finder's zero = unverified, not clean
reconciling per-run files? --> clear / namespace the artifact dir first; a prior run's file is not this run's verdict
```

## Validation checklist

- [ ] Fan-out ran in small sequential waves, not one large burst.
- [ ] The reduce is null-safe: a failed agent degraded the run and was recorded, not crashed it.
- [ ] Progress is journaled and edits are additive or sentinel-guarded (re-run converges, no double-apply).
- [ ] Each agent owned a disjoint file set; one canonical vocabulary was shared.
- [ ] Every subagent "done" was verified by a deterministic main-thread scan.
- [ ] One subagent per long-form item (no single agent producing many long outputs at once).
- [ ] For audits: survey -> parallel single-concern -> cited synthesis -> live verification, with no applied changes.
- [ ] Wave size accounted for the remaining session/token budget; each item was checkpointed to disk as it finished.
- [ ] Final counts came from a re-glob of the output directory, not the workflow's summary field.
- [ ] Any workflow script embeds its work-list as a literal (not via args) and assembles large outputs on disk.
- [ ] Any "all pass" / zero-corrections aggregate was gated on every verifier having completed; crashed finders were surfaced, not read as clean.
- [ ] Per-run artifacts were reconciled from a cleared / namespaced location, so no prior run's verdict counted as this run's.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Dispatch 50 subagents at once | Bursts trip transient rate-limit / overload errors and fail good work | Small sequential waves; let each settle |
| Let one failed agent abort the run | A single flake sinks the whole fan-out | Null-safe reduce: degrade, record the gap, continue |
| Re-run a workflow that re-applies every edit | Duplicate / stacked changes; non-convergent state | Journal progress; additive or sentinel-guarded edits |
| Two agents write the same file in one wave | Races, lost writes, conflicting output | Disjoint file ownership per agent |
| Each agent invents its own names/terms | Outputs don't stitch together | One central canonical vocabulary all agents reference |
| Trust "I edited the file" without checking | The report is a claim, not proof; silent no-ops slip through | Verify with grep / JSON-validate / reachability scans |
| One agent asked to emit ten long documents | Bloated context, one failure loses everything | One subagent per long-form item |
| Subagent mutates shared state during an audit | Investigation became mutation; race + hidden risk | Bounded read-only subagents; propose fixes to the user |
| Size a burst to the rate limit, ignoring the token budget | Every agent dies at the session quota with zero output | Size waves to the remaining budget; checkpoint each item to disk |
| Idle until the session limit resets | Wastes the window; the main loop still has capacity | Author the remaining items in-thread to the identical structure |
| Assemble the final result from the workflow's summary count | The summary can undercount (a retry wave wrote more after it) | Re-glob and re-count the output directory |
| Pass the work-list via args / build output with template literals | Silent 0-agent run; script parse errors | Embed the work-list as a literal; array-join strings; assemble on disk |
| Read a `corrections: 0` / all-pass reduce as clean when a finder died | A dead finder and a clean finder both report empty; the zero is unverified | Gate the aggregate on producer completion; a crashed verifier => unverified, re-run it |
| Reconcile over whatever artifact files are on disk | A prior run's checkpoint gets counted as this run's verdict | Clear / namespace the artifact dir per run; match by run-id / mtime |

## Cross-references

- `agent-safety` (skill) — per-session safety primitives (pasted-secret compromise, read-only immutability, authorization verification, no-fabrication, report-don't-patch, structured-output exactly-once + schema-gating, don't-route-around-a-denial, refute-a-green-verdict-before-it-mutates). This skill assumes those primitives hold inside every wave and subagent; its completion-gated reduce (pattern 8) and agent-safety's "refute a pass before it mutates state" are two halves of one rule — a zero is only trustworthy once the producer finished AND the pass survives an adversarial re-check.
- The orchestrator / user — owns wave size, retry budget, and the final apply decision.
