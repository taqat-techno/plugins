---
name: browser-qa-discipline
description: Evidence discipline for browser QA. Owns the PASS / BLOCKED / NOT-TESTABLE vocabulary, the per-check evidence requirement, and the "code-read is NOT runtime evidence" rule. Activates at the start of any QA pass, before reporting a check as PASS, and before signing off a UAT or release. Generic and portable — no framework or product assumptions.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - PASS / BLOCKED / NOT-TESTABLE three-status vocabulary
  - per-check evidence requirement
  - code-read-is-not-evidence rule
  - the mirror rule — a defect inferred from static reading is latent until runtime-confirmed
  - silent-pass-is-not-pass rule
  - no-exception-as-valid-evidence rule (with named-run convention)
  - absence-of-signal evidence must rule out client-side collapse of that signal
  - disabled-control-is-not-evidence rule (fixture state must enable the action before a flow counts as exercised)
defers_to:
  - safe-destructive-testing (safety constraints on what evidence-gathering may do)
  - runtime-reality-check (verify target is actually running before claiming PASS)
  - uat-readiness-report (how to compose the final report from these statuses)
user_invocable: false
---

# browser-qa-discipline

## Purpose

The most common QA failure is the silent or speculative pass — "looks good", "should work", "all good ✓" without showing the run. This skill replaces that with a per-check evidence requirement, a 3-status vocabulary, and a hard rule: **reading the source code is not runtime evidence.**

Every other skill in `qa-browser` produces evidence that lands in a status from this skill's vocabulary.

## When to use

Activate when:

- Starting any QA pass (smoke test, regression, UAT).
- About to mark any check as PASS.
- Filling in a QA checklist or release sign-off.
- Reviewing someone else's "done" claim before approving it.
- Composing the final QA report.

## Inputs

- The list of checks (from a smoke test plan, a UAT checklist, a release sign-off form, or a derived menu of role × route × action).
- The evidence each check requires (command + expected output, test name, screenshot, log query, manual probe).

## The three statuses (and only these)

| Status | Meaning | When to use |
|---|---|---|
| **PASS** | The check succeeded; evidence proves it | The run produced the expected outcome AND the evidence is attached |
| **BLOCKED** | A precondition failed; the check could not run | A required role does not exist yet; the API errored before the UI assertion; a dependency is down |
| **NOT-TESTABLE** | The surface does not exist or access is missing | The page is not built yet; we lack production credentials; the feature is behind a flag we cannot toggle |

No other statuses. No `PARTIAL`. No `MOSTLY`. No emoji-only checkmarks without evidence.

`FAIL` is a synonym of "the run was performed AND the outcome did not match expectations." Use it sparingly; most "fails" are actually BLOCKED (the run could not complete) or evidence of an actual bug (in which case file the bug and mark the check FAIL with a link to it).

## The workflow

1. For each check on the list, identify **what evidence proves it**.
2. Run the evidence — load the page, click the button, fill the form, observe the network response, take a screenshot.
3. Capture the output. Paste, save, or summarize honestly.
4. Mark with the 3-status vocabulary. Attach evidence per check.
5. If asked to ship: every BLOCKED item must be resolved or explicitly accepted by the user in writing. NOT-TESTABLE items must be handed off with the exact command / access required.
6. Never mark PASS without exercised evidence. Reading the source code is NOT runtime evidence.

## Per-check evidence requirement

Every check is one row in the report. Every row has at least:

- **Status** (PASS / BLOCKED / NOT-TESTABLE / FAIL)
- **Evidence** — a concrete artifact:
  - Screenshot file path (preferred for UI checks)
  - Network response excerpt with timestamp
  - Console message excerpt with timestamp
  - Audit-log query result
  - The specific selector / URL that was exercised
- **Run identifier** (when / where / by whom / on what build)

If the evidence column is empty, the row is unfinished — not a pass.

### A disabled control is evidence of nothing

A greyed-out button is not a result. It is a **non-observation**: the flow behind it never ran, so nothing about it was tested. Recorded as a row either way it is wrong — as a PASS it claims a verification that did not happen, and as a permission FAIL it claims a deny that may never have been evaluated.

The reason it is inadmissible is that a disabled state is ambiguous between at least two causes that look identical on screen:

- **A permission deny** — the role genuinely lacks the right, and the UI is correctly hiding it.
- **A fixture-state gap** — the role is permitted, but the record is not in the state that enables the action (no stock to hand on, nothing selected, a prerequisite step not completed, an empty child collection). The control would enable the moment the data was right.

