---
name: defect-triage-and-closure
description: >-
  The closure gate for an EXISTING defect report — passed before "working as designed", "cannot
  reproduce", "external blocker", or "won't do" is written into a resolution. Owns the spec-granularity
  rule (a WAD close is only as correct as the granularity you reproduced against; a re-raised report makes
  your model of the rule the suspect), the exact-gesture rule for cannot-reproduce, the
  volunteered-workaround-is-the-diagnostic rule, measure-before-declaring-evidence-gone, file-before-fix
  ordering with per-bug dedup, the re-open instruction on a retracted close,
  decompose-before-calling-it-external for a permissions-shaped error, and re-probe-a-stale-blocker.
  Activates when a verdict is about to be recorded: drafting "cannot reproduce" / "works as designed" /
  "not a bug" / "blocked by environment", a reporter re-raises a closed issue or volunteers a workaround,
  or evidence is about to be called unrecoverable. Not for a general "is my work done" check, and never
  for writing tests.
version: 0.2.0
last_reviewed: 2026-08-10
owns:
  - the spec-granularity gate on a working-as-designed close (re-raised report => your rule model is the suspect)
  - the exact-gesture requirement for a cannot-reproduce close
  - the volunteered-workaround-is-the-highest-value-diagnostic rule
  - the measure-before-you-declare-evidence-gone rule (rotated .1 / archive / backup)
  - file-before-fix ORDERING, one bug at a time, deduped against the known cohort
  - the re-open instruction required in a retracted (not disproven) close
  - the requirement that a permissions-shaped error be decomposed BEFORE it is recorded as an external blocker (the decomposition method itself is not owned here)
  - re-probing an environment blocker before restating it in a later turn
defers_to:
  - browser-qa-discipline for the PASS / BLOCKED / NOT-TESTABLE / FAIL status words and the code-read-is-not-runtime-evidence rule
  - runtime-reality-check for confirming the target is on the expected build before any reproduction attempt counts
  - safe-destructive-testing for what a reproduction attempt is allowed to mutate
  - uat-readiness-report for how closed and open defects roll up into a sign-off
  - windows-script-and-task-authoring (claude-env-doctor) for the vary-one-dimension-at-a-time decomposition method and the privileged-environment blind spot; this skill only requires that the decomposition happened before BLOCKED is written
  - the host's write-approval gate (devops-plugin rules/write-gate.md, agent-safety) for how approval to create a tracked issue is obtained; this skill only fixes the ordering relative to the fix
  - systematic-debugging (superpowers) for root-cause method once a reproduction from real failure output exists
user-invocable: false
---

# defect-triage-and-closure

## Purpose

A wrong close is more expensive than an open bug. An open bug costs attention; a wrong close costs the reporter's trust, because you sent them proof that a real gap is fine. The four closes that go wrong — *working as designed*, *cannot reproduce*, *blocked externally*, *won't do* — all fail the same way: the investigation was competent but answered a slightly different question than the one that was reported. This skill is the gate between "I finished investigating" and "I am recording a verdict".

`browser-qa-discipline` owns the status vocabulary and the evidence bar for a *check*. This skill extends forward into the *closure decision* for a *defect*, and uses that vocabulary rather than inventing its own.

## When to use

Activate when:

- You are about to write "works as designed", "cannot reproduce", "not a bug", "by design", "won't do", or "blocked — external".
- A reporter re-raises an issue you (or the team) already closed — especially the 2nd, 3rd, or 4th time.
- A reporter volunteers a workaround ("it works if I do X first", "it only happens when…").
- You are about to say logs, traces, or evidence are gone / unrecoverable / unknowable.
- You are about to start fixing a defect that has no filed issue yet.
- You are about to restate an environment blocker that you measured in an earlier turn or an earlier session.
- A permissions-shaped error (`Access is denied`, 403, `EACCES`, `permission denied`) is about to be recorded as an infrastructure constraint.

Do **not** activate for a general "have I finished?" self-check (that belongs to `verification-before-completion`) or to author tests (that belongs to the framework testing skills). This skill needs a defect report that already exists.

## Inputs

