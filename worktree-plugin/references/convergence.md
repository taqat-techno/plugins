# Convergence — turning lanes into one integrated trunk

Integration is where the defects that no lane could see become visible. It is
also the only place the Main Agent commits.

> **Green per lane says nothing about green per release.** Ten independently
> green branches once merged into a trunk with nine failures — **not one of them
> visible from any single branch**, and one of them a real latent defect that had
> been shipping unexercised for several packages.

## The ten steps

### 1 — Verify each lane from git, not from its report

For every lane at the gate:

```bash
git -C <worktree> diff --cached --name-only     # the actual staged set
git -C <worktree> rev-parse HEAD                # still the base? nothing committed?
git -C <worktree> symbolic-ref --short HEAD     # the branch it claims to be on
```

Check the staged paths against the lane's `Owns`. **A lane that touched
anything outside its ownership set is excluded from this convergence** and
returned to its owner — not merged with an apology.

### 2 — Capture a pre-integration baseline

Run the `[release]` contract on the trunk **before** merging anything, and keep
the result.

This is the step that converts post-merge failures from arguments into
assignments. Without a baseline, every failure is *"was that already broken?"*
With one, every failure is attributable to a named lane.

### 3 — Predict conflicts, textual and semantic

Textual conflicts are the easy half. The dangerous half is semantic: two lanes
that never touch the same line and still contradict each other — one removing an
elevation it proved unnecessary while another adds one it proved necessary, each
correct on its own evidence.

Look for: the same component in two `Owns` sets; two lanes citing each other's
findings; a shared registry, index, or generated file; anything both lanes call
a fix to the same symptom.

### 4 — Re-derive the merge order immediately before merging

**A pre-written merge resolution decays while work continues.** One set of
predicted union counts was already wrong within an hour of being written, and
merging to the written figure would have silently dropped test classes — a
dropped import does not fail, the class simply never runs.

Re-derive. Do not trust the plan you wrote earlier in the same session.

Order by: hard correctness constraints first (a branch whose fix another branch
depends on), then dependency order, then size. **State any hard constraint
explicitly** — *"z-repairs must land before x-portal, because x-portal alone
carries two red tests whose only correct fix lives on the other branch; if a
merge fixes them there, the defect becomes the specification."*

### 5 — One consolidated approval request

The human authorises **once per convergence**, not once per branch:

```
CONVERGENCE 2 — 10 branches, 74 commits, 21 components

  order   branch              files   predicted conflicts
  1       lane/u-ui              18    —
  2       lane/z-repairs         15    operation_sale (union with #6)
  ...
  HARD CONSTRAINT: z-repairs before x-portal (see step 4)

  Baseline captured: 957 tests, 1 failed, 0 errors
  Expectation after merge: 21/21 components installed — a run reporting 19/19
  is a FALSE PASS, because the two new components would simply not have built.

Approve?
```

### 6 — Merge centrally, resolve to the union

The Main Agent merges. Never a worker — and never ask a worker to commit
something your own session would be prompted for. That is permission laundering
and `SendMessage` forbids it.

Resolve conflicts **to the union**, never to a side, unless a hard constraint
says otherwise. Then verify structurally:

- zero conflict markers left
- zero duplicated imports or registrations
- **every named test module present on disk** — this is the check that catches
  both a dropped import and an invented one

### 7 — Validate against a stated expectation

Run the `[release]` contract. Compare against the number stated in step 5.

**A run that reports the previous component count is a false pass.** The new
components would not have installed, and nothing in the output would say so.

### 8 — Attribute every new failure

Diff against the baseline. For each new failure, name the lane and the cause:

```
component            cause                                           owner
notifications ×2     new constraint refusing a fixture that assigns   agent 3
                     a role-less user — the fixture has been creating
                     unperformable work for several packages
portal ×3            idempotency guard failed its first real
                     exercise — a retry genuinely posts twice         agent 4
```

A merge-caused failure is not a regression to hide; it is the run working. Route
it, do not absorb it.

### 9 — Tell every gate-holder

**Releasing a gate is an event the holder must be told about.**

Committing a lane's work without telling the lane leaves it reporting a state
that no longer exists — and it cannot detect this from inside its own session.
Lanes once reported *"staged, holding at the gate"* for four hours after their
work was already committed and merged, and it surfaced only when one of them
happened to notice a commit on its own branch that it had not made.

Two corollaries worth passing on:

- **Finding a commit you did not make is a question, not a provocation.** *Who
  committed this, and under what authorisation?* is answerable from
  `git reflog show <branch> --date=iso` in one command.
- **Do not `git reset --soft` a commit you did not make.** Check
  `git merge-base --is-ancestor <sha> <default>` first. If it is an ancestor, the
  reset removes nothing from the trunk and merely leaves the branch pointer
  behind an already-merged commit — producing a phantom "uncommitted work"
  report on the next check.

### 10 — Stamp the next wave base

The new trunk tip is the base for the next wave. Every lane cut afterwards uses
it, which is what makes in-wave dynamic scheduling safe: a new lane can never
depend on work that is still staged somewhere else.

## Retiring lanes

A lane is retired only when its branch is an ancestor of the default branch and
its work landed — `merged` on the board. `/worktree:clean` refuses any lane with
an open assignment or an unmerged branch, whatever the tree looks like.
