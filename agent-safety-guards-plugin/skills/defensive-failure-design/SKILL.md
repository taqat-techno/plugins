---
name: defensive-failure-design
description: How code must behave when something goes wrong — language- and framework-neutral. Owns the normalisation-is-not-authorisation rule (if a system declares a difference insignificant for MATCHING, that same collapsed comparison must not be what decides an automatic BIND or grant; collapse it for the blocking/duplicate decision, keep the exact value only for presentation and ordering, and check the clamp formula itself because `min(tier, NORMALIZED)` maps an archived match onto the live class where `max` is correct). Owns the scope-hint degradation rule (a hint that exists only to narrow a search degrades to "ignored" when it cannot be resolved, never to fatal — otherwise a derived, export-only, documented-as-ignored column hard-fails whole rows that used to import; if the narrowed search is then genuinely ambiguous THAT is the error to raise, and its message must name the column or scope that failed to resolve plus how to opt out). Owns the wrong-step diagnosis (when a shipped fix does not recover the machine, "is the fix present?" is the useless question — enumerate the branches at the entry point and determine which one production is actually on, because a correct fix on an unexecuted branch is indistinguishable from no fix). Owns the crash-context capture rule (snapshot diagnostics in the `except`, before cleanup — a `finally` that nulls state runs before the post-mortem reads it, so the record describes a machine that had nothing). Owns the silence-assertion rule (a test asserting that nothing happened passes identically against code with no handler at all, so pair it with a positive assertion and prove it by reverting the fix). Activates when writing or reviewing a failure path, an error branch, a retry or fallback, a normalisation/matching/dedup rule that also feeds an automatic bind, a scoping hint on a lookup, a crash recorder or post-mortem log, a teardown beside a diagnostic, or a test whose expected outcome is that nothing happens — and when a shipped fix did not change production behaviour.
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - normalisation is not authorisation (a difference collapsed for matching must not decide a bind, a grant, or an identity — and the tie-break clamp's direction is part of the rule)
  - scope-hint degradation (an unresolvable narrowing hint is ignored, never fatal; the ambiguity it was meant to prevent is the error worth raising, named by the scope that failed)
  - error-message content for a failed narrowing (name the column/scope that created the scope and how to opt out, so the operator can tell which of the two lookups failed)
  - the wrong-step diagnosis for a shipped fix that did not recover the machine (enumerate entry-point branches; ask which one production takes)
  - crash-context capture in the `except`, before teardown (re-check every consumer that reads state after a failure once cleanup is added)
  - the silence-assertion rule (pair every "nothing happened" assertion with a positive one, and prove it by reverting the fix)
defers_to:
  - test-result-evidence skill (this plugin) for the general rule that a passing run is not proof until you have shown it could have failed — the named discriminator, the control on the control, and the collection-error reading
  - test-double-seams skill (this plugin) for the per-branch coverage ledger form of a branch enumeration (which side of the seam each branch's tests called)
  - structural-assertions skill (this plugin) for proving by parser that no path reaches an unsafe primitive
  - agent-safety skill (this plugin) for what a green verdict is allowed to authorize
  - the user for every policy call about what an ambiguous match should do
user_invocable: false
---

# defensive-failure-design

## Purpose

Most of the damage a program does happens on the path nobody rehearsed. The failure path is written last, reviewed least, and exercised only by the situation you were trying to avoid — so its defects survive review and then decide, silently, which record gets bound, which row gets rejected, and what the post-mortem is allowed to say. This skill is the small set of rules that keep an error branch honest: never let a comparison you deliberately blurred be the one that grants access, never let a hint that was only meant to narrow become a veto, never conclude a fix is present without asking which path production takes, never let teardown run before the recorder, and never accept a test whose only claim is that nothing happened.

## When to use

Activate when any of these appear:

- A **matching, normalisation, dedup, or fuzzy-lookup rule** is being written — casefold, trim, strip accents, collapse whitespace, slugify — and its result feeds anything that binds, grants, merges, or assigns ownership.
- A **tie-break, ranking, or confidence tier** decides between candidates, especially one expressed as a formula (`min`/`max`/clamp against a named tier).
- A lookup is being **scoped by a hint** — a parent column, a tenant, a namespace, a `--scope` flag — added to stop it binding too widely.
- An **error branch, retry, fallback, or degraded mode** is being added to a path that previously succeeded.
- A **crash recorder, post-mortem log, or diagnostic snapshot** is being added, or cleanup (`finally`, teardown, context-manager exit, `defer`) is being added to a path a diagnostic already reads.
- A **shipped fix did not change production behaviour**, and the next instinct is to look for a defect inside the fix.
- A test's expected outcome is that **nothing happens** — no notification, no log line, no write, no exception.

Do NOT use this for ordinary happy-path design, for framework-specific error-handling mechanics (the stack's own skill owns those), or to relitigate an error taxonomy that already works.

## The rules

### 1. A normalisation rule must not become an authorisation rule

If the system declares a difference insignificant **for matching**, that same collapsed comparison must not be what decides an automatic **bind**.

The worked case: match ranking was specified as `live_exact > live_normalized > archived`, so a live record would beat an archived namesake. But the normaliser casefolds *because the identity model declares case meaningless* — so using case as the tie-break that authorises an automatic bind contradicts the very rule that produced the match. Two live records differing only in case stop tying, and the stray one silently wins every child record that referenced the name.

- **Collapse the difference for the blocking decision.** Duplicate detection, ambiguity detection, and "should this stop and ask?" all run on the normalised value. If two candidates are equal under the normaliser, they *tie* — and a tie on an automatic bind is an error, not a race to be broken.
- **Keep the exact value for presentation and ordering only.** Show the operator the original casing, sort by it, log it. Do not let it confer identity or access.
- **Check the clamp formula, not just its intent.** The first proposed fix was `min(tier, LIVE_NORMALIZED)`, which is wrong in a way the prose hides — it maps an *archived* match down onto the live class. `max(tier, LIVE_NORMALIZED)` is correct. A brief that contains a formula needs the formula evaluated against each tier, not just the sentence around it read.

The general shape: any pair of rules of the form "X is irrelevant here" and "X decides this" is a defect even when both rules are individually reasonable.

### 2. A scope hint must never veto the lookup it was meant to narrow

A hint added to stop a lookup binding too widely has one job — narrowing. It must degrade to **ignored** when it cannot be resolved, never to **fatal**.

The worked case: an unscoped foreign-key lookup in an importer could silently bind across parents, so it was scoped by the row's parent columns. Review caught that an unresolvable value in a **derived, export-only, documented-as-ignored** column now hard-failed the entire row — converting a silent mis-bind into a loud regression on files that had always imported cleanly.

- **Unresolvable hint → drop the hint, run the wider search.** The pre-hint behaviour is the floor; the hint may only improve on it.
- **If the narrowed search is then genuinely ambiguous, THAT is the error to raise.** Ambiguity is the condition the scoping existed to prevent, and it is worth stopping for. An unreadable hint is not.
- **The message must name the scope that failed.** State which column or parameter created the scope, that it could not be resolved, and how to opt out. Without that, an operator cannot tell whether the hint failed or the target lookup failed — two different fixes behind one string.
- **Grade the column before you let it fail anything.** A column the docs describe as ignored, derived, or export-only has no standing to reject a row.

### 3. A fix can be complete and still guard the wrong step

When a shipped fix does not recover the machine, **"is the fix present?" is the useless question.**

The worked case: supervision of a child process was real — instantiated in the packaged startup lifespan, started, watching, bounded restarts, exit codes logged. There was no defect inside it. The failure entered one step earlier: a later component's DNS lookup killed startup two seconds after the child had already spawned, and the teardown living after `yield` had nothing guarding it, so the child was orphaned. Its ownership manifest still vouched for it, so every subsequent boot took the **reattach** path rather than the spawn path. The fix supervised a *spawned* child well; it had never been asked to supervise one it *inherited*.

- **Enumerate the branches at the entry point** — for example `inspect → spawn | reattach | refuse` — and determine which one production is actually on. Write the list from the dispatch itself, not from memory or from the tests.
- **A correct fix on an unexecuted branch is indistinguishable from no fix at all.** Verifying the fix's own code proves nothing about the run; the branch selector is the thing to instrument.
- **Ask what changed the branch selection.** Orphaned state, a stale manifest, a cached handle, or a lock file can flip production onto a path that existed but was never the one under test.
- Log or print the selected branch at the entry point. It is one line and it retires this whole class of investigation.

### 4. Snapshot crash context in the `except`, not at recording time

A `try`/`finally` was added so a failed startup tears down what it built, and a crash recorder read engine and migration state to write the crash record. The `finally` had already nulled both by the time the framework re-raised, so the record would have reported "no engine, no migration" about a machine that had both.

- **Capture diagnostics in the `except`, before cleanup runs.** Build the snapshot dict there, then let teardown proceed; write the record afterwards from the captured values.
- **When you add cleanup to a failure path, re-check every consumer that reads state AFTER the failure.** Crash recorders, error reporters, retry logic, exit-code mappers, and shutdown logs all read state at a moment cleanup has already moved.
- **Teardown and post-mortem want the same state at different times, and teardown wins.** That ordering is not negotiable, so the recorder must take its copy first rather than expecting the state to survive.
- The failure is silent by construction — the record is written, is well-formed, and is wrong. Nothing goes red.

### 5. "Assert silence" tests are vacuous against a swallowing bug

Two tests for a notification handler asserted `notifications).toHaveLength(0)` for cases that should be silent. Those pass identically on code that has **no handler at all** — that is, on the exact bug they were meant to pin. When the failure mode *is* "nothing happens", a test that asserts nothing happens pins nothing.

- **Pair every silence assertion with a positive one.** Assert the suppressed case is silent *and* that the error still reaches the user by the other route — the inline field error, the returned status, the log line. The pair is what distinguishes "correctly suppressed" from "never handled".
- **Prove the test by reverting the fix.** Restoring the old code made six tests fail, which is the only real proof they discriminate. A silence test that survives the revert is decoration.
- Prefer asserting on a **discriminating observable** over a count of zero — the handler was called, the branch was taken, the specific channel stayed empty while another carried the message.

`test-result-evidence` (this plugin) owns the general rule that a passing run is not proof until you have shown it could have failed, including the named discriminator and the control on the control. This rule is only its silence-shaped instance — go there for how to read the run.

## Decision framework

```
writing a normaliser/matcher?   --> does its output authorise a bind? if yes, ties must STOP, not be broken by the collapsed field
tie-break on a match tier?      --> evaluate the clamp per tier; min() maps archived onto live, max() is the safe direction
exact value still needed?       --> presentation and ordering only; never identity, access, or ownership
adding a scope hint?            --> unresolvable => ignore the hint and run the wider search; never fail the row
narrowed search now ambiguous?  --> THAT is the error; name the scope column and the opt-out in the message
column is derived/export-only?  --> it has no standing to reject anything
shipped fix didn't help?        --> stop auditing the fix; enumerate entry-point branches and find which one production takes
which branch is live?           --> log the selection at the entry point; a fix on an unexecuted branch == no fix
adding cleanup to a failure path? --> re-check every consumer that reads state AFTER the failure
crash recorder present?         --> capture in the `except` before teardown; `finally` runs first and wins
test expects nothing to happen? --> pair with a positive assertion; revert the fix and watch it fail, or it proves nothing
```

## Validation checklist

- [ ] No value that the system collapses for matching is used to decide a bind, a grant, or an identity.
- [ ] A tie under the normaliser stops for a human decision rather than being broken by the collapsed field.
- [ ] Every tier/clamp formula was evaluated against each tier by hand, not just read as prose.
- [ ] Every scoping hint degrades to ignored when unresolvable; none of them can fail a row on its own.
- [ ] The error raised for a genuinely ambiguous narrowed search names the scope that created it and the opt-out.
- [ ] Columns documented as derived, export-only, or ignored reject nothing.
- [ ] Any "the fix is shipped but nothing changed" investigation enumerated the entry point's branches and identified the live one before looking inside the fix.
- [ ] The selected branch is observable at runtime (logged or printed) at the entry point.
- [ ] Every diagnostic that reads post-failure state captures it in the `except`, before cleanup.
- [ ] Every consumer reading state after a failure was re-checked when cleanup was added to that path.
- [ ] Every silence assertion is paired with a positive assertion, and the pair was proven by reverting the fix.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Break a normalised-match tie by exact case | The normaliser casefolds *because* case is declared meaningless; the tie-break contradicts the rule that produced the match | Treat the tie as an error on an automatic bind; keep case for display only |
| Clamp a match tier with `min(tier, LIVE_NORMALIZED)` | Maps an *archived* match down onto the live class, promoting exactly the candidate the tiers existed to demote | `max(tier, LIVE_NORMALIZED)`; evaluate the formula per tier before shipping it |
| Let an unresolvable scope hint fail the row | Turns a silent mis-bind into a loud regression on files that always imported | Ignore the hint, run the wider search, and raise only if the result is ambiguous |
| Raise "value not found" for a failed narrowing | The operator cannot tell whether the hint or the target lookup failed — two fixes behind one string | Name the scope column that failed to resolve and how to opt out |
| Let a derived / export-only column veto an import | It carries no authority the docs ever claimed for it | Grade the column first; ignored columns reject nothing |
| Audit the inside of a shipped fix that didn't help | A correct fix on an unexecuted branch looks identical to no fix | Enumerate the entry point's branches; determine which one production takes |
| Infer the live branch from the code you just wrote | Orphaned state or a stale manifest can flip production onto a branch that was never under test | Log the branch selection at the entry point and read it |
| Read engine/migration state at crash-record time | `finally` has already nulled it, so the record describes a machine that had nothing | Capture the snapshot in the `except`, before cleanup, and write it afterwards |
| Add teardown to a failure path and stop there | Every post-failure consumer now reads state that moved under it, silently and without going red | Re-check each consumer that reads after the failure when cleanup is introduced |
| Assert `toHaveLength(0)` for a case that should be silent | Passes identically against code with no handler at all — against the exact bug | Pair it with a positive assertion that the error still reaches the user elsewhere |
| Ship a silence test without reverting the fix | A test that survives the revert never discriminated | Revert, confirm it goes red, restore |

## Cross-references

- `test-result-evidence` (skill, this plugin) — owns the epistemics of a test RESULT, including the named discriminator, proving which artifact ran, and reading a collection error as zero-tests-ran. Rule 5 is only the silence-shaped instance of that rule; the general "prove it could have failed" discipline lives there.
- `test-double-seams` (skill, this plugin) — owns the per-branch coverage ledger built from the same enumeration rule 3 uses, marking which side of the seam each branch's tests called. Rule 3 is the diagnosis-time use of that enumeration (which branch is production ON), that skill is the coverage-time use (which branch is tested ACROSS).
- `structural-assertions` (skill, this plugin) — owns proving by parser that no exit path reaches an unsafe primitive, which is how a rule-1 or rule-2 guarantee is asserted rather than asserted-about.
- `agent-safety` (skill, this plugin) — owns what a green verdict may authorize, and the report-don't-silently-patch rule for a defect of this shape found while doing something else.
- The user — owns the policy call for what an ambiguous match should do (stop, prompt, or pick). This skill only insists the ambiguity is surfaced rather than resolved by a blurred comparison.
