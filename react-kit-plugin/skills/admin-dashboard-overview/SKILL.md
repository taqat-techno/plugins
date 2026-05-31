---
name: admin-dashboard-overview
description: Design rules for an admin module overview / landing page or a metrics dashboard. Owns KPI card design (label + value + optional trend/delta + drill-down link), role-aware metric visibility, a quick-actions block, a recent-activity / workflow-summary feed, a data-freshness indicator, the chart-vs-table-vs-number affordance choice, and the per-widget state set that distinguishes NO-DATA (zero is legitimate) from FAILED-KPI (the metric API errored) from LOADING (skeleton). Activates when building an overview or landing page for an admin module, assembling a metrics dashboard, adding or arranging KPI cards, choosing between a number, a trend chart, or a small table, or wiring per-widget loading and error affordances. Generic and portable — role names, metric sources, the data-fetching library, and the auth convention are project-supplied adapter inputs.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - KPI card anatomy (label + value + optional trend/delta + optional drill-down link)
  - role-aware metric visibility (only render metrics the role may see)
  - the quick-actions block (the role's common create/act entry points)
  - the recent-activity / workflow-summary feed
  - the data-freshness indicator (as-of timestamp / refresh affordance)
  - the chart-vs-table-vs-number affordance decision
  - the per-widget state set — distinguish NO-DATA from FAILED-KPI from LOADING
  - the "never render 0 when the KPI fetch failed" rule
defers_to:
  - data-fetching-states (maps each fetch outcome to one state; owns the no-0-on-failure data contract)
  - admin-roles-and-permissions (authorization; UI hide is not a security boundary)
  - admin-states (the visual rendering of loading / error / empty affordances)
user_invocable: false
---

# admin-dashboard-overview

## Purpose

An overview page is the first surface a role sees, and it is the easiest place to lie to a user. A KPI that renders `0` because its fetch failed reads as "you have nothing" when the truth is "we don't know." A chart drawn for a single number wastes a screen. A metric a role may not see, rendered anyway, leaks scope. This skill makes an overview page honest: every widget declares which role may see it, which source feeds it, which affordance fits its data shape, and how it distinguishes a legitimate zero from a failed fetch from a still-loading state.

## When to use

Activate when:

- Building or modifying an overview / landing page for an admin module.
- Assembling a metrics dashboard.
- Adding, removing, or arranging KPI cards.
- Deciding whether a metric should be a number, a trend chart, or a small table.
- Adding a quick-actions block or a recent-activity feed.
- Adding a data-freshness / "as-of" indicator or a refresh control.
- Wiring per-widget loading and error affordances on an overview.

Skip when:

- Building a list / table page (use `admin-crud`).
- Building a record detail page or a status-transition action (that is the detail/workflow surface).
- Wiring the data hook itself (use `data-fetching-states`).

## Inputs (adapter)

Every project value is a named adapter input — never hard-code one.

1. **`ROLE_SOURCE`** — how the current role / permission set is read. The skill asks "may this role see this metric"; the project answers.
2. **`METRIC_SOURCE(metricKey)`** — the endpoint or aggregate that produces each metric. Aggregation is owned by the backend; the dashboard renders, it does not compute.
3. **`DATA_LIB`** — the data-fetching library (its loading / error / stale flags). Defer the outcome→state mapping to `data-fetching-states`.
4. **`DRILL_TARGET(metricKey)`** — the filtered list route a KPI links to when clicked. May be absent (some KPIs are display-only).
5. **`FRESHNESS_SOURCE`** — where the "as-of" timestamp comes from (server response metadata, last-fetch time).
6. **`STATE_COLORS` / `STATE_LABELS`** — centralized status→color and status→label maps. Charts and badges read these; no widget hard-codes its own palette.
7. **`QUICK_ACTIONS(role)`** — the role's common entry points (create / act). Filtered by role before render.
8. **`i18n_KEYS`** — copy for labels, empty messages, and freshness text. The skill does not hard-code copy.

## Read-only investigation steps

1. **What does a KPI show when its fetch fails today?** If it shows `0`, that is a defect — a failed fetch must not read as a legitimate zero. Look at one example.
2. **Are NO-DATA and FAILED-KPI visually distinct?** A legitimate zero ("0 open Tickets") must look different from "this metric errored."
3. **Is any rendered metric gated by role?** Compare the widgets to the role's permission set. A metric the role may not see should not render at all.
4. **Is any widget a chart where a single number would do?** A lone scalar inside a chart frame is noise.
5. **Does the page state a freshness time?** If counts can go stale, the user needs an "as-of" cue — and a manual refresh if there is no auto-revalidation.
6. **Where is aggregation done?** If the frontend sums or computes percentages, that is a smell — the backend owns aggregation; the dashboard transforms (rename / filter zero series / apply colors) only.

## Decision framework

### KPI card anatomy

A KPI card is single-purpose: it displays, it does not fetch or aggregate.

```
+---------------------------------+
|  [icon]   Open Requests         |  ← label (what the number means)
|                                 |
|        1,248        ▲ +6%       |  ← value (large) + optional trend/delta
|                                 |
|  Awaiting first response        |  ← optional one-line description
|                                 |
|  View open Requests  →          |  ← optional drill-down to a filtered list
+---------------------------------+
```

| Element | Required | Rule |
|---|---|---|
| Label | yes | Plain noun phrase; says what the number counts |
| Value | yes | Large; the one fact the card exists for |
| Trend / delta | optional | Sign + magnitude vs a prior period; green up / red down / gray flat — read from `STATE_COLORS`, never reuse red for a non-negative meaning |
| Description | optional | One muted line of context |
| Drill-down link | optional | Navigates to `DRILL_TARGET(metricKey)` (a filtered list); absent if there is nowhere to drill |

- Drill-down logic lives outside the card (the card is display-only); the card receives a target, it does not build queries.
- Cap a single grid at roughly 3–6 KPIs. Beyond that, group into sections or tabs — a wall of numbers is unreadable.

### Role-aware metric visibility

```
canSee(metricKey, role) under ROLE_SOURCE ?
        │
   ┌────┴────┐
  yes        no
   │          │
 render    DO NOT render the widget at all
 widget    (no placeholder, no "restricted" tile,
            no disabled card)
```

- Visibility is decided per widget against `ROLE_SOURCE`. A metric the role may not see is omitted, not greyed out.
- A platform-wide aggregate and a self-scoped metric are different widgets feeding from different `METRIC_SOURCE`s — never relabel one as the other for a different role.
- **UI omission is not authorization.** The backend must still refuse a metric the caller may not request. Defer the gate to `admin-roles-and-permissions`.

### Quick-actions block

- A small set of the role's most common entry points (e.g., "New Order", "New Ticket").
- Filter `QUICK_ACTIONS(role)` *before* render — never render an action the role cannot perform, even disabled.
- Actions navigate or open a create surface; they do not perform mutations inline on the overview.

### Recent-activity / workflow-summary feed

- A short reverse-chronological list of recent events or a per-status count summary (e.g., "12 pending, 4 in review").
- Read-only on the overview. Acting on an item navigates to its detail surface.
- Feed data is pre-shaped by the backend; the feed renders it, it does not recompute counts.

### Data-freshness indicator

| Condition | Affordance |
|---|---|
| Counts can drift and auto-revalidate runs | Show an "as-of `<time>`" line from `FRESHNESS_SOURCE`; no manual button needed |
| Counts can drift and there is no auto-revalidation | Show "as-of" **and** a manual refresh control |
| Numbers are effectively static | No freshness cue |

- Never show "as-of `<time>`" without either auto-revalidation or a refresh control — a stale timestamp with no way to refresh is worse than none.

### Affordance choice — number vs trend chart vs table

```
Is the metric ONE scalar that stands alone?
   └─ yes → KPI card (number). Do NOT wrap a lone number in a chart.

Is the point a change OVER TIME or a DISTRIBUTION across categories?
   └─ yes → chart (line/area for time; bar/pie for distribution).
            Backend supplies the pre-aggregated series.

Is it a SMALL set of rows the user will read row-by-row
   (e.g., top 5 records, recent activity)?
   └─ yes → small table / feed. A chart of 5 labelled rows is harder
            to read than the 5 rows.
```

| Data shape | Affordance |
|---|---|
| Single scalar | KPI card (number) |
| Time series | Trend chart (line / area) |
| Category distribution | Bar / pie chart |
| ≤ ~7 labelled rows to read exactly | Small table or feed |
| Long browsable list | Not a dashboard widget — link out to a list page |

### Per-widget state set — NO-DATA vs FAILED-KPI vs LOADING

This is the rule that matters most. Resolve each widget's fetch outcome (via `DATA_LIB`, mapped per `data-fetching-states`) into exactly one of:

```
                    fetch outcome
                         │
        ┌────────────────┼────────────────────┐
   in flight         resolved OK            errored
        │                │                     │
     LOADING      value present?           FAILED-KPI
   (skeleton)    ┌───────┴────────┐      (show "—" / "unavailable"
                yes              no        + retry; NEVER show 0)
                 │                │
            show value        NO-DATA
                              (legitimate zero:
                               "0 open Requests")
```

| State | Trigger | Affordance |
|---|---|---|
| LOADING | request in flight | Skeleton sized to the final widget; never a 0, never an empty chart |
| NO-DATA | resolved, value is a legitimate zero/empty | Show the real zero ("0 open Requests") or an inline empty-chart placeholder — this is a true fact |
| FAILED-KPI | request errored | Value renders as `—` (or "unavailable") + a retry affordance; the chart is omitted, not drawn empty |

- A `0` is a claim that the count is zero. Only render it when the fetch **succeeded**. A failed fetch renders `—`, never `0`.
- For charts: NO-DATA shows an inline empty placeholder; FAILED-KPI omits the chart and shows the error affordance. Never draw a chart with zero points to represent failure.
- Prefer centralizing the fetch so widgets share one loading/error resolution; the *display* of each state defers to `admin-states`.

## Safety gates

- **Never** render `0` (or any number) when the metric fetch failed — a failed fetch is `—`/"unavailable", not zero.
- **Never** make NO-DATA and FAILED-KPI look identical.
- **Never** render a metric a role may not see — omit the widget, do not disable or placeholder it.
- **Never** treat UI omission as authorization; the backend must still refuse out-of-scope metrics.
- **Never** wrap a single scalar in a chart frame.
- **Never** draw a chart with zero data points to signify either empty or failed — use the matching state affordance.
- **Never** aggregate or compute sums/percentages on the frontend — the backend owns aggregation; the dashboard transforms only.
- **Never** show an "as-of" timestamp with no refresh path when there is no auto-revalidation.
- **Never** render a quick action or drill-down link the role cannot use.
- **Never** hard-code a color, label, or copy string in a widget — read `STATE_COLORS` / `STATE_LABELS` / `i18n_KEYS`.

## Validation checklist

Before committing a dashboard / overview change:

- [ ] Every widget declares its role visibility against `ROLE_SOURCE`; out-of-scope widgets are omitted entirely.
- [ ] No widget renders `0` on a failed fetch — FAILED-KPI shows `—`/"unavailable" + retry.
- [ ] NO-DATA, FAILED-KPI, and LOADING are three visually distinct states per widget.
- [ ] Each KPI has a label and a value; trend / description / drill-down are present only when meaningful.
- [ ] No single scalar is rendered inside a chart frame.
- [ ] Charts receive pre-aggregated data; no frontend sums or percentages.
- [ ] Quick actions and drill-down links are filtered by role before render.
- [ ] A freshness cue is present when counts can drift, with a refresh path if there is no auto-revalidation.
- [ ] Colors / labels / copy come from `STATE_COLORS` / `STATE_LABELS` / `i18n_KEYS`, not inline literals.
- [ ] The corresponding backend metric endpoint enforces the same role scope (paired gate; defer to `admin-roles-and-permissions`).

## Output format

When scaffolding a dashboard, emit a DASHBOARD SPEC: one widget per row.

```
DASHBOARD SPEC — <module> overview
  visible-to: <role(s)>     freshness: as-of <FRESHNESS_SOURCE> (refresh: yes/no/auto)

  | Widget            | Metric / source        | Role  | Affordance     | NO-DATA            | FAILED-KPI        |
  |-------------------|------------------------|-------|----------------|--------------------|-------------------|
  | Open Requests     | open_count / METRIC..  | all   | KPI number     | "0 open Requests"  | "—" + retry       |
  | Requests over time| requests_series / ...  | mgr   | line chart     | empty-chart note   | omit chart + retry|
  | Top 5 Customers   | top_customers / ...    | mgr   | small table    | "No Customers yet" | "—" + retry       |
  | By status         | status_breakdown / ... | all   | pie chart      | empty-chart note   | omit chart + retry|

  quick-actions (role-filtered): [ New Order ] [ New Ticket ]
  recent-activity feed: reverse-chrono, read-only, links to detail
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Vanity metric (a big number nobody acts on) | Consumes prime space; no decision follows from it | Show metrics that drive a drill-down or an action; drop the rest |
| `0` rendered on a failed fetch | Reads as "you have nothing" when the truth is "we don't know" | FAILED-KPI shows `—`/"unavailable" + retry; only a succeeded fetch shows `0` |
| NO-DATA and FAILED-KPI look the same | User trusts a zero that is actually an error | Three distinct states: LOADING / NO-DATA / FAILED-KPI |
| Chart where a single number suffices | Wastes space; harder to read than the scalar | KPI card for a lone scalar; charts only for trend/distribution |
| Role-blind metric (rendered to everyone) | Leaks scope; clutters the page | Gate each widget by role; omit (don't disable) out-of-scope widgets |
| Disabled / "restricted" tile for an unauthorized metric | Still reveals the metric exists; clutter | Omit the widget entirely |
| Frontend computes sums / percentages | Drifts from the backend's source of truth | Backend aggregates; dashboard renders/transforms only |
| "As-of `<time>`" with no refresh and no auto-revalidate | A stale number the user cannot refresh | Add a refresh control, or rely on auto-revalidation, or drop the timestamp |
| Empty chart drawn to mean "failed" | Looks like real (zero) data | Omit the chart on FAILED-KPI; inline placeholder only on NO-DATA |

## Portability rationale

The skill names every project-specific value as an adapter input — role source, metric sources, data library, drill targets, freshness source, color/label maps, quick actions, i18n keys. It does not depend on:

- A specific charting library (the affordance choice is shape-based, not library-based).
- A specific data-fetching library (outcome→state mapping is delegated to `data-fetching-states`).
- A specific auth model (visibility is "may this role see it"; the project answers).
- Any domain noun — Orders, Tickets, Requests, Customers, Products, Records are interchangeable placeholders.

The widget shape, the three-state rule, and the affordance decision hold for any module in any domain.

## Cross-references

- `data-fetching-states` — maps each widget's fetch outcome to one state and owns the no-0-on-failure data contract; this skill consumes that resolution and decides the *widget* affordance.
- `admin-roles-and-permissions` — authorization for the metrics a role may request; UI omission here is presentation, not a security boundary.
- `admin-states` — the visual rendering of LOADING (skeleton), empty, and error affordances that the per-widget states resolve to.
- `admin-crud` — the list page a KPI drill-down navigates into.
