---
name: test-scope
description: Use when about to run tests during development, choosing which tests prove a change, or about to create a test file. Picks the smallest test set that still proves the change; the full suite runs only when the user asks or in CI.
version: 0.2.0
user-invocable: false
metadata:
  last_reviewed: 2026-11-23
  owns:
    - the test-scope ladder (T0 static, T1 targeted, T2 affected, T3 full) and which tier each moment of development gets
    - batching (one test run per coherent change, never per edit)
    - the escalation triggers that widen a run, and the rule that widening stops at T2 unless the user asks
    - the FULL_SUITE=1 override semantics (who may use it and when)
    - the order for a change on a shared path (baseline first, then the change, as it ships, as the affected actor)
    - test-file hygiene (extend before creating, scratch probes outside the repo, every new file justified)
    - the test-scope report block (what ran, what did not, what to run before merge)
    - the change-to-test mapping for generic runners (references/runner-recipes.md)
  defers_to:
    - test-result-evidence skill (this plugin) for reading any result - 0 collected is a failure, summary line plus exit code, narrow-green vs wide-red, the pre-fix failing run
    - test-double-seams skill (this plugin) for why a seam change needs its consumers' tests, not just its own
    - the framework testing skills, if their plugins are installed (odoo test, django-testing, fastapi-testing), for framework selectors, warm-database loops and fixture mechanics
    - worktree plugin, if installed, for lane / integration / release test ownership across parallel agents
---

# test-scope

## Purpose

Running the whole suite after a small change buys almost no accuracy and costs minutes
per edit. The accuracy lives in running the **right** tests: the ones that exercise
what changed, plus the ones that depend on it. This skill picks that set, says when to
widen it, and keeps the full suite for the moments that actually need it.

The full suite is **not** run automatically. It runs when the user asks for it, or in
CI. Everything below is designed so that a scoped run is honest about that.

## When to use

- You are about to run a test command during development.
- A change is finished and you are deciding what proves it.
- You are about to create a new test file, or a throwaway script to "check something".
- A command you ran was denied by the test-scope hook.

Do NOT use this to judge whether a finished run proves anything. That belongs to
`test-result-evidence`.

## The ladder

| Tier | When | What runs | Typical cost |
|---|---|---|---|
| **T0 Static** | After an edit, before running anything | Parse/compile/lint/typecheck of the **touched files** | Seconds, no database |
| **T1 Targeted** | After a coherent change is complete | The tests for the changed units **plus** the tests you added, selected by path, class or name | Seconds to a minute |
| **T2 Affected** | Before you say the task is done | The full test module/app/package of **each touched unit**, plus the direct dependents an escalation trigger names | Minutes, once |
| **T3 Full** | **Only when the user asks, or in CI** | Everything | Whatever it costs, once |

Never skip a tier to save time: T1 green before T2, T2 green before you report done.

## Batch, then run

- Do not run tests after each edit. Finish the coherent change (the model, its view,
  its test) and then run T1 once.
- After a red run, fix and re-run **only what failed** (`--lf`, the failing test id,
  the failing class). Return to the whole T1 set once those pass.
- Do not re-run a green tier when nothing it covers has changed since.

## Widen, do not jump

A trigger widens the next run **within T2**: add the dependents it names, run once, and
record in the report that T3 was not run and why it is recommended.

| Trigger | Widen to |
|---|---|
| Shared or base code changed (a base class, mixin, util, fixture, conftest) | Every module that imports or inherits it |
| Schema, migration, model field or manifest changed | The owning module in its install/upgrade mode, plus modules that read those fields |
| Security, access rules, permissions, settings or dependency versions changed | The modules whose behaviour they gate |
| An injected collaborator gained a read, a method or a field | The consumers' tests (see `test-double-seams`) |
| A narrow run is green but a wider run you have seen is red | The wider run wins - localise before reporting (see `test-result-evidence`) |
| A hook or override on a core write path (create, write, delete, a state transition) or a new constraint | Every module whose flow passes through it, including ones that never mention your module |
| The change spans repositories, a submodule or a vendored copy | The dependents in **each** repository, at the versions that ship together |
| A reviewer says another flow depends on it | That flow's tests. "The data has none of those" is a fact about the data, not about the code path |
| You cannot tell what depends on the change | Ask, or report that impact is unknown - never guess green |

For a change on a shared path, run in this order:

1. **Baseline first.** Run the widened set on the untouched target before the change. A
   test that is already red is named in the report with whoever owns it. It is not absorbed
   into your result and not blamed on your change.
2. **Then the change.** Report every test that changed colour, in either direction.
3. **Run it the way it ships.** A new or changed unit is proven twice: installed with only
   its own declared dependencies, and inside the full stack it ships with. A copy of an
   existing installation is not a clean install, and a unit tested only inside the full
   stack has not shown its dependency list is complete.
