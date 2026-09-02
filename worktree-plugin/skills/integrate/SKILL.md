---
name: integrate
description: Converge finished lanes into the trunk - verify each from git, capture a pre-merge baseline, re-derive the merge order, merge centrally after one approval, validate against a stated expectation, and tell every gate holder. Main agent only, user-invoked.
disable-model-invocation: true
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *)
---

# Converge lanes

Turn several staged lanes into one integrated trunk. **Main Agent only, and
user-invoked — this skill commits and merges.**

`$0` may name the lanes. With no argument: every lane at the gate.

Load `references/convergence.md` and follow it. The summary below is the shape;
that file is the contract.

## Never skip these four

They are the ones that get dropped under time pressure, and each has cost a real
release.

**1. Verify every lane from git, not from its report.** Staged set, base
unchanged, branch as claimed, and **nothing outside its ownership set**. A lane
that touched shared ground is excluded from this convergence and returned to its
owner.

**2. Capture the baseline before merging anything.** Run the `[release]`
contract on the trunk first and keep the result. This is what turns post-merge
failures from *"was that already broken?"* into an assignment with a name on it.

**3. Re-derive the merge order immediately before merging.** A pre-written
resolution decays while work continues — one predicted union was wrong within an
hour, and merging to the written figure would have silently dropped test classes.
A dropped import does not fail; the class simply never runs.

**4. Tell every gate-holder when the gate opens.** Lanes have reported *"staged,
holding at the gate"* for hours after their work was already merged, because
nobody told them. A lane cannot detect this from inside its own session.

## One approval, not one per branch

Present the whole convergence and ask once:

```
CONVERGENCE <n> — <k> branches, <n> commits, <c> components

  order  branch            files  predicted conflicts
  1      lane/u-ui            18  —
  2      lane/z-repairs       15  operation_sale (union with #4)
  ...
  HARD CONSTRAINT: z-repairs before x-portal — x-portal alone carries two red
  tests whose only correct fix lives on the other branch.

  Baseline: 957 tests, 1 failed, 0 errors
  Expectation after merge: 21/21 components — a run reporting 19/19 is a
  FALSE PASS, because the two new components would not have built.

Approve?
```

State the expectation **as a number**. A run reporting the previous count is a
false pass and nothing in its output will say so.

## Merging

Merge in the derived order. Resolve conflicts **to the union**, never to a side,
unless a hard constraint says otherwise. Then verify structurally:

- zero conflict markers
- zero duplicated imports or registrations
- **every named test module present on disk** — catches a dropped import *and* an
  invented one

Semantic conflicts are the dangerous half: two lanes that never touch the same
line and still contradict each other — one removing a permission it proved
unnecessary while another adds one it proved necessary, each correct on its own
evidence. Rule from the merged trunk, not from either report.

## After the merge

1. Run the `[release]` contract against the stated expectation.
2. Diff against the baseline; **attribute every new failure to a named owner.** A
   merge-caused failure is the run working — route it, do not absorb it.
3. Reconcile the completion contract, if the plan carries one —
   `references/completion-contract.md`, convergence step 8b. You re-verify every
   CC on the merged trunk; no COMPLETE verdict while any CC is UNMET or
   uncovered.
4. Notify every gate-holder, by name, that its work is committed and merged.
5. Stamp the new trunk tip as the next wave base.

## Guardrails

- **Never ask a worker to commit, merge, or push** — including to avoid a
  permission prompt. `SendMessage` forbids routing a blocked action through a
  peer; route it back to the user instead.
- Never merge on a merge plan written earlier than this run.
- Never accept a lane's own test result as the integration result.
- Never mark a contract entry MET from a lane's contract evidence or an
  earlier convergence.
- Never release a gate silently.
- Never `git reset --soft` a commit you did not make. Check
  `git merge-base --is-ancestor <sha> <default>` first — if it is an ancestor the
  reset removes nothing from the trunk and only produces a phantom
  "uncommitted work" report on the next check.
