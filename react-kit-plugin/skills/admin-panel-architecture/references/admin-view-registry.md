# Admin view registry

A single declarative object per resource that names every view the resource exposes (list, tree, kanban, form, dashboard, settings, detail-drawer, import/export, audit) and the data that drives those views: columns, default filters, row and bulk actions, and the workflow state set. One registry entry is the source of truth so navigation, views, and any scaffolding generator stay consistent. This document defines the shape and the rules; it carries no business logic.

## Why one registry per resource

A resource is any addressable collection an admin panel manages — neutral placeholders here are Orders, Tickets, Requests, Customers, Products, and Records. Without a registry, the same facts (which columns show, which filters default on, which actions a row exposes) get re-declared in the list view, the nav menu, the form page, and the export config. They drift. The registry collapses those into one object that every consumer reads.

- Views render from the registry; they do not invent their own column or action lists.
- Navigation builds menu entries from the registry's `views` map, so a view that is not declared cannot be linked.
- A generator can scaffold pages, routes, and API query params directly from one entry.

## Core rules

These are non-negotiable for the pattern to hold.

| Rule | Statement |
|---|---|
| R1 | Exactly one registry entry per resource. Never split a resource's view declarations across files. |
| R2 | A view type that is not listed in `views` does not exist for that resource — no orphan pages. |
| R3 | Columns, filters, actions, and states are declared as data, not as JSX or inline render code. |
| R4 | Every action declares the capability it needs (e.g. `create`, `update`, `delete`); the registry never enforces it. |
| R5 | Enforcement is server-side and at the page/handler layer. The registry is descriptive metadata only. |
| R6 | Workflow `states` are a closed set; status values used by columns/filters/kanban must come from this set. |
| R7 | The registry holds no business logic, no data fetching, and no domain branching. |

## Registry object shape

Example (illustrative — not required): a registry entry for a neutral `Orders` resource. Field names are suggestions; a team may rename them, but the layering must hold.

```ts
const ordersRegistry = {
  key: "orders",                 // stable machine id; used in routes, query keys, nav
  label: "Orders",               // singular/plural pair drives titles and breadcrumbs
  labelPlural: "Orders",
  idField: "id",                 // row identity for selection and detail links

  // Which view types this resource exposes. Absent key = view does not exist.
  views: {
    list: { default: true },     // table; the primary landing view
    tree: false,                 // hierarchical view, off for this resource
    kanban: { groupBy: "status" },
    form: { mode: "drawer" },    // create/edit surface; "drawer" | "page"
    dashboard: { widgets: ["countByStatus", "recentActivity"] },
    settings: false,
    detail: { mode: "drawer" },  // read-only record view
    importExport: { import: true, export: true, formats: ["csv"] },
    audit: { enabled: true },    // change history per record
  },

  columns: [ /* see Column declarations */ ],
  defaultFilters: [ /* see Filters */ ],
  rowActions: [ /* see Actions */ ],
  bulkActions: [ /* see Actions */ ],
  states: [ /* see Workflow states */ ],
}
```

## View types

The `views` map enumerates the surfaces a resource supports. A value of `false` (or an omitted key) means the view does not exist. An object value carries that view's minimal config.

| View | Purpose | Typical config keys |
|---|---|---|
| list | Tabular browse with sort/filter/paginate | `default`, `pageSizes` |
| tree | Self-referential hierarchy browse | `parentField`, `labelField` |
| kanban | Grouped card board by a status field | `groupBy` (must be a `states` key) |
| form | Create / edit surface | `mode` (`drawer` or `page`) |
| dashboard | Aggregate widgets for the resource | `widgets` |
| settings | Resource-level configuration | `sections` |
| detail | Read-only single-record view | `mode` (`drawer` or `page`) |
| importExport | Bulk in/out | `import`, `export`, `formats` |
| audit | Per-record change history | `enabled` |

## Column declarations

Columns are typed objects, never inline render code. An accessor (property name or function) extracts the cell value so formatting stays out of the column definition.

