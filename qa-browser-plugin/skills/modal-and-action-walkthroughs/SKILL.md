---
name: modal-and-action-walkthroughs
description: Per-action walkthrough — row actions, bulk actions, modal open/close, confirmation dialogs, form submit + cancel + dirty-leave. Owns the "open → assert → cancel" pattern, the "confirm → undo / verify" pattern, the modal-stack hygiene check (no orphaned modals), and the cancel-vs-close button distinction. Generic and framework-agnostic.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - open → assert → cancel walkthrough (verify the action is reachable AND cancellable without effect)
  - confirm → verify outcome walkthrough (verify the action actually does what it claims)
  - modal-stack hygiene check (cancellation does not leave a modal mounted)
  - confirmation-dialog handling (type-to-confirm, two-step button)
  - cancel-vs-close button distinction (does Esc work? does clicking the backdrop close?)
  - dirty-leave warning verification on forms
defers_to:
  - runtime-reality-check (must pass first)
  - browser-qa-discipline (status vocabulary)
  - safe-destructive-testing (only confirm destructive actions on disposable data)
  - console-and-network-capture (capture surrounding the action)
  - project user-flow definitions (which actions exist per surface)
user_invocable: false
---

# modal-and-action-walkthroughs

## Purpose

Smoke tests prove pages render. Action walkthroughs prove the interactions inside the pages work. The most common UI bug in this category is "the modal opens but Cancel does not close it" or "the action button fires twice on a double-click." This skill makes per-action evidence routine.

## When to use

Activate when:

- A change touches a row action, bulk action, modal, drawer, or confirmation flow.
- A change touches a form submit, cancel, or dirty-state warning.
- After `role-smoke-tests` passes and `route-access-matrix` passes — the next layer of QA.
- Before sign-off of any release with UX changes.

## Inputs

- Reality-check passed.
- Role with permission to perform each action under test (from credential map).
- **Action catalogue per page** — for each route in scope, the list of actions to walk:
  - Row actions (Edit, Archive, Delete, Impersonate, Custom).
  - Bulk actions (Archive selected, Export selected, Custom).
  - Modal flows (a modal that opens from a button, has internal state, submit/cancel).
  - Form flows (create / edit / submit / cancel / dirty-leave).
- **Disposable data signal** — for destructive actions, the rule from `safe-destructive-testing` applies.

## The two walkthrough patterns

### Pattern 1 — Open → Assert → Cancel (non-destructive verification)

For any modal / dialog / drawer:

```
1. Locate the trigger (button, row action menu item).
2. Click the trigger.
3. ASSERT: modal opens (selector visible).
4. ASSERT: modal contains expected fields / buttons / labels.
5. ASSERT: backdrop (if any) is rendered.
6. ASSERT: focus moved into the modal.
7. Cancel the modal — try each path:
   - Click Cancel button.
   - Hit Esc.
   - Click the backdrop (if the project's UX intends backdrop-close).
8. ASSERT: modal is no longer in the DOM (or properly hidden).
9. ASSERT: no underlying data changed.
10. ASSERT: focus returned to the trigger.
```

PASS: every assertion passes; no data change; no console errors; no network mutation.

This pattern proves the modal is reachable and reversible without side effects. Run it BEFORE the confirm pattern.

### Pattern 2 — Confirm → Verify (destructive verification, disposable data only)

Only on disposable data. Only with the safety rules from `safe-destructive-testing` applied.

```
1. Identify a disposable target (record clearly marked as test data; see safe-destructive-testing).
2. Capture the target's pre-state (screenshot of detail page; API GET of the record).
3. Trigger the action (open modal, fill required fields, click confirm).
4. Handle confirmation:
   - Type-to-confirm: type the literal expected string.
   - Two-step button: click; wait; click again.
   - Type/wait deliberately so the action is intentional.
5. ASSERT: action fires (network call expected — capture).
6. ASSERT: response is success.
7. Capture post-state (screenshot; API GET; audit-log query if available).
8. ASSERT: outcome matches expectation (record deleted / archived / state-transitioned).
9. ASSERT: audit-log row appeared.
10. Where supported, exercise undo within the window:
    - Click Undo in the post-action toast.
    - ASSERT: record restored.
11. Capture cleanup-evidence (whatever restore happened).
```

PASS: action effect matches expectation; audit row present; undo (if available) works.

## Modal-stack hygiene

After every walkthrough:

- Inspect the DOM for orphaned modals: a hidden modal that is still mounted (commonly `display:none` on the wrapper but the modal tree persists).
- A mounted-but-hidden modal is a memory leak risk and a cause of bugs like "the second open shows stale state."
- The check: count modal roots before and after the walkthrough; the count should be the same.

## Confirmation dialog handling

| Dialog shape | How to handle |
|---|---|
| Simple confirm modal with Cancel + OK | Click Cancel for pattern 1; click OK for pattern 2 |
| Modal with consequence summary + checkbox "I understand" | The checkbox must be ticked before the confirm button enables |
| Modal with type-to-confirm input | Must type the exact expected string (case-sensitive by default per `react-kit/admin-dangerous-actions`) |
| Two-step button (click → "click again to confirm" → click) | Wait briefly between clicks; do not auto-click |
| Native browser `confirm()` | Use the MCP's dialog handler (`handle_dialog`) to accept or dismiss |

For type-to-confirm: capture the modal's instruction text, derive the expected string, type it, screenshot, then click. Do not hardcode the string assumption.

## Cancel vs close distinction

UX intent matters:

- **Cancel button** = explicit "discard, do nothing." Always present, always cancels.
- **X / Close icon** = "I'm done with this dialog." May or may not save (project-dependent).
- **Esc** = same as Cancel by convention.
- **Backdrop click** = project-dependent. Some apps treat as Cancel, some require explicit button, some ignore.

