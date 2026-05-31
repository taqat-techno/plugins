---
name: admin-panel-architecture
description: The design-before-coding skill for React / Next.js admin panels. Owns the project adapter contract, the route-group structure, the single navigation-builder function, the module/permission role model with admin-implies-all, the per-resource view registry, and the generic component inventory. Activates when starting or extending an admin panel, before scaffolding routes, navigation, or layouts; when a new staff dashboard, back-office, or operator console needs structure; or when an existing panel grows a new section and you must place it without hardcoding a per-role nav.
version: 0.4.0
last_reviewed: 2026-05-31
owns:
  - project-adapter contract (base path, role/module model, auth+audit helpers, data-fetch lib, UI lib)
  - route-group structure (panel group, overview-first, per-section folders, nested detail routes)
  - single navigation-builder function (grants + flags in, filtered nav sections out)
  - role/module model (module-permission map, admin-implies-all, generic read/full/manager levels)
  - view-registry concept (one declared view type per resource — list/tree/kanban/form/dashboard/settings/audit)
  - generic component inventory (AdminShell, SidebarNav, ModuleGate, AdminTable, ... — names are illustrative)
  - the ADMIN PANEL PLAN output template
defers_to:
  - admin-shell (renders the layout, sidebar collapse, mobile overlay, header)
  - admin-view-patterns (what each declared view type looks like)
  - admin-roles-and-permissions (route/component/API gating mechanics, access matrix)
  - data-fetching-states (query keys, mutation invalidation, loading/error/empty)
  - admin-kanban-workflow (status-gated actions, transitions, confirmation flows)
user_invocable: false
---

# admin-panel-architecture

## Purpose

An admin panel that is structured wrong is expensive to fix later: routes calcify, navigation forks per role, and access checks scatter across files that drift out of sync. This skill forces the structural decisions to happen ONCE, on paper, before any component is written. It produces a single plan: an adapter table, a route tree, one navigation-builder contract, a role/module model, and a view registry. Everything downstream references that plan instead of re-deciding.

## When to use

Activate when:

- Starting a new admin panel, staff dashboard, back-office, or operator console.
- Adding a whole new section or resource area to an existing panel.
- Onboarding a new role/module and deciding what it sees.
- A reviewer asks "where does this route live" or "why is the nav forked per role."

Do NOT activate for: a single component tweak inside an already-structured panel (defer to the owning sibling skill).

## Inputs (adapter)

Every project value is a NAMED adapter input. Collect these BEFORE planning; do not invent them.

| Adapter field | What it supplies | Example (illustrative — not required) |
|---|---|---|
| `BASE_PATH` | URL prefix for the whole panel | `/panel` |
| `ROLE_MODEL` | shape of a user's grants: a module→level map | `{ orders: "manager", products: "full" }` |
| `MODULE_LIST` | the set of modules the project defines | `orders`, `products`, `customers` |
| `LEVEL_SET` | the access levels, lowest→highest | `read` < `full` < `manager` |
| `ADMIN_MODULE` | the module that implies all others | `admin` |
| `AUTH_HELPER` | reads the current user + grants (store/hook) | `useAuth()` |
| `GUARD_HELPER` | the route/component access check | `useHasModule(module, minLevel)` |
| `AUDIT_HELPER` | how a sensitive view/action is recorded | `logAccess(event)` (backend-owned) |
| `DATA_LIB` | the data-fetching library | a query/cache lib |
| `UI_LIB` | the component primitives library | a headless UI kit |
| `FLAGS` | extra booleans the nav-builder reads | `{ hasExtraSection: true }` |

If a field is unknown, list it under **Open questions** in the output — never hardcode a guess into the plan.

## Read-only investigation steps

1. **Does a panel already exist?** Find the route-group folder under `BASE_PATH`. If present, read its layout to learn the current shell + nav-builder. Extend; do not fork.
2. **How are grants modeled today?** Confirm `ROLE_MODEL` is a module→level map, not a single role enum. A single enum is the smell this skill replaces.
3. **Is there one navigation-builder or many?** Search for the function that returns nav sections. If you find per-role configs, that is the anti-pattern to consolidate.
4. **What view types already exist?** Inventory list/table/detail/board/form pages so the new view registry stays consistent with what is there.
5. **Where do guards live?** Note whether checks run in middleware, layouts, and components. The plan must reuse `GUARD_HELPER`, not add a new check style.

## Decision framework

### Route structure

One route-group wraps the entire panel. Overview first, one folder per section, detail nested under its list.

```
app/
  (panel)/                     ← route group, shared shell + nav-builder
    layout.tsx                 ← AdminShell + buildNavigation(grants, flags)
    page.tsx                   ← overview / landing (first thing a user sees)
    <section>/                 ← one folder per module/resource (Orders, Tickets, ...)
      layout.tsx               ← optional per-section guard (cross-module OR rule)
      page.tsx                 ← list / board / dashboard view
      [id]/
        page.tsx               ← nested detail route for one Record
```

Rules:

- The panel lives under exactly one route-group so the shell + nav-builder are declared once.
- Overview (`page.tsx` at the group root) renders first — never land a user on a blank section.
- A detail view is a nested route under its list (`<section>/[id]`), not a sibling top-level route.
- A section that needs cross-module access gets its own `layout.tsx` guard expressing the OR rule.

### Navigation model — one builder, never a nav-per-role

A SINGLE function takes the user's grants + flags and RETURNS the filtered nav sections. The sidebar renders whatever it returns. There is no second code path per role.

```
buildNavigation(grants, flags) -> NavSection[]
   │
   ├─ iterate MODULE_LIST in a fixed priority order
   ├─ for each module the user has (or ADMIN_MODULE) → push its section
   ├─ conditionally append level-gated items (e.g. a manager-only item)
   ├─ add cross-module/shared sections once (dedupe)
   └─ return ordered, already-filtered NavSection[]
```

Rules:

- The builder filters items by access, so the sidebar NEVER renders a link the user cannot reach.
- Level-gated items are appended conditionally inside the builder, not branched in the component at render time.
- Section order is deterministic (a fixed module priority), so multi-module users see a stable layout.
- The builder's access logic MUST mirror the route guard (`GUARD_HELPER`) so nav and middleware never disagree.

### Role / menu model

Grants are a module→level map. `ADMIN_MODULE` implies every module at the highest level.

| Concept | Rule |
|---|---|
| Grant shape | `{ <module>: <level> }`, never a single role string |
| Levels | generic `read` < `full` < `manager` (`LEVEL_SET`) — project may rename, order is fixed |
| Admin implies all | if user has `ADMIN_MODULE`, treat every module as granted at `manager` — short-circuit before per-module checks |
| Level check | "has module at ≥ minLevel" via `GUARD_HELPER`; compare against `LEVEL_SET` order |
| Cross-module resource | requires ANY of N modules (OR logic) — same condition in builder, guard, and API |

```
hasAccess(grants, module, minLevel):
    if ADMIN_MODULE in grants: return true        # admin-implies-all
    level = grants[module]
    if not level: return false
    return index(level) >= index(minLevel)         # by LEVEL_SET order
```

### View registry — declare each resource's view types once

Each resource declares which view types it exposes, in ONE registry, so views stay consistent and the panel never invents a one-off layout per page.

| View type | Use for | Defers to |
|---|---|---|
| `list` | rows with filter/sort/paginate | admin-view-patterns |
| `tree` | self-referential / nested hierarchy | admin-view-patterns |
| `kanban` | status-gated workflow columns | admin-kanban-workflow |
| `form` | create / edit a single Record | admin-view-patterns |
| `dashboard` | aggregated overview / metrics | admin-view-patterns |
| `settings` | configuration surface | admin-view-patterns |
| `audit` | read-only immutable change trail | admin-roles-and-permissions |

Registry shape (illustrative — not required):

```
viewRegistry = {
  Orders:    ["list", "kanban", "form", "audit"],
  Products:  ["list", "tree", "form"],
  Customers: ["list", "form", "dashboard"],
}
```

Rule: a resource's pages may only use a view type it declares. Adding a new view type to a resource is a registry edit first, a page second.

### Data / state contract (defer)

Query keys, mutation invalidation, and loading/error/empty states are NOT decided here. The plan records WHICH resources need lists vs detail vs mutations, then defers the mechanics to `data-fetching-states`.

### Action / workflow contract (defer)

Status-gated actions, transitions, and confirmation/required-input flows are NOT decided here. The plan records WHICH resources have a `kanban`/workflow view, then defers to `admin-kanban-workflow`.

### Component inventory (generic — project picks final names)

Plan against these generic roles. Names are illustrative; the project chooses real names.

| Generic component | Responsibility |
|---|---|
| `AdminShell` | top-level wrapper: layout, sidebar state, config context |
| `SidebarNav` | renders `NavSection[]` from the builder, active-state, collapse |
| `NavItem` | one nav link: icon, label, badge, active styles |
| `ModuleGate` | wraps a route, checks access, shows fallback while redirecting |
| `AdminTable` | the `list` view primitive |
| `AdminKanbanBoard` | the `kanban` view primitive |
| `AdminDetailDrawer` | single-Record detail surface with conditional actions |
| `AdminFormSection` | grouped fields for `form`/`settings` views |
| `AdminStatusBadge` | color-coded status indicator |
| `AdminActionMenu` | per-row / per-record action set |
| `AdminFilterBar` | filter + search controls for a `list` |
| `AdminEmptyState` | empty vs no-results affordance |
| `AdminAccessState` | required / forbidden / not-found access UI |
| `AdminAuditTrail` | read-only `audit` view |

## Safety gates

