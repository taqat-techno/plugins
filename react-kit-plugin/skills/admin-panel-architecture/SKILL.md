---
name: admin-panel-architecture
description: Use when starting or extending a React / Next.js admin panel, staff dashboard, back-office, or operator console, before scaffolding its routes, navigation, or layouts; when an existing panel grows a new section that must be placed without a hardcoded per-role nav; or when deciding how the panel's access checks should be modelled. Detects the project's existing access model (role enum, permission strings, module-level grants, or a policy engine such as CASL, Casbin, OPA) and adapts to it rather than replacing it. Owns the adapter schema, the route-group structure, the single navigation builder that mirrors the route guard, the per-resource view registry, the generic component inventory, and the ADMIN PANEL PLAN template.
version: 0.5.0
last_reviewed: 2026-10-19
owns:
  - the adapter schema (references/admin-panel-adapter.md is the single owner of every adapter key)
  - access-model detection and the decision framework (role-enum / permission-strings / module-levels / policy-engine)
  - route-group structure (panel group, overview-first, per-section folders, nested detail routes)
  - single navigation-builder function (user + flags in, filtered nav sections out, same guard as the route)
  - view-registry concept (one declared view type per resource — list/tree/kanban/form/dashboard/settings/audit)
  - generic component inventory (AdminShell, SidebarNav, AccessGate, AdminTable, ... — names are illustrative)
  - the ADMIN PANEL PLAN output template
defers_to:
  - admin-shell (renders the layout, sidebar collapse, mobile overlay, header)
  - admin-view-patterns (what each declared view type looks like)
  - admin-roles-and-permissions (route/component/API gating mechanics, access matrix)
  - data-fetching-states (query keys, mutation invalidation, loading/error/empty)
  - admin-kanban-workflow (status-gated actions, transitions, confirmation flows)
user-invocable: false
---

# admin-panel-architecture

## Purpose

An admin panel that is structured wrong is expensive to fix later: routes calcify, navigation forks per role, and access checks scatter across files that drift out of sync. This skill forces the structural decisions to happen ONCE, on paper, before any component is written. It produces a single plan: adapter values, a route tree, one navigation-builder contract, the access model the project uses, and a view registry. Everything downstream references that plan instead of re-deciding.

## When to use

Activate when:

- Starting a new admin panel, staff dashboard, back-office, or operator console.
- Adding a whole new section or resource area to an existing panel.
- Onboarding a new role, permission, or area and deciding what it sees.
- A reviewer asks "where does this route live" or "why is the nav forked per role."

Do NOT activate for: a single component tweak inside an already-structured panel (defer to the owning sibling skill).

## Inputs (adapter)

Every project value is a named key in the adapter schema, `references/admin-panel-adapter.md`. That file is the only definition of the keys; this skill uses its names and adds none of its own.

The keys this skill needs for a plan: `framework`, `panelDir`, `panelBasePath`, `accessModel` + `access`, `authHelper`, `guardHelper`, `auditHelper`, `navSource`, `dataLibrary`, `uiLibrary`, `flags`.

If `.react-kit.local.json` exists, read the values from it. If a key is unknown after detection, list it under **Open questions** in the output — never hardcode a guess into the plan.

## Read-only investigation steps

1. **Does a panel already exist?** Find the route folder (`panelDir`). If present, read its layout to learn the current shell and navigation source. Extend; do not fork.
2. **Which access model does the code use?** Run the detection in `references/admin-panel-adapter.md` → *Detecting the access model*: grep for role-enum, permission-string, module-level, and policy-engine signatures; identify the function the existing guards call (`guardHelper`). Record `accessModel` with file:line evidence. If several models are layered, record the one the guard evaluates (see *Mixed models*). If detection is inconclusive (new project, no access code, contradictory hits), present the decision framework below and ask — do not default silently.
3. **Is there one navigation source or many?** Search for the function or file that returns nav sections (`navSource`). Per-role nav configs are the thing to consolidate into one builder — keep the access model, change only how nav is produced.
4. **What view types already exist?** Inventory list/table/detail/board/form pages so the new view registry stays consistent with what is there.
5. **Where do guards live?** Note whether checks run in middleware, layouts, components, and API handlers. The plan must reuse `guardHelper`, not add a new check style.

## Decision framework

### Access model — adapt to what exists

The plan uses the project's existing access model. Choosing one is only a decision when there is nothing to detect. All four are legitimate; the field lists and requirement shapes live in the adapter schema.

| `accessModel` | Shape of a check | Fits well when | Costs |
|---|---|---|---|
| `role-enum` | user has role ∈ `{ roles }` | few, stable staff roles; simple audits | new capabilities mean editing role lists; per-record nuance needs predicates |
| `permission-strings` | user has `'orders:update'` | many capabilities; roles change often (roles bundle permissions) | permission list grows; needs naming discipline |
| `module-levels` | user has `{ module, minLevel }` | staff work across several areas at different depths | coarse levels; the level order is a policy the project owns |
| `policy-engine` | `can(action, subject, record?)` via CASL / Casbin / OPA / Cerbos / ... | attribute or record conditions; central policy shared with other services | extra dependency and decision layer; client evaluation needs the rules or a decisions endpoint |

