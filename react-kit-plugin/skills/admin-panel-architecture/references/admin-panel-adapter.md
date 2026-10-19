# Admin panel adapter schema (single owner)

This file is the **one** definition of the react-kit admin adapter. Every skill, command, and agent in this plugin reads adapter values by the key names defined here and nowhere else. If a skill or command needs a new project value, add the key here first, then reference it.

The adapter has two forms that share the same key names:

1. **The adapter cache** — `.react-kit.local.json` in the project root (gitignored). Written by `/admin-scaffold` or `/admin-role-matrix` after detection + intake; read by every command and by the `admin-route-auditor` agent.
2. **The runtime contract** — what the project's code exposes (guard helper, navigation builder, auth status). Skills describe it with the same keys so the cache and the code never use different words for the same concept.

Rules:

- **One adapter per project.** Project-specific names, paths, roles, permissions, and library choices live in the adapter, never in skill logic.
- **Detect first, ask second.** Every key lists how to detect it from the codebase. Ask the user only for keys detection could not resolve, and say what was detected.
- **Adapt to the existing access model; never migrate it.** The adapter records the access model the project already uses. No skill or command proposes replacing it unless the user explicitly asks for a migration.
- **Examples are non-binding.** Every concrete value below is illustrative. Plugin behavior must never depend on an example value.

## Adapter keys