- **Never** model grants as a single role enum — always a module→level map (`ROLE_MODEL`).
- **Never** write more than one navigation source — one `buildNavigation` function, period.
- **Never** branch nav items by role inside the sidebar component — all filtering happens in the builder.
- **Never** render a nav link to a route the user cannot reach per `GUARD_HELPER`.
- **Never** let the builder's access logic and the route guard disagree — they share one rule.
- **Never** hardcode `MODULE_LIST`, `BASE_PATH`, or level names into the plan — they are adapter inputs.
- **Never** create a one-off page layout that is not a declared view type in the registry.
- **Never** treat UI hiding as security — the API re-validates every write (defer to `admin-roles-and-permissions`).
- **Never** place a detail view as a top-level sibling of its list — nest it under `<section>/[id]`.

## Validation checklist

Before handing off the plan:

- [ ] Every adapter field is filled or listed under Open questions — no guessed values.
- [ ] The panel uses exactly one route-group; overview renders first.
- [ ] Detail routes are nested under their list (`<section>/[id]`).
- [ ] There is exactly one `buildNavigation(grants, flags)` returning filtered `NavSection[]`.
- [ ] `ADMIN_MODULE` short-circuits to all-modules-granted in the access rule.
- [ ] Levels use the fixed `LEVEL_SET` order; level checks go through `GUARD_HELPER`.
- [ ] Cross-module resources use identical OR logic in builder and guard.
- [ ] Every resource has a view-registry entry; no page uses an undeclared view type.
- [ ] Data/state and workflow concerns are DEFERRED, not specified here.
- [ ] Component inventory uses generic roles; final names noted as project choice.

## Output format

Produce an ADMIN PANEL PLAN:

```
ADMIN PANEL PLAN

ADAPTER VALUES
  BASE_PATH      : <value | OPEN>
  ROLE_MODEL     : module->level map
  MODULE_LIST    : [<module>, ...]
  LEVEL_SET      : read < full < manager
  ADMIN_MODULE   : <value>
  AUTH_HELPER    : <name>
  GUARD_HELPER   : <name>
  AUDIT_HELPER   : <name | backend-owned>
  DATA_LIB       : <name>
  UI_LIB         : <name>
  FLAGS          : [<flag>, ...]

ROUTE TREE
  (panel)/
    layout.tsx          -> AdminShell + buildNavigation
    page.tsx            -> overview
    <section>/page.tsx  -> <view type>
    <section>/[id]      -> detail

NAV SECTIONS BY ROLE  (output of buildNavigation, not hardcoded)
  admin     -> [<section>, ..., system, audit]
  <module>  -> [<section>, ...]
  cross-module (OR) -> [<shared section>]

VIEW REGISTRY
  | Resource | View types declared        |
  | Orders   | list, kanban, form, audit  |
  | Products | list, tree, form           |

COMPONENT INVENTORY  (generic role -> project name)
  AdminShell -> <?>   SidebarNav -> <?>   ModuleGate -> <?>   ...

OPEN QUESTIONS
  - <unresolved adapter field or access rule>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| One nav config per role | Forks drift; new role = new file to maintain | One `buildNavigation(grants, flags)` returning filtered sections |
| Single role enum for access | Cannot express multi-module or level grants; rigid | module→level map (`ROLE_MODEL`) |
| Conditional nav items in the sidebar component | Filtering scatters; sidebar can leak forbidden links | Append level-gated items inside the builder |
| Hardcoded module names / base path in the plan | Not reusable; breaks for the next project | Read from adapter inputs |
| Detail page as a top-level sibling route | Breaks back-nav and breadcrumbs; duplicates list context | Nest under `<section>/[id]` |
| Builder and route guard use different access logic | Nav shows a link middleware then blocks | Share one rule; builder mirrors `GUARD_HELPER` |
| Ad-hoc per-page layouts | Inconsistent UX; no shared primitives | Declare a view type in the registry first |
| Admin handled as just another module | Admin must see everything; per-module checks miss it | `ADMIN_MODULE` short-circuits to all-granted |
| Deciding query keys / mutations here | Wrong layer; duplicates `data-fetching-states` | Record the need, defer the mechanics |

## Portability rationale

This skill decides STRUCTURE, not implementation. It binds to no specific framework, data library, or UI kit — every project value is a named adapter input. The patterns (one route-group, one nav-builder, module→level grants with admin-implies-all, a view registry) are reusable by any team in any domain: swap `Orders`/`Tickets`/`Requests` for your resources and `admin`/`manager`/`operator`/`viewer` for your roles, and the plan still holds. No example here is load-bearing.

## Cross-references

- `admin-shell` — renders the layout, sidebar collapse, mobile overlay, and header the plan assumes.
- `admin-view-patterns` — defines what each declared view type (list/tree/form/dashboard/settings) looks like.
- `admin-roles-and-permissions` — implements the route/component/API gating, access matrix, and audit view.
- `data-fetching-states` — query-key design, mutation invalidation, and loading/error/empty states.
- `admin-kanban-workflow` — status-gated actions, transitions, and confirmation flows for `kanban` resources.
- `references/admin-panel-adapter.md` — full adapter field reference.
- `references/admin-view-registry.md` — view-registry schema and examples.
- `references/admin-state-contract.md` — the data/state hand-off contract to `data-fetching-states`.
