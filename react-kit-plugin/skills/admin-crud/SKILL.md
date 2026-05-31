---
name: admin-crud
description: List / table / tree / detail / filter / pagination patterns for admin CRUD pages. Owns the "URL is the source of truth for filters/page/sort" rule, server-side pagination as default, the filter chip pattern, the detail-page tab convention, the loading-skeleton-matches-final-layout rule, and how a parent-child tree behaves (expand/collapse, lazy-load, depth/breadcrumb, nested-route detail, cascade-aware bulk actions). Activates when building any admin list page, table, tree, filter bar, search input, or detail view. Generic and portable — entity names, columns, and APIs are project-supplied.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - URL-as-source-of-truth for filters, page, sort
  - server-side pagination contract (default)
  - filter chip pattern (visible active filters + clear individual / clear all)
  - sortable column convention
  - detail-page tab convention (overview / edit / related / audit)
  - row-action affordance (where actions live in the row)
  - empty-state and "no results match filters" distinction
  - tree / grouped-row behavior (expand/collapse, lazy-load children, depth + breadcrumb, nested-route detail)
  - tree bulk-action cascade semantics (selected nodes vs nodes + descendants)
  - server-side virtualization note for very large lists
defers_to:
  - admin-view-patterns (flat-list-vs-tree and inline-expand-vs-nested-route presentation choice)
  - admin-roles-and-permissions (per-row visibility, action authorization)
  - admin-forms (the form rendered on the edit tab)
  - admin-states (loading skeleton, error, empty patterns)
  - admin-dangerous-actions (destructive row actions)
  - project data layer (how list/detail APIs are structured)
user_invocable: false
---

# admin-crud

## Purpose

Every admin panel is mostly CRUD: list things, filter them, find one, look at it, change it. The same pattern recurs across every entity, and getting it slightly wrong on the tenth entity hurts. This skill captures the shape that scales: URL-driven state, server-side pagination, visible active filters, predictable detail layout.

## When to use

Activate when:

- Building a new admin list page.
- Adding a filter or search to an existing list.
- Building a new admin detail page.
- Adding pagination or sort to a table.
- Reviewing an admin PR that touches a list / table / detail / filter / pagination.

Skip when:

- Building dashboards (read-only charts and counters — different concern).
- Building wizards / multi-step flows (different concern).
- Building real-time streams (different concern).

## Inputs (adapter)

1. **Entity name** (singular + plural).
2. **Field list** with types — for list columns AND detail page.
3. **Filter set** — which fields are filterable, by what operator (equals, contains, range, in).
4. **Default sort** — `created_at DESC` is the safe default; ask if different.
5. **API endpoint shape** — REST (`GET /api/<entity>?page=&pageSize=&sort=&filter=`), tRPC, GraphQL, server actions. The skill adapts.
6. **Row actions** — which actions per row (`view`, `edit`, `archive`, `delete`, `impersonate`, custom).
7. **Bulk actions** — actions on selected rows (often: archive, export, assign). Optional.
8. **Pagination strategy** — page-based (default), cursor-based (for high-cardinality), offset (rarely correct).
9. **Hierarchy** (optional) — is the entity flat, two-level grouped, or self-referential (`parent_id`)? If hierarchical: inline-expand or nested-route, and do bulk actions cascade to descendants? (Flat-vs-tree presentation choice is `admin-view-patterns`.)

## Read-only investigation steps

Before adding or modifying a list:

1. **Does the API support server-side pagination + filter + sort?** If not, that is the gating bug — list pages cannot scale without it. Surface this before building the UI.
2. **What is the maximum row count this list can reach in production?** If unbounded, client-side filter / sort is wrong even if it "works for now."
3. **Are filter inputs already in the URL or only in component state?** Component-only state breaks back/forward, refresh, share-the-URL, browser bookmark.
4. **Does the API return per-row permissions** (`canEdit`, `canDelete`) **or does the UI compute them?** Server is the source of truth; UI mirrors.

## Decision framework

### URL is the source of truth

```
/admin/users?status=active&role=manager&q=ahmad&page=2&pageSize=25&sort=created_at:desc
```

- Filters live in query parameters.
- Pagination state lives in query parameters.
- Sort lives in query parameters.
- Component reads URL, fetches data; URL change is the only way to refetch.

Why:

- Back / forward / refresh / share / bookmark all work.
- Deep-linking from emails, dashboards, audit log entries works.
- Server-side rendering / streaming gets the right data on first paint.

How:

- Use the framework's URL hook (`useSearchParams`, `useRouter.query`, equivalent).
- Update URL on filter change; do not also set local state (one-way).
- Defaults are NOT written to URL until the user diverges (a clean URL is shareable).