Disambiguate before scoring: put the record into the enabling state with a fixture or a setup step, then click. If the control enables and the action runs, the earlier grey was a data gap and the flow was never covered. If it stays disabled for a role that should have it, *now* you have a permission finding — and the API-side half of it still belongs to `route-access-matrix`, because a UI that hides a control proves nothing about the endpoint behind it.

The failure this hides is the expensive kind: a whole set of flows is declared browser-verified while every one of their buttons was grey, and the first real click — once the fixture carries real data — raises an error on every environment at once. Before claiming a flow is browser-verified, confirm the fixture put the record in the state where the action is *enabled*, and say so in the evidence.

## "No exception" as valid evidence

For checks like "the page loads without errors":

```
PASS — page loaded; 0 console errors during the 10s observation window after navigate; screenshot attached
```

Acceptable. The "no exception" claim names:

- **What was observed** (console errors)
- **The window of observation** (10s after navigate)
- **The output** (zero, and a screenshot)

Not acceptable:

```
PASS — looks fine
PASS — no errors
PASS ✓
```

These do not name what was observed, the window, or the output.

### An absence must also rule out client-side collapse of the signal

Naming the window is necessary but not sufficient when the check is "did the app tell the user". Notification layers routinely **dedupe**: a global toast / snackbar / alert store keyed on the message text will collapse an identical message rather than stack it, so the second and third trigger of the same failure add no new node to the DOM. Repeat a refusal three times to be thorough, check the DOM immediately after, find nothing, and the honest-looking conclusion — "the failure is silent, the user is never told" — is a false finding about a feature that works. The first trigger *did* surface it; the store simply refused to say it twice.

So an absence-of-signal observation is only evidence if the signal had a clear channel:

- Trigger it **once from a reset store** — a reload or a fresh context clears the collapsed set — rather than as the nth repeat of the same attempt.
- Or assert the underlying event instead of the rendered one: the network response, the console entry, the audit row. A deduped view cannot suppress those.
- Record which of the two you did. "No toast after the 3rd attempt" and "no toast on the first attempt after reload" are different claims, and only the second supports a silent-failure finding.

The same shape applies to any deduped or throttled surface — a banner shown once per session, a rate-limited email, an error boundary that renders once. Absence of a repeat is not absence of the signal.

## Code-read is not runtime evidence

Reading the source and concluding "the code handles X" is NOT evidence that X works in the running app:

- The code may not be in the current build (uncommitted local changes; wrong branch).
- The code may be guarded by a feature flag that is off in this environment.
- A configuration value may divert the actual code path.
- The build may have failed silently and shipped a stale bundle.

Code-read informs hypothesis. Runtime evidence confirms.

### The rule runs in both directions — a defect read from the source is also unconfirmed

The rule is usually applied to passes, but it holds identically for failures: "the code is wrong, therefore the app is broken" is the same unverified inference with the sign flipped. Reporting it as a live bug costs the report's credibility the first time the browser disagrees.

The mechanism that makes this common is that a **specification violation and a runtime failure are decided by different machinery**. A worked example: a `<form>` nested inside another `<form>` is invalid HTML — the HTML *parser* holds a form-element pointer from the context element and simply ignores the nested start tag, so the inner form is never created and its buttons submit the outer one. A live bug, on the reading. The browser said otherwise: the fragment was injected by a client library that parses the response into a **detached** container with no form ancestor and then moves the nodes in, and the DOM API permits a nesting the parser forbids. The inner form existed and its buttons pointed at their own endpoint. Ten seconds of runtime observation settled what the reading could not.

Handle it as follows:

- **Verify the failure in the browser before reporting a parser-level or spec-level defect.** Design a cheap direct observation — count the elements that should not exist, read the property that should be wrong — rather than arguing from the specification.
- If runtime says it works, the finding is **latent, not active**: still real, still worth fixing, but filed with the trigger condition named — in the example, "activates the moment this fragment is server-rendered inline, SSR'd, or pasted into the template", because those paths go through the parser the injection route bypassed.
- Latent findings do not belong in the FAIL column of a QA run. They are a separate line item, so that a reader can tell what is failing now from what will fail on a foreseeable change.

## Decision framework

- If investigation confirms the check PASSED → record evidence + move on.
- If a precondition failed → BLOCKED. Name the precondition.
- If the surface does not exist or is inaccessible → NOT-TESTABLE. Name what is needed.
- If the run completed and produced a wrong outcome → FAIL. File the bug. Link in the report.
- If two or more checks are genuinely about the same thing → merge into one check, evidence once.

## Safety gates

