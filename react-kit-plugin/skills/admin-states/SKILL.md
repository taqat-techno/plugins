---
name: admin-states
description: Loading / error / empty / no-results / partial-error display patterns for admin UI. Owns the "skeleton matches final layout" rule, the "error message + actionable next step + support hint" contract, the empty-vs-no-results distinction, and the per-row partial-error rule. Activates when adding or modifying any loading state, error display, empty state, or partial-error indicator anywhere in the admin UI.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - loading-skeleton-matches-final-layout rule
  - error-display contract (message + next step + support hint; never raw stack)
  - empty-state vs no-results-state distinction
  - per-row partial-error indicator pattern
  - in-flight feedback during pagination / refetch
  - non-blocking toasts vs blocking modals
defers_to:
  - admin-shell (the shell renders a bootstrap loading state)
  - admin-crud (loading state inside a list)
  - admin-forms (in-flight feedback during submit)
  - project observability layer (where unexpected errors should be reported, with what fields)
user_invocable: false
---

# admin-states

## Purpose

Three states confuse users more than any others: a blank screen during loading, an "Error" message with no path forward, and an empty state that looks identical to "your filters match nothing." This skill makes each state a distinct, predictable affordance.

## When to use

Activate when:

- Adding any first-load loading state.
- Adding any error display.
- Adding an empty state (no records yet).
- Adding a no-results state (records exist but filters return zero).
- Showing in-flight feedback during pagination, refetch, or submit.
- Handling partial failure (some items in a list failed; others did not).

## Inputs (adapter)

1. **Error reporting service** — Sentry, Datadog, Bugsnag, custom, or none. The skill specifies what to send, not which service.
2. **Support contact convention** — link, email, chat, ticket flow. Used in error messages.
3. **Illustration / iconography source** — for empty states. Project picks the look; the skill says where to place it.
4. **i18n keys for state messages** — keys live in the i18n bundle; skill does not hard-code copy.

## Read-only investigation steps

1. **What is the first-paint experience today?** Spinner-on-blank or skeleton? If spinner-on-blank, that is a known smell — fix to a skeleton.
2. **What does an unexpected error currently display?** Raw stack trace? "Error" only? An actionable message? Look at one example.
3. **Are empty and no-results visually identical?** If yes, the user cannot tell whether to "add" or "clear filters." Fix.
4. **What happens when one item in a list fails to load?** Does the whole list crash, or does it indicate per-item?

## Decision framework

### Loading skeleton matches final layout

```
Final list                            Skeleton
+-----+-----------+--------+         +-----+-----------+--------+
| #   | Name      | Role   |         | ▢▢▢ | ▢▢▢▢▢▢▢▢▢ | ▢▢▢▢▢▢ |
+-----+-----------+--------+         +-----+-----------+--------+
| 1   | Ahmed S.  | Manager|         | ▢▢▢ | ▢▢▢▢▢▢▢▢▢ | ▢▢▢▢▢▢ |
| 2   | Sara K.   | Viewer |   →     | ▢▢▢ | ▢▢▢▢▢▢▢▢▢ | ▢▢▢▢▢▢ |
+-----+-----------+--------+         | ▢▢▢ | ▢▢▢▢▢▢▢▢▢ | ▢▢▢▢▢▢ |
                                     +-----+-----------+--------+
```

- Skeleton column count = final column count.
- Skeleton row height ≈ final row height.
- Skeleton uses a subtle shimmer or pulse animation — never a full-screen blocking spinner.
- First-load shows skeleton; subsequent pagination shows the previous page dimmed with an inline indicator (avoids the layout flash).

For detail pages:

- Skeleton matches the page's section structure (header card + tabs + content blocks).
- Detail loading does NOT block the shell; the shell stays interactive.

### In-flight feedback

| Phase | Affordance |
|---|---|
| Initial load | Skeleton matching layout |
| Refetch after filter change | Previous data dimmed + inline spinner near the filter bar; list does not disappear |
| Pagination | Previous page dimmed; pagination control disabled briefly |
| Submit | Submit button → "Saving…" disabled state; form stays interactive but read-only-ish |
| Bulk action in progress | Progress bar "200 / 1247" + cancel button |
| Background job | Non-blocking toast "Import in progress — you can navigate away" |

### Error display contract

Every error display has three parts:

```
+----------------------------------------------+
|  ⚠  We couldn't load the user list.          |  ← what failed (1 line)
|                                              |
|  Try refreshing the page or check your       |  ← actionable next step
|  internet connection.                        |
|                                              |
|  Still stuck? [Contact support]              |  ← support hint with link
+----------------------------------------------+
                          [Retry]
```

1. **What failed** — one line, plain language. NOT "Error" alone. NOT a stack trace.
2. **Actionable next step** — what the user can try. Refresh, retry, check connection, wait a moment, contact support.
3. **Support hint** — a way to escalate. Link, ticket, email, in-app chat.

Variants:

| Variant | When |
|---|---|
| Inline (in place of the list) | Major: list cannot render at all |
| Banner at top of page | Moderate: page partially works, one section failed |
| Toast | Minor: a non-blocking action failed (e.g., autosave) |
| Modal | Rare — only when the user MUST acknowledge |

### Empty state vs no-results state

```
EMPTY                               NO RESULTS
+---------------------+             +-------------------------+
|    [illustration]   |             |       [smaller icon]    |
|                     |             |                         |
| No users yet        |             | No users match filters  |
|                     |             |                         |
| Add your first user |             | Try adjusting filters   |
| to get started.     |             |                         |
|                     |             |                         |
| [+ Add user]        |             | [Clear all filters]     |
+---------------------+             +-------------------------+
```