### Server-side pagination (default)

Request:

```
GET /api/users?page=2&pageSize=25&sort=created_at:desc&status=active
```

Response:

```json
{
  "data": [...],
  "page": 2,
  "pageSize": 25,
  "totalCount": 1247,
  "totalPages": 50
}
```

- `pageSize` is configurable per list. Default 25. Cap 100. Never "show all" on a list that can grow unbounded.
- `totalCount` enables "Page 2 of 50" and "1,247 results" affordances. If the API cannot return total count cheaply, switch to cursor-based pagination instead of guessing.
- Cursor-based pagination is correct for: high-cardinality lists, infinite scroll, append-on-scroll. Use `{ data, nextCursor, hasMore }` instead.

### Filter bar shape

```
+---------------------------------------------------------+
| [Search ahmad____]  [Status: Active ×]  [Role: Manager ×]| ← active filters as chips
| [+ Add filter ▾]  Showing 1247 results       [Clear all] |
+---------------------------------------------------------+
```

- **Search input** for free-text on the most-searched field. Debounce 250–400ms.
- **Active filters as chips** — visible, dismissable individually (× on the chip).
- **Add filter** button reveals available filter fields the user is not already using.
- **Result count** is always visible. "1,247 results" not "Showing 1-25 of many".
- **Clear all** button when at least one filter is active.

### Sortable columns

- Click column header to sort ASC. Click again for DESC. Click a third time to remove (return to default sort).
- Show sort indicator (arrow + which direction) in the header.
- Only sortable columns get a hover affordance; non-sortable do not.
- Multi-column sort is rarely needed for admin; ship it only when asked.

### Row action affordances

Choose one shape per list and stay consistent:

| Shape | When | Example |
|---|---|---|
| Trailing-column buttons | 1–3 common actions per row | `Edit / Archive` |
| Trailing-column menu (kebab) | 4+ actions or actions that vary by row | `⋮` → menu with `Edit / Archive / Impersonate / Delete` |
| Inline icons (no labels) | Power-user lists with high density | hover-revealed icons |

Destructive actions (delete, suspend) always go through `admin-dangerous-actions` confirmation, never one-click.

### Bulk action affordances

- Row selection via checkbox; "select all on this page" is one checkbox in the header.
- "Select all 1,247 results" is a separate explicit affordance after "select all on page" — never accidental.
- Bulk action bar appears above the table when any row is selected; sticks while scrolling.
- Bulk action calls a batch endpoint; never N parallel calls.
- Show per-item progress for long batches; the user must know "200 of 1247 done."

### Tree / nested-list / hierarchy

When records form a parent-child hierarchy (self-referential `parent_id`, or a fixed two-level grouping), a flat table is not enough. **Whether a list should be flat or a tree is a presentation decision — defer it to `admin-view-patterns`.** This subsection owns *how* a tree behaves once that choice is made.

#### Expandable / grouped rows

```
▾ Parent A                          (12)   [bulk-select ☐]
    ├─ Child A1        …row data…           [☐]
    └─ Child A2        …row data…           [☐]
▸ Parent B                          (3)    [bulk-select ☐]
```

- Render parent header rows and child data rows as **sibling table rows**, not children nested inside a parent cell (`colspan`). Separate rows keep column alignment and per-row styling intact.
- Track expand/collapse state as a set of collapsed (or expanded) parent IDs — independent from selection state. **Collapse state and selection state are orthogonal; never couple them.**
- Memoize the grouping transform on the data input only; do not recompute the group map on every render.
- A toggle on the parent header must `stopPropagation` so expanding a group does not also fire a row action.
- Show a count badge on each parent (`Parent A (12)`) so collapsed groups still convey scale.

#### Self-referential hierarchy display (depth)

- For unbounded `parent_id` trees, convey depth by **indentation + a disclosure chevron** per node (`▸` collapsed, `▾` expanded). Indent by depth × a fixed step.
- Keep one depth indicator only — chevron *or* indent rail — not three competing affordances per row.
- For deep trees, add a **breadcrumb / path affordance** ("ancestor ▸ ancestor ▸ current") so the user never loses position. The breadcrumb only navigates; it does not enforce permissions (the destination route does). Filter out opaque ID segments from the breadcrumb so it never renders a dead link.

#### Lazy-loading children on expand

- For large or deep trees, do not fetch the whole tree up front. Fetch a node's children **on first expand**, keyed by `parent_id`, and cache them so re-expanding does not refetch.
- Show a per-node loading indicator on the expanding row (not a full-table spinner).
- A node with unknown child count shows a chevron optimistically; resolve "has children / is leaf" from the API (`hasChildren` flag) rather than guessing.

