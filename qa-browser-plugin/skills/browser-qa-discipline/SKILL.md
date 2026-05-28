---
name: browser-qa-discipline
description: Evidence discipline for browser QA. Owns the PASS / BLOCKED / NOT-TESTABLE vocabulary, the per-check evidence requirement, and the "code-read is NOT runtime evidence" rule. Activates at the start of any QA pass, before reporting a check as PASS, and before signing off a UAT or release. Generic and portable — no framework or product assumptions.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - PASS / BLOCKED / NOT-TESTABLE three-status vocabulary
  - per-check evidence requirement
  - code-read-is-not-evidence rule
  - silent-pass-is-not-pass rule
  - no-exception-as-valid-evidence rule (with named-run convention)
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

## Code-read is not runtime evidence

Reading the source and concluding "the code handles X" is NOT evidence that X works in the running app:

- The code may not be in the current build (uncommitted local changes; wrong branch).
- The code may be guarded by a feature flag that is off in this environment.
- A configuration value may divert the actual code path.
- The build may have failed silently and shipped a stale bundle.

Code-read informs hypothesis. Runtime evidence confirms.

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
- [ ] No code-read used as runtime evidence.

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
- `uat-readiness-report` — composes the final report from these statuses.
