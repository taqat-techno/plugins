---
name: test-double-seams
description: The two-sided contract at the boundary between production code and a test double. TEST side (extends the across-the-seam rule owned by test-result-evidence, never restates it) — owns the per-branch ledger that makes that rule checkable, namely enumerate the branches from the PRODUCTION entry point rather than from the test file, mark for each which side of the seam its tests called, and read an at-the-seam-only branch as untested for construction defects, since a double is authored from the consumer's expectations and so always supplies the field the real producer forgot to pass. Carries the detection question "which side of this seam did the test call?" and a catalog of seam shapes (constructor parameter, DI dependency override, stub client, fake supervisor, lambda/factory starter, monkeypatched module attribute) naming what each double silently supplies. PRODUCTION side (owned outright) — a double is a legitimate implementation of the seam, so a newly added read on an injected collaborator uses getattr(obj, "name", default) unless the value is genuinely load-bearing; a diagnostic log line or optional hook must never acquire veto power over a startup path, and shipping a feature must never require existing doubles to grow new methods. Activates when a new attribute or method is read on an object that was passed in rather than constructed locally; when a suite goes red with "double lacks attribute" right after a field was added to an injected class; when a review comment says "add the attribute to the fixtures"; when a branch (reattach, fallback, resume, retry, degraded mode) is called covered although its production entry point is never called; and when judging whether a passing unit test is evidence that a code path runs in production. NOT the framework mechanics — django-testing, fastapi-testing and odoo-test own how to write the mock, the fixture, or the dependency_overrides.
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - per-branch seam bookkeeping — enumerate the production dispatch at the entry point and mark, per branch, which side of the seam its tests called
  - the detection question "which side of this seam did the test call?" and the proven/unproven table it resolves to
  - the seam-shape catalog (constructor param, DI override, stub client, fake supervisor, lambda starter, monkeypatched attribute) and what each double silently supplies
  - the getattr(obj, "name", default) rule for newly read attributes on injected collaborators
  - the load-bearing vs diagnostic classification that decides whether a missing attribute may fail a path
  - the "production code must not require test doubles to grow new methods" constraint
  - the reuse-the-existing-tolerance-pattern rule (one tolerance mechanism per codebase, never a second shape)
defers_to:
  - test-result-evidence skill (this plugin) for the across-the-seam rule itself — that a hand-built fixture tests the component against itself, that "handles X" and "production produces X" are different claims, that every branch that matters needs one test calling the real producer, and the name "implemented and tested at the seam, never across it". This skill extends that rule per branch and adds the production side; it must not restate it.
  - django-testing / fastapi-testing / odoo-test / any project testing skill for framework mechanics — how to write the mock, fixture scope, dependency_overrides syntax, patching helpers, test-DB lifecycle
  - agent-safety skill for the "a green verdict is a claim to refute" reflex that a passing seam test invites
  - workflow-reliability skill for treating a producer's self-reported completion as an unverified claim
  - the project's own tolerance pattern (an existing broad-except / narrower-signature shim) when one already exists — apply it rather than inventing a second one
user-invocable: false
---

# test-double-seams

## Purpose

Every injected collaborator is a seam, and a seam has two sides. On the test side a double is written to make the component happy, so a test that only touches that side confirms what you already assumed and cannot see a defect in the code that builds the real object. On the production side that same double is a *legitimate* implementation of the seam, so any new attribute production reads on a collaborator becomes a hard requirement every double must satisfy — and a merely diagnostic read can take down a startup path against a stub. These reflexes keep both sides honest: tests that cross, production that tolerates.

`test-result-evidence` owns the test-side rule as a rule. This skill exists because that rule is stated over a *set* of branches ("for any branch that matters, one test must cross") and is unfalsifiable until the set is written down — and because nothing else in this plugin governs the production side of the same boundary at all.

## When to use

Activate when any of these appear:

- You are about to call a branch **"covered"** on the strength of a unit test whose fixture you wrote.
- A test asserts behaviour on a branch (reattach, resume, fallback, retry, degraded/offline mode, cache-hit) that production reaches through a *different* entry point.
- New code reads an attribute, field, property, or method on an object that is *passed in* rather than constructed locally.
- The whole suite (or a startup/smoke test) goes red right after adding a field to a class that other code injects — and the feature itself is correct.
- A review comment says "add the attribute to the fixtures" — that is the smell this skill exists to catch.
- A production defect turns out to be in *how the object was built*, on a path the tests never constructed.

Do NOT load this to write the double. Choosing the mock library, the fixture scope, `dependency_overrides` / `override_settings` syntax, the patching helper, or the test-DB lifecycle belongs to the framework's own testing skill (`django-testing`, `fastapi-testing`, `odoo-test`, or the project's conventions). This skill starts only once a double exists and the question is *which side of the seam a test reached* or *how strictly production may read the collaborator*. Merely injecting a stub is not by itself a trigger.

## The seam contract

### Half A — the test side: inherited rule, owned bookkeeping

**The rule itself lives in `test-result-evidence` (rule 5).** Load it there for the statement, the mechanism, the worked example, and the name of the failure mode. It is not restated here, and this skill must never be cited as its source. One sentence so this page stands alone: a double is authored from the consumer's expectations, so it always carries the field the real producer forgot to pass, which puts construction defects structurally out of its reach no matter how many assertions you add.

What this skill adds is the bookkeeping. The inherited rule quantifies over a *set* — "for any branch that matters, one test must cross" — and a claim about a set nobody has written down cannot be checked or refuted. "We cross the seam somewhere" is not a coverage statement.

**A1. Enumerate the production dispatch at the real entry point, before declaring anything covered.**
Write out the branches as production actually chooses between them (for example `inspect → spawn | reattach | refuse`). The enumeration has to come from the production entry point, not from the test file, because the failure being hunted is a branch the tests never reach — and a list derived from the tests can only contain branches the tests already reach. That circularity is why "we have tests for this" survives review.

**A2. Mark every enumerated branch with the side its tests called, and let unmarked mean uncovered.**
Per branch, record at-the-seam or across-the-seam (the detection question below resolves it). A branch carrying only at-the-seam tests is covered for *handling* and untested for *construction*, so it must be marked untested rather than left blank — a blank reads as "fine" to the next reader, which is how a green suite launders an unreached path. One crossing test per branch is the floor, not the ceiling.

**A3. Crossing one seam proves one seam.**
A test that enters through the real producer proves that producer builds the collaborator correctly. The collaborator it built may itself hold doubles one layer down, and those are as unexamined as before. The bookkeeping is therefore per seam, not per test run — ask the detection question again at the next collaborator, or the enumeration silently claims more than it checked.

**A4. Name a seam-only test after what it proves, not after the production behaviour.**
A test called `test_reattached_worker_is_watched` asserts a production fact it never reached; `test_lifecycle_polls_by_pid_when_given_a_procless_supervisor` asserts what actually ran. This is not cosmetic — the name is what a reviewer reads instead of the fixture, so an over-claiming name is the mechanism by which the enumeration above gets filled in wrong by someone who never opened the file.

### Half B — the production side: a double is a legitimate implementation

**B1. Read new attributes on injected collaborators defensively.**
When new code reads an attribute that did not exist on a collaborator before, reach for:

```python
value = getattr(obj, "log_path", None)
```

unless the attribute is genuinely load-bearing. The mechanism: every existing double in the suite was written against the *old* interface. Adding an unguarded read retroactively invalidates all of them at once — the suite goes red not because the feature is wrong but because a stub lacks a field.

**B2. A diagnostic must never be the reason a startup path fails.**
The characteristic disaster is asymmetric: you add a *log line* or an *optional hook*, and a service refuses to start against a double. The value contributed nothing to correctness, yet it acquired veto power over the boot sequence. Classify before you dereference — if the code can do its job without the value, it must not raise for the value's absence.

**B3. Production code must not require test doubles to grow new methods.**
If shipping a feature means editing every fixture to add `set_storage_gate()`, the seam has been narrowed by the production side. That edit is not a test-maintenance chore; it is the design telling you the read should have been optional, or that the capability belongs behind a small explicit protocol the double can opt into. Widening a required interface is a breaking change to the seam, and the fixtures are its first casualty.

