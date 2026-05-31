# Admin list & tree pattern

A reusable reference for building admin list views and their tree/nested extensions in a React + server-data UI. It is domain-neutral: every concrete name (Orders, Categories, Records) is a placeholder you replace with your own entity. No example below is required behavior — the plugin's contracts hold regardless of which entity you map onto them.

## Scope and vocabulary

This document covers two layers, in order:

1. The flat **admin list** — column model, server-driven pagination/sort/filter, toolbar/search, row and bulk actions, status badges, empty vs no-results, skeletons.
2. The **tree/nested extension** — expandable rows, parent-child hierarchy, lazy children, depth breadcrumb, nested-route detail, cascade semantics for bulk actions, and virtualization.

Neutral placeholders used throughout:

| Placeholder | Stands for |
|---|---|
| `Records` | The primary collection shown in a list |
| `Orders`, `Tickets`, `Requests` | Example flat collections |
| `Categories` | Example hierarchical (tree) collection |
| `Products`, `Customers` | Example related entities |
| `admin`, `manager`, `operator`, `viewer` | Generic role tiers |
| `canCreate`, `canUpdate`, `canDelete`, `canAct` | Generic per-record permission flags |

## List column model

A list is driven by a typed column array, defined once and referenced everywhere. Treat it as data, not JSX assembled inline per render.

- Define columns **outside the component** or memoize them; never rebuild the column array on every render.
- Each column declares: a stable `key`, a human `header`, an accessor, an optional `sortable` flag, an optional cell renderer, and an optional responsive `hideBelow` breakpoint.
- Keep cell renderers pure — given a row, return a node. No data fetching inside a cell.
- Action columns are the only place row-level controls live; data columns never embed buttons that mutate state.

Example (illustrative — not required):

```ts
type Column<T> = {
  key: string;
  header: string;
  accessor: (row: T) => unknown;
  sortable?: boolean;
  hideBelow?: "sm" | "md" | "lg";
  cell?: (row: T) => React.ReactNode;
};
```

## Server pagination, sort, and filter

All paging, sorting, and filtering happen on the server. The client holds a single state object and reflects it into query parameters; the data layer (e.g. a query cache keyed on those parameters) refetches automatically when they change.

| State field | Meaning | Resets page to 1? |
|---|---|---|
| `page` | Current 1-based page | No (it *is* the page) |
| `pageSize` | Rows per page | Yes |
| `search` | Free-text query | Yes |
| `sortBy` | Active sort column key | No |
| `sortOrder` | `asc` / `desc` | No |
| `filters` | Map of `key -> value` | Yes |

Rules:

- One state object owns all of the above. Build the query string from it via a memoized derivation; do not stringify the params repeatedly.
- Any change to `search`, a `filter`, or `pageSize` resets `page` to 1. Changing `sortBy`/`sortOrder` does **not** reset page, and does **not** reset `pageSize`.
- Clicking an already-active sort column flips `sortOrder`; clicking a new column sets it and defaults the order.
- Never call a manual `refetch()` to react to UI changes. Let the parameter change drive the refetch through the cache key. Reserve explicit refetch for true out-of-band events.
- Namespace the cache key per endpoint so list state does not bleed across routes; do not persist `page` across route changes.

## Toolbar and search

The toolbar is the single horizontal control strip above the table. It reads list state and selection; it does not own data.

- Search input updates `search` (debounced), which resets `page`.
- Active filters render as removable tags; provide a "Clear all" that resets `search` and every filter at once.
- Render the toolbar **once**. Do not stack a default toolbar and a custom toolbar — choose one composition path.
- Filter options are passed in as a config array prop, not hardcoded inside the toolbar.

## Row actions and bulk actions

Row actions act on one record; bulk actions act on a selected set.

Row actions:

- Render per-row controls (view, edit, delete, act) gated by permission flags — hide a control when its `canX` is false rather than disabling it silently.
- A row-action click must not toggle selection or trigger row navigation. Stop event propagation at the action boundary.

Bulk actions:

- Selection is tracked as a `Set` of row keys in the list component for O(1) membership checks.
- Bulk-action buttons appear in the toolbar **only** when the selection is non-empty.
- Execute a bulk mutation **sequentially** over the selected keys — never in parallel — to avoid race conditions and server overload.
- Track live progress as `done/total`, collect `success` and `failed` separately, and continue past individual failures (partial success is reported, not aborted).
- Disable the trigger while running; on completion, invalidate affected cache keys and optionally clear the selection.
- For mixed selections, compute eligibility and surface it (e.g. "Act on 3 of 5") rather than failing late. Selection itself is permission-agnostic; gate the actual `execute` call behind the relevant `canX`.

## Status badges

Status is a derived, enumerated display — not free text.

- Map each status value to a fixed label + visual token (color/variant). Define the full map upfront.
- Do not infer a label by capitalizing the raw value; unmapped values should fall back to a neutral "unknown" token, surfacing the gap.
- Badges are display-only; they never carry click behavior.

## Empty vs no-results vs skeleton

Three distinct states, three distinct renders. Conflating them confuses users.

| State | Trigger | Render |
|---|---|---|
| Skeleton / loading | Request in flight | Placeholder rows matching the real layout |
| Empty (no data exists) | Total is 0 **and** no active search/filter | Call-to-action ("Create your first Record") |
| No results | Total is 0 **but** a search/filter is active | "No matches" + a way to clear the query |
| Error | Request failed | Error message + retry / back affordance |

Skeleton rule: the skeleton must **match the loaded layout** — same column count, same approximate row count (e.g. as many rows as `pageSize`), same responsive column hiding. A skeleton that does not match causes layout shift on load.

---

## Tree/nested extension overview

The list above is flat. The tree extension adds hierarchy: rows can have parents and children, and a record may have its own nested detail route. Everything from the flat list still applies; the additions below layer on top.

Two complementary shapes:

1. **Expandable grouped rows** — a single table renders parent header rows with collapsible child rows beneath them (in-place hierarchy).
2. **Nested-route detail** — list → detail → sub-detail across routes, where each level shows a parent header plus a child table.

## Expandable rows and parent-child hierarchy

Flatten hierarchical data into rows carrying both `parentId`/`parentName` and `childId`/`childName`, then group on the client by parent id.

- Group with a memoized derivation keyed on the source data; **preserve first-appearance order** of parents. Do not recompute the grouping on every render.
- Render a parent **header row** (collapsible, with a child-count badge) followed by its child data rows — but only render the child rows when that parent is expanded.
- Render children as **sibling table rows**, not nested inside a parent cell via `colspan`. Separate rows keep column alignment and styling correct.
- Track expansion as a `Set` of collapsed (or expanded) parent ids. **Collapse state and selection state are independent** — never fold one into the other.
- Toggling a parent header must `stopPropagation` so it does not fire a row action.

For deeper nesting, you may add a non-selectable **sub-header** row (visual indent only, no checkbox) between a parent and its leaf rows. Sub-headers carry no action.

## Lazy children

For large or expensive subtrees, do not fetch children until a parent expands.

- On first expand of a parent, fetch its children with a `parentId` filter against the server endpoint; cache the result keyed by parent id.
- Show a small inline loading indicator within the expanded region while children load; show an inline error with retry if the child fetch fails.
- Cache fetched children so a collapse/re-expand does not refetch within the cache's freshness window.
- Keep a per-parent "loaded" flag distinct from the "expanded" flag so an empty child set is not mistaken for "not yet loaded".

## Depth breadcrumb

A breadcrumb communicates the current position in the hierarchy and lets the user climb back up.

- Derive segments from the current path. **Filter out opaque id segments** (e.g. UUID-shaped) so the trail has no dead, non-navigable links.
- Map each remaining segment slug to a human label via a defined label map plus optional overrides; do not capitalize the raw slug as a fallback — define every expected label upfront.
- Build each link's target by slicing the **original** segment list up to that position, accounting for the filtered id segments — not by slicing the post-filter list (that produces wrong hrefs).
- The last segment is the current location: bold and non-clickable. Earlier segments are links.
- Render nothing when only one navigable segment remains.
- The breadcrumb only navigates; it enforces no permissions. Authorization is checked at the destination, not in the trail.

