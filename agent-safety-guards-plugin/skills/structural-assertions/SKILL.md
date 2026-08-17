---
name: structural-assertions
description: The discipline for asserting facts about the SHAPE of source code — this symbol is gone, this call precedes that one, this component is wired into that entry point, no path reaches this primitive. Owns the rule that such a claim goes through the language's own parser (`ast`, tree-sitter, a TS compiler pass), never string containment — because `assert "sys.platform" not in source` matches the comment you wrote explaining why the module no longer does platform dispatch, so it goes red for the wrong reason, and it goes green for the wrong reason the moment the real violation is spelled `getattr(sys, "platform")`. Also owns the `ast.walk` ordering trap (walk is breadth-first, so `called.index("a") < called.index("b")` compares traversal positions rather than source order — sort by `node.lineno` first), the AST FORM of the side-by-side wiring probe (parse the old file and the new file in one script, print one boolean each), the negative-universal rule for functions with several exit branches (assert that NO path does the unsafe thing, never that the obvious path is right), the sweep-the-class rule (one hit is a sample, not the population), and reading a red PRE-EXISTING architecture test as evidence about your design rather than as a test to edit. Activates when an assertion or check uses `in source`, `assertIn` over file text, `grep`, or a regex over a file's CONTENTS to establish something about code; when the evidence offered for "the pattern is gone" or "the new component is wired in" is a search over source text; when asserting call order or that a symbol is or is not used; when an existing lint / architecture / structural test goes red on a change; or immediately after finding one instance of a bad code shape. NOT a test-authoring skill — framework and unit-test mechanics belong to the stack's own testing skill, and whether a test RUN counts as evidence belongs to test-result-evidence; this governs only the FORM of a claim about code shape.
version: 0.1.0
last_reviewed: 2026-08-10
owns:
  - structural claims go through a parser (`ast`), never string containment — comments and docstrings are indistinguishable from code to a grep
  - the `ast.walk` breadth-first ordering trap (sort by `node.lineno` before asserting source order)
  - the AST FORM of the side-by-side wiring probe (how to write it; test-result-evidence owns WHY a harness-free control is preferred)
  - the multi-exit-path rule — assert that NO path does the unsafe thing, not that the obvious path is correct
  - the sweep-the-class rule — after one instance of a code-shape defect, AST-sweep the whole repository
  - reading a failing EXISTING structural test as evidence about your design, before reaching for the test file
defers_to:
  - test-result-evidence skill for everything about a test RUN as evidence — which artifact a control actually imported (editable-install sys.path pinning), a collection-time ImportError meaning zero tests ran, the named discriminator, and why the harness-free control is preferred at all
  - test-double-seams skill for hand-built fixtures and the at-the-seam vs across-the-seam distinction
  - agent-safety skill for the structured-output contract and for refuting a green verdict before it mutates state
  - workflow-reliability skill for fan-out sweeps across many files and for treating a subagent's "clean" as a claim
  - runtime/behavioural tests for anything about what the code DOES; this skill only governs claims about its SHAPE
user-invocable: false
---

# structural-assertions

## Purpose

