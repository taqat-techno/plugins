---
name: plan-for-parallel
description: Use when writing, refining or auditing a multi-phase implementation plan, breaking a large project into phases or work packages, or deciding what could be built in parallel by several agents. Adds the few fields that make delegation computable - prerequisites, ownership, laneability, test levels, acceptance, negative scope - and reports what a plan cannot answer.
allowed-tools: Bash(bash "${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh"*), Bash(bash ${CLAUDE_PLUGIN_ROOT}/scripts/wt-lanes.sh *)
---

# Plan for parallel execution

Make a plan **delegation-ready**: enough structure that whoever executes it can
compute what is ready, what may run concurrently, and what done means — without
re-deriving a dependency graph from prose at execution time.

`$0` may name the plan file. With no argument, work on the plan in hand.

Load `references/plan-schema.md` for the field definitions and a worked example.

## First: is this plan worth the overhead?

**Stay silent if it is not.** Skip this entirely when the work is one phase, has
no independent work packages, or is plainly a single-session job. The metadata
buys nothing there, and adding it to a plan nobody will parallelise is noise.

Apply it when there are several work packages, some genuinely independent, and
the project is large enough that execution will span sessions.

## Two modes

### Authoring — the cheap path

When the plan is being written, supply the eight fields **as you go**. Seven of
them are facts the author already knows and would otherwise write as prose:

| Field | What it answers |
|---|---|
| Prerequisites | what is ready |
| **Owns** | what may run concurrently — the collision key |
| **Laneable** | whether this may be delegated at all |
| Tasks + depends_on | order inside the package |
| Tests, tagged `[lane]` / `[integration]` / `[release]` | whose test it is |
| Acceptance | what done means |
| **Must NOT be built** | negative scope |
| Integration contract | what the other side of a shared seam may assume |
| **Satisfies** | which task-level outcome it serves — when a Completion Contract exists |

If the request has several independently required outcomes and the plan has no
`## Completion Contract`, establish one first — `/worktree:completion-contract`
— and point each package at it with `Satisfies`.

Retrofitting these later costs far more than writing them down once.

### Auditing — an existing plan

Report what is missing. **Never invent it.** An imagined dependency costs exactly
as much as a real one, and a guessed ownership set is worse than an absent one
because it will be trusted.

Checks that find the expensive defects:

| Check | Why it matters |
|---|---|
| No `Owns` | concurrency is unknowable. **Report it; do not guess it** |
| Prerequisites at two levels with no join rule | the wrongly-started-lane defect — the single most reliable way to burn a lane |
| Intersecting `Owns` scheduled together | a collision that has already happened |
| No `Laneable` verdict | a lane may be provisioned for work that can only run on the trunk |
| Tests present but untagged | ownership undefined at the moment it matters |
| **A blocker note that never names its own row's subject** | boilerplate copied from a sibling row. Suspect it — such rows have turned out to be startable, one blocker being an *instruction* rather than a bar |
| No `Must NOT be built` next to a tempting adjacent feature | scope drift has no brake |
| A Completion Contract entry no package `Satisfies`, or a package that satisfies nothing | an outcome the run cannot deliver, or work outside the contract. **Report; never guess** |

## Readiness must be computable

One rule, no ambiguity:

```
ready(task) ⇔ every package Prerequisite complete
            ∧ every task depends_on complete
            ∧ no unresolved external blocker
```

**Both levels.** If a plan expresses dependencies at two levels in two places
without saying they are conjoined, say so explicitly — that is the finding, not a
formatting nit.

## Then report the shape of execution

Once the fields exist, say what they imply:

- the readiness graph;
- a wave partition — the ready set grouped so no two packages in a wave share an
  `Owns` component;
- **the concurrency ceiling, and where it comes from.** If the plan is a set of
  serial chains, the unit of parallelism is the chain, not the task, and the
  ceiling is however many chains are startable. Say the number. It is a property
  of the plan, not of how many agents exist, and pointing more agents at it buys
  nothing.

## Guardrails

- **Additive only.** Supply fields; do not restructure prose or rewrite a plan
  that was not asked to be rewritten.
- Never invent a dependency, an ownership set, or a prerequisite.
- Never add orchestration metadata to a plan that will not be executed in
  parallel.
- Do not write to the plan without saying what will change and getting agreement.
- If asked to audit, **audit** — read-only unless told otherwise.