- **The report itself, in its original wording** — specifically the reporter's *earliest* clear statement of the rule and of the gesture. Your ticket summary is a paraphrase and is the thing most likely to have drifted.
- **The reproduction attempt** — the gesture actually performed, the starting state, the role, and the build it ran against (`runtime-reality-check`).
- **The known-defect cohort** — the existing issue list or index this finding must be deduped against before anything is filed.
- **The evidence set** — screenshots, console/network capture (`console-and-network-capture`), server logs *including rotated siblings*, and any artifact the reporter attached.
- **Any prior verdict on this report** — a previous close, a previous deferral, or a previously measured environment blocker, each with the turn or date it was measured.

## The eight closure gates

### 1. A working-as-designed close is only as correct as the SPEC GRANULARITY you reproduced against

A reproduction confirms *what the code does*. It never confirms *whether that matches the intended rule*. A thorough, honest reproduction — API + live DB + browser — can faithfully demonstrate the wrong rule and prove nothing about the report.

The failure shape: a uniqueness rule was implemented and validated at the **child** scope; the requirement, stated in the reporter's earliest clear message, was uniqueness within the **parent** scope. Every screenshot in the WAD close was true. It answered a question one level of granularity off from the requirement, and the close shipped to the reporter as proof.

Granularity axes that produce this: per-child vs per-parent, per-row vs per-batch, per-record vs per-tenant, per-session vs per-user, live vs archived, draft vs published, one axis vs the composite key.

- Before closing WAD, re-read the reporter's **earliest** clear statement of the rule, not the latest paraphrase and not your ticket summary. Paraphrase drift is how the scope shifts.
- Reproduce at **that** granularity explicitly, and name the granularity in the close. Naming it is what makes the close falsifiable: an unnamed scope reads as "we checked everything", so the reporter has nothing to point at when it is the wrong scope, and the only move left to them is to re-raise the whole report.
- **A re-raised report is evidence against your model of the rule, not against the reporter.** By the 2nd re-raise the live hypothesis is "I am testing the wrong scope", not "they are confused".
- A WAD verdict that contradicts a repeated complaint means re-confirm the SPEC. Do not re-demonstrate the behavior harder.

### 2. Cannot-reproduce requires the user's EXACT interaction, not an adjacent one

Two interactions that reach the same visible state can run entirely different code paths. Reaching the state a different way and finding it healthy disproves nothing.

The mechanism, from a real miss: the report was "the table controls never appear when the cursor is in a cell". The check *inserted* a table and watched the controls appear — the **document-change** path, which was never broken. The reported path was **selection-only** (clicking into an existing cell). Under `@tiptap/react` 3.19, `useEditor` no longer force-re-renders on every transaction, and the core emits `update` only when `tr.docChanged` — so a caret move produced no re-render and the controls were genuinely absent from the DOM. Same visible end state, different trigger, different result.

- Replay the reporter's **gesture**, in their order, from their starting state. "Insert a table" and "click into a table" are not the same test.
- Replay their environment where it is cheap, because each of these dimensions selects a different branch rather than merely restyling the same one: **viewport** crosses responsive breakpoints that mount different components; **role** changes which guarded branch renders at all; **locale/direction** flips RTL layout and swaps date/number parsers; **data volume** crosses pagination and virtualization thresholds so the target node may not be in the DOM; and **pre-existing vs created-this-session** decides whether the record is served from a warm client cache or fetched cold.
- **"They probably clicked the wrong thing" is a hypothesis about the user, not evidence.** It is not admissible in a close. Cost of that one in the field: two days and a repeat complaint.
- If you cannot obtain the exact gesture, the status is BLOCKED (missing repro precondition), not cannot-reproduce. See `browser-qa-discipline`.

### 3. A volunteered workaround is the highest-value diagnostic in the report

When a reporter says "it works if I do X first", they have handed you a controlled experiment they ran for free: X is the one differing precondition between broken and working.

In the case above, the workaround was "they appear when I click the border between the columns" — column resizing writes a `colwidth` attribute, which **is** a document change, which is exactly the trigger the broken path lacked. The workaround named the root cause before any code was read.