## Nested-route detail

A three-level route shape covers most hierarchical admin needs:

```
/records                      → list of parents
/records/[id]                 → one parent's detail + a table of its children
/records/[id]/items/[itemId]  → one child's detail or edit
```

Rules:

- Each level extracts its parent id from route params, validates existence, then loads children via the server-table hook with a `parentId` filter.
- The detail page shows parent metadata in a header (with a back-link / breadcrumb), then the child table below with its own pagination and toolbar — reusing the flat-list machinery.
- "New child" navigates to a dedicated create route carrying the parent context in the query (e.g. `?parentId=...`). Do **not** render the child create form inline on the parent detail page.
- Always read the parent id from route params and validate before rendering a child form; never hardcode it into the child route.
- Cache parent metadata so navigating between sibling detail pages does not refetch the parent each mount.
- Child tables paginate with explicit page/pageSize controls; do not substitute infinite scroll for the child table.

## Cascade semantics for bulk actions on nodes

Selection and actions in a tree must define how they propagate across the hierarchy.

- A **parent checkbox** cascades: toggling it selects/deselects all of that parent's currently-known children.
- A parent checkbox renders **partial** (indeterminate) when some — but not all — of its children are selected.
- Cascade affects the in-memory selection set only; it does not mutate data. The actual mutation runs sequentially over the resolved leaf ids, exactly like the flat bulk-action flow.
- Respect per-child permissions when resolving the effective target set: a cascade from a parent should not include children the user cannot act on. Surface the eligible count ("Act on 3 of 5").
- Do not disable a parent checkbox because a permission is false — keep selection ergonomic and instead disable the bulk-action trigger when no eligible target remains.
- Lazy subtrees: a parent cascade can only select children that are loaded. Decide and document whether selecting an unexpanded parent loads its children first or selects only loaded leaves — and make the UI state honest about which.

## Virtualization for large sets

When a list or expanded tree can render hundreds-plus rows, virtualize.

- Virtualize the row list so only visible rows mount; keep the column model and renderers pure so they are cheap to mount/unmount.
- Sticky headers must survive virtualization — pin the header outside the virtualized scroll region.
- For trees, virtualize the **flattened visible-row stream** (parents + currently-expanded children), recomputed when expansion changes — not the raw nested structure.
- Keep selection in an external `Set` (not per-row component state) so it persists as rows scroll in and out of the virtual window.
- The loading skeleton should still match layout (correct column set, sticky header) even under virtualization, so the first paint does not shift.

## Anti-patterns (do not do these)

- Mixing collapse/expand state with selection state — they are independent concerns.
- Recomputing grouping or column arrays on every render instead of memoizing.
- Manually calling refetch to react to UI changes instead of letting query params drive it.
- Parallelizing bulk mutations instead of running them sequentially.
- Including opaque id segments in breadcrumbs, or building hrefs from the post-filter segment list.
- Resetting `pageSize` on a filter change (only `page` resets).
- Rendering children inside a parent cell via colspan instead of as sibling rows.
- Capitalizing raw path/status slugs as a label fallback instead of mapping them upfront.
- Rendering a child create form inline on a parent detail page instead of a dedicated create route with parent context in the query.
- Showing only final bulk results without live `done/total` progress.

## Permission layering

Authorization is enforced in layers, outermost first:

| Layer | Responsibility |
|---|---|
| Route/layout gate | Blocks an entire section for users lacking the required role tier |
| Per-entity gate | Resolves `canCreate` / `canUpdate` / `canDelete` / `canAct` for the current entity |
| Row visibility | Hides individual row actions when their flag is false |
| Bulk eligibility | Partitions a selection into eligible/ineligible and reports the count |

Parent and child rows in a single grouped table share the same permission context. Selection UI stays permission-agnostic; the gate sits on the action trigger, not on the checkbox.
