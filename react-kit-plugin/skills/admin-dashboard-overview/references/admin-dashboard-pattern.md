# Admin dashboard / overview pattern

A reusable reference for building an admin landing/overview screen: a grid of KPI cards, supporting charts, quick actions, a recent-activity feed, and a workflow summary. It is domain-neutral. Use placeholder entities (Orders, Tickets, Requests, Customers, Products, Records) and generic roles (admin, manager, operator, viewer). Plugin behavior must never depend on any example below.

## Core rules

- The dashboard owns ONE data fetch. All widgets read from the same query result and the same loading/error state. Never let each widget fetch independently.
- The backend owns aggregation (counts, breakdowns, time-series). The frontend only transforms for display (rename fields, drop zero rows, map colors). Never compute sums or percentages on the client.
- A widget is single-purpose: it displays. Drill-down, filtering, and permission decisions live in the parent or in guards — not inside the widget.
- Distinguish three negative states explicitly: loading, no-data (empty), and failed. They render differently and must be decided upstream, not inferred inside a card.
- Permission-denied is never an empty state. If a role cannot see a widget, omit the widget entirely — do not render a "you don't have access" placeholder.
- Centralize the color/label maps for statuses at the dashboard level. Every widget reads the same map.
- Cap a KPI grid at 6 cards. Beyond that, move to a secondary section or tab.

## KPI card anatomy

A KPI card shows one number and the minimum context needed to read it.

| Part | Required | Notes |
|---|---|---|
| Title / label | yes | Short, neutral (e.g. "Open Requests") |
| Value | yes | Large format, the focal point |
| Icon | optional | Neutral glyph; reinforces the metric, never decorative-only clutter |
| Trend / delta badge | optional | Shows direction vs a prior period |
| Description | optional | Muted secondary line ("all time", "vs last period") |
| Click target | optional | Navigates to a pre-filtered list |

Layout: responsive grid, e.g. 1 column on mobile, 2 at small, 3 at large, up to 6 at extra-large, with consistent gaps.

## Trend / delta semantics

The trend badge answers "up or down vs the comparison period," not "is this good." Direction and sentiment are separate concerns.

| changeType | Typical color | Meaning |
|---|---|---|
| positive | success/green | Value rose |
| negative | error/red | Value fell |
| neutral | muted/gray | No meaningful change |

Rules:

- Compute the delta from current vs previous period values supplied by the backend. The frontend only formats the result.
- Whether "up" is good depends on the metric. Decide sentiment-to-color mapping per metric at the parent; do not assume up = green everywhere.
- Reserve red strictly for negative/error meaning. Do not reuse the error color for a neutral down-tick if down is expected.

## Role-aware metric visibility

Two visibility scopes commonly coexist:

- Personal/scoped metrics: counts limited to the current user's own records. Show only when the user is in a personal-scope role AND is not viewing as a platform admin.
- Platform-wide aggregates: org-wide totals. Show whenever the user is authenticated and permitted.

Rules:

| Situation | Personal block | Platform block |
|---|---|---|
| Admin viewing as admin | hidden | shown |
| Personal-scope role (no admin) | shown first | shown if permitted |
| Manager | hidden | shown, role filter applied |

- Gate the personal section in logic (props/derived flags), not via a user-facing toggle.
- Never mix personal and platform numbers in the same grid — segregate them into distinct sections or tabs so a scoped count is never mistaken for an org total.
- Drive visibility from a single permission source (e.g. a `usePermission()` hook exposing flags like canViewPersonal / canViewPlatform / canCreate / canEdit / canDelete), not scattered inline role checks.

## Quick actions

A compact grid of clickable navigation cards (label + trailing arrow) that jump to common list views. No data fetch; purely navigational.

- Filter the link list by permission BEFORE render. Never show a link the user cannot follow.
- Do not render disabled links — remove inaccessible links entirely.
- Do not put badge counts on quick-action links; counts belong on KPI cards.
- Responsive grid (e.g. 1/2/4 columns); hover state indicates interactivity.

## Recent-activity feed

A short, reverse-chronological list of recent events (created, updated, status-changed). Reads pre-shaped event rows from the same dashboard query.

- Render generic event types and entity placeholders; never embed domain-specific verbs.
- Each row: actor or source (optional), action, target, relative timestamp.
- Empty: show a single neutral "No recent activity" line, not a full-page empty state.
- Keep it bounded (e.g. last N items) with an optional "view all" link to a full list.

## Workflow summary

A breakdown of records by stage/status, usually as a small table or a pie/bar chart fed by a pre-aggregated array (e.g. counts per status).

- Filter out zero-count rows before rendering; do not draw an empty slice/bar.
- Use the shared status color/label map so the summary matches every other widget.
- If the entire breakdown is empty, show the empty state instead of an empty chart.

