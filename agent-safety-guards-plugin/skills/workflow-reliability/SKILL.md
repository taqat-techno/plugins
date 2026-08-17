---
name: workflow-reliability
description: Lightweight reliability discipline for multi-agent / subagent fan-out workflows. Owns running fan-outs in SMALL sequential waves (not one big burst that trips transient rate limits), making the reduce/aggregation NULL-SAFE (a failed agent returns null — degrade, do not crash the run), designing long workflows to be journaled + idempotent (byte-identical prompts resume from cache; additive or sentinel-guarded edits never double-apply), giving each agent DISJOINT file ownership plus a single central canonical vocabulary, treating a subagent "done" as a CLAIM to be verified by deterministic main-thread scans (grep / JSON-validate / reachability), dispatching ONE subagent per long-form item, keeping policy/knowledge in skills with bounded read-only execution in subagents, treating an all-clear / zero-corrections reduce as trustworthy ONLY when every producer actually completed (a crashed finder's empty result is unverified, not clean) and reconciling only the current run's artifacts (never a prior run's stale checkpoint), and the investigation-first audit shape (read-only survey, then parallel single-concern subagents, then cited synthesis, then live verification). Also owns treating a KILLED subagent as UNKNOWN on-disk state rather than no state (inspect the tree before rebuilding or reverting), standing down when a concurrent session shares the same ports / database / background servers, and the recon-subagent prompt contract (read-only with a file:line citation per claim, an explicit [Needs confirmation] label instead of an invented interpretation, the final message IS the deliverable, plus an adversarial verifier pass over the citations). Activates when planning or running a subagent fan-out, an orchestrated multi-step pipeline, a parallel audit, or any long workflow that must resume and verify reliably.
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
  - trust the on-disk output over the workflow's own completion-report counts, and over a background job's reported exit code (which is the trailing wrapper command's, not the real command's)
  - an all-clear / zero-corrections reduce is trustworthy only when every producer COMPLETED (a crashed finder's empty result is unverified, not clean); reconcile only the current run's artifacts, never a prior run's stale checkpoint; a poll loop that cannot parse its reading must keep waiting, never report settled
  - a killed subagent leaves UNKNOWN state, not no state — inspect the working tree before rebuilding or reverting
  - concurrent sessions share ports / databases / background servers — an unexplained SIGTERM can be a peer's teardown; inspect and stand down instead of restarting into the race
  - the recon-subagent prompt contract (read-only + file:line per claim, [Needs confirmation] over invention, the final message IS the deliverable, adversarial verifier pass)
  - workflow-script footguns (literal work-list not args, and a defensive args parse when args are unavoidable; array-join not template literals; no Date.now/Math.random; assemble mega-output on disk)
defers_to:
  - agent-safety skill for per-session safety primitives (secrets, read-only immutability, authorization, no-fabrication)
  - the orchestrator / user for wave size, retry budget, and final apply decisions
user-invocable: false
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
- **Checkpoint at item granularity, never at a time bucket that is still open.** Marking a coarse bucket (a date, an hour, a batch window) "processed" asserts something about items that have not arrived yet: a day marked done at midday kept reporting "0 outstanding" while 23 more items landed that afternoon, and the gap was only caught because the *raw* count had moved from 18 to 41. Journal the **last-processed item id** instead, or wait until the bucket is closed. Treat any marker derived from a heuristic ("the log mentions that date") as unset — your own status report stamped with today's date can set it.
- **Re-scout against the raw source count, not the marker.** Compare how many items the source actually holds for the scope against how many were processed. A marker only ever agrees with itself; it is not evidence that nothing new appeared.
- **Dedup from the durable artifact, not from a sidecar state file.** When a run must not re-process what it already handled, seed the seen-set by reading the **append-only archive it writes into**, not a companion `.state.json`. The sidecar can be deleted, truncated, or restored from an older copy while the archive survives — and the moment it is, every item re-appends as new. The thing you dedup against and the thing you accumulate into should be the same object.
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

**The provenance can be the lie, not the edit.** The harder confabulation is an agent that writes real, working code and then narrates it as pre-existing — "found already present but uncommitted, no changes required, just verified". The artifact is genuinely there, so a grep-for-the-change scan confirms it and learns nothing; what is false is *who wrote it* and *whether anything was actually run against it*.

- **Re-derive provenance from the tree, not the narration.** `git status` against a **known-clean pre-launch baseline** and the files' mtimes say what this run wrote (that is how "already present" was caught — the tree was clean at launch and the mtimes fell inside the run).
- **Never accept "it already passes" / "already exists" as verification.** Run the checks yourself: the new tests *plus* the regression suite, and a schema-drift check (`makemigrations --check` or the framework's equivalent) before trusting a reported "1282 OK".

**An orchestrator's status line and the editor are two more claims.**

- A workflow reporting `stage: "complete"` states that its stages *ran*, not that the result compiles.
- **Stale IDE diagnostics fail in the other direction.** Errors an editor shows after a multi-package run can be a mid-write snapshot the compiler no longer agrees with (`MODEL_OPTIONS is not defined` in a file two packages had both edited, while `tsc --noEmit` was clean) — and the reverse happens too, a real break sitting under a "complete".
- After any workflow where two packages touched one file, **run the real typecheck / test command yourself**. Trust the compiler, not the status line and not the editor.

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

**A poll / watch loop has the same fail-open shape.** A watcher whose exit condition is the *absence* of an in-progress marker concludes "done" whenever its reading is empty — including when the reading is empty because the reading itself failed. One backgrounded deploy watcher shelled out to parse a status file through a path the runtime could not resolve; the parse returned an empty string, the loop's `grep -qE "BUILDING|WAITING"` found no match in it, and it cheerfully printed `ALL SETTLED` while a service was still mid-deploy on the wrong build.

- **Match explicitly on the terminal states** (`SUCCESS`, `FAILED`, `SETTLED`), never on the absence of the non-terminal ones.
- **Treat an unparseable or empty reading as keep-waiting**, and bound the wait with an iteration cap that reports a timeout. An unrecognised reading is a failure case, not the exit case.

Before any green aggregate is allowed to drive an apply / commit / mutation, **adversarially refute it first** — see the agent-safety skill ("refute a pass before you let it mutate state").

### 9. A killed subagent leaves UNKNOWN state, not no state

Pattern 2 degrades a failed agent to a `null` *payload* and pattern 8 refuses to read that null as clean. Neither says anything about the **disk**. An agent killed mid-run — a quota hit, a timeout, a dropped connection — has usually already written part of its work: three packages that reported "failed, you've hit your session limit" had most of their files on disk, and one had its entire backend, endpoint, tests and UI component in place, having died at the *reporting* step.

- **Inspect the working tree before rebuilding or reverting.** `git status` (or a diff against the pre-launch baseline) shows what actually landed. Rebuilding on top of it duplicates work and produces conflicting edits; reverting it discards finished work.
- **A failure report's content is itself a mid-flight snapshot.** An agent reporting test failures may have read the tree while a peer agent was still writing it — re-run the tests yourself before acting on the report.
- **"Failed" means needs reconciliation, not needs re-execution** — mark the item that way until you have looked.

## Surviving session/usage limits + workflow-script footguns

The wave + journal patterns above assume agents fail *individually*. Two failure modes hit the WHOLE run at once and need their own discipline.

### Budget-aware waves + checkpoint each item to disk

- **Size the wave to the remaining session/token budget, not just to the rate limit.** A burst that exceeds the budget does not degrade gracefully — *every* agent in it can die at the quota ("You've hit your session limit") with zero output, losing the entire batch.
- **Checkpoint each item's output to disk the moment that agent finishes** (one file per item), on top of journaling which-item-is-done. A quota hit or a resume then re-does only the missing files, never the completed work.

### Main-thread fallback when the limit halts every subagent

- When a session/usage limit halts *all* subagents mid-run, the **main conversation loop usually still has capacity**. Switch to authoring the remaining items directly in-thread, to the **identical structure**, rather than idling until the limit resets. Keep the canonical item structure handy so the hand-off is seamless.

### Trust on-disk reality over the completion report

- A fan-out's reported result can **undercount** what actually landed: a retry wave may write more files *after* the summary was emitted (observed: report said 40/221, disk had 51/285). This is distinct from "verify a done-claim" — the aggregate count itself is stale. Before finalizing, **re-glob and re-count the output directory**; never assemble the final result from the summary field.
- A background job's **reported exit code is the trailing wrapper command's, not the real command's**. A compound command that ends in a harmless `echo` reports that `echo`'s status, so an install that aborted with `INSTALL_EXIT=255` ("CRITICAL: Failed to initialize database") was notified as "exit code 0" — twice, and would have shipped a broken database. After any backgrounded install / build / migration, read the operation's **own log** (grep for `ERROR`, `CRITICAL`, `Traceback`) and the wrapped command's own exit status. The same trap hits any pipeline whose last stage succeeds (`… | tail`); use `set -o pipefail` or drop the pipe when the result matters, and verify the side effect rather than the status.

### Workflow-script authoring footguns

- **Embed the work-list as a literal in the script.** Passing it through `args` can arrive stringified or `undefined`, yielding a silent **0-agent run** that wastes the whole launch.
- **If a script must take `args`, parse them defensively at the top.** The runtime can hand the script the raw JSON **string** even when the tool call passed a JSON object, so `args.projects` reads `undefined` and the next line dies with `undefined is not an object`. Open every script with `const A = (typeof args === 'string') ? JSON.parse(args) : (args || {})` and read `A.field`. After editing the persisted script, re-run it by its `scriptPath` (returned in the launch result) rather than resending the whole script body.
- **No `Date.now()` / `Math.random()` in a workflow script.** They throw in the script sandbox, and nondeterminism would break resume anyway — a replayed run must produce the same values it produced the first time. Pass timestamps in through args, or stamp them after the run.
- **Build emitted strings with array `.join('\n')`, not template literals** — large template-literal blocks are a recurring source of script parse errors.
- **Assemble mega-outputs (200k+ chars of JSON-wrapped markdown) on disk** with a small helper that strips agent preambles and reports counts. Never inline-read a giant aggregate into context.

## A shared runtime is not yours alone

The patterns above assume your run is the only thing touching the machine. It is not: another agent session — or the user — can hold the same ports, the same database, the same background servers, and its teardown step does not know about your run.

- **An unexplained SIGTERM is a peer, not necessarily a crash.** A background server dying with exit code 144 (SIGTERM) and no error output is the signature of something else killing it — typically a concurrent session running a reset / teardown whose broad `pkill` swept your process while it still held database connections.
- **Inspect before restarting.** Check the process table and the target database's active connections for a competing restore, teardown, or build before relaunching. Restarting blindly races the other driver and collides on the shared port, producing "address already in use" lines from processes that are already dead.
- **Stand down and let one driver hold the wheel.** Two runs restarting into each other leave half-initialised state neither can diagnose. Wait for the peer's operation to finish, then start once, cleanly.

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

### The recon-subagent prompt contract

Stage 2 only returns directly usable reports if the prompt demands it. Across investigations, the reports that needed no rework all carried the same four clauses — reuse them close to verbatim:

1. *"This is READ-ONLY recon. Cite `file:line` for every claim — read the actual content before citing."* Without the second half, an agent cites from memory or from a search hit it never opened, and the citation is the part that later fails verification.
2. *"If a metric's meaning cannot be proven from code or data, label it [Needs confirmation]. NEVER invent an interpretation."* Given no sanctioned way to say "unknown", an agent fills the gap with plausible fiction that reads exactly like a finding.
3. *"Your final message IS the deliverable and is consumed as raw data by an orchestrator, not shown to a human."* Otherwise the agent spends its output on a preamble and a reader-facing summary, and the orchestrator has to parse prose to recover the data.
4. Tool steering wherever accuracy depends on it — *"decode the JSON with a targeted `python -c` rather than eyeballing raw text."*

Then add an **adversarial verifier pass** over anything you will act on: *"Independently verify EACH claim against the actual code — do not trust the citations. A claim that is right in spirit but wrong in detail (wrong field name, model, or file) is 'refuted' with a correction."* Right-in-spirit-wrong-in-detail is the failure this catches, and it caught real mis-citations every time it ran.

Operational note: a workflow subagent may be blocked from writing report files, so the whole report comes back as return text — size the prompt and the expected output accordingly.

## Decision framework

```
many parallel items?      --> small sequential waves, not one burst
an agent failed?          --> null result, degrade the reduce, record the gap; do not crash
will this run again?       --> journal progress + make edits additive / sentinel-guarded (idempotent)
agents writing files?      --> disjoint ownership + one canonical vocabulary
agent reports "done"?      --> treat as a claim; verify with grep / JSON-validate / reachability
agent says "already there"? --> provenance is the lie; git status vs the pre-launch baseline + run the tests yourself
agent FAILED / was killed? --> unknown state, not no state; inspect the tree before rebuilding or reverting
long per-item output?      --> one subagent per item
audit / review?            --> survey -> parallel single-concern -> cited synthesis -> live verify
burst near the budget?     --> size to remaining budget; checkpoint each item to disk
session limit hit mid-run? --> finish remaining items in-thread to the same structure
reading the final count?   --> re-glob the output dir; do not trust the summary field
background job "exit 0"?   --> that's the wrapper's status; grep the operation's own log for ERROR / CRITICAL
authoring a workflow script? --> literal work-list (not args, or parse args defensively); array-join strings; no Date.now/Math.random; assemble on disk
all-pass / zero result?    --> trustworthy only if every producer COMPLETED; a crashed finder's zero = unverified, not clean
watcher says "settled"?    --> match the terminal states explicitly; an empty / unparseable reading = keep waiting
reconciling per-run files? --> clear / namespace the artifact dir first; a prior run's file is not this run's verdict
marking progress?          --> journal the last-processed item id, not a still-open time bucket; re-scout the raw source count
server died with SIGTERM?  --> could be a peer session's teardown; inspect processes / connections and stand down
writing a recon subagent prompt? --> read-only + file:line per claim, [Needs confirmation], "your message IS the deliverable", then an adversarial verifier pass
```

## Validation checklist

- [ ] Fan-out ran in small sequential waves, not one large burst.
- [ ] The reduce is null-safe: a failed agent degraded the run and was recorded, not crashed it.
- [ ] Progress is journaled and edits are additive or sentinel-guarded (re-run converges, no double-apply).
- [ ] Each agent owned a disjoint file set; one canonical vocabulary was shared.
- [ ] Every subagent "done" was verified by a deterministic main-thread scan.
- [ ] Any "already present / already passes" claim was re-derived from `git status` against the pre-launch baseline, with the tests run on the main thread.
- [ ] Every failed or killed agent's working tree was inspected before anything was rebuilt or reverted.
- [ ] One subagent per long-form item (no single agent producing many long outputs at once).
- [ ] For audits: survey -> parallel single-concern -> cited synthesis -> live verification, with no applied changes.
- [ ] Wave size accounted for the remaining session/token budget; each item was checkpointed to disk as it finished.
- [ ] Final counts came from a re-glob of the output directory, not the workflow's summary field; a backgrounded job's success came from its own log, not the notification's exit code.
- [ ] Any workflow script embeds its work-list as a literal (or parses `args` defensively), uses no `Date.now()` / `Math.random()`, and assembles large outputs on disk.
- [ ] Any "all pass" / zero-corrections aggregate was gated on every verifier having completed; crashed finders were surfaced, not read as clean.
- [ ] Any poll / watch loop exits on an explicit terminal state, and treats an empty or unparseable reading as keep-waiting.
- [ ] Progress markers are per-item, not per-open-time-bucket, and dedup reads from the durable archive rather than a sidecar state file.
- [ ] Per-run artifacts were reconciled from a cleared / namespaced location, so no prior run's verdict counted as this run's.
- [ ] An unexplained SIGTERM / port collision was traced to a possible concurrent session before anything was restarted.
- [ ] Recon subagent prompts carried the read-only + `file:line` + [Needs confirmation] + "your message IS the deliverable" clauses, and acted-on findings went through an adversarial verifier pass.

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Dispatch 50 subagents at once | Bursts trip transient rate-limit / overload errors and fail good work | Small sequential waves; let each settle |
| Let one failed agent abort the run | A single flake sinks the whole fan-out | Null-safe reduce: degrade, record the gap, continue |
| Re-run a workflow that re-applies every edit | Duplicate / stacked changes; non-convergent state | Journal progress; additive or sentinel-guarded edits |
| Two agents write the same file in one wave | Races, lost writes, conflicting output | Disjoint file ownership per agent |
| Each agent invents its own names/terms | Outputs don't stitch together | One central canonical vocabulary all agents reference |
| Trust "I edited the file" without checking | The report is a claim, not proof; silent no-ops slip through | Verify with grep / JSON-validate / reachability scans |
| Accept "already present, I only verified it" from an implementer agent | The code can be real while the provenance is confabulated — nothing was actually run | `git status` vs the pre-launch baseline, check mtimes, run the tests yourself |
| Read a workflow's `stage: "complete"` (or the IDE's red squiggles) as a typecheck | Both are snapshots of a process, not of the compiler | Run the real typecheck / tests after any multi-package run that shared a file |
| Rebuild or revert a failed agent's item without looking | It usually died at the reporting step with its files already written | Inspect the working tree first; reconcile, don't re-execute blindly |
| Conclude a backgrounded job succeeded from its "exit code 0" | That is the trailing wrapper command's status, not the real command's | Grep the operation's own log for ERROR / CRITICAL / Traceback |
| Restart a background server that died with SIGTERM | It may be a concurrent session's teardown; restarting races it and collides on the port | Inspect processes / DB connections; let one driver hold the wheel |
| Exit a poll loop when the in-progress markers aren't found | An unparseable or empty reading looks identical to "finished" | Match the terminal states explicitly; unparseable = keep waiting, bounded |
| Mark a still-open day / batch window "processed" | Items arriving later fall behind the marker and are never seen | Track the last-processed item id; re-scout against the raw source count |
| Dedup from a sidecar `.state.json` beside an append-only archive | Losing or rolling back the sidecar re-appends everything as new | Seed the seen-set from the archive itself |
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