A structural assertion is a test about the *shape* of source code: this symbol is gone, that call happens before this one, this component is wired into that entry point, no path reaches this primitive directly. These assertions are cheap and durable — they encode architectural rules that no runtime test can express. They are also uniquely easy to get wrong, because the naive implementation (search the file's text for a substring) is answering a question about English prose while pretending to answer a question about code. This skill is the small set of reflexes that keep a structural claim honest: parse, don't grep; order by line, not by traversal; probe both files side by side; quantify over all paths; and when the check fails, suspect the design first.

## When to use

Activate when any of these appear:

- A test or check does `assert "foo" not in source`, `assertIn(...)`, `grep`, or a regex over a file's **contents** to prove something about the code.
- The evidence offered for "the refactor **removed** that pattern / symbol / import / branch" is a search over source text.
- The evidence offered for "the new function, hook, adapter, or middleware **is wired up**" is a search over source text.
- You need to assert **ordering** — this is called before that, this runs first at shutdown.
- A function has **more than one exit path** (early return, exception branch, test-double shortcut) and one of them must not do something.
- You just found **one instance** of a bad code shape (bare `except` returning a plausible literal, a direct call that should go through a seam, a platform branch outside its seam).
- An **existing** structural / architecture / lint test goes red on your change and you are tempted to edit it.

Do NOT use this for behavioural claims. "The endpoint returns 200", "the retry stops after 3 attempts", "the migration is reversible" are runtime facts; assert them at runtime. Do NOT use it as a general test-writing skill either — fixture scope, parametrization, client factories, and the rest of the framework mechanics belong to the stack's own testing skill. This skill engages only once the assertion is about **syntax**.

## The six rules

### 1. Structural assertions go through `ast`, never string containment

A file's text contains code, comments, docstrings, string literals, and identifiers embedded inside longer words. A substring search cannot tell them apart, so it answers a different question than the one you asked.

The concrete failure: `assert "sys.platform" not in source`, written to prove a module no longer does platform dispatch, **failed on the comment explaining why the module no longer does platform dispatch**. That is the signature of this bug — it is double-sided:

- It **fails for the wrong reason**: prose describing the rule reads identically to a violation of the rule. Every clarifying comment you add makes the test redder.
- It **passes for the wrong reason**: the real violation moves into a `getattr(sys, "platform")`, an f-string, an alias (`from sys import platform`), or a differently spelled equivalent, and the substring never appears. Green means "this exact spelling is absent", which is not what you wanted to know.

The parser discards comments entirely, so they cannot be matched. Assert on nodes: an `ast.Attribute` whose `attr == "platform"` over a `Name` `sys`, an `ast.Call` whose `func` resolves to the forbidden name, an `ast.ExceptHandler` with `type is None`. Node predicates are also *broader* than the string in the direction you want — they catch spelling variants of the same construct while ignoring every mention in prose.

This generalizes past Python, because the mechanism is not Python's: **every language has comment and string syntax that its parser discards and a regex cannot distinguish from code.** So use the language's own parser (`ast` / `tree-sitter` / a TS compiler-API pass / an ESLint rule with an AST selector), not a regex, whenever the claim is about syntax.

### 2. `ast.walk` is breadth-first — never assert source ORDER from walk position

`ast.walk` yields nodes level by level from a queue, so a call nested one branch deeper is emitted *later* than a shallower call that appears further down the file. A test that did:

```python
called = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)]
assert called.index("a") < called.index("b")
```

reported **correct** code as wrong, because it compared tree-traversal positions, not line numbers. Recover the source order explicitly before comparing:

```python
order = sorted(
    (n.lineno, n.col_offset, n.func.id)
    for n in ast.walk(tree)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
)
```

`lineno` first, then `col_offset` — needed because two calls can share a line (`f(g())`), where line number alone leaves the pair unordered and `sorted` would fall back to comparing the third tuple element, silently ordering them *alphabetically by name*. See `references/ast-probes.md` for the full ordering probe, its pitfalls (decorators, nested functions, `finally` blocks), and why `col_offset` is not always evaluation order.

### 3. For "is X wired up?", write the claim as a side-by-side AST probe

When the claim is binary — the new adapter is registered / the hook is installed / the branch is gone — parse the **old file and the new file in the same script** and print one boolean each. Old prints `False`, new prints `True`.

**Why a harness-free control is preferred at all is not this skill's rule** — `test-result-evidence` owns it, along with the two mechanisms that make a harness untrustworthy for a version comparison (an editable install pins the working tree's `src/` onto `sys.path`, so the "old version" run executes new code; and a symbol missing from the baseline raises one `ImportError` at collection, so none of the discriminating tests run). Read that skill before you accept any cross-version test result. What this skill owns is the **AST form** of the probe:

- It takes a **file path**, not a module name. Nothing resolves, imports, or collects, so the only thing that can be misconfigured is the path you typed — and the probe prints that path back at you, which makes the one remaining failure mode self-evident in its own output. That is why a probe/harness disagreement resolves in the probe's favour: it has strictly fewer ways to be wrong, and each of them is visible.
- Its predicate is a **node** predicate (rule 1), so "wired up" survives an alias, an f-string, or a rename of the import — and is not satisfied by the changelog entry announcing the wiring.
- It must be aimed at the right **axis**. A probe that reports `True`/`False` for presence is sound; the same probe extended to report *order* inherits the walk trap in rule 2.

Get the old file with `git show "<tag>:<path>" > <tmp>` rather than by checking out a tag, so the working tree is never disturbed. The runnable probe is in `references/ast-probes.md`.

### 4. With two exit paths, assert that NEITHER does the unsafe thing