- Extract the workaround from the report before doing anything else, and write down what it changes that the broken path does not.
- Diff the two paths at the mechanism level: what event fires, what state is written, what re-render or invalidation is triggered.
- Never dismiss a workaround as "they found a way around it, lower priority". It is the free half of the root-cause analysis.

### 4. "The evidence was destroyed" is a claim to MEASURE, not to accept

Concluding "the exit cause is unknowable" ends the investigation with a claim you did not test. Test it.

The mechanism: a report concluded a log had been opened in truncate mode and the restart had overwritten the dead process's output. The code said `open(path, "ab")` — append. Running the shipped functions against a temp directory showed the previous instance's lines survive a restart, and that oversize rotation *preserves* them as `<name>.log.1`. The observed symptom — one banner, earliest entry belonging to the current instance — is produced by **rotation**, not truncation. A rotating handler means the base file is only ever the *current* generation, so "I searched the whole log and found nothing" is often a search of the wrong file.

Before recording "unknowable", check, in order:

- The rotated siblings: `<name>.log.1`, `.2`, `.gz`, and whatever the handler's `backupCount` implies.
- The archive / retention store, the aggregator, and the previous deploy's artifact directory.
- The backup or snapshot taken before the event.
- The reporter's own artifacts: screenshots, HAR, downloaded exports, the email that quoted the error.

Then record what you actually checked. "Unknowable" is only credible with a list attached.

### 5. File the issue BEFORE fixing — one bug at a time, deduped against the known cohort

Fixing first and filing afterwards means the record reflects what *survived the fix*, not what was *found*. Bugs merged into one commit disappear as separate facts; the regression that reappears next quarter has no ancestor to link to.

The loop that holds:

1. Reproduce from the actual failure output — the server-log traceback, the network response, the console error. No guessing. (Root-cause discipline lives in `systematic-debugging`; this gate only requires that you have it.)
2. Log the finding locally first.
3. **Dedup against the known cohort** — the existing issue list / cohort index — before creating anything. Re-filing a known bug pollutes the count and splits the history.
4. Pick ONE. File it with a before/after context body and the exact reproduction gesture from gate 2.
5. If issue creation is a tracked write, clear it through the host's write-approval gate (`devops-plugin` `rules/write-gate.md`, `agent-safety`) — this skill does not restate those approval mechanics, it only insists the filing happens *here*, before the fix.
6. Then fix. Then validate end-to-end on a **clean instance** — a clean instance is what separates "the fix works" from "the fix works on a box already carrying the state my debugging left behind" (a warmed cache, a manually corrected row, a still-loaded module). Then move to the next bug.

Filing precedes the fix. A fix with no filed issue is an undocumented behavior change: the diff records *what changed* but nothing records *what was wrong*, so the next person reading it cannot tell an intentional fix from an accidental regression.

### 6. A RETRACTED close carries an explicit re-open instruction

Closing something that was **retracted** by the reporter is different from closing something you **disproved**. Nothing was tested; the only fact recorded is that the reporter withdrew it. The next person to see the symptom has no way to know that.

The concrete save: a retracted report was closed `Won't Do` **with a note** saying that if the reporter raised it again it must be opened as a FRESH issue rather than dismissed a second time. The reporter later said he had cancelled a *different* report. That one sentence turned a judgement call into an obvious call.

- On any retracted / withdrawn / "never mind" close, write the trigger and the action into the resolution: *"if this recurs, open a fresh issue with X — do not dismiss as a duplicate of this one."*
- Name X concretely: the screenshot, the exact gesture, the timestamp, the role.
- Do the same for a deferred close ("won't do — out of scope"): name what would change the decision.

### 7. Decompose a permissions-shaped error before declaring it an external blocker

`Access is denied` reads like an infrastructure constraint, so it gets recorded as one and the check sits unrunnable. Frequently it is a **product defect wearing an infrastructure costume**.