4. **Run it as the affected actor.** A change to who may do what is run as an account that
   holds only that role, with one negative test for each way a record can match the new
   rule. A run as the administrator or the superuser proves nothing about permissions.

## The full suite

- Run it when the user explicitly asks, or when a workflow the user invoked defines a
  full-suite gate (a release or integration step). Prefix the command with
  `FULL_SUITE=1` so the hook lets it through.
- Otherwise, do not run it. Recommend it in the report: "T3 not run - recommended
  before merge because <trigger>." CI is where it normally runs.
- Never add `FULL_SUITE=1` just to get past a denial. A denial means you picked the
  wrong tier, not that the hook is in the way.

## Choosing the tests for a change

1. List what you changed: the files you edited this session. The hook's denial message
   repeats them.
2. Map each file to its tests:
   - a test file maps to itself;
   - a source file maps to the test module named after it, or found by grepping the tests
     for its module or class name;
   - a template, view or UI file maps to the tests that render it.
3. Select them with the runner's narrowest selector. Generic runners (pytest, vitest,
   jest, playwright, npm scripts) are in `references/runner-recipes.md`. Framework
   runners are in their own skills when those plugins are installed (Odoo `test`,
   `django-testing`, `fastapi-testing`); without them, use the framework's own docs.
4. If nothing maps, say so. A change with no covering test gets a new test (below), not a
   full-suite run.

## Test-file hygiene

- **Extend before creating.** Add the new case to the existing test module for that
  unit. Create a new file only when no module covers the unit, and name it after the
  unit.
- **Scratch probes never enter the repo.** One-off "does X work" scripts go in the
  session scratchpad or the system temp directory, and are deleted when answered.
  A probe worth keeping becomes a real test in the right module.
- **Every new test must bite**, meaning it fails without the change (the pre-fix run can
  itself be scoped). When the bug was seen in a live environment, set the fixture's
  configuration to match that environment first. A fixture whose settings differ can
  fail or pass for a reason unrelated to the bug. Every new test file must be registered wherever the framework
  discovers tests. A file that is never collected is worse than none, because it reads
  as coverage.
- **Report each new test file** with its reason in one line.
- **Parallel lanes are the one exception:** agents working on disjoint files may each
  write a per-lane test file to avoid contention. The lead folds them into their
  modules afterwards.

## What does not change

Scoping changes which tests run, never how a result is read. `test-result-evidence`
rules still hold:
- a scoped run that collected 0 tests is a failed invocation;
- the verdict is the summary line plus the exit code;
- a regression test must fail before the fix.

## Report block

End every change that ran tests with:

```
Tests: T1 <selector> -> <N> collected, <result> | T2 <selector> -> <N>, <result>
New test files: <path - reason> (or none)
Not run: T3 full suite - <recommended before merge because ... | not needed: ...>
```

## The hook

`hooks/test_scope_guard.py` records the files you edit and reacts to a command that runs a
whole suite. The user chooses the mode with the environment variable `TEST_SCOPE_GUARD`:

| Value | Effect |
|---|---|
| `advise` (default) | The run **happens**, and the guidance (changed files, a scoped command) arrives with its result. It steers your next run; it cannot undo this one |
| `ask` | You are **asked** to approve the run, with the same reason. Same meaning as in git-safety and release-safety |
| `enforce` | The run is **denied**, with the same reason. Any unrecognised value also means `enforce` |
| `off` | No hook |

`FULL_SUITE=1` in the command passes in every mode. Treat an advise-mode note exactly like a
denial: the next run is scoped. Detection is best-effort; a runner the hook does not
recognise is simply allowed. See `${CLAUDE_PLUGIN_ROOT}/docs/decisions.md` D-001, D-002, D-003 and D-005.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Full suite after every small edit | Minutes per edit for no added signal | T0 per edit, T1 per change, T2 once |
| "Just to be safe" full run before reporting done | Not requested; CI does it | T2 plus a T3 recommendation |
| Prefixing `FULL_SUITE=1` to get past a denial | Defeats the policy silently | Pick the right tier |
| A new `test_*.py` per bug in a unit that already has a test module | Scattered coverage nobody finds | Extend the existing module |
| `check_x.py` / `try_x.py` scripts left in the repo | Noise; sometimes collected as tests | Scratchpad, then delete |
| Reporting "tests pass" from a scoped run | Hides what was not run | The report block |
| Running only the changed module after touching security or a core write path | The breakage is in the neighbours | The widened set, baseline first |
| Proving a permission change as the administrator | The administrator bypasses the rule under test | An account with only the affected role |
| "New install works" shown on a copy of an installed database | Missing dependencies are already loaded there | A clean install with only the declared dependencies |