**B4. Reuse the codebase's existing tolerance pattern.**
Most codebases that inject collaborators already have one — a `_get()` helper, a call site catching `TypeError` for a double with a narrower signature, an adapter with defaults. Find it and apply it. A second, differently-shaped tolerance mechanism is worse than none: with one pattern a reader can tell a deliberate tolerance from a missing one, and with two every site becomes ambiguous, so the next author picks by coin flip and neither pattern is ever enforceable again. Search for the existing pattern before writing a new one — the recurring failure is not disagreement about the pattern but never having looked for it.

**B5. When an attribute IS load-bearing, fail loudly and early.**
Defensive `getattr` is for optional reads only. If the code genuinely cannot proceed without the value, a default does not remove the failure — it relocates it. The missing attribute stops being an error at the seam, where the collaborator is still in scope and the cause is one frame away, and reappears as a wrong number, an empty write, or a lost record much further downstream, where nothing points back to the double that never had the field. That trade is why B1 is bounded: validate at construction/entry, raise a message naming both the missing attribute and the collaborator, and update the doubles deliberately as part of the change.

## The detection question

For any test you are about to trust, ask exactly this:

> **Which side of this seam did the test call?**

| Answer | What is proven | What is still unproven |
|---|---|---|
| It built the collaborator itself (stub / `SimpleNamespace` / DI override) | the consumer handles that state | that production ever produces that state, or produces it correctly |
| It called the real producer and let it build the collaborator | the producer builds it, and the consumer handles what was built | only the far side of the *next* seam down |

If the answer is the first row for a branch that matters, the branch is not covered — write the crossing test before moving on.

## Seam shapes

| Seam shape | Typical double | What the double silently supplies | A crossing test must call |
|---|---|---|---|
| Constructor parameter | hand-built object / `SimpleNamespace` | every field the consumer reads, always populated | the real factory or `__init__` caller that assembles the argument |
| DI dependency / container override | override registration, fake provider | a fully-formed dependency with no wiring errors | the app's real dependency resolution (startup/app factory), not the override |
| Stub client (HTTP, DB, queue, SDK) | fake client returning canned payloads | a response shape matching the parser's assumptions | the real client against a local/recorded backend, so the shape is observed not asserted |
| Fake supervisor / lifecycle owner | object with the polled attributes present | process handles, pids, paths — including ones the real path omits | the real start/attach function that decides what the supervisor gets |
| Lambda / factory starter (`starter=lambda: ...`) | one-line closure returning a ready object | the entire construction step the lambda replaced | the production starter function itself, on each of its branches |
| Monkeypatched module attribute | patched function/constant | a stable, always-available collaborator | at least one unpatched path exercising the real module-level wiring |

The column that matters is the third one: it names precisely what the test can never see.

## Decision framework

```
about to declare a path covered?
  -> list the branches from the PRODUCTION entry point, not from the test file
  -> per branch: which side of the seam did its tests call?  (see table above)
       built-it-itself -> covered for handling, NOT for construction -> mark untested
       real producer   -> covered for construction -> now ask the same at the next seam down
  -> any branch still unmarked is untested, not fine
     (the crossing rule itself is test-result-evidence rule 5; this is only its ledger)

naming a seam-only test?
  -> the fixture came from the component's expectations, so it proves "handles", not "produces"
       -> put "handles" in the name; a production-behaviour name fills the ledger in wrong

adding a read on an injected collaborator?
  -> can the code do its job without the value?
       yes (diagnostic, log, optional hook, metric) -> getattr(obj, "name", default); never raise
       no  (genuinely load-bearing)                 -> validate at entry, raise naming the attribute,
                                                       and update the doubles deliberately

the suite went red after adding a field / method?
  -> is the failure "double lacks attribute" rather than "behaviour wrong"?
       yes -> the production read was too strict. Guard it (B1/B2) instead of editing every fixture.
       and: if the fix requires doubles to grow methods, the seam just got narrower (B3)
```

## Validation checklist