The mechanism is one of measurement scope, not of measurement accuracy. A denial is emitted by whichever single dimension the call happened to combine — the operation, the mode or trigger shape, the target scope, the calling identity, or the client surface used to reach the service. One failing invocation varies all of them at once, so it identifies *that* something is privileged and never *which* thing. Recording that composite as "needs elevation" converts one unresolved measurement into a permanent constraint on the check, and — because elevating usually does make it pass — the wrong conclusion arrives with confirming evidence attached.

The closure consequence, which is what this skill owns:

- **Decomposition is a precondition for the BLOCKED verdict, not an optimization.** Until each dimension has been varied separately, "external blocker" is a guess wearing a measurement's clothes.
- Once decomposed, the close must **name the specific privileged dimension**. "Access denied, needs admin" is not a close; "registering this trigger shape without an explicit user id requires administrator, all other operations succeed unelevated" is.
- **If the check only passes with rights real users do not have, the passing run is the finding, not the fix.** Elevating (or re-running on a CI runner that is already administrator/root) turns the row green by removing the exact condition the defect lives in, so the green row is evidence of nothing and the defect ships.
- The decomposition **method** — varying operation / mode / scope / identity / API surface one at a time, and the rule that a CLI is not the service's API — is owned by `windows-script-and-task-authoring` (`claude-env-doctor`). Apply it there; do not re-derive it here.

### 8. Re-probe an environment blocker before you repeat it

An environment finding is a **timestamped observation, not a standing fact**. Restating it in a later turn converts a stale measurement into a permanent false constraint, and typically sends the user chasing a workaround they no longer need.

The mechanism is that the environment has other authors. Nothing in your session pins a service's liveness, a network route, a DNS answer, a firewall state, a token's validity, or a container's existence — a restart, a lease renewal, a background update, or the user acting between turns can flip any of them without producing a signal you would notice. So an environment measurement decays the moment it is taken, and restating it is asserting a fact you last observed under conditions that no longer necessarily hold.

The concrete case: "the host cannot reach the guest VM's listener, you need an elevated firewall rule" was stated twice in one session. On the third turn it was re-tested instead of restated — the connection succeeded and the URL returned 200 from the host, name resolution included. A VM restart between turns had changed the networking mode and host-firewall state. Cost of the two restatements: an admin-rights workaround the user did not need, plus a working deliverable hedged as unreachable.

- Before repeating "X is blocked" — and **always** before asking the user to run a privileged or destructive command — re-run the one-line probe.
- Stamp every environment finding with when it was measured and by what command, so its age is visible.
- Blockers expire silently in both directions: a passing environment can also go stale. Re-probe before a sign-off too.

## Decision framework

Walk down; the first row that matches decides the close.

| Situation | Gate that applies | Verdict |
|---|---|---|
| Report re-raised after a previous close | 1 | Re-read the earliest statement of the rule. Assume your granularity is wrong until re-confirmed. |
| You reproduced the behavior and it matches the spec | 1 | WAD — only if you can name the granularity you tested and cite where the rule was pinned. |
| You could not reproduce, using a different gesture | 2 | Not a close. Re-run the reporter's exact gesture. |
| You could not reproduce, using the exact gesture and environment | 2 | Cannot-reproduce — record the exact gesture, environment, and build you ran. |
| You could not obtain the reporter's gesture or environment | 2 | BLOCKED (per `browser-qa-discipline`), naming the missing precondition — never cannot-reproduce. |
| Reporter volunteered a workaround | 3 | Not a close. The workaround names the differing precondition — diff the two paths first. |
| Logs / traces appear missing | 4 | Not "unknowable" until you have checked `.1`, the archive, the backup, and the reporter's artifacts. |
| Root cause found, no issue filed yet | 5 | File first, deduped against the cohort, one bug. Then fix. |
| Reporter withdrew the report | 6 | Retracted close + the "if this comes back, open fresh with X" instruction. |
| `Access is denied` / 403 / `EACCES` | 7 | Not external until each dimension was varied separately and the privileged one is named. |
| Blocker measured in an earlier turn | 8 | Re-probe before restating. A stale blocker is a false constraint. |
| None of the above; run completed and diverged from spec | — | FAIL. File the bug. Link it. (`browser-qa-discipline` owns the word.) |

## Safety gates