Asserting that the obvious path is correct leaves every other path unasserted, and the unobvious path is the one that breaks — it is unobvious precisely because nobody looked at it.

The concrete failure: a framework `lifespan` (FastAPI-style startup/shutdown) had a normal shutdown branch and an **early-return branch for injected test doubles**. The ordering fix went into the normal branch only; the early branch was the one CI actually crashed on. A test asserting "the shutdown path closes A before B" was green throughout.

The durable assertion is a **universal over all call sites**: *no path calls the low-level primitive directly*. Written as an AST sweep, it is one predicate over every `ast.Call` in the module, so a new exit branch added next month is covered without touching the test. It also exerts useful design pressure — the only way to satisfy it is to funnel the ordering into a single named function that every path calls, which is the fix you wanted anyway.

Prefer the negative universal (`no node matches P`) over the positive existential (`some node in this function matches Q`) whenever the property is a safety property — because a safety property *is* a statement about every path, and an existential witness cannot establish one. Worse, the existential stays green **by construction** when a path is added: it already found its witness on the old path and never looks at the new one. The universal is the only form whose truth value can change when someone adds the branch you were worried about.

### 5. One instance is a sample, not the population — sweep the class

A code-shape defect is produced by a habit, and a habit is repository-wide. After you find one, run an AST sweep for the whole class **before** declaring the fix complete.

The mechanism that makes this non-optional: the second instance can **defeat the fix you just applied**. In the worked case, a bare `except Exception: return 0` was replaced with a distinct sentinel — and the sentinel could never fire, because the layer below it caught its own errors and also returned `0`, so the fixed layer never saw an exception. A sweep for "broad handler returning a plausible literal" found 33 sites; most were legitimately best-effort, and the audit is what surfaced the one that mattered.

Budget for the sweep's noise: most hits will be fine. The value is not the count, it is that you now know the population instead of guessing from one sample. Sweep recipes for the recurring classes are in `references/ast-probes.md`.

### 6. When an EXISTING structural test fails on your change, read it as evidence about your design

A structural test is a compressed architectural constraint with no docstring. Its failure is the only moment that constraint speaks. Editing the test deletes the constraint silently and permanently — no diff reviewer will reconstruct why the assertion existed.

The concrete case: an AST sweep for platform-dispatch nodes went red on a fix that had put `sys.platform == "win32"` directly into a storage module, breaking the project's rule that **every platform branch lives behind one seam**. The test was right and the change was wrong. Order of operations when a pre-existing structural test fails:

1. Read the assertion and name the rule it encodes, in one sentence.
2. Find the seam / abstraction the rule is protecting.
3. Change the design to satisfy the rule.
4. Only if the rule is genuinely obsolete: change the test, in its own commit, with the reason written down.

The age of the assertion is what carries the signal, and it points the opposite way for a test you just wrote — `test-result-evidence` owns that half (a fresh assertion is the likelier bug). The asymmetry has a mechanism: an old structural test has survived every commit since it was written, so the prior that it is wrong *today* is low, whereas a five-minute-old assertion has survived nothing. **Old test failing: suspect your design. New test failing: suspect your assertion.**

## Decision framework

| The claim you want to assert | Do this | Not this |
|---|---|---|
| "This symbol / construct is gone" | AST node predicate (`ast.Attribute`, `ast.Call`, `ast.ExceptHandler`) | `assert "name" not in source` |
| "A is called before B" | `sorted((n.lineno, n.col_offset, ...))` over matching `ast.Call` nodes | `walk_order.index("a") < walk_order.index("b")` |
| "X is wired into Y" | Side-by-side AST probe over old file and new file, printing one bool each | A regex for the registration line, or an existential over one function |
| "This path is safe" (multi-exit fn) | Negative universal: no `ast.Call` in the module reaches the primitive | Assert the happy path calls things in the right order |
| "I fixed the bad pattern" | AST-sweep the repo for the class, then fix; report the population | Fix the one site you found and close it |
| An old structural test just went red | Name the rule, fix the design | Edit the assertion |
| A test you wrote 5 minutes ago went red | Suspect the expectation — see `test-result-evidence` | Assume the implementation is wrong |
| A cross-version run disagrees with the probe | Trust the probe; take the run to `test-result-evidence` | Re-tune the probe until it agrees with the harness |
| "The endpoint returns 200" / "retry stops at 3" | Runtime test — out of scope for this skill | An AST assertion about the code shape |

