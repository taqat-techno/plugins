---
name: completion-contract
description: Use when a plan is being prepared for lane-based parallel execution, when the main agent is about to dispatch or converge lanes, or when asked to define or reconcile what must be true before a coordinated task is complete. Not for single-session work.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *)
---

# Completion contract

Write down what must be objectively true of the whole result before a
plan-driven parallel run may be called complete — then prove it on the
integrated trunk, not from the lanes' reports. **Main Agent only.**

`$0` may name the plan file, a mode (`establish`, `audit`, `reconcile`), or
both. With no argument: `establish` if the plan has no `## Completion Contract`
section, otherwise `audit`.

Load `references/completion-contract.md` first. It owns the entry shape, the
states, the `Satisfies` mapping and the reconciliation procedure. This file is
only the workflow.

## First: is a contract warranted?

Stay silent if it is not. One work package, a single-session job, or one
outcome already named by the `[release]` expectation — say so and stop. The
contract is for a run with several independently required outcomes executed
as lanes.

## establish

1. **Reread the request and every amendment**, not your memory of it. List
   each independently required outcome — the things the user could notice
   missing one at a time.
2. **One `CC-nn` per outcome**, in the user's terms, observable on the
   integrated trunk. Each gets a `Verification` that names an instrument
   defined once in the plan, and an `Expected` that can fail: a number where
   one exists, a success-only marker, and the sentence *"if this were false,
   the run would show X"*.
3. **A figure the request supplies is measured, never copied** into `Expected`.
4. **No instrument can decide it?** Name a reviewer and an artifact. Do not
   invent a command that prints "ok".
5. **Say what will change, then write** the section into the plan. Additive
   only; the packages are not restructured.
6. If the packages already exist, add `**Satisfies.**` to each and run `audit`.

## audit

Report; never invent. Findings, in this order:

| Check | Finding |
|---|---|
| a CC no package `Satisfies` | an outcome the run cannot deliver |
| a package that `Satisfies` nothing | work outside the contract |
| a CC whose title is an activity, not an outcome | met the moment someone starts it |
| an `Expected` nothing measures, or that copies a supplied figure | cannot fail |
| a `Verification` that restates a test instead of naming it | two definitions that will drift |
| a `Verification` that names a `[lane]` test | the Main Agent cannot re-run it on the trunk — promote it to `[integration]` or `[release]` |
| a contract revision behind the latest amendment | the contract is not the scope |

## reconcile

Read-only with respect to git: it runs the named instruments and merges
nothing. Inside the merge sequence, `/worktree:integrate` performs this step
at `convergence.md` 8b.

1. Reread the request and amendments; confirm the revision.
2. For every CC, **run its `Verification` on the current trunk yourself**. A
   report's *contract evidence* is where to look, never the result.
3. MET on the stated observable; UNMET on anything else, and say which signal
   you read. ABANDONED comes from the amendments only.
4. **Re-measure every number in the report** immediately before writing it.
5. Render the table from the reference and give the verdict. COMPLETE only
   when every CC is MET or ABANDONED-by-decision and none is uncovered;
   otherwise NOT COMPLETE, unmet ids named. Never compose a done report over
   an open CC.

`bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"` shows which lanes are
`merged` — which packages the trunk can even contain yet.

## Guardrails

- Never store MET or UNMET in the plan. Derive it when it matters.
- Never delete or renumber a CC. Withdrawn means ABANDONED, with a reason.
- Never mark a CC MET from a lane's report, a status line, or an earlier
  convergence.
- Never write a `Verification` whose output would be the same if the outcome
  were false.
- Never add a contract to a plan that will not run as lanes.