- [ ] The branch list was derived from the production entry point, not from the existing test file.
- [ ] Every enumerated branch is marked at-the-seam or across-the-seam; none is left blank.
- [ ] Every at-the-seam-only branch that matters is recorded as untested for construction, not as covered. (The crossing rule is `test-result-evidence` rule 5; this checklist only audits its ledger.)
- [ ] Each crossing test was re-questioned at the next collaborator down, so the ledger claims one seam, not a whole path.
- [ ] Seam-only tests are named so they claim "handles X", not "X happens".
- [ ] Every newly added read on an injected collaborator is either `getattr(obj, "name", default)` or explicitly justified as load-bearing.
- [ ] No diagnostic value (log path, metric sink, optional hook) can raise on a startup or request path.
- [ ] The change ships without requiring existing test doubles to grow new methods or fields.
- [ ] Where a tolerance pattern already exists in the codebase, this change uses it rather than adding a second one.
- [ ] A load-bearing requirement fails early with a message naming the missing attribute and the collaborator.
- [ ] The full suite was run after the change — a seam narrowing shows up as a broad, shallow failure across unrelated tests.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Enumerate the branches by reading the test file | Circular — a list derived from the tests can only contain branches the tests already reach, so the unreached branch is definitionally absent | Enumerate from the production entry point's own dispatch |
| Leave a branch's seam-side column blank because nobody checked | A blank reads as "fine" to the next reader, so the unchecked branch is promoted to covered by silence | Unmarked means untested; mark it before the ledger is used |
| Name a seam test after the production behaviour ("a reattached X is watched") | The name is what a reviewer reads instead of the fixture, so an over-claiming name is how the ledger gets filled in wrong by someone who never opened the file | Name what it proves ("the lifecycle polls by pid when given a proc-less supervisor") |
| Treat one crossing test as proof the whole path is real | It proves one seam; the collaborator that producer built may hold doubles one layer down, still unexamined | Re-ask the detection question at the next collaborator |
| Add an unguarded read of a new attribute on an injected object | Every pre-existing double was written against the old interface; the suite goes red at once | `getattr(obj, "name", default)` unless load-bearing |
| Let a log path / metric / optional hook raise on the startup path | A diagnostic acquires veto power over boot; the service dies for a value it never needed | Default it; never let a non-load-bearing read fail a path |
| Fix the red suite by adding the attribute to every fixture | Production just narrowed the seam and made the doubles pay for it | Guard the read, or put the capability behind an opt-in protocol |
| Invent a new tolerance shim next to an existing one | Two mechanisms mean neither is the rule; the next author picks wrong | Find and apply the codebase's existing pattern |
| Default a genuinely load-bearing value to keep tests green | Relocates the failure rather than removing it — it resurfaces downstream as wrong data, where nothing points back to the double that lacked the field | Validate early and raise, naming the attribute and collaborator |

## Cross-references

- `test-result-evidence` (skill, this plugin) — **owns the across-the-seam rule itself** (rule 5): that a hand-built fixture tests the component against itself, that "handles X" and "production produces X" are different claims, and the name "implemented and tested at the seam, never across it". Read it for the rule; read this skill for the per-branch ledger that makes the rule checkable, and for the production side, which that skill does not cover.
- `structural-assertions` (skill, this plugin) — owns the negative-universal assertion over all exit paths, which is the cheapest way to enforce A2's ledger for a branch that keeps growing new exits.
- `agent-safety` (skill, this plugin) — the refute-a-green-verdict reflex. A passing seam test is exactly the kind of green claim that deserves an attempt at disproof before it authorises a merge or deploy.
- `workflow-reliability` (skill, this plugin) — treats a producer's self-reported completion as an unverified claim; the same posture applied to workflows that this skill applies to fixtures.
- `django-testing`, `fastapi-testing`, `odoo-test`, or the project's own testing conventions — own the framework mechanics (mock library, fixture scope, `dependency_overrides` syntax, patching helpers, test-DB lifecycle). This skill owns only *which side of the seam* a test must reach and *how tolerantly* production may read a collaborator; it never dictates how the double is written.