- **Never** mark PASS for a production check using only a staging probe — say so explicitly. Either re-run against production with permission, or mark NOT-TESTABLE.
- **Never** mark PASS without exercised evidence.
- **Never** collapse a checklist into a single "✅ all good" — every check gets a status.
- **Never** falsify evidence. If a screenshot was for a different run, do not attach it.
- **Never** mark FAIL without a concrete divergence (and when you do, treat it as a real failure that needs surfacing).

## Validation checklist

Before sending a QA report:

- [ ] Every check has one of the three statuses.
- [ ] Every PASS has exercised evidence attached.
- [ ] Every BLOCKED names the failed precondition.
- [ ] Every NOT-TESTABLE names what would unblock it.
- [ ] Every FAIL links to a filed bug.
- [ ] Run identifier present (when / where / who / build).
- [ ] No status downgraded to PASS to clear the report.
- [ ] No code-read used as runtime evidence — in either direction; every reported defect was observed at runtime, and anything that was not is filed as latent with its trigger condition.
- [ ] Every "nothing appeared" claim was observed with the notification store reset, or against the underlying network / console / audit signal.
- [ ] No row rests on a disabled control; every action-level check names the fixture state that enabled it.

## Output format

For each check:

```
[<status>] <check name>
  Evidence: <file path / excerpt / command output>
  Run: <YYYY-MM-DD HH:MM tz> on <env-name> by <actor> on build <commit-sha>
  Notes: <optional context>
```

For the report-level summary (one paragraph):

```
RUN — <env-name> — <date>
  Total checks: <N>
  PASS: <n>   BLOCKED: <n>   NOT-TESTABLE: <n>   FAIL: <n>
  Sign-off recommendation: <YES — ship | NO — see BLOCKED / FAIL list>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| "All tests pass ✓" (no per-check status) | Cannot audit; cannot replay; trust collapses on the first regression | Per-check status with evidence |
| "Code looks right" claimed as PASS | The running build may differ from the source | Runtime evidence required |
| "Should work" claimed as PASS | Speculative; unverifiable | Run it; capture; status |
| A static-analysis finding reported as a live bug | A spec violation and a runtime failure are decided by different machinery; the invalid construct may never reach the code path that breaks on it | Observe the failure in the browser first; if it does not occur, file it as latent with the trigger condition named |
| "No notification appeared" after repeating the same trigger | A deduped toast / banner store collapses the identical message, so the repeat produces no node even though the first one did | Trigger once from a reset store (reload / fresh context), or assert the network / console / audit signal |
| Scoring a greyed-out control as a PASS or as a permission FAIL | Disabled is a non-observation, ambiguous between a real deny and a fixture that never enabled the action | Put the record in the enabling state, then click; score what the click did |
| "Flow verified" when every button in it was disabled | Nothing in the flow was exercised; the first real click surfaces errors the whole pass claimed to cover | Confirm the fixture enables the action before claiming a flow is browser-verified |
| Marking PASS to clear a long checklist before deadline | The deadline does not move; the bug just hits later | Mark honestly; surface what cannot be done |
| BLOCKED with no named precondition | Operator cannot help unblock | Name the precondition |
| NOT-TESTABLE with no named access need | Cannot be handed off | Name the access / command needed |
| FAIL with no filed bug | The failure evaporates after the report | File bug; link in the report |
| Evidence is "see screenshot" without the screenshot | No evidence | Attach |
| Evidence is "we tried it last sprint" | Not a current run | Re-run on the current build |

## Portability rationale

The vocabulary and evidence requirement apply to any QA discipline:

- Manual UI testing
- Automated end-to-end testing
- API testing
- Performance regression
- Accessibility audit
- Security review sign-off

The skill does not assume:

- A specific test runner
- A specific UI framework
- A specific evidence storage
- A specific report format (the output format above is a default, not a constraint)

## Cross-references

- `runtime-reality-check` — verify the target is actually running on the expected build before evidence is meaningful.
- `safe-destructive-testing` — the evidence-gathering itself must not break the data being tested.
- `role-smoke-tests` — produces evidence rows that land in this skill's status vocabulary.
- `route-access-matrix` — produces evidence rows that land here.
- `modal-and-action-walkthroughs` — produces evidence rows that land here.
- `import-export-ui-checks` — produces evidence rows that land here.
- `defect-triage-and-closure` — owns what happens after a FAIL becomes a defect report: the closure gates behind "cannot reproduce" (the reporter's exact gesture, not an adjacent one), "works as designed", and "blocked — external". This skill owns the status word; that skill owns whether the verdict is admissible.
- `uat-readiness-report` — composes the final report from these statuses.
