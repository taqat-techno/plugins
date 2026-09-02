# The completion contract

A **completion contract** states what must be objectively true of the whole
integrated result before a plan-driven parallel run may be called complete. It
sits above the work packages: a package's `Acceptance` says what one lane must
prove in its own worktree; the contract says what the *task* must deliver, in
the user's terms, on the trunk, after every lane has converged.

It exists because per-lane green says nothing about the task. Ten green lanes
can converge into a trunk that still does not do what was asked — an outcome
nobody's package owned, a number nobody re-measured, a requirement the user
amended mid-run that no lane ever heard about.

## When a contract is warranted

Write one when work will run as lanes and the request has more than one
independently required outcome. Skip it — and say so — when:

- there is one work package: its `Acceptance` already is the contract;
- the work is a single-session job that will never be dispatched;
- the request has one outcome and the `[release]` expectation already names it.

The contract is proportional or it is noise. Never add one to a plan that will
not be executed in parallel.

## The entry

One entry per independently required outcome, in a top-level
`## Completion Contract` section of the plan, above the work packages.

```markdown
## Completion Contract  (revision 1)

- CC-01 — <outcome in the user's terms, observable on the integrated result>
  Verification: <the instrument: a [release] or [integration] test id, a command, or a named manual review>
  Expected: <the decisive observable; a number where one exists>
- CC-02 — ...

Amendments:
- <date> rev 2 — CC-03 ABANDONED: <reason> — decided by <who>
```

| Field | Rule | Why |
|---|---|---|
| id | `CC-nn`, stable for the life of the plan; never renumbered, never deleted | packages, briefs and reports cite it |
| Outcome | the requirement, observable on the trunk — an outcome ("every order row carries a currency"), not an activity ("migrate the orders table") | an activity is met the moment someone starts it |
| Verification | **names** an instrument defined once elsewhere — a `[release]` / `[integration]` test id from the plan, a command, or a named reviewer and artifact. Never a `[lane]` test: a lane proves itself in its own worktree, and a CC instrument is one the Main Agent runs on the trunk | restating the test here creates two definitions that drift; a `[lane]` instrument cannot be re-run at reconciliation |
| Expected | the observable that decides it: a count, a success-only marker, a specific assertion — plus the sentence *"if this were false, the run would show X"* | an expectation that cannot fail certifies nothing |

### Expectations that can fail

- **Measure; never copy.** A figure supplied in the request is a claim to
  verify, not the expectation to match. The instrument computes the value from
  source; the entry states the acceptance rule.
- **A number where one exists.** "21/21 components" — a run reporting the old
  count is a false pass, and nothing in its output says so (`convergence.md`
  step 7).
- **Prove the instrument on a known positive** before believing its negative.
  `report-template.md` already requires this of every lane instrument; it
  applies to every CC instrument too.
- **A manual review is a named reviewer and a named artifact**, not "reviewed".
  Use it only when no command can decide the outcome, and say why.

Whether a given run is evidence at all — which artifact it imported, whether
its discriminating tests executed, which signal is authoritative — is owned by
the `agent-safety-guards` plugin (`test-result-evidence`, `agent-safety`). This
file does not restate those rules; a CC whose instrument fails them is UNMET.

## Mapping packages to outcomes: `Satisfies`

Each work package declares `**Satisfies.** CC-01, CC-03`. A package may satisfy
several outcomes; several packages may satisfy one.

Two defects fall out of the mapping. Both are findings to report, never to
guess at:

| Finding | Meaning |
|---|---|
| A CC no package satisfies | an outcome the run cannot deliver — the plan is incomplete, or the entry is not a requirement |
| A package that satisfies nothing | work outside the contract — scope drift, or an outcome nobody wrote down |

Dispatch gate 2 queues a lane whose package has no `Satisfies` while the plan
carries a contract (`dispatch-gates.md`).

## States

| State | Where it lives | Set by |
|---|---|---|
| OPEN | implicit — every entry that is not abandoned | — |
| MET / UNMET | **rendered at reconciliation, never stored** | the Main Agent, by running `Verification` on the integrated trunk |
| ABANDONED | an amendment line in the plan, with the reason and who decided | the user's decision, recorded by the Main Agent |

MET is not written into the plan for the same reason the board is not written
to disk: a stored MET goes stale the moment the trunk moves, and is then
believed. If the state matters now, derive it now.

ABANDONED is a decision, not a result. It is honest non-completion: the run
ends with a visible handoff, never with "complete".

## Revision and amendments

The contract is revisioned. Before establishing it, and again before
reconciling it, **reread the original request and every amendment since**. A
change of scope increments the revision and is recorded under `Amendments:`;
affected entries are updated in place, never deleted. An outcome the user
withdraws becomes ABANDONED with the reason "withdrawn by user", not removed —
otherwise the final report cannot show what was asked against what was
delivered.

## Reconciliation

Run by the Main Agent, on the integrated trunk, at the final convergence — and
on demand, read-only, at any point to show where the run stands.
`convergence.md` step 8b is its place in the merge sequence.

1. **Reread the request and the amendments.** Confirm the revision matches the
   latest scope.
2. **Run every CC's `Verification` on the current trunk yourself.** A lane
   report's *contract evidence* says where to look; it is never the result.
   Never mark a CC MET from a report, a status line, or a prior convergence.
3. **Compare to `Expected`.** Met on the stated observable is MET. Anything
   else — a wrong count, a missing marker, an instrument that could not run, an
   instrument that failed its known-positive check — is UNMET. Say which signal
   you read.
4. **Take ABANDONED from the amendments**, and from nowhere else.
5. **Re-measure every number that will appear in the report**, immediately
   before writing it. A count carried forward from an earlier turn is a stale
   figure with a confident tone.
6. **Render the table and the verdict:**

```
COMPLETION CONTRACT — rev 2 — 2 met, 1 unmet, 1 abandoned — NOT COMPLETE
CC-01  MET        R-04 release run: 21/21 components (expected 21)   via WP-07, WP-09
CC-02  UNMET      probe returned 19/19 (expected 21)                  via WP-11
CC-03  ABANDONED  rev 2 — withdrawn by user
Uncovered: none
```

COMPLETE only when every CC is MET or ABANDONED-by-decision and none is
uncovered. Otherwise NOT COMPLETE, with the unmet ids named. A done report is
not composed while any required CC is OPEN or UNMET, and an abandoned CC is a
handoff in that report, not a footnote.

## What this file does not own

| Concern | Owner |
|---|---|
| a lane's definition of done | `plan-schema.md`, `Acceptance` |
| the form of a lane's evidence | `report-template.md` |
| the merge sequence, the baseline, the stated expectation | `convergence.md` |
| whether a run is evidence — could it have failed, which artifact ran, which signal counts | `agent-safety-guards`: `test-result-evidence`, `agent-safety` |
| a subagent's "done" is a claim | `agent-safety-guards`: `workflow-reliability` (principle); `convergence.md` step 1 (procedure) |
| a CI gate that swallows its exit code | `release-safety`: `github-actions-release-safety` |
| fresh evidence at the moment of any done claim | `superpowers:verification-before-completion`, where installed |
