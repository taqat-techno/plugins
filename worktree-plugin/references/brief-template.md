# Lane brief template

The brief is written to `.claude/lanes/briefs/<lane>.md` **before** the dispatch
message is sent, and the message points at it. A message can be lost; the file
cannot.

Generate it from the plan work package plus the lane record. Do not compose it
freehand — a hand-written brief drifts from the plan, and the drift is invisible
until integration.

---

```markdown
# LANE <lane-id> — <package title>

**Assigned <date> to session `<owner>`.**<, moved from <previous lane> if reassigned>
Read `references/roles.md` for the worker protocol before starting.

## Cut from `<base>` — and why

<Which integration this base is. If it differs from an earlier lane's base, say
so and say what it means at merge: a lane based on an older snapshot builds
against code that does not exist yet.>

## Prerequisites — verified, not assumed

<The prerequisite line, resolved, with the evidence that each is complete.>

**Re-verify this yourself before starting.** Resolve the heading, not a line
offset. No lane starts on the controller's word alone.

## Your workspace

| | |
|---|---|
| Worktree | `<absolute path>` |
| (POSIX)  | `<the /mnt/c or /c form, if this machine has one>` |
| Branch   | `<branch>`, cut from `<base>` |
| <env key> | `<env value>`   <- one row per `env` line in the lane record |

<Any run command the project supplies through `env`. Work Tree does not invent
these and does not interpret them.>

## Your ownership set — and why it stops here

**`<owns>`. That is the whole set.**

<Why anything adjacent is excluded — a deferral, another lane's claim, a
sequencing constraint. A deferral that is not written down is indistinguishable
from a task nobody noticed.>

**Before editing any path outside this set, read that path in every other live
worktree.** One command per lane.

## The boundary that decides whether this package is right

<The one architectural invariant that makes this package pass or fail. One
paragraph. This is the thing most likely to be got wrong.>

## Tests you own

<Every `[lane]` test from the package. State that `[integration]` and
`[release]` tests are NOT this lane's to run.>

- Assert the negatives too — the movement that must *not* happen is a
  requirement, not an omission.
- Report tests as **defined against started, per class**. A gap between them
  must be explained, not published: if class setup raises, every test in that
  class is skipped and the run still reports zero failures.
- Prove any instrument on a known positive before believing its negative.

## Definition of done

<The package's acceptance criteria, numbered.>

<`Satisfies: CC-…` — each task-level outcome this package serves, with its
`Expected`, when the plan carries a Completion Contract. Whether a CC is MET is
decided by the Main Agent at convergence, on the integrated trunk — never by
this lane. Report evidence toward it; do not claim it.>

## Do not

- touch anything outside `<owns>`
- **commit, merge, or push.** A packet ends staged and reported and waits at the
  gate; the user authorises each commit
- edit any shared ledger, index, or register
- allocate a number, id, or name from a shared namespace — leave findings
  unnumbered and ask
- <package-specific prohibitions from **Must NOT be built**>

## Report after each packet

1. write `.claude/lanes/reports/<lane>-<nnn>.md`
2. leave the work **staged**
3. `SendMessage` to **"<main agent name>"**

In that order. The file first, always.
```

---

## Why each section is there

| Section | Failure it prevents |
|---|---|
| Base **and why** | A lane cut from a stale snapshot builds against code that does not exist |
| Prerequisites **verified + re-verify** | A wrongly-started lane that produced nothing |
| Both path spellings | Worktrees created from different shells register under different path forms; each shell then reports the other's as prunable |
| Ownership set **with rationale** | Two lanes editing one component |
| The deciding boundary | The single most likely way to fail the gate, stated once, in advance |
| Test ownership | Duplicated expensive runs, and integration tests run by the wrong party |
| Explicit **Do not** | Scope drift, and shared-namespace collisions |
| **Satisfies** | A lane serving no required outcome, and a lane claiming a task-level completion it cannot see |
| Report protocol **in order** | A lost message costing work instead of latency |
