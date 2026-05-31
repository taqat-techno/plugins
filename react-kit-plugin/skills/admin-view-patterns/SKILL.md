---
name: admin-view-patterns
description: The view-type chooser for admin screens — maps a resource's data shape plus the user's task to exactly one view type (list, tree/nested, kanban, form, dashboard, settings, detail drawer, import/export, audit/history) and routes to the sibling skill that owns the implementation. Activates when deciding which admin view to build for a resource, when an agent is unsure whether a screen should be a list versus a tree versus a kanban versus a form versus a dashboard, when a new resource needs an admin screen, or when an existing screen feels like the wrong shape for its data.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - the data-shape + user-task -> view-type decision table
  - per-view-type routing to the owning sibling skill
  - the "wrong view for data shape" anti-pattern catalogue
  - the "use the registry view before a custom view" rule
  - the view-selection validation checklist
defers_to:
  - admin-crud (implements list and tree/nested views)
  - admin-kanban-workflow (implements kanban + stage transitions)
  - admin-forms (implements create/edit forms)
  - admin-dashboard-overview (implements metrics/at-a-glance views)
  - admin-states (loading / error / empty / no-results states for every view)
  - admin-dangerous-actions (destructive-confirm flows triggered from any view)
  - admin-import-export (bulk data in/out)
  - admin-roles-and-permissions (permission checks every view defers to)
user_invocable: false
---

# admin-view-patterns

## Purpose

Picking the wrong view shape is the most expensive admin mistake: a workflow forced into a flat list, a hierarchy flattened into pagination, a settings screen rebuilt as a CRUD list. This skill is a thin ROUTER. It answers one question — "given this data shape and this user task, which view type, and which skill builds it?" — and then hands off. It never re-implements the owning skills.

## When to use

Activate when:

- A new resource (Orders, Tickets, Requests, Customers, Products, Records) needs an admin screen and the view type is undecided.
- An agent is unsure whether a screen should be a list, tree/nested, kanban, form, dashboard, settings, detail drawer, import/export, or audit/history view.
- An existing screen feels mismatched to its data (e.g., a status pipeline shown as a sortable table).
- Someone proposes building a custom view and you must check whether a standard registry view already fits.

Do NOT activate to implement a view — once the type is chosen, defer to the owning skill below.

## Inputs (adapter)

Every project value is a named adapter input; this skill hard-codes none of them.

1. **Resource shape descriptor** — is the collection flat, parent-child hierarchical, or moving through ordered stages? Supplied by the caller or read from the data model.
2. **Primary user task** — browse/find, edit one record, advance work through stages, read metrics, configure, act-in-context, move data in/out, or inspect change history.
3. **Registry view list** — the set of standard/generated views the project already offers (the "registry"). The skill prefers these over bespoke screens.
4. **Permission resolver name** — the hook/util the project uses for `canCreate / canRead / canUpdate / canDelete` and role checks. The skill names it; `admin-roles-and-permissions` owns its contract.
5. **State catalogue source** — where loading/error/empty/no-results states are defined. Owned by `admin-states`.

## Read-only investigation steps

1. **Classify the data shape.** Flat collection? Parent-child (and how deep)? Items that pass through named stages? A single record? Key-value config? Aggregated metrics? Append-only events?
2. **Name the primary task** in one verb phrase: "find an Order", "advance a Ticket", "configure thresholds", "review yesterday's totals".
3. **Check the registry first.** Does a standard list/tree/form/dashboard view already cover this resource? If yes, the answer is usually "use the registry view" — stop before designing anything custom.
4. **Identify the permission context** — which roles see this resource at all, and which CRUD verbs each role holds. Do not design the view around a role you cannot verify.
5. **Confirm secondary needs** — does the task also need contextual quick-act (detail drawer), bulk in/out (import/export), or a change trail (audit/history)? These layer onto a primary view; they are rarely the primary view themselves.

## Decision framework

### Primary table: data shape + task -> view type -> owning skill

| Data shape | Primary user task | View type | Owning skill |
|---|---|---|---|
| Flat collection | Browse, search, filter, sort, bulk-act | List / table | `admin-crud` |
| Parent-child hierarchy (2+ levels) | Navigate/expand the tree, act per node | Tree / nested list | `admin-crud` |
| Items moving through ordered stages | Advance work through a workflow | Kanban board | `admin-kanban-workflow` |
| Single record | Create or edit one record | Form | `admin-forms` |
| Aggregated metrics | At-a-glance read of totals/trends | Dashboard | `admin-dashboard-overview` |
| Key-value configuration | Change a handful of named settings | Settings | `admin-forms` (per-row save variant) |
| Any record, contextual quick read/act | Read & act without leaving the current view | Detail drawer | `admin-crud` (drawer slot) / `admin-kanban-workflow` |
| Bulk rows in/out | Import or export many records at once | Import / export | `admin-import-export` |
| Append-only change events | Inspect who-changed-what-when | Audit / history | `admin-crud` (read-only list variant) |

