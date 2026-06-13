---
name: workflow-reliability
description: Lightweight reliability discipline for multi-agent / subagent fan-out workflows. Owns running fan-outs in SMALL sequential waves (not one big burst that trips transient rate limits), making the reduce/aggregation NULL-SAFE (a failed agent returns null — degrade, do not crash the run), designing long workflows to be journaled + idempotent (byte-identical prompts resume from cache; additive or sentinel-guarded edits never double-apply), giving each agent DISJOINT file ownership plus a single central canonical vocabulary, treating a subagent "done" as a CLAIM to be verified by deterministic main-thread scans (grep / JSON-validate / reachability), dispatching ONE subagent per long-form item, keeping policy/knowledge in skills with bounded read-only execution in subagents, and the investigation-first audit shape (read-only survey, then parallel single-concern subagents, then cited synthesis, then live verification). Activates when planning or running a subagent fan-out, an orchestrated multi-step pipeline, a parallel audit, or any long workflow that must resume and verify reliably.
version: 0.1.0
last_reviewed: 2026-06-13
owns:
  - small-sequential-wave fan-out (avoid one big burst that trips transient rate limits)
  - null-safe reduce / aggregation (a failed agent returns null; degrade, do not crash)
  - journaled + idempotent long-run design (byte-identical resume; additive / sentinel-guarded edits)
  - disjoint file ownership per agent + a single central canonical vocabulary
  - treat a subagent "done" as a CLAIM; verify with deterministic main-thread scans
  - one subagent per long-form item; policy in skills, bounded read-only execution in subagents
  - the investigation-first audit shape (survey -> parallel single-concern -> cited synthesis -> verify)
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
```

## Validation checklist

- [ ] Fan-out ran in small sequential waves, not one large burst.
- [ ] The reduce is null-safe: a failed agent degraded the run and was recorded, not crashed it.
- [ ] Progress is journaled and edits are additive or sentinel-guarded (re-run converges, no double-apply).
- [ ] Each agent owned a disjoint file set; one canonical vocabulary was shared.
- [ ] Every subagent "done" was verified by a deterministic main-thread scan.
- [ ] One subagent per long-form item (no single agent producing many long outputs at once).
- [ ] For audits: survey -> parallel single-concern -> cited synthesis -> live verification, with no applied changes.

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

## Cross-references

- `agent-safety` (skill) — per-session safety primitives (pasted-secret compromise, read-only immutability, authorization verification, no-fabrication, report-don't-patch, structured-output exactly-once). This skill assumes those primitives hold inside every wave and subagent.
- The orchestrator / user — owns wave size, retry budget, and the final apply decision.