## Validation checklist

- [ ] No assertion in the change uses `in source`, `assertIn` over file text, or a regex over source to make a **syntax** claim.
- [ ] Every "X is absent" assertion is expressed as a node predicate that a comment or docstring cannot satisfy.
- [ ] Every ordering assertion sorts by `lineno` (and `col_offset`) before comparing; no `walk(...).index(...)` comparisons remain.
- [ ] Any "is it wired up?" claim was demonstrated by a side-by-side probe over both file versions, with the old one printing the negative, and the probe echoed the two paths it read.
- [ ] If a test harness was used for the version comparison instead, `test-result-evidence`'s artifact-identity check was run first.
- [ ] Every function with an early-return / exception / test-double branch is covered by a **negative universal**, not by a happy-path assertion.
- [ ] A repo-wide AST sweep for the defect class was run after the first instance, and its population size is stated in the report.
- [ ] The sweep was re-run after the fix, to confirm no sibling instance defeats it one layer down.
- [ ] No pre-existing structural / architecture test was edited to make a change pass; each such failure was resolved in the design or documented as obsolete in its own commit.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| `assert "sys.platform" not in source` | Matches the comment explaining why the module no longer does platform dispatch; also misses `getattr(sys, "platform")` and aliases | Assert on `ast.Attribute` / `ast.Call` nodes — the parser drops comments |
| Add `# noqa`-style prose to dodge a grep-based structural test | Encodes the bug: the test's truth now depends on how you word your comments | Replace the grep with a parser-based predicate |
| `called.index("a") < called.index("b")` over `ast.walk` | `walk` is breadth-first; you compared traversal depth, not source order — correct code reports as wrong | `sorted((n.lineno, n.col_offset, name) ...)` then compare |
| Reach for a test harness to prove "the old version lacked X" | The harness adds import resolution and collection between you and a claim that is pure syntax; both have documented ways of silently answering a different question (`test-result-evidence`) | Probe the two files directly — a file path, a parse, and a printed bool |
| Assert the shutdown path closes A before B | The early-return branch for injected doubles is unasserted, and it is the one CI crashes on | Assert no path calls the low-level primitive directly |
| Fix the one bad handler you found and close the issue | The shape is a habit; a sibling instance one layer down can silently defeat your fix | AST-sweep the class, report the population, re-sweep after fixing |
| Edit a red architecture test so the change passes | Deletes an unwritten architectural constraint; no reviewer will reconstruct it | Name the rule, fix the design; retire the test only deliberately and separately |
| Use a regex to assert TS/JS structure because `ast` is Python-only | Same prose-vs-code confusion, different language | Use that language's parser: tree-sitter, the TS compiler API, or an AST-selector lint rule |
| Push a behavioural claim into an AST assertion because it is easier to write | The shape of a call site does not establish what it does at runtime; the assertion goes green on dead code | Assert it at runtime; keep the AST assertion for the architectural rule |

## Cross-references

- `references/ast-probes.md` — the breadth-first ordering mechanism in full, a runnable side-by-side wiring probe, and sweep recipes for the recurring defect classes.
- `test-result-evidence` (skill, this plugin) — owns whether a test RUN is evidence at all: the named discriminator, proving which artifact a control imported, a collection-time `ImportError` meaning zero tests ran, and the general case for a harness-free control. That skill decides whether to believe a run; this one decides how a syntax claim is written. Rule 3 here is the AST instance of its harness-free control, and rule 6 here is the old-test half of its new-test rule.
- `test-double-seams` (skill, this plugin) — owns hand-built fixtures and the at-the-seam vs across-the-seam distinction. Rule 4 here covers the *early-return branch that exists for a double*; that skill covers what the double itself can and cannot prove.
- `agent-safety` (skill) — owns the structured-output contract and the rule that a green verdict is a claim to refute before it mutates state. A passing structural test is exactly such a claim; rule 1 here explains one way it goes green while lying.
- `workflow-reliability` (skill) — owns fan-out sweeps across many files, and the rule that a producer's empty result is trustworthy only if the producer completed. A sweep that returns zero hits because it crashed on a syntax error is not a clean repository.
- Runtime/behavioural tests — own everything about what the code *does*. This skill governs only claims about its shape; do not push a behavioural claim into an AST assertion because it is easier to write.
