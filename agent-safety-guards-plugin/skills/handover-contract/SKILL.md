---
name: handover-contract
description: >-
  Use when writing an issue, ticket, work item, task brief or subagent prompt that someone else
  will implement or review without access to your working tree - especially when the fix is
  already built and tested locally and the hand-over describes it, when acceptance criteria are
  being written, when the text says "either A or B", "out of scope", "follow-up" or "after #N",
  or when implementing from such a hand-over and a tested change was supplied with it. Covers
  carrying the code complete instead of describing it, acceptance criteria as runnable effects,
  no open decisions, an owner for every remainder, declared order between dependent items,
  keeping the item true after it is filed, and comparing what shipped with what was asked.
version: 0.1.0
user-invocable: false
metadata:
  last_reviewed: 2026-11-23
  owns:
    - the hand-over contract (what a work item must carry when the receiver cannot see the author's tree)
    - acceptance criteria as observable, runnable effects, including the hard half
    - the remainder rule (every out-of-scope, follow-up or deployment step has a tracked item or a named owner)
    - the receiver's side (apply a supplied tested change; state every deviation)
    - the shipped-versus-asked comparison after delivery
  defers_to:
    - test-scope skill (this plugin) for which tests prove the change before it is handed over
    - test-result-evidence skill (this plugin) for reading the runs quoted as evidence
    - workflow-reliability skill (this plugin) for fan-out, resume and verifying a subagent's "done"
    - the tracker's own plugin, if installed, for fields, templates, states and write rules
    - the framework plugin, if installed, for what "upgrade", "role" and "fresh install" mean there
---

# handover-contract

## Purpose

A hand-over is everything the receiver has. A pipeline, a subagent or a colleague cannot see
your branch, your database or what you tried. Whatever the text leaves out is rebuilt from a
guess, and the parts rebuilt from a guess are where the defects come back: the migration guard
that was in the local commit, the tests that were only described, the second half of a fix that
lived in a comment.

Authors who diagnose well still lose work here. The diagnosis is rarely the weak point; the
proof, the transport and the follow-through are.

## When to use

- You are writing an issue, ticket, work item, task brief or subagent prompt for work someone
  else will do or check.
- The change already exists locally and you are about to describe it.
- You are writing acceptance criteria.
- You are implementing from someone else's hand-over.
- A delivered item is being closed.

Do NOT use this for a commit message, a changelog entry or release notes: those describe
finished work to readers who have the code.

## Before writing

1. **Reproduce at runtime, as the affected actor, on the current target.** A finding read from
   code and never run is labelled "not reproduced" in the title or first line. It is a
   hypothesis, and it is sized and prioritised as one.
2. **Settle the decision first.** If the change removes, hides, tightens or redesigns
   something people rely on, get the keep / change / remove answer from whoever owns it and
   quote it with the date. An item that says "either A or B" or "decision required" is a
   question. File it as a question, or do not file it yet.
3. **Look for your own overlapping items.** Search open items and recent merges for the same
   unit and file. Link each one and say which item owns which lines.
4. **One audit, one report.** A read-through that produced twenty findings becomes one report.
   Individual items are filed for the findings you then reproduce.

## The contract

| # | Rule | What it prevents |
|---|---|---|
| 1 | **Carry the change, do not describe it.** If it is built and tested, hand over the thing itself: a pushed commit or patch if the receiver can fetch it, otherwise every changed file in full, tests and data migrations included. No `...`, no "rest unchanged", no "N more like this". | The receiver re-implementing from prose and losing what was not written out |
| 2 | **Facts come from the target, not from your tree.** Versions, paths, "already fixed in", "not yet released" are read from the fetched target branch and quoted with its commit id. Never write a literal "next version"; say "the next one above the target at merge". | Fixes written against a state that no longer exists |
| 3 | **Every acceptance criterion is an observable effect** for a named actor on a named environment, and the receiver can run it. "Tests green", a grep count, "method X is not overridden" and "identical to the original" describe the change; they do not show it works. Mark checks only you can do (a browser, a device, production) as yours. | Criteria that pass while the feature is broken |
| 4 | **One criterion covers the hard half:** the upgrade of existing data, the actor who must be refused, the value that is printed or sent. | Shipping the easy half proven and the hard half assumed |
| 5 | **Tests are part of the change.** Name the file, include the test code, say which assertion fails before the fix. Tests build their own data and cannot skip. | Tests that were described and never shipped |
| 6 | **Say what existing data gets**, in one line: nothing, a migration, or a manual step. A manual step names the open item that tracks it. | A correct change that never reaches the installed systems |
| 7 | **Every remainder has a home.** Each "out of scope", "follow-up", "later", deployment step or step in another repository carries a tracked item or a named owner when the hand-over is written, or is dismissed in so many words. | Known defects that live only in a closed thread |
| 8 | **Order between items is a link, not a sentence.** Use the tracker's blocked-by or dependency field and state the merge order. File dependent items one at a time when they touch the same files. One root cause and one reviewable change per item. | Item B built while item A is parked; collisions between your own items |
| 9 | **Stay inside the receiver's limits.** Size, template and required fields are part of the contract; split before filing, not after a refusal. | Intake refusals and rewrites |

## After it is filed

- **The text the receiver started from is frozen.** A change of scope or design goes in a
  comment addressed to the receiver. If the design changes, rewrite the body once and say so at
  the top, because an implementer builds what the body says.
- **State belongs to the process that owns it.** Do not mark your own item done, and do not
  close it without a comment. Withdrawn is "not planned" plus a pointer to what replaces it;
  it is not "completed".
- **A defect fixed only on your machine is still open** for everyone else.

## When you are the receiver

- **If a tested change came with the hand-over, apply it.** Do not rebuild it from the
  description. Where you deviate, list each deviation and why.
- **If the text and the code disagree, or a block is elided, ask** before filling the gap.
- **Never meet a criterion by weakening the check** (relaxing a test, skipping it, narrowing
  what it asserts). Report that the criterion cannot be met as written.
- **Side findings are filed or dismissed in writing.** A note beside the item is neither.

## After delivery

Compare what shipped with what was asked, line by line:

```
Required change / criterion      Shipped as asked | Shipped differently | Not shipped
```

Include tests, documentation and data steps. Then turn each remainder and each side finding
into a tracked item or a written dismissal. A first-pass "accepted" says the gate was passed.
It does not say the outcome is right.

## Validation checklist

- [ ] Reproduced at runtime as the affected actor, or labelled "not reproduced".
- [ ] The decision the change depends on is quoted, with who and when.
- [ ] No elided code; tests and data steps are in the hand-over.
- [ ] Target facts carry the target's commit id; no literal next version.
- [ ] Every criterion is an effect the receiver can run; one covers the hard half.
- [ ] The existing-data line is present.
- [ ] Every remainder has an item, an owner or a dismissal.
- [ ] Dependencies are links, with the order stated.

## Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| "Implemented and tested locally; summary below" | The summary is all that travels | Hand over the commit, the patch or the full files |
| Acceptance: "all tests pass" | True of a change that does nothing | An effect for a named actor, plus the hard half |
| "Decide whether to keep or remove X" in an implementation item | The implementer picks, or parks it | Get the decision first and quote it |
| "A follow-up can handle Y" | Nobody owns Y | File Y, or name its owner, or dismiss it |
| Three items on one file filed in ten minutes, "apply in order" | The tracker cannot read the order | Blocked-by links, one item at a time |
| Editing the body after the receiver started | They build the stale text | Comment, or rewrite once and say so |
| Closing your own item as completed when it was withdrawn | Reads as delivered | Not planned, with a pointer |
| Passing a criterion by loosening its test | The criterion is now false | Report it as unmet |

## Cross-references

- `test-scope`: what to run before the hand-over, including the neighbours of shared code.
- `test-result-evidence`: whether a quoted run could have failed.
- `workflow-reliability`: briefs for a fan-out and checking what comes back.