## Data freshness / as-of

- Reflect the as-of moment using the query's last-updated timestamp. The whole dashboard shares one staleness window (e.g. a few minutes).
- On background revalidation of stale data, keep the previous values on screen — no spinner, no layout shift.
- Only show a "last refreshed at …" label if you also provide a manual refresh control. A timestamp with no way to refresh is misleading.
- Apply loading uniformly: all cards and charts show skeletons together, or all retain prior values together. No per-widget loaders.

## Choosing number vs chart vs table

| Use a… | When |
|---|---|
| Single number (KPI card) | One headline value the user must read at a glance |
| Chart | The shape, distribution, or trend over time matters more than exact figures |
| Table | Users need exact values, multiple columns, sorting, or row-level drill-down |

Chart-type guidance:

| Chart | Good for |
|---|---|
| Pie/donut | Part-to-whole distribution across a few categories |
| Bar (incl. stacked) | Comparing categories; stacked shows sub-breakdown (requires a clear legend) |
| Area/line | Trend of a value over time |

- Use a responsive container with a fixed numeric height for predictable layout; avoid magic fixed widths.
- Never render a chart with zero data points — show the empty state.

## State distinction: loading vs no-data vs failed

These three are different and must be decided upstream, then rendered distinctly.

| State | Trigger | KPI card | Chart | Feed/table |
|---|---|---|---|---|
| Loading | Fetch in flight (first load) | Skeleton placeholder | Skeleton block | Skeleton rows |
| No-data (empty) | Fetch succeeded, result is empty | Value shows a neutral zero or `—` | Empty placeholder with neutral message | "No records" line / empty state |
| Failed | Fetch errored | Value shows `—` (or retains prior) | Omit the chart | Omit or retain prior |

Rules:

- Handle errors once, at the dashboard level. Do not propagate raw API errors into individual widgets, and do not render an inline error box inside a card.
- Never show a skeleton and an empty message at the same time.
- Filtered-to-zero is a distinct empty: show "No results for current filters" with a clear-filters action, separate from "nothing exists yet."
- Use neutral empty-state icons and copy ("No records yet"); never domain-specific empty text.

## A generic widgets table shape

A neutral catalog you can adapt. Names and props are placeholders only.

| Widget | Purpose | Key props (illustrative) | Data source | Permission gate |
|---|---|---|---|---|
| MetricCard | One KPI | title, value, change?, changeType?, icon?, description, loading | shared query | optional |
| HeaderBar | Title + subtitle + optional CTA | title, subtitle, action?{label, href} | none | none |
| ChartCard | Card-framed chart with loading/empty | title, data, children, loading, emptyMessage | shared query | by data scope |
| EmptyPlaceholder | Inline empty for a chart slot | message | none | none |
| StatusLegend | Color-to-label mapping | mapping: Record<string,{color,label}> | shared map | none |
| PermissionGate | Renders children for allowed roles | roles[], children | permission source | self |
| QuickActionLink | Single nav card | label, href | none | filter before render |
| ActivityFeed | Recent events list | items[], emptyMessage | shared query | by data scope |
| FreshnessIndicator (optional) | As-of + manual refresh | timestamp, onRefresh | shared query meta | none |

## Color and label mapping

- Define status → color and status → label as constants at the dashboard level; key them by the status enum value, not its display label.
- Pick one color strategy (design-system CSS variables OR fixed tokens) and use it consistently; do not mix hex and variables.
- A neutral palette: a primary accent for the active/default status, success for completed, warning for in-progress/attention, neutral/gray for draft/inactive, error for archived/failed.
- Reserve the error color for genuine error/negative states only.

## Anti-patterns

- Fetching per-widget instead of one shared dashboard query.
- Rendering an inline error inside a KPI card instead of centralizing error handling.
- Showing a permission-denied message where a widget would be — hide it instead.
- Drawing an empty pie/bar instead of an empty placeholder.
- Aggregating, summing, or computing percentages on the frontend.
- More than 6 KPI cards in one grid.
- Mixing personal-scope counts and platform totals in the same grid.
- A "last refreshed" label with no refresh control.
- Per-widget spinners mid-card instead of a unified skeleton pass.
- Badge counts on navigation links instead of on KPI cards.

## Example (illustrative — not required)

A "Requests" overview: top row of MetricCards ("Open Requests", "Resolved Today", "Avg. Handling Time" with a neutral trend badge); a ChartCard showing Requests-by-status as a pie using the shared status map; a workflow summary table of counts per stage; an ActivityFeed of the last 10 status changes; a quick-actions grid linking to "All Requests" and "New Request" (the New Request link filtered out for viewer role). One shared query feeds everything; on error every card shows `—` and the chart is omitted. This is one illustration only — do not treat its entities, metrics, or layout as required.