#### Nested-route detail (alternative to inline expand)

Instead of expanding inline, a parent can navigate to its own detail page that lists its children:

```
/records                         → parent collection (list)
/records/:id                     → parent detail + child table below
/records/:id/items/:itemId       → child detail / edit
```

- Each level reads its parent from route params, validates it exists (404 → error state + back-link), then loads children with a `parent_id` filter — **reusing the server-side list patterns from this skill** (pagination, search, sort).
- Creating a child navigates to a dedicated create route with the parent context in the query string (`?parent_id=…`); do not embed a child create form on the parent detail page.
- Cache parent metadata so navigating between siblings does not refetch the parent on every mount.
- Inline-expand vs nested-route is a view choice — defer it to `admin-view-patterns`. Rule of thumb: inline expand for shallow browse-in-place; nested routes when each level has its own filters, actions, or deep-link needs.

#### Bulk actions on a tree

Tree bulk actions extend the flat bulk-action contract with one added concern — **cascade semantics**:

- A parent checkbox that selects "all children" must make the cascade explicit. State clearly whether a bulk action applies to **selected nodes only** or **selected nodes and their descendants**; never leave it ambiguous.
- A parent is "partially selected" (indeterminate checkbox) when some but not all of its children are selected.
- Honor per-node permissions inside a cascade: if a parent cascade-selects children the user cannot act on, partition into eligible / ineligible and show the eligible count (`Archive 3 of 5`) rather than failing the whole batch.
- The action still calls one batch endpoint with the resolved ID set and still reports per-item progress (per the flat bulk-action rules above).

(Full worked patterns: `references/admin-list-tree-pattern.md`.)

### Server-side virtualization (very large lists)

- Pagination is the default. **Virtualization (windowed rendering) is a rendering optimization, not a substitute for server-side paging or filtering** — never fetch the whole dataset to virtualize it client-side.
- Reach for virtualization only when a single page legitimately renders thousands of DOM rows (dense operator views, append-on-scroll). Pair it with cursor-based pagination so the window fetches more as it scrolls.
- A virtualized list must still keep filters/sort/cursor in the URL and keep the skeleton matching the row height, so scroll position and state survive refresh.

### Detail page tabs

Default detail-page layout:

```
[Overview]  [Edit]  [Related]  [Audit]
```

- **Overview** — read-only summary of the most important fields. The fast scan.
- **Edit** — the form (delegated to `admin-forms`). Save here, not on Overview.
- **Related** — child collections (e.g., a user's orders, a project's tasks). Each is a smaller list, reusing the list patterns from this skill.
- **Audit** — the audit-log entries scoped to this record (per `admin-roles-and-permissions` audit visibility).

Not every entity needs all four tabs. Drop unused tabs; do not show empty tabs.

### Empty state vs no-results state

These are different:

- **Empty state**: the underlying list has zero records ever. Show the illustration + 1-line explanation + primary CTA (`+ Add user`).
- **No-results state**: the list has records, but the current filters return zero. Show "No results match your filters" + `Clear all` button.

Confusing the two leads to a "+ Add" button on a filtered no-results state, which causes the user to add a duplicate.

### Loading skeleton matches the final layout

```
+----+----------+------+--------+--------+
| ▢▢ | ▢▢▢▢▢▢▢▢ | ▢▢▢▢ | ▢▢▢▢▢▢ | ▢▢▢▢▢ |
| ▢▢ | ▢▢▢▢▢▢▢▢ | ▢▢▢▢ | ▢▢▢▢▢▢ | ▢▢▢▢▢ |
| ▢▢ | ▢▢▢▢▢▢▢▢ | ▢▢▢▢ | ▢▢▢▢▢▢ | ▢▢▢▢▢ |
+----+----------+------+--------+--------+
```

- Skeleton table has the same column count and approximate row height.
- Skeleton on first load only; subsequent paginations show the previous page dimmed with an inline spinner (avoids full-screen flash).
- Per-row error indicator on partial failures (do not crash the whole list).

(See `admin-states` for the catalogue.)

## Safety gates

- Never fetch all rows to filter / sort / paginate client-side on a list that can grow.
- Never display PII unmasked in a list (per `admin-roles-and-permissions`).
- Never expose row-level permissions client-only — every action enforces server-side too.
- Never write filter / search inputs to a query string in a way that includes secrets (filter values that contain tokens go in POST body, not URL).
- Never auto-select destructive bulk actions on the action dropdown (the first option should be safe).
- Never lose the user's filter state on detail-page back navigation (the URL preserves it).
- Never refetch on every keystroke without debounce.

## Validation checklist

Before committing a list/detail change:

- [ ] Filters, page, sort all live in URL params.
- [ ] Server-side pagination is in use; `totalCount` rendered.
- [ ] Active filters render as chips with individual dismiss + clear-all.
- [ ] Empty state and no-results state are distinct.
- [ ] Loading skeleton matches the final table shape.
- [ ] Detail tabs are only included if they have content.
- [ ] Row actions: destructive ones go through `admin-dangerous-actions`.
- [ ] Bulk actions call a batch endpoint, with per-item progress.
- [ ] Per-row permissions come from the API (not computed only on the client).
- [ ] Back / forward / refresh / bookmark / share all preserve filter state.
- [ ] If hierarchical: collapse/expand state is independent from selection state.
- [ ] If hierarchical: parent/child rows are sibling rows (no `colspan` nesting); grouping is memoized.
- [ ] If hierarchical: tree bulk-action cascade semantics (nodes only vs nodes + descendants) are explicit.
- [ ] If lazy-loaded: children fetch on first expand and are cached; per-node loading indicator (not full-table).
- [ ] If virtualized: server-side paging/filter still in use and in the URL (no whole-dataset client fetch).

## Output format

When scaffolding a new list page, output:

```
LIST PAGE
  Entity: <plural>
  Columns: [<field:type>, ...]
  Default sort: <field>:<dir>
  Filters: [<field:op>, ...]
  Row actions: [<action>, ...]
  Bulk actions: [<action>, ...]
  Pagination: <page-based | cursor-based>  pageSize=<default>
  URL params: status, role, q, page, pageSize, sort
```

When scaffolding a new detail page, output:

```
DETAIL PAGE
  Entity: <singular>
  Tabs: [Overview, Edit, Related, Audit]   ← drop unused
  Related: [<child-collection>, ...]
  Audit scope: this record only
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Filters in `useState`, not URL | Refresh / share / back-button broken | Read + write URL params |
| Client-side `.filter()` on the full list | Breaks at scale; ships full dataset to client | Server-side filter |
| "Showing 1-25" without total count | User cannot estimate scope; cannot jump pages | Show `totalCount` |
| Loading spinner over a blank table | Layout shifts when data arrives | Skeleton matching final shape |
| Detail tabs duplicate Overview content | Tab content drifts; user does not know which is "right" | Overview read-only, Edit owns the form |
| `+ Add` button when filters return zero | Encourages duplicates | "No results match — Clear filters" |
| Bulk action button "Delete" first | Easy misclick | Safe actions first; destructive last + confirmed |
| Refetch on every keystroke | API hammered; race conditions | Debounce 250–400ms |
| Sort applied client-side after server pagination | Sort only affects current page (wrong) | Sort goes to the server as a param |
| Coupling collapse state with selection state | Expanding a group toggles selections (surprising) | Keep the two sets independent |
| Children rendered inside the parent cell via `colspan` | Breaks column alignment + per-row styling | Render parent/child as sibling rows |
| Recomputing the group map on every render | Re-renders thrash a large tree | Memoize grouping on the data input |
| Fetching the whole tree to expand one node | Slow first paint; ships the whole tree | Lazy-load children on first expand, cached |
| Ambiguous tree bulk action (cascade or not?) | User archives descendants by accident | State cascade scope explicitly before run |
| Virtualizing a list fetched whole client-side | Defeats the point; still loads everything | Virtualize over server-paged/cursored data |

## Portability rationale

The list + filter + pagination shape works the same in:

- Next.js (`useSearchParams`, `useRouter`)
- Remix (`useSearchParams`, `useNavigate`)
- React Router (`useSearchParams`)
- Vite + React (any URL state lib)
- Pages with query-string-driven `getServerSideProps`

The detail-tab convention adapts to any router that supports nested routes or query-param tab state.

The skill does not depend on:

- A specific table library (TanStack Table, AG Grid, plain HTML table all work)
- A specific data-fetching library (React Query, SWR, RTK Query, framework loaders all work)
- A specific styling solution

## Cross-references

- `admin-view-patterns` — the flat-list-vs-tree and inline-expand-vs-nested-route presentation decisions.
- `references/admin-list-tree-pattern.md` — worked tree / grouped-row / lazy-load / cascade-selection patterns.
- `admin-roles-and-permissions` — per-row permissions, audit visibility.
- `admin-forms` — the form on the Edit tab.
- `admin-dangerous-actions` — destructive row + bulk actions.
- `admin-states` — loading skeleton, error, empty state catalogue.
- `admin-rtl-ltr` — column alignment and chevron mirroring in RTL.
- `admin-route-auditor` (agent) — verifies URL-state-of-truth and server-side pagination.