States for every view (loading / error / empty / no-results / partial-error) are owned by `admin-states`. Destructive confirmations from any view are owned by `admin-dangerous-actions`. Every permission check defers to `admin-roles-and-permissions`.

### Quick decision flow

```
Is the data a single record to create/edit?  -> FORM (admin-forms)
Does each item move through named stages?     -> KANBAN (admin-kanban-workflow)
Is it a parent-child hierarchy (2+ levels)?   -> TREE / NESTED (admin-crud)
Is it mostly numbers/trends to glance at?     -> DASHBOARD (admin-dashboard-overview)
Is it a small fixed set of named settings?    -> SETTINGS (admin-forms, per-row save)
Otherwise (a flat collection to browse/act)   -> LIST / TABLE (admin-crud)

Layered on top of any primary view:
  Quick read/act without navigating away       -> DETAIL DRAWER
  Move many rows in/out at once                 -> IMPORT / EXPORT (admin-import-export)
  Inspect change history                        -> AUDIT / HISTORY (read-only list)
```

### Per-view-type cards

Each card lists: when to use, required UI states (always defer to `admin-states`), required actions, permission checks (always defer to `admin-roles-and-permissions`), and the owning skill.

**List / table**
- When: a flat collection the user browses, searches, filters, sorts, and bulk-acts on.
- Required states: loading skeleton matching columns, empty, no-results (distinct from empty), per-row partial-error — all per `admin-states`.
- Required actions: search, filter, sort, paginate, row actions, optional bulk actions and drag-reorder.
- Permissions: `canRead` to view; `canCreate` gates the New button; per-row `canUpdate`/`canDelete` gate row/bulk actions — per `admin-roles-and-permissions`.
- Owning skill: `admin-crud`.

**Tree / nested list**
- When: a parent-child hierarchy of 2+ levels where structure itself carries meaning (expand/collapse, act per node).
- Required states: loading, empty, per-node error — per `admin-states`.
- Required actions: expand/collapse a node, per-node row actions, breadcrumb navigation, optional cascading multi-level selection.
- Permissions: parent and child share the CRUD context; bulk-select respects per-node permission — per `admin-roles-and-permissions`.
- Owning skill: `admin-crud`.

**Kanban board**
- When: items move through a fixed set of ordered stages and the task is to advance them.
- Required states: column skeletons, per-column empty, board error+retry, in-flight transition (action disabled + spinner) — per `admin-states`.
- Required actions: open a card (detail drawer), trigger a stage transition via action button, collect side-data via an inline panel before transition.
- Permissions: each transition button is gated by stage + role + card state and is NOT rendered when disallowed — per `admin-roles-and-permissions`.
- Owning skill: `admin-kanban-workflow` (transitions are its core; never re-implement here).

**Form**
- When: creating or editing a single record.
- Required states: edit-load spinner/error, submit-in-flight (button disabled), validation, success — per `admin-states`.
- Required actions: edit fields, pick relations (with cascading clears), submit, cancel; dirty-state and unsaved-changes warning.
- Permissions: `canCreate`/`canUpdate` gate the submit; immutable fields read-only on edit — per `admin-roles-and-permissions`.
- Owning skill: `admin-forms`.

**Dashboard**
- When: aggregated metrics/trends for an at-a-glance read; no row-level editing.
- Required states: unified loading (all cards skeleton), per-chart empty, global error (value shows a placeholder) — per `admin-states`.
- Required actions: drill into a filtered list on metric click; optional manual refresh.
- Permissions: hide whole sections by role; never show a permission-denied inline state — per `admin-roles-and-permissions`.
- Owning skill: `admin-dashboard-overview`.

**Settings**
- When: a small, fixed set of named key-value configuration entries.
- Required states: per-row dirty/saving/saved feedback — per `admin-states`.
- Required actions: edit a value, per-row save (explicit, no auto-save on blur).
- Permissions: `canUpdate` on the settings resource gates each save — per `admin-roles-and-permissions`.
- Owning skill: `admin-forms` (per-row save variant).

**Detail drawer**
- When: the user must read or act on one record without leaving the current list/board.
- Required states: drawer open with content/actions, in-flight action, action error inline — per `admin-states`.
- Required actions: open from a row/card, run a quick action or open an inline action panel, close (non-modal — never trap the user).
- Permissions: action buttons gated by role + record state, not rendered when disallowed — per `admin-roles-and-permissions`.
- Owning skill: `admin-crud` (list drawer slot) or `admin-kanban-workflow` (card drawer).

**Import / export**
- When: moving many rows in or out at once.
- Required states: per-phase progress (validating, importing X/Y), partial-failure report — per `admin-states`.
- Required actions: upload/download, map columns, run, review the success/failed summary.
- Permissions: `canCreate`/`canUpdate` for import, `canRead` for export — per `admin-roles-and-permissions`.
- Owning skill: `admin-import-export`.

**Audit / history**
- When: inspecting an append-only trail of who-changed-what-when.
- Required states: loading, empty ("no changes yet"), no-results for a filtered range — per `admin-states`.
- Required actions: browse, filter by actor/date/action, read a diff; NO create/edit/delete (it is a record of the past).
- Permissions: `canRead` on the audit resource — per `admin-roles-and-permissions`.
- Owning skill: `admin-crud` (read-only list variant).