Rules that hold for every model:

- **One guard.** Route guards, the navigation builder, and API handlers all call `guardHelper` with the same requirement object.
- **Requirements, not branches.** Each nav item, route, and action declares a `requires` value in the model's shape; code never branches on a literal role/permission name inline.
- **OR logic for cross-resource sections.** A section reachable through any of several requirements uses `{ anyOf: [...] }`, evaluated identically in builder, guard, and API.
- **No silent migration.** Never propose moving the project to a different access model unless the user asks for that migration explicitly.

#### Option detail: `module-levels`

When the project uses (or chooses) per-area grants, the user carries a map `{ <module>: <level> }`, `access.levels` is the project's own ordered level list, and `access.adminModule` — only if the project has one — implies every module at the highest level:

```
hasAccess(grants, module, minLevel):
    if adminModule and adminModule in grants: return true   # only when access.adminModule is set
    level = grants[module]
    if not level: return false
    return index(level) >= index(minLevel)                  # by access.levels order
```

| Concept | Rule |
|---|---|
| Grant shape | `{ <module>: <level> }` read from the auth source |
| Levels | `access.levels`, project-named and project-ordered lowest → highest |
| Admin module | optional; if set, short-circuit before per-module checks so no check misses it |
| Level check | "has module at ≥ minLevel" via `guardHelper`, compared by `access.levels` order |

The other models are documented field-by-field in the adapter schema; their guard is the model's native check (`hasRole`, `hasPermission`, `ability.can`).

### Route structure

One route-group wraps the entire panel. Overview first, one folder per section, detail nested under its list. Shown for the Next.js App Router; Pages Router, Remix, and Vite routers follow the same nesting with their own file conventions (`framework`).

```
app/
  (admin)/                     ← route group, shared shell + nav-builder (name is the project's)
    layout.tsx                 ← AdminShell + buildNavigation(user, flags)
    page.tsx                   ← overview / landing (first thing a user sees)
    <section>/                 ← one folder per resource area (Orders, Tickets, ...)
      layout.tsx               ← optional per-section guard (anyOf rule)
      page.tsx                 ← list / board / dashboard view
      [id]/
        page.tsx               ← nested detail route for one Record
```

Rules:

- The panel lives under exactly one route-group so the shell + nav-builder are declared once.
- Overview (`page.tsx` at the group root) renders first — never land a user on a blank section.
- A detail view is a nested route under its list (`<section>/[id]`), not a sibling top-level route.
- A section that needs cross-resource access gets its own `layout.tsx` guard expressing the `anyOf` rule.

### Navigation model — one builder, never a nav-per-role

A SINGLE function takes the user + flags and RETURNS the filtered nav sections. The sidebar renders whatever it returns. There is no second code path per role, permission, or area.

```
buildNavigation(user, flags) -> NavSection[]
   │
   ├─ iterate sections in a fixed priority order
   ├─ keep an item only if guardHelper(user, item.requires) is true
   ├─ append conditionally-gated items inside the builder (never in the sidebar)
   ├─ add shared sections once (dedupe)
   └─ return ordered, already-filtered NavSection[]
```

Rules:

- The builder filters items by access, so the sidebar NEVER renders a link the user cannot reach.
- Gated items are appended inside the builder, not branched in the component at render time.
- Section order is deterministic (a fixed priority), so users with broad access see a stable layout.
- The builder's access logic MUST mirror the route guard (`guardHelper`) so nav and middleware never disagree.

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
| `AccessGate` | wraps a route, evaluates a requirement via `guardHelper`, shows fallback while redirecting |
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

- **Never** replace or restructure the project's existing access model unless the user explicitly asks for that migration.
- **Never** pick an access model for a project silently — detect it, or ask when detection is inconclusive.
- **Never** write more than one navigation source — one `buildNavigation` function, period.
- **Never** branch nav items by role/permission inside the sidebar component — all filtering happens in the builder.
- **Never** render a nav link to a route the user cannot reach per `guardHelper`.
- **Never** let the builder's access logic and the route guard disagree — they call the same guard with the same requirement.
- **Never** hardcode role names, permission strings, module or level names, or `panelBasePath` into the plan — they are adapter values.
- **Never** create a one-off page layout that is not a declared view type in the registry.
- **Never** treat UI hiding as security — the API re-validates every write (defer to `admin-roles-and-permissions`).
- **Never** place a detail view as a top-level sibling of its list — nest it under `<section>/[id]`.

## Validation checklist

Before handing off the plan:

- [ ] Every adapter key the plan uses is filled or listed under Open questions — no guessed values.
- [ ] `accessModel` is recorded with detection evidence (file:line), or was chosen by the user after inconclusive detection.
- [ ] The plan keeps the existing access model; any migration was explicitly requested.
- [ ] The panel uses exactly one route-group; overview renders first.
- [ ] Detail routes are nested under their list (`<section>/[id]`).
- [ ] There is exactly one `buildNavigation(user, flags)` returning filtered `NavSection[]`.
- [ ] Builder, route guard, and API all evaluate the same `requires` through `guardHelper`.
- [ ] Cross-resource sections use identical `anyOf` logic in builder, guard, and API.
- [ ] Every resource has a view-registry entry; no page uses an undeclared view type.
- [ ] Data/state and workflow concerns are DEFERRED, not specified here.
- [ ] Component inventory uses generic roles; final names noted as project choice.

## Output format

Produce an ADMIN PANEL PLAN:

```
ADMIN PANEL PLAN

ADAPTER VALUES  (keys per references/admin-panel-adapter.md)
  framework      : <value | OPEN>
  panelDir       : <value | OPEN>
  panelBasePath  : <value | OPEN>
  accessModel    : <role-enum | permission-strings | module-levels | policy-engine>
                   evidence: <file:line of guard + definition>  | chosen by user
  access         : <per-model fields, e.g. roles=[...] | permissionFormat=... | modules/levels | engine=...>
  authHelper     : <name>
  guardHelper    : <name + signature>
  auditHelper    : <name | none>
  navSource      : <path | new>
  dataLibrary    : <name>
  uiLibrary      : <name>
  flags          : [<flag>, ...]

ROUTE TREE
  (<group>)/
    layout.tsx          -> AdminShell + buildNavigation
    page.tsx            -> overview
    <section>/page.tsx  -> <view type>
    <section>/[id]      -> detail

NAV SECTIONS  (output of buildNavigation, not hardcoded)
  | Section   | requires                         |
  | Orders    | <requirement in accessModel shape> |
  | Reports   | anyOf [<req>, <req>]             |

VIEW REGISTRY
  | Resource | View types declared        |
  | Orders   | list, kanban, form, audit  |
  | Products | list, tree, form           |

COMPONENT INVENTORY  (generic role -> project name)
  AdminShell -> <?>   SidebarNav -> <?>   AccessGate -> <?>   ...

OPEN QUESTIONS
  - <unresolved adapter key, mixed-model layer, or access rule>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| One nav config per role | Forks drift; a new role means a new file to maintain | One `buildNavigation(user, flags)` returning filtered sections |
| Rewriting the project's access model to fit this plan | Unrequested architecture churn in someone else's codebase | Detect the model and plan in its terms |
| Inline literal checks (`role === 'x'`, `'orders:write'` scattered in JSX) | Checks drift from the guard; one forgotten place becomes a bypass | Declare `requires` per item/route/action; evaluate via `guardHelper` |
| Conditional nav items in the sidebar component | Filtering scatters; sidebar can leak forbidden links | Append gated items inside the builder |
| Hardcoded role/permission/module names or base path in the plan | Not reusable; breaks for the next project | Read from adapter values |
| Detail page as a top-level sibling route | Breaks back-nav and breadcrumbs; duplicates list context | Nest under `<section>/[id]` |
| Builder and route guard use different access logic | Nav shows a link middleware then blocks | Share one guard; builder mirrors `guardHelper` |
| Ad-hoc per-page layouts | Inconsistent UX; no shared primitives | Declare a view type in the registry first |
| Deciding query keys / mutations here | Wrong layer; duplicates `data-fetching-states` | Record the need, defer the mechanics |

## Portability rationale

This skill decides STRUCTURE, not implementation. It binds to no framework, data library, UI kit, or access model — every project value is a key in the adapter schema, and the access section adapts to role enums, permission strings, module-level grants, and policy engines alike. The universal parts (one route-group, one nav-builder that mirrors one guard, deterministic section order, `anyOf` for cross-resource access, a view registry) hold for any team in any domain. No example here is load-bearing.

## Cross-references

- `admin-shell` — renders the layout, sidebar collapse, mobile overlay, and header the plan assumes.
- `admin-view-patterns` — defines what each declared view type (list/tree/form/dashboard/settings) looks like.
- `admin-roles-and-permissions` — implements the route/component/API gating, access matrix, and audit view.
- `data-fetching-states` — query-key design, mutation invalidation, and loading/error/empty states.
- `admin-kanban-workflow` — status-gated actions, transitions, and confirmation flows for `kanban` resources.
- `references/admin-panel-adapter.md` — the adapter schema: every key, the four access models, detection greps.
- `references/admin-view-registry.md` — view-registry schema and examples.
- `references/admin-state-contract.md` — the data/state hand-off contract to `data-fetching-states`.