- **Never** send a close to a reporter as proof when the report has already been re-raised once — a second wrong close costs the reporter's willingness to report at all, which is the one input this whole discipline depends on.
- **Never** record `cannot reproduce` when the reporter's exact gesture was unavailable; use BLOCKED with the missing precondition named (`browser-qa-discipline`). A cannot-reproduce close silently transfers the burden of proof onto the reporter.
- **Never** let a reproduction attempt mutate data that is not disposable while chasing the reporter's gesture — bounds are owned by `safe-destructive-testing`. Chasing an exact repro is the single most common reason a QA pass wanders onto real records.
- **Never** delete, rotate, truncate, or "clean up" a log while investigating whether evidence survives. The rotated generation you are about to overwrite is usually the one holding the answer (gate 4).
- **Never** ask the user for elevated rights, a privileged shell, or a destructive command on the strength of a blocker measured in an earlier turn — re-probe first (gate 8). The cost of the probe is one command; the cost of the unnecessary escalation is borne by the user.
- **Never** close a defect on a build other than the one it was reported against without saying so (`runtime-reality-check`).

## Validation checklist

Before recording any close:

- [ ] The close names the **granularity** it was reproduced at, and that granularity traces to the reporter's earliest clear statement of the rule.
- [ ] For a re-raised report: the spec was re-confirmed, not just the behavior re-demonstrated.
- [ ] The reproduction used the reporter's **exact gesture**, from their starting state, on the build they reported against (`runtime-reality-check`).
- [ ] Any volunteered workaround is quoted in the close, with what it changes that the broken path does not.
- [ ] No close rests on "the user probably clicked the wrong thing".
- [ ] "Evidence gone" is backed by a list of what was checked — rotated `.1`, archive, backup, reporter artifacts.
- [ ] The issue existed before the fix; it was deduped against the known cohort; it is one bug, not a merged batch.
- [ ] A retracted close carries an explicit "if this comes back, open fresh with X" instruction.
- [ ] A permissions-shaped blocker was decomposed one dimension at a time, and the close names which dimension is privileged.
- [ ] Every environment blocker restated in this turn was re-probed in this turn, with the probe and timestamp recorded.
- [ ] The status word used is one of `browser-qa-discipline`'s — no invented statuses.

## Output format

A close is one record. Minimum shape:

```
CLOSE — <defect id / title>
  Verdict: <working-as-designed | cannot-reproduce | blocked-external | retracted | deferred | FAIL>
  Rule as reported: "<the reporter's EARLIEST clear statement, quoted>"
  Granularity tested: <per-parent | per-child | per-tenant | per-batch | composite key | n/a>
  Gesture replayed: <exact steps, in order, from starting state <X>>
  Environment: <role / viewport / locale / data state / pre-existing vs created-this-run>
  Build: <commit-sha or version> — confirmed per runtime-reality-check at <timestamp>
  Reporter workaround: "<quoted>" -> differs from broken path by: <mechanism>
  Evidence checked: <artifacts; for an "evidence gone" claim, the LIST of locations checked>
  Re-open trigger: <required for retracted / deferred — "if this recurs, open fresh with X">
```

For a blocked-external close, one extra line, because the verdict is not admissible without it:

```
  Privileged dimension: <the ONE dimension that is privileged, after decomposition>
  Dimensions varied: <operation / mode / scope / identity / API surface — and the result of each>
  Measured at: <timestamp> by <exact probe command>
```