The walkthrough captures which paths are supported per dialog and reports inconsistency:

```
[FAIL] Modal "Edit User"
  Cancel button: closes modal — PASS
  Esc key: does NOT close modal — FAIL (inconsistent with the rest of the app)
  Backdrop click: closes modal — PASS
  Verdict: Esc should also cancel; otherwise the modal is inconsistent
```

## Dirty-leave warning verification

For forms (per `react-kit/admin-forms`):

```
1. Open the edit form.
2. Make a field change (typing in an input).
3. Try to navigate away (browser_navigate to a different route).
4. ASSERT: beforeunload warning appears OR the navigation is intercepted with a confirm dialog.
5. Cancel the navigation.
6. ASSERT: still on the form, dirty state preserved.
7. Try Cancel button on the form.
8. ASSERT: "Discard changes?" confirmation appears.
9. Click Discard.
10. ASSERT: form reset OR navigation completes.
```

A form without dirty-leave warning is a finding (MEDIUM per `react-kit/admin-forms`).

## Per-action evidence row

```
[<status>] action="<verb> on <entity>" route=<url>
  Pattern: <open-assert-cancel | confirm-verify>
  Pre-state: <screenshot / API snapshot>
  Trigger: <selector clicked>
  Modal: <opened in <Xms>; field assertions PASS>
  Confirmation: <none | checkbox | type-to-confirm "<string>" | two-step>
  Action fire: <network call, status>
  Post-state: <screenshot / API snapshot>
  Audit log: <row found | missing>
  Undo (if applicable): <PASS | not supported | FAIL>
  Modal stack: <clean | orphaned modal detected>
  Console: <0 errors>
  Run: <YYYY-MM-DD HH:MM tz>
```

## Safety gates

- **Never** run pattern 2 (Confirm → Verify) on non-disposable data.
- **Never** run pattern 2 on production by default — staging / UAT only.
- **Never** click destructive bulk actions on selections that include real records.
- **Never** bypass confirmation flows by directly POSTing to the API endpoint; the test is of the UI flow.
- **Never** mark a walkthrough PASS when the audit-log row is missing (per the project's audit requirements).
- **Never** include passwords / OTPs / sensitive field values in captured screenshots — verify post-capture and redact if needed.

## Validation checklist

Before sending an action-walkthrough report:

- [ ] Reality-check PASS row.
- [ ] Pattern 1 (open-cancel) ran first for every modal-opening action.
- [ ] Pattern 2 (confirm-verify) only on disposable data.
- [ ] Every confirmation dialog handled per its actual shape.
- [ ] Modal-stack hygiene checked after every walkthrough.
- [ ] Dirty-leave warning verified for every form in scope.
- [ ] Audit-log evidence present for every destructive action.
- [ ] No PII visible in screenshots.

## Output format

```
ACTION WALKTHROUGHS — <env-name> — <date>

[PASS] reality-check

PATTERN 1 — OPEN → ASSERT → CANCEL

  [PASS] route=/admin/users  action="Edit user"
    Modal opened in 240ms; Cancel/Esc/backdrop all close cleanly; no data change; stack clean
  [FAIL] route=/admin/orders action="Refund order"
    Modal opened; Cancel button closes; Esc does NOT close
    Severity: MEDIUM (inconsistency)

PATTERN 2 — CONFIRM → VERIFY (disposable data)

  [PASS] route=/admin/users  action="Delete user (disposable: qa-user-1)"
    Type-to-confirm "qa-user-1" → fired; record deleted; audit row present; undo works
  [FAIL] route=/admin/orders action="Cancel order (disposable: qa-order-1)"
    Action fired; record state changed to "cancelled"; audit row MISSING
    Severity: HIGH (audit-log gap)

DIRTY-LEAVE WARNINGS

  [PASS] form=/admin/users/[id]/edit  — beforeunload + cancel-confirm both work
  [FAIL] form=/admin/products/[id]/edit  — no dirty-leave warning on cancel
    Severity: MEDIUM

SUMMARY
  Walkthroughs: <N>
  Pattern 1 PASS: <n> / FAIL: <n>
  Pattern 2 PASS: <n> / FAIL: <n>
  Dirty-leave PASS: <n> / FAIL: <n>
  Highest-severity failure: <link to finding>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Confirm-verify before Open-cancel | If the modal cannot cancel, you cannot recover from a misconfigured probe | Run Pattern 1 first |
| Skip the dirty-leave check | Most common form bug; users lose work | Verify every form |
| Hardcode the type-to-confirm string | Project changes it; test breaks | Read the instruction text from the modal |
| Mark PASS without checking the audit row | Destructive action with no audit trail is a compliance bug | Verify audit |
| Mark PASS without checking modal-stack after | Orphaned modals accumulate; future test runs see stale state | Stack hygiene check |
| Use Pattern 2 to test "Delete account" without a disposable account | Real account destroyed | Disposable data only |
| Trust UI feedback ("Deleted!") without checking the API and audit | UI lies on optimistic update failure | Verify post-state |

## Portability rationale

Modal walkthroughs apply to any web app with interactive UI. The skill does not depend on:

- A specific modal library
- A specific form library
- A specific audit log shape

It only needs the MCP browser to navigate, click, type, and inspect DOM + network.

## Cross-references

- `runtime-reality-check` — required first.
- `browser-qa-discipline` — status vocabulary.
- `role-smoke-tests` — navigation pass that comes first.
- `route-access-matrix` — access pass that comes second.
- `safe-destructive-testing` — required gate for Pattern 2.
- `console-and-network-capture` — capture format for the API responses.
- `uat-readiness-report` — walkthrough rows feed the final report.