| Field | Meaning |
|---|---|
| `key` | Stable column id; also the server ordering param |
| `header` | Display label |
| `accessor` | Property name or `(row) => value` for computed cells |
| `sortable` | Whether the header toggles sort |
| `hideBelow` | Responsive breakpoint to hide the column (`sm` / `md` / `lg`) |
| `align` / `className` | Presentation hints |

Rules: keep status/badge logic in the accessor, not the column object (R3); always leave identity and primary-label columns visible on small screens; do not couple the column list to the raw row shape — let accessors bridge.

## Filters

`defaultFilters` declares the filter controls a view offers and which start active. Each filter binds to a field and supplies its option set or input type.

```ts
defaultFilters: [
  { key: "status", type: "select", field: "status",
    options: "fromStates",        // derive option list from the workflow state set
    default: "all" },
  { key: "createdAfter", type: "date", field: "created_at" },
]
```

Rules: a status filter's options derive from `states` (R6) — do not hardcode a parallel list. Filters describe intent; the server applies the predicate. Changing a filter resets pagination to the first page.

## Row and bulk actions

Actions are declared once and reused by the list, detail, and form surfaces. Each action names the capability it requires; the registry does not check it (R4, R5).

| Field | Meaning |
|---|---|
| `key` | Action id |
| `label` | Button/menu text |
| `scope` | `row` (single record) or `bulk` (operates on a selection) |
| `capability` | Capability string the handler must verify server-side (`create` / `update` / `delete` / custom) |
| `confirm` | Whether to prompt before running (recommended for destructive actions) |

```ts
rowActions: [
  { key: "edit",   label: "Edit",   scope: "row",  capability: "update" },
  { key: "delete", label: "Delete", scope: "row",  capability: "delete", confirm: true },
],
bulkActions: [
  { key: "archive", label: "Archive", scope: "bulk", capability: "update", confirm: true },
],
```

Rules: bulk actions read the live selection set at invoke time; selection is volatile and never persists across navigation or page change. A handler must validate that every targeted id is permitted before acting.

## Workflow states

`states` is the closed set of lifecycle values for the resource. Any column, filter, or kanban grouping that references status must use a key from this set (R6). Each state may declare which states it can transition to so the form/detail surface can offer only valid moves.

```ts
states: [
  { key: "new",        label: "New",        color: "neutral", next: ["open"] },
  { key: "open",       label: "Open",       color: "info",    next: ["resolved", "cancelled"] },
  { key: "resolved",   label: "Resolved",   color: "success", next: ["closed"] },
  { key: "cancelled",  label: "Cancelled",  color: "danger",  next: [] },
  { key: "closed",     label: "Closed",     color: "muted",   next: [] },
]
```

Rules: keep the set closed and finite; new statuses are added here first, then surfaced. Transition validity (`next`) is advisory UI metadata — the server is the authority on whether a transition is allowed.

## Consumers of the registry

One entry feeds many consumers. None of them re-declares the facts; they read them.

| Consumer | Reads from registry |
|---|---|
| Navigation | `views` keys → menu entries and routes |
| List view | `columns`, `defaultFilters`, `rowActions`, `bulkActions` |
| Kanban view | `states` + `views.kanban.groupBy` |
| Form / detail | `views.form` / `views.detail` mode, `states.next` for transitions |
| Import / export | `views.importExport`, `columns` for field mapping |
| Audit | `views.audit`, `idField` |
| Scaffolding generator | the whole entry → pages, routes, query keys, API params |

## Anti-patterns

- Declaring columns or actions inside a view component instead of the registry — defeats consistency (R3).
- Linking a nav item to a view not present in `views` — produces an orphan page (R2).
- Enforcing capabilities in the registry or in the table component instead of server-side (R5).
- Hardcoding status option lists in filters or kanban that diverge from `states` (R6).
- Embedding fetch calls, domain conditionals, or formatting logic in the registry (R7).
- Persisting the selection set so bulk actions act on stale ids after a page change.