The verdict word must come from `browser-qa-discipline`'s vocabulary; the fields above describe *why the verdict is admissible*, not a new status set.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Works as designed" with proof screenshots sent to the reporter | A faithful reproduction of the *wrong* granularity is fully true and fully useless; it burns trust because it proves "fine" for a real gap | Re-read the earliest rule statement; reproduce at that scope; name the scope in the close |
| "They keep re-raising it, they're confused" | The base rate says a repeated complaint is a spec mismatch, not a user error; each iteration ships another wrong close | Treat re-raise as evidence your model of the rule is wrong |
| Reproducing by creating the record, when the report was about an existing one | Create and select are different code paths — one fires a change event, one does not; the healthy path proves nothing about the broken one | Replay the exact gesture from the exact starting state |
| "Cannot reproduce — probably user error" | A hypothesis about the user recorded as a verdict; unfalsifiable and un-actionable | Cannot-reproduce only after the exact gesture; otherwise BLOCKED with the missing precondition named |
| Filing the workaround under "notes" and moving on | Discards the one controlled experiment isolating the differing precondition | Lead the analysis with the workaround; diff broken vs working at the mechanism level |
| "The log was overwritten, cause unknowable" | Rotating handlers keep only the current generation in the base file; the previous one is usually right there as `.1` | Check `.1`, archive, backup, and reporter artifacts; list what you checked |
| Fixing first, filing "once it's confirmed" | The record ends up describing what survived the fix, not what was found; the regression has no ancestor | File before fixing, one bug at a time |
| Batch-filing every bug found in a sweep | Duplicates the known cohort, splits history, and buries per-bug approval | Dedup against the cohort index; file one at a time with explicit per-issue approval |
| Closing a retraction as a plain duplicate/won't-do | The next occurrence starts from zero and risks being dismissed twice | Write the "if this comes back, open fresh with X" instruction into the resolution |
| "`Access is denied` — needs elevation, external blocker" | One invocation varies every dimension at once, so it shows *that* something is privileged and never *which*; the composite gets recorded as a standing constraint | Decompose first (method: `windows-script-and-task-authoring`), then close naming the one privileged dimension |
| Verifying only on an admin/root CI runner | The privileged environment removes the exact condition the defect lives in, so the green row is evidence of nothing | Reproduce under the least-privileged identity a real user has |
| Restating last turn's environment blocker | Blockers expire silently; the restatement becomes a permanent false constraint and sends the user after a workaround they no longer need | Re-probe with the one-line check before restating, and stamp findings with their measurement time |

## Portability rationale

The eight gates are properties of the *closure decision*, not of any stack. They apply to a browser defect, an API defect, a CLI defect, a data-pipeline defect, or a hardware ticket, because each gate turns on something universal to defect reports:

- A report is a claim about an intended rule; a reproduction is a measurement of actual behavior. That gap exists in every medium (gates 1, 3).
- Two routes to the same observable state are two code paths in every system (gate 2).
- Logs rotate, retention expires, and artifacts survive elsewhere, whatever writes them (gate 4).
- A record of what was found is a different artifact from a diff of what changed (gate 5).
- A withdrawal is not a disproof in any tracker (gate 6).
- A refusal names a boundary, not which part of the call crossed it (gate 7).
- An environment has authors other than you, in every environment (gate 8).

The skill does not assume a tracker, a status taxonomy beyond `browser-qa-discipline`'s, a log format, a language, an operating system, or that the reporter is external. It does assume a defect report exists and that a verdict is about to be attached to it — without those, none of the gates has anything to gate.

## Cross-references

- `browser-qa-discipline` — owns the PASS / BLOCKED / NOT-TESTABLE / FAIL vocabulary, the per-check evidence requirement, and the code-read-is-not-runtime-evidence rule. Use its words; this skill decides the *closure*, not the status names.
- `windows-script-and-task-authoring` (`claude-env-doctor`) — owns the vary-one-dimension-at-a-time decomposition method and the privileged-environment blind spot. Gate 7 requires that decomposition to have happened; it does not re-teach it.
- `agent-safety` / `devops-plugin` `rules/write-gate.md` — own how approval for a tracked write (creating the issue in gate 5) is obtained. Gate 5 owns only the ordering: file before fix.
- `runtime-reality-check` — confirms the target is actually running the expected build; a reproduction against the wrong build is not a reproduction.
- `safe-destructive-testing` — bounds what a reproduction attempt may mutate while chasing the reporter's exact gesture.
- `console-and-network-capture` — produces the artifacts that make a cannot-reproduce close auditable.
- `uat-readiness-report` — rolls closed and open defects into the sign-off; a close made under these gates is the unit it consumes.
- `systematic-debugging` (superpowers) — owns root-cause method once gate 5 has you reproducing from real failure output.