## Safety gates

- **Never** implement a view inside this skill — route to the owning skill and stop.
- **Never** force a stage-based workflow into a list when the task is to advance items; that belongs in `admin-kanban-workflow`.
- **Never** flatten a parent-child hierarchy into a single paginated list when the structure carries meaning; use the tree/nested view.
- **Never** build a custom view when a registry view already covers the resource — check the registry first.
- **Never** make a settings screen a full CRUD list; it is a fixed set of named values with per-row save.
- **Never** make a detail drawer modal — it must not trap the user away from the underlying view.
- **Never** add create/edit/delete actions to an audit/history view.
- **Never** redefine states, permission rules, or destructive-confirm flows here — defer to `admin-states`, `admin-roles-and-permissions`, and `admin-dangerous-actions`.

## Validation checklist

Before committing a view-type decision:

- [ ] The data shape was classified (flat / hierarchy / staged / single / key-value / metrics / append-only).
- [ ] The primary user task was named in one verb phrase.
- [ ] The registry was checked; a custom view is chosen only because no registry view fits.
- [ ] Exactly one primary view type was selected from the decision table.
- [ ] The owning skill is named, and implementation is deferred to it (not done here).
- [ ] Required states are delegated to `admin-states`, not redefined.
- [ ] Permission checks are delegated to `admin-roles-and-permissions`, not redefined.
- [ ] Any destructive action routes to `admin-dangerous-actions`.
- [ ] Secondary needs (drawer / import-export / audit) are layered, not mistaken for the primary view.

## Output format

When routing a resource to a view, output:

```
VIEW DECISION FOR <resource>
  Data shape: <flat | hierarchy | staged | single | key-value | metrics | append-only>
  Primary task: <verb phrase>
  Registry view available: <yes -> use it | no -> custom>
  View type: <list | tree | kanban | form | dashboard | settings | drawer | import-export | audit>
  Owning skill: <admin-crud | admin-kanban-workflow | admin-forms | admin-dashboard-overview | admin-import-export>
  States: deferred to admin-states
  Permissions: deferred to admin-roles-and-permissions
  Destructive actions: deferred to admin-dangerous-actions
  Layered views: <none | detail-drawer | import-export | audit-history>
```

Example (illustrative — not required):

```
VIEW DECISION FOR Tickets
  Data shape: staged (passes through New -> In Progress -> Done)
  Primary task: advance a Ticket through stages
  Registry view available: no -> custom
  View type: kanban
  Owning skill: admin-kanban-workflow
  States: deferred to admin-states
  Permissions: deferred to admin-roles-and-permissions
  Destructive actions: deferred to admin-dangerous-actions
  Layered views: detail-drawer (read/act on a card)
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Stage workflow shown as a sortable list | Hides progress; forces the user to read a status column instead of moving cards | Kanban via `admin-kanban-workflow` |
| Parent-child hierarchy flattened into one paginated table | Loses structure; navigation becomes filtering | Tree / nested list via `admin-crud` |
| Settings built as a full CRUD list page | Over-built; invites accidental add/delete of config | Per-row-save settings via `admin-forms` |
| A dashboard that lets you edit rows inline | Mixes at-a-glance reading with mutation risk | Dashboard reads; drill into a list/form to edit |
| Building a custom view when a registry view fits | Duplicates maintained code; drifts from the standard | Use the registry view; customize only the gap |
| Detail drawer made modal | Traps the user away from the list/board they were working | Non-modal drawer (`admin-crud` / `admin-kanban-workflow`) |
| Audit/history view with edit/delete buttons | A change trail must be immutable | Read-only list variant via `admin-crud` |
| This skill re-implementing list/form/kanban logic | Duplicates the owning skill; breaks single-owner layering | Route and defer; keep this skill a thin chooser |
| Choosing a view by gut without classifying the data | Yields the wrong shape and costly rework | Run the decision table on shape + task first |

## Portability rationale

This skill is pure routing logic over data shape and user task — both framework- and domain-agnostic. It depends on no UI library, no data layer, and no specific component set. Every project-specific value (registry view list, permission resolver, state catalogue) is a named adapter input. Any team in any domain reuses it by mapping their resources onto the neutral shapes (flat / hierarchy / staged / single / key-value / metrics / append-only).

## Cross-references

- `admin-crud` — implements list, tree/nested, detail-drawer, and read-only audit views.
- `admin-kanban-workflow` — implements the kanban board and all stage transitions.
- `admin-forms` — implements create/edit forms and the per-row-save settings variant.
- `admin-dashboard-overview` — implements metrics/at-a-glance dashboards.
- `admin-states` — owns loading / error / empty / no-results / partial-error states for every view.
- `admin-dangerous-actions` — owns destructive-confirm flows triggered from any view.
- `admin-import-export` — owns bulk data in/out.
- `admin-roles-and-permissions` — owns the permission checks every view defers to.