- **Empty** = the underlying table has zero rows ever. CTA is the primary action (add the first record).
- **No-results** = rows exist; filters return zero. CTA is to clear or change the filters. NO "Add" button (encourages duplicates).
- The two states are visually distinct (illustration vs icon; CTA verb differs).
- Detect via API: response includes `totalCount` of unfiltered list separately from `filteredCount`, OR the UI knows there are active filters.

### Per-row partial-error

```
+-----+-----------+--------+-----------+
| #   | Name      | Role   |           |
+-----+-----------+--------+-----------+
| 1   | Ahmed S.  | Manager| ✓         |
| 2   | Sara K.   | (error)| ⚠ Reload  |  ← row failed; offer retry
| 3   | Omar L.   | Admin  | ✓         |
+-----+-----------+--------+-----------+
```

- One row failing does NOT crash the whole list.
- Failed row shows a per-row indicator + retry affordance.
- The user can still scroll, sort, filter, and act on other rows.
- The error is logged to the observability layer (per project) with rowId for debugging.

### Toasts vs modals

| Modal | Toast |
|---|---|
| User MUST acknowledge | User CAN dismiss |
| Blocks interaction | Non-blocking |
| Used for: destructive confirmations, critical errors that require action | Used for: success feedback, recoverable failures, background-job completion |
| Default focus on Cancel | Auto-dismiss after a few seconds |

- Success toasts: 2–4 second auto-dismiss. Position: bottom-right (LTR) / bottom-start (RTL-friendly per `admin-rtl-ltr`).
- Error toasts: do NOT auto-dismiss; require the user to dismiss (the failure may scroll out of view otherwise).
- Toast queue: only one toast at a time visible; new ones stack with a small offset.

### Reporting unexpected errors

When an unexpected error happens (e.g., the API returned a 5xx):

1. Display the user-facing error (what / next-step / support).
2. Send to observability with: route, action attempted, user role (NOT user PII), timestamp, request id.
3. Include a `request-id` header in API requests so support can correlate the user's report to the server log.
4. Surface the `request-id` in the error UI's "contact support" link so the user can include it.

## Safety gates

- **Never** show a raw stack trace, error object, or internal field name to the user.
- **Never** show "Error" with no next step.
- **Never** silently swallow errors (no `catch {}` that drops the error). Either show, retry, or log.
- **Never** auto-dismiss an error toast.
- **Never** put user PII in the support hint link query parameters.
- **Never** crash an entire list because one row failed.
- **Never** use a modal for a non-blocking outcome.
- **Never** ship loading states that flash content (skeleton → real → skeleton).

## Validation checklist

Before committing a state-related change:

- [ ] First-load shows a skeleton matching final layout (not a spinner-on-blank).
- [ ] Pagination shows previous-page-dimmed, not full-screen reset.
- [ ] Error displays have what / next-step / support-hint.
- [ ] Empty vs no-results are visually distinct.
- [ ] Per-row partial-error does not crash the list.
- [ ] Success: short auto-dismiss toast.
- [ ] Error: persistent toast (manual dismiss).
- [ ] Observability gets route + role + request-id; no PII.
- [ ] Tested in both LTR and RTL if RTL locales exist (per `admin-rtl-ltr`).

## Output format

When scaffolding a state catalogue, output:

```
STATES FOR <page-name>
  First load: skeleton matching <layout>
  Refetch: previous-data-dimmed + inline indicator
  Error (major): inline error block with retry
  Error (moderate): top banner with retry
  Empty: illustration + "Add your first <entity>" CTA
  No-results: smaller icon + "Clear filters" CTA
  Per-row error: row-end indicator + per-row retry
  Submit in flight: button → "Saving…" disabled
  Background job: non-blocking toast
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Spinner-on-blank during first load | Layout shift when data arrives; user sees empty screen | Skeleton matching final layout |
| "Error" with no next step | User cannot recover | What / next-step / support-hint |
| Identical empty and no-results state | User adds duplicates from a no-results screen | Distinct affordances |
| Whole list crashes on one row's error | Lose access to N records because of 1 | Per-row partial-error indicator |
| Auto-dismiss error toast | Failure invisible if user looks away | Manual dismiss |
| Raw stack trace in UI | Discloses internals; intimidates non-technical actors | User-friendly message; full trace in observability |
| `catch (e) {}` | Failure invisible; debugging impossible | Log; surface; retry |
| Multiple modals stacked | Cognitive overload; user dismisses without reading | One blocking interaction at a time |
| Skeleton column count differs from final table | Layout shift when data arrives | Match column count |
| Loading flashes between skeleton ↔ real ↔ skeleton on every keystroke | Disorienting | Debounce; show previous data dimmed |

## Portability rationale

State patterns are framework-agnostic. The skill does not depend on:

- A specific UI library (skeleton primitives exist everywhere)
- A specific toast library
- A specific error-reporting service

## Cross-references

- `admin-shell` — bootstrap loading state.
- `admin-crud` — list-level skeleton, empty, no-results.
- `admin-forms` — submit-in-flight feedback.
- `admin-import-export` — per-phase progress affordances.
- `admin-rtl-ltr` — toast position, skeleton direction.
- `admin-route-auditor` (agent) — flags spinner-on-blank, raw stack traces, missing empty-vs-no-results distinction.