| Key | Type | Required | Purpose | Detect from |
|---|---|---|---|---|
| `schemaVersion` | number | yes | Cache format version. Currently `1`. | — |
| `framework` | `next-app` \| `next-pages` \| `remix` \| `vite-react` \| `other` | yes | Shapes the file layout commands generate. | `package.json` deps; `app/` vs `pages/` dirs; `remix.config.*` / `vite.config.*` |
| `panelDir` | string | yes | Source directory that holds the panel's routes. | existing admin/staff route folder (`app/**/admin`, `src/routes/admin*`, `pages/admin`) |
| `panelBasePath` | string | yes | URL prefix of every panel route. | route folder name, middleware matchers, nav hrefs |
| `accessModel` | `role-enum` \| `permission-strings` \| `module-levels` \| `policy-engine` | yes | How the project expresses who may do what. Selects the per-model fields below. | see [Detecting the access model](#detecting-the-access-model) |
| `access` | object | yes | Per-model fields for the selected `accessModel`. | see each model |
| `authHelper` | string (import) | yes | Returns the verified current user/session on the server. | `auth()`, `getServerSession`, `getSession`, `currentUser`, `getUser` imports |
| `guardHelper` | string (import/name) | yes | The ONE access check used by route guards, the navigation builder, and API handlers. Signature depends on `accessModel`. | the most-used check function among the detection hits |
| `auditHelper` | string (import) \| `"none"` | yes | Writes an audit row. `"none"` means commands scaffold a minimal one. | `audit(`, `auditLog.`, `logAccess(`, an `AuditLog` model |
| `navSource` | string (path) \| `"none"` | yes | File holding the single navigation builder or menu definition. | `buildNavigation`, `ALL_MENU_ITEMS`, `navItems`, `sidebarConfig` |
| `piiFields` | string[] | yes | Sensitive field names, masked by default. Not reliably detectable; always confirm with the user. | hints only: `email`, `phone`, `national_id`, `dob`, `address` in schemas |
| `rtlLocales` | string[] | no (default `[]`) | Locales rendered right-to-left. | i18n config (`ar`, `he`, `fa`, `ur` in locale lists) |
| `i18nLibrary` | string \| `"none"` | no | Translation provider the shell wraps. | `next-intl`, `react-i18next`, `@lingui/*`, `react-intl` |
| `dataLibrary` | string | no | Data-fetching/cache library. | `@tanstack/react-query`, `swr`, `@apollo/client`, `@reduxjs/toolkit` (RTK Query) |
| `uiLibrary` | string \| `"none"` | no | Component primitives library. | `@radix-ui/*`, `@mui/*`, `@chakra-ui/*`, `@mantine/*`, `antd`, shadcn `components/ui` |
| `validationLibrary` | `zod` \| `yup` \| `joi` \| `valibot` \| `none` | no | Shared client/server schema library. | `package.json` |
| `formLibrary` | `react-hook-form` \| `formik` \| `tanstack-form` \| `plain` | no | Form state library. | `package.json` |
| `cssFramework` | `tailwind` \| `css-modules` \| `vanilla` \| `styled-components` \| `other` | no | Decides utility vs property names in RTL checks. | `tailwind.config.*`, `*.module.css`, `styled-components` dep |
| `importFormat` | `csv` \| `xlsx` \| `json` \| `none` | no | Only when import/export is scaffolded. | existing import handlers |
| `flags` | object | no | Extra booleans the navigation builder reads. | — |

## Access models

Every model plugs into the same universal contract: one `guardHelper`, one navigation builder that calls it, and a **requirement** object attached to each nav item, route, and action. The requirement shape is the only thing that changes per model. A cross-resource section uses `{ anyOf: [requirement, ...] }` (OR logic) in every model.

### `role-enum` — each user has one (or a few) named roles

`access` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `roles` | string[] | yes | The role values, as defined in code. |
| `roleSource` | string | yes | Where the role type is defined (`prisma/schema.prisma` `enum Role`, `types/auth.ts`). |
| `multiRole` | boolean | no (default `false`) | `true` when a user can hold several roles. |
| `superRole` | string \| null | no (default `null`) | A role that bypasses every check. Set only if the code already does this; never invent one. |

- Requirement: `{ roles: ['admin', 'editor'] }` (nav items commonly spell this `allowedRoles`).
- Guard: `guardHelper(user, { roles })` → user's role(s) intersect `roles`.
- Matrix cell: role × resource × operation → allow / deny / predicate.
- Trade-offs: simplest to read and audit; every new capability means editing role lists; per-resource nuance needs record predicates.

### `permission-strings` — checks name a capability string

`access` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `permissionFormat` | string | yes | Shape of a permission, e.g. `resource:action`, `resource.action`, `action_resource`. |
| `permissions` | string[] \| `"derived"` | yes | Known permission set, or `"derived"` when it is generated from resources × operations. |
| `wildcard` | string \| null | no | Wildcard token the code already supports (`*`, `orders:*`). `null` if none. |
| `roles` | string[] | no | Present when roles bundle permissions (role → permission set). |
| `rolePermissionsSource` | string | no | File or table that maps roles to permissions. |

- Requirement: `{ permission: 'orders:read' }`.
- Guard: `guardHelper(user, { permission })` → user's effective permission set contains it (honouring `wildcard` only if the code does).
- Matrix cell: resource × operation → permission string, plus role → permission set when `roles` exists.
- Trade-offs: fine-grained and stable as roles change; the permission list grows and needs naming discipline; roles become bundles rather than checks.

### `module-levels` — per-area grants at ordered levels

`access` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `modules` | string[] | yes | The areas the project defines. |
| `levels` | string[] | yes | The project's own level names, ordered lowest → highest (e.g. `view` < `edit` < `manage`). Names and count are project-defined. |
| `adminModule` | string \| null | no (default `null`) | A module that implies every other module at the highest level. Set only if the code already does this. |

- Requirement: `{ module: 'orders', minLevel: 'edit' }`.
- Guard (reference pseudo-code):

  ```
  hasAccess(grants, module, minLevel):
      if adminModule and adminModule in grants: return true   # only when adminModule is set
      level = grants[module]
      if not level: return false
      return index(level) >= index(minLevel)                  # by access.levels order
  ```

- Matrix cell: resource × operation → (module, minLevel).
- Trade-offs: expresses multi-area staff without a role explosion; levels are coarse, so per-action exceptions need predicates; the level order is a policy decision the project owns.

### `policy-engine` — an ability/policy library or service decides

`access` fields:

| Field | Type | Required | Meaning |
|---|---|---|---|
| `engine` | `casl` \| `casbin` \| `opa` \| `cerbos` \| `oso` \| `permit` \| `other` | yes | The engine in use. |
| `abilityImport` | string | yes | How code obtains a decision (`defineAbilityFor(user)`, an `enforcer`, a PDP client). |
| `actions` | string[] | yes | Action vocabulary (`read`, `create`, `update`, `delete`, `manage`, ...). |
| `subjects` | string[] | yes | Resource/subject types the policies cover. |
| `policySource` | string | yes | Where policies live (`src/abilities.ts`, `policy.csv`, `policies/*.rego`, a remote PDP). |
| `evaluatedWhere` | `client+server` \| `server-only` | yes | `server-only` means the client reads decisions from the API instead of evaluating policies. |

- Requirement: `{ action: 'read', subject: 'Order' }` (optionally with a record for attribute conditions).
- Guard: `guardHelper(user, { action, subject }, record?)` → the engine's `can` / `enforce` / decision call.
- Matrix: rules in the engine's native format (CASL rules, Casbin `p, sub, obj, act` lines). When policies live outside the repo (OPA/Cerbos/permit service), the matrix is a review document plus checks, never a generated policy.
- Trade-offs: expresses attribute/record conditions and central policy; adds a dependency and a decision layer to debug; client-side evaluation needs the same rules shipped to the browser or a decisions endpoint.

### Mixed models

Real projects often combine models: roles that bundle permission strings, or role enums plus a policy library for record rules. Record the model the **guard evaluates** as `accessModel` and the upstream source in its per-model fields (e.g. `permission-strings` with `roles` + `rolePermissionsSource`, or `policy-engine` whose rules are written per role). Note any remaining layer in the plan's open questions instead of collapsing it.

## Detecting the access model

Search the source tree (excluding `node_modules`, build output, and lock files). Count hits per model and identify the function the existing guards actually call.

| Model | Grep for (illustrative patterns) |
|---|---|
| `role-enum` | `type Role =`, `enum Role`, `role ===`, `role !==`, `roles.includes(`, `hasRole(`, `requireRole(`, `isAdmin(`, `session.user.role`, `allowedRoles` |
| `permission-strings` | quoted `'<word>:<word>'` / `'<word>.<word>'` capability literals passed to checks, `hasPermission(`, `requirePermission(`, `permissions.includes(`, `can('<word>:<word>')`, `PERMISSIONS = {` |
| `module-levels` | a map of area → level (`grants[`, `modules[`), `hasModule(`, `minLevel`, an ordered levels array used with `indexOf` |
| `policy-engine` | imports of `@casl/ability`, `@casl/react`, `casbin`, `@open-policy-agent/*`, `@cerbos/*`, `oso`, `permitio`; `defineAbility`, `AbilityBuilder`, `<Can I=`, `enforcer.enforce(`; `*.rego`, `model.conf`, `policy.csv` |

Decision:

- **One model dominates the guards** → record it; report the evidence (file:line of the guard and of the type/policy definition).
- **Several models present** → apply [Mixed models](#mixed-models); state the layering you inferred.
- **No access code, or hits are contradictory** → detection is inconclusive. Present the four models with their trade-offs (above) and ask the user to pick. Do not default silently.

## Runtime contract

### Navigation builder

One pure function produces the navigation; nothing else decides which links render.

- **Signature:** `buildNavigation(user, flags?) -> NavConfig`. Each item carries a `requires` requirement in the selected model's shape.
- **Filtering happens only here**, by calling `guardHelper(user, item.requires)`. Shell components render the result; they never re-filter.
- **Mirrors the route guard.** The builder and the route/API guard call the same `guardHelper` with the same requirement, so nav and server never disagree.
- **Deterministic order.** Sections follow a fixed project-defined priority; shared sections that several users can reach are emitted once.
- **Pure and memoizable** on the user's access data.

NavConfig shape (illustrative — not required):

```ts
type NavItem = {
  href: string;          // composed under panelBasePath
  label: string;         // or an i18n key
  icon?: string;
  badgeKey?: string;     // optional live count source
  requires: Requirement; // shape per accessModel; { anyOf: [...] } for cross-resource items
};
type NavSection = { title?: string; items: NavItem[] };
type NavConfig = { sections: NavSection[] };
```

### Auth status and access data

| Member | Returns | Notes |
|---|---|---|
| `useIdentity()` | `{ id, displayName } \| null` | Current user, or null when unauthenticated. |
| `useAccess()` | the user's access data for `accessModel` | role(s), permission set, grant map, or ability. |
| `useAuthStatus()` | `"loading" \| "authenticated" \| "anonymous"` | Skills show a spinner while `loading`. |
| `defaultRouteFor(user)` | `string` | Landing route after login, derived from access, never hard-coded. |
| `loginRoute(returnTo)` | `string` | Where anonymous users go; carries a return path. |

Rules:

- **Wait for `loading` to settle.** Never gate or redirect while status is `loading`.
- **Stale-session guard.** If required access data is absent after rehydration, treat the session as stale and route to login rather than assuming no access.
- **Server is authoritative.** The server gate decides; the client gate exists for ergonomics and must evaluate the same requirement. UI hiding is never authorization.
- **Access can change mid-session.** Read it from the auth source on each render; do not snapshot it into component state.

### Panel base path

- Every route is composed as `<panelBasePath>/<segment>`; guards, redirects, and active-route matching derive from it.
- Active detection: `pathname === href` **or** `pathname.startsWith(href + "/")`, so `/area` never matches `/area-extra`.

### Audit helper

- **Signature:** `audit(event)` with `event = { action, targetType, targetId?, meta? }`.
- Sensitive actions (PII reveal, destructive operations, permission changes) await the audit write; if it fails, the action fails (see `admin-roles-and-permissions`).

### UI library and status palette

- The shell composes primitives from `uiLibrary` (`Button`, `Link`, `Spinner`, `Badge`, `Tooltip` — illustrative names).
- Status badges map neutral tokens (`neutral`, `pending`, `active`, `warning`, `error`) to design tokens (`var(--badge-warning)`), never literal colors.

### RTL locales

- When the active locale is in `rtlLocales`, set `dir="rtl"` on the shell root and mirror directional affordances (see `admin-rtl-ltr`). Direction never affects access or navigation filtering.

## Example cache (illustrative — not required)

```json
{
  "schemaVersion": 1,
  "framework": "next-app",
  "panelDir": "app/(admin)/admin",
  "panelBasePath": "/admin",
  "accessModel": "role-enum",
  "access": {
    "roles": ["owner", "editor", "support"],
    "roleSource": "prisma/schema.prisma",
    "multiRole": false,
    "superRole": null
  },
  "authHelper": "import { auth } from '@/auth'",
  "guardHelper": "import { requireRole } from '@/lib/access'",
  "auditHelper": "none",
  "navSource": "app/(admin)/admin/_nav.ts",
  "piiFields": ["email", "phone"],
  "rtlLocales": [],
  "i18nLibrary": "next-intl",
  "dataLibrary": "swr",
  "uiLibrary": "none",
  "validationLibrary": "zod",
  "formLibrary": "react-hook-form",
  "cssFramework": "tailwind",
  "importFormat": "none"
}
```

## Legacy cache keys

Caches written before `schemaVersion` 1 used other names. When a command reads one, map the keys, show the user the result, and rewrite the file:

| Legacy key | Current key |
|---|---|
| `adminBasePath` | `panelDir` (and derive `panelBasePath`) |
| `roleList` | `accessModel: "role-enum"` + `access.roles` (re-run detection to confirm the model) |
| `authHelperImport` | `authHelper` |
| `auditHelperImport` | `auditHelper` |
| `i18nProvider` | `i18nLibrary` |

## Adapter completeness checklist

- [ ] `accessModel` recorded with detection evidence, or chosen by the user after an inconclusive detection.
- [ ] Every required `access` field for that model is filled.
- [ ] `guardHelper` is one function used by route guards, the navigation builder, and API handlers.
- [ ] `panelDir` and `panelBasePath` set; all routes compose under `panelBasePath`.
- [ ] `authHelper` reads a verified server-side session.
- [ ] `auditHelper` set, or `"none"` with a scaffolded minimal helper.
- [ ] `piiFields` confirmed by the user.
- [ ] Optional library keys filled from `package.json` where present.
