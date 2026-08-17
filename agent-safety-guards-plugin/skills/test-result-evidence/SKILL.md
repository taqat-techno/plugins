---
name: test-result-evidence
description: Owns the epistemics of a test RESULT — a passing run is not proof until you have shown it could have failed. Covers naming the discriminator before a control run (write one sentence saying what observable would have appeared if the claim were false, then confirm the run could have produced it); proving WHICH artifact the run actually executed (an editable install pins the working tree's src/ onto sys.path permanently, so cd-ing into a git worktree or an old-tag checkout changes nothing and the "old version" run silently executes the NEW code — print the resolved module file BEFORE the test invocation, and disable the runner cache across versions); reading a collection-time ImportError as zero-tests-ran rather than a clean run (a symbol missing from the baseline kills the whole module at import, so absence of failures is not evidence of a pass — split those tests into their own module and compare COLLECTED COUNTS, never pass/fail lines); and cleanup assertions (assert the connection/handle/thread is CLOSED or joined, never that its temp directory deletes — deletability is vacuously true on POSIX because an open file unlinks fine, and only Windows raises PermissionError WinError 32, which is why a one-OS failure means the other legs were never able to fail that test at all). Reads results only — it never authors tests and never owns runner, fixture, or assertion mechanics. Activates when a run is being READ AS EVIDENCE — a negative control or bug-reproduction suite that came back all-green, a run aimed at a git worktree / previous tag / vendored old copy, a pytest or jest collection error, a collected count that dropped between versions, a teardown or tempdir assertion, or a failure that reproduces on exactly one OS.
version: 0.2.0
last_reviewed: 2026-08-10
owns:
  - the named-discriminator rule (before any control, state the result that would have proven the opposite)
  - proving which artifact a control run imported (resolved module path printed before the invocation; editable-install sys.path pinning)
  - the collection-error reading (an ImportError at collection means zero discriminating tests ran; absence of failures is not a pass)
  - the split-out rule for tests that reference a symbol absent from the baseline version
  - comparing COLLECTED COUNTS across versions rather than pass/fail lines
  - cleanup-assertion form (assert the resource is closed; never assert its temp directory deletes)
  - the one-OS-flake reading (a control that can only fail on one platform did not run as a control anywhere else)
defers_to:
  - structural-assertions skill (this plugin) for every claim about SOURCE SHAPE — the harness-free side-by-side AST probe, the ast.walk ordering trap, the no-path-does-the-unsafe-thing universal, and the new-test-just-went-red reading
  - test-double-seams skill (this plugin) for the at-the-seam vs across-the-seam contract and what a hand-built double can structurally never expose
  - the framework testing skills (django-testing, fastapi-testing, odoo-plugin test) for runner selection, fixture strategy, and test authoring — this skill judges a result, it does not write the test
  - release-verification skill (release-safety plugin) for the DEPLOY-altitude twin of this failure — a /health 200 served by the OLD build, per-service SHA, code-marker probes
  - agent-safety skill for what to do with a green verdict that is about to authorize an irreversible action
  - workflow-reliability skill for whether the producer of a result completed at all (a zero from a crashed producer reads identical to a clean zero)
user-invocable: false
---

# test-result-evidence

## Purpose

A green test run is a measurement, and a measurement is worthless until you know what it could have measured. The expensive failures are not red runs — they are runs that were *structurally incapable of going red* and were read as confirmation: a negative control that imported the code it was supposed to exclude, a suite whose discriminating tests never executed, a teardown assertion that is vacuously true on the developer's OS. This skill is the reflex set that turns "it passed" into "it passed, and here is why it could have failed."

## When to use

Activate when any of these appear:

- A negative control, bug-reproduction suite, or "prove the old version was broken" run comes back **all green**.
- A test run is aimed at a `git worktree`, a previous tag, a vendored old copy, or a second checkout.
- A pytest/jest/go run reports a **collection / import error**, or the collected test count is lower than expected.
- A test asserts on cleanup: a temp directory being removable, a file being deletable, a process "gone".
- A failure reproduces on exactly **one OS** (or only in CI, or only on the Windows leg of a matrix).
- Someone is about to conclude "these tests don't discriminate — rewrite them" from a passing control.

Do NOT use this to author tests, pick a runner, or design fixtures — the framework testing skills own that, and this skill only judges what a finished run is evidence *of*. Do NOT use it to second-guess ordinary in-scope red/green cycles on tests whose discriminating power is already established.

## The evidence rules

### 1. Name the discriminator before the run

For any control, write one sentence: **"if the claim were false, this run would show X."** X must be a concrete observable — a specific assertion failing, a specific string absent, a specific exit code. Then check the run *could have produced X*: was that assertion reached, did that test execute, was the instrument pointed at the right artifact.

A control without a named discriminator cannot be falsified, so its green tells you nothing. The mechanism is plain: every rule below is one way X was unreachable while the run still reported success.

### 2. Prove WHICH artifact the control executed

An editable install (`pip install -e .`, and the same idea in `npm link`, a `go.work` replace, a `PYTHONPATH` export in a shell profile) puts the **working tree's** `src/` on `sys.path` permanently. `cd`-ing into a `git worktree` pinned to the previous tag changes **nothing** — `import pkg` still resolves to the main checkout, so the "old version" run executes the **new** code.

Observed shape: 30 tests written to reproduce a shipped defect, run against a worktree at the prior tag, reported **30 passed** — which reads as "these tests don't discriminate, rewrite them." They discriminated fine. The worktree was never tested.

Print the resolved module path **before** the test invocation, in the same shell, with the same environment:

```bash
PYTHONPATH="$WT/src" python -c "import pkg; print(pkg.__file__)"
PYTHONPATH="$WT/src" python -m pytest tests/... -p no:cacheprovider
```

The first line is the control on the control. If it prints the main checkout's path, the run below it is vacuous no matter what it reports. Disable the runner's cache (`-p no:cacheprovider`, or the equivalent) for a cross-version run: the cache keys on node IDs and last-failed state from the *other* version, so it can alter which tests are selected or reordered — and a comparison in which the two runs did not select the same tests is not a comparison.

### 3. Absence of failures is not evidence of a pass

If a test module imports a symbol that **does not exist in the baseline version**, the interpreter raises at import time. The runner reports **one** `ImportError` at collection and **none** of the tests in that module ever run. The summary line then shows a small number of errors and zero failures — and reading that as "nothing failed" inverts the result completely.

- Treat any collection error as **"the discriminating tests did not execute"**, never as a neutral or green outcome.
- **Split those tests out** into their own module, so a collection error in one file cannot suppress the tests that could still have run in another.
- Compare the **collected count** between the two versions. A drop is the signal; the pass/fail line is not.
- When a symbol genuinely does not exist in the baseline, check the old source **directly** (rule 4) instead of asking a runner to import it.

### 4. When the claim is about source shape, take the harness out of the loop

Rules 2 and 3 are both failures *of the harness* — path resolution, conftest, plugins and caches all sit between the claim and the evidence. So when the claim happens to be structural ("is X wired up / called / ordered / gone?"), the cheapest way to make this whole class of error unreachable is to stop asking a runner: read and parse the two files directly instead. That control has no import path to get wrong and no fixture to shape the result, which is exactly why it outranks a harness run as evidence.

The instrument itself then has to be aimed correctly, and a false RED from a mis-aimed probe costs the same as a false green — both send you to rewrite code that was right.

**`structural-assertions` (this plugin) owns that probe** — how to build the side-by-side old-file/new-file comparison, why `ast.walk` order is not source order, and when a structural assertion is the wrong tool. Go there rather than reproducing a probe from memory; this skill only tells you *why the probe is better evidence than the run*.

### 5. A green from a hand-built fixture is evidence about the component, not about production

A test that injects a double shaped to the component's expectations — a `starter` lambda returning a hand-made `SimpleNamespace(...)`, a stub response, a fabricated config object — was authored from the same mental model as the component, so it can only confirm that model. Its green is therefore evidence for the claim "the component handles this state" and for no other claim; in particular it is structurally incapable of reporting a defect in the code that *builds* that state, because the double always supplies the fields the real producer forgets.

Read such a green as a **narrower result than it looks**, and never as coverage of the production branch. Step 4 of the ladder below exists for this reason.

**`test-double-seams` (this plugin) owns the rule and its remedy** — the at-the-seam vs across-the-seam contract, the detection question, and the seam-shape catalog. This skill only records what the resulting green may and may not be used to assert.

### 6. Assert the resource is CLOSED — never that its directory deletes

Cleanup assertions of the form "the temp directory was removed" / "the file could be deleted" are **vacuously true on POSIX**: an open file can be unlinked, so the assertion passes while the handle is still live. Only Windows refuses, raising `PermissionError: [WinError 32]` from `TemporaryDirectory` cleanup. That asymmetry is exactly how two instances of the same leak survived review.

The mechanism worth carrying:

```python
store = ProfileStore(...)          # no context manager
profile = store.get(pid)
if profile is None:
    raise OperationRefused(...)    # `store` is still a live local in THIS frame
```

The `raise` attaches the frame to the exception's traceback, creating a traceback-to-frame cycle. The connection is then freed only by the **cyclic** collector, on no schedule. A background thread that outlives the store it writes to is the same shape — a dead thread's traceback holds every frame beneath it, including any handle opened there.

So: assert **`conn.closed is True`** (or the library's equivalent — the handle, the pool, the thread joined), on the object, at the point cleanup should have happened. Deletability is a proxy that only one OS actually evaluates.

### 7. A one-OS flake is a control that ran nowhere else

When a failure appears on exactly one platform, the useful reading is not "flaky on Windows" but **"the other platforms were never able to fail this test."** The green legs of the matrix were not corroboration; they were silence. Fix the resource lifetime (rule 6) rather than skipping or retrying the leg that can actually see it — the skip removes the only instrument that works.

## Decision framework

| Signal | What it usually means | Do this |
|---|---|---|
| Control run is all-green | The control may never have touched the baseline artifact | Print the resolved module path first; re-read the pass only after |
| "These tests don't discriminate" | Far more often the artifact under test was wrong, not the tests | Verify artifact identity before rewriting a single assertion |
| Collection / import error, 0 failures | The discriminating tests did not run | Read as UNKNOWN, not green; split the module; compare collected counts |
| Collected count differs between versions | Some tests silently vanished from one side | Reconcile the counts before comparing outcomes |
| Fixture is a hand-built double | The green covers "handles X", not "production produces X" | Narrow the claim; hand the remedy to `test-double-seams` |
| The claim is about source shape, not behaviour | A harness run is the weakest available instrument for it | Hand off to `structural-assertions` (side-by-side probe) |
| Assertion is "tempdir deleted / file removable" | Vacuous on POSIX | Assert the connection/handle/thread is closed or joined |
| Fails only on Windows (WinError 32) | A handle is alive; other OSes cannot detect it | Fix the lifetime; never skip the only leg that can observe it |
| A green run is about to authorize a mutation | Evidence quality now has blast radius | Hand off to `agent-safety` (refute the pass before it mutates) |

Ladder for a control run, in order — each step is worthless until the one above it holds:

```
1. Which artifact did this import?          -> print the resolved path, don't infer it
2. Did the discriminating tests execute?    -> collected count, no collection errors
3. Could any of them have failed?           -> named discriminator, reachable assertion
4. Did the real producer get called?        -> see test-double-seams; a double's green is narrower
5. Only now: does green mean anything
```

## Validation checklist

- [ ] The discriminator is written down: one sentence naming the result that would have proven the opposite.
- [ ] The resolved module/artifact path was **printed** before the control invocation and matches the intended version (not the editable-install working tree).
- [ ] Test caches were disabled for the cross-version run (`-p no:cacheprovider` or the runner's equivalent).
- [ ] Collected test counts were compared across versions; no collection/import error is being read as green.
- [ ] Tests referencing symbols absent from the baseline live in their own module.
- [ ] Any "is X wired up" claim was settled by a source-shape probe rather than by a harness run (built per `structural-assertions`).
- [ ] Every green produced by a hand-built fixture is recorded as evidence for "handles X" only; the seam question was taken to `test-double-seams`.
- [ ] Every cleanup assertion targets a closed/joined resource, not a deletable path.
- [ ] No single-OS failure was skipped, retried, or marked flaky in place of fixing the resource lifetime.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `cd` into a worktree/old tag and run the suite | An editable install pins the working tree's `src/` on `sys.path`; the old-version run executes the new code | Print `pkg.__file__` under the intended `PYTHONPATH` before the run |
| Conclude "the tests don't discriminate" from 30 passed | The far likelier cause is that the baseline artifact was never loaded | Verify artifact identity, then judge the tests |
| Read "1 error, 0 failed" as nothing-broke | One collection-time `ImportError` means none of that module's tests ran | Treat a collection error as UNKNOWN; split the module out |
| Compare pass/fail lines across versions | The counts can differ silently; fewer tests looks like fewer failures | Compare collected counts first, outcomes second |
| Assert the temp directory was deleted | Vacuously true on POSIX — an open file unlinks fine; only Windows raises `WinError 32` | Assert `conn.closed` / handle released / thread joined |
| Mark the Windows-only failure flaky and skip it | Removes the only platform that can observe a live handle | Fix the resource lifetime (context-manage or close before `raise`) |
| Cite a stub-fixture green as proof the production path works | The double was authored from the component's own expectations, so the producer's defect is out of its reach | Record it as "handles X" only; take the seam question to `test-double-seams` |
| Settle "is X wired up?" with a harness run against an old checkout | Import resolution, conftest and caches all sit between the claim and the answer (rules 2-3) | Use the side-by-side source probe owned by `structural-assertions` |

## Cross-references

- `structural-assertions` (skill, this plugin) — owns every claim about the SHAPE of source: the side-by-side probe referenced in rule 4, the `ast.walk` ordering trap, the negative universal over all exit paths, and the "a brand-new test that goes red is more likely wrong about its expectation than the code is" reading. This skill decides whether a run is evidence; that one decides how a source-shape claim is measured.
- `test-double-seams` (skill, this plugin) — owns the seam contract behind rule 5: at-the-seam vs across-the-seam, the detection question, and how tolerantly production may read an injected collaborator. This skill only narrows what a double-backed green may be used to assert.
- The framework testing skills (`django-testing`, `fastapi-testing`, the odoo plugin's test skill) — own runner choice, fixture strategy, and writing the tests. This skill never authors a test; it reads a finished run.
- `agent-safety` (skill, this plugin) — what to do once a verdict is green: refute a "pass" before it authorizes an irreversible action, and gate on a schema boolean rather than "pass" prose. This skill establishes whether the evidence is real; that one governs what a green result is allowed to authorize.
- `workflow-reliability` (skill, this plugin) — whether the producer of a result completed at all; a zero from a crashed producer is indistinguishable from a clean zero. Complements rule 3 at the run level.
- `release-verification` (skill, release-safety plugin) — the DEPLOY-altitude twin of the same failure: a `/health` 200 answered by the OLD build during a cold rebuild, a multi-service deploy where one service still runs the old SHA, a deploy-from-source CLI shipping the working tree. Same mechanism (the artifact under test is not the artifact you believe), one altitude up.
