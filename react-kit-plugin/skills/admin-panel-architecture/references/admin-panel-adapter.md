# Admin panel adapter (project inputs)

The react-kit admin-panel skills stay project-agnostic by reading a single **adapter** that each project supplies. The adapter is the only place where project-specific names, paths, roles, and library choices live. Skill logic (navigation building, route guarding, active-route detection, responsive shell) consumes the adapter and never hard-codes any of these values.

This page is a checklist of the adapter fields a project must provide, the contract each field must satisfy, and an illustrative adapter shape. Provide every field below; defaults are noted where a field is optional.

## How the adapter is used

The adapter is loaded once at the panel root and passed down (via context or props) to every shell component and hook. Rules:

- **One adapter per project.** Do not scatter project names across components. If a value is project-specific, it belongs in the adapter.
- **Skills read, never write.** Skill code treats the adapter as immutable configuration resolved at startup.
- **No business nouns in skill code.** Skills refer to abstract entities (Orders, Tickets, Requests, Customers, Products, Records) and to adapter fields, never to a concrete domain term.
- **Examples are non-binding.** Every concrete example in this doc is labeled illustrative. Plugin behavior must never depend on any example value.

## Adapter field checklist

| Field | Type | Required | Purpose |
|---|---|---|---|
| `panelBasePath` | string | yes | Path prefix under which all admin/staff routes live. |
| `roleModel` | object | yes | Module/grant map shape + level semantics. |
| `buildNavigation` | function | yes | Pure factory: grants -> filtered nav sections. |
| `auth` | object | yes | How to read current identity, grants, and auth status. |
| `audit` | function | optional | How to record an audit event. No-op default. |
| `dataClient` | object | yes | Data-fetching library binding (query/mutation). |
| `ui` | object | yes | Component library + status-badge palette. |
| `rtlLocales` | string[] | optional | Locale codes that render right-to-left. Default `[]`. |

## Panel base path

The single prefix under which every protected admin route lives. All guards, redirects, and active-route matching derive from it.

- Provide one value, e.g. an admin/staff prefix. Skills compose all routes as `<panelBasePath>/<segment>`.
- The "current area" is the first path segment after `panelBasePath`.
- The default landing route for an authenticated user is computed from grants (see `auth.defaultRouteFor`), never hard-coded.
- Use a trailing-slash-aware match for active detection: a route is active when `pathname === href` **or** `pathname.startsWith(href + "/")`. This avoids `/area` falsely matching `/area-extra`.

## Role / module model and level semantics

Access is **grant-based**, not a single role enum. A user carries a map of grant-key to level. This generalizes single-role systems and multi-area systems alike.

Level semantics (ordered, low to high):

| Level | Meaning |
|---|---|
| `read` | May view records in the area. |
| `full` | May create/update/delete records in the area. |
| `manager` | Full plus area-administration actions (assignment, approvals, configuration). |

Rules the adapter must encode:

- **Minimum-level checks.** An access check is "has grant `K` at level `>= L`". A `manager` grant satisfies a `read` or `full` requirement for the same key.
- **Admin-implies-all.** A designated admin grant implicitly satisfies every area check. The adapter exposes which grant key is the admin key; skills do not assume a literal name.
- **Grants are dynamic.** Never branch on a fixed role string. Read grants from auth state every render; they can change mid-session.
- **Two-gate enforcement.** Server middleware is the first gate; client guards/hooks are the second. Both consult the same grant map (server reads a synced cookie/snapshot; client reads the live store).
- **Cross-area resources.** Some routes require any-of several grants. Encode these as an explicit allow-set, not as a single key.

## Navigation source: `buildNavigation`

Navigation is produced by one pure function, not hard-coded per role. It takes the user's grants (and any extra flags the project needs) and returns a config of **already-filtered** sections.

Contract:

- **Signature:** `buildNavigation(grants, flags?) -> NavConfig`.
- **Pure and memoizable.** Same inputs -> same output. Skills memoize on grants so the sidebar only rebuilds when grants change.
- **Filtering happens here, only here.** The returned sections contain only items the user may reach. Shell components must not re-filter or conditionally add items at render time.
- **Stable ordering.** Section order follows a project-defined priority. Shared sections that several grants can see are emitted once.
- **No forbidden hrefs.** Every emitted item's href must be reachable per the same rules the server gate enforces.

NavConfig shape (illustrative — not required):

```ts
type NavItem = {
  href: string;        // composed under panelBasePath
  label: string;
  icon?: string;
  badgeKey?: string;   // optional live count source (e.g. "pendingRequests")
};
type NavSection = {
  title?: string;      // hidden when sidebar is collapsed
  items: NavItem[];
};
type NavConfig = { sections: NavSection[] };
```

## Auth helper and reading current identity

The adapter exposes how skills learn who the current user is, what they are allowed to do, and whether auth is settled.

Required members:

| Member | Returns | Notes |
|---|---|---|
| `useIdentity()` | `{ id, displayName } \| null` | Current user, or null when unauthenticated. |
| `useGrants()` | `Record<string, Level>` | Grant map from the auth store. |
| `useAuthStatus()` | `"loading" \| "authenticated" \| "anonymous"` | Skills show a spinner while `loading`. |
| `hasAccess(grants, key, level)` | `boolean` | Min-level check; honors admin-implies-all. |
| `defaultRouteFor(grants)` | `string` | Landing route after login, derived from grants. |
| `loginRoute(returnTo)` | `string` | Where to redirect anonymous users; carries a return path. |

Rules:

- **Wait for `loading` to settle.** Never gate or redirect while status is `loading`; render a spinner. Auth state may rehydrate asynchronously from storage.
- **Stale-session guard.** On rehydration, if required fields (e.g. the grant map) are absent, treat the session as stale and route to login rather than assuming empty grants.
- **Single source of truth.** The client store is authoritative for the live session; the server gate reads a synced snapshot. Keep them in sync on login/logout.

## Audit helper

Optional hook for recording privileged actions (sign-in, grant changes, destructive operations).

- **Signature:** `audit(event)` where `event = { action, targetType, targetId?, meta? }`.
- **No-op default.** If the project omits it, skills call a default that does nothing — behavior must not depend on audit being present.
- `targetType` uses neutral entity names (Orders, Tickets, Requests, Customers, Products, Records).

## Data-fetching library binding

Skills do not import a specific data library; they call adapter-provided bindings so the project picks the client.

| Member | Purpose |
|---|---|
| `useQuery(key, fetcher, opts?)` | Read with caching/dedup. |
| `useMutation(fn, opts?)` | Write with pending/error state. |
| `invalidate(key)` | Refresh cached reads after a write. |

Rules: keys are arrays for hierarchical caching; the binding owns retries and stale-time policy; skills never reach a network primitive directly.

## UI / component library and status-badge palette

The adapter names the component library primitives the shell renders with, plus a status-to-style map for badges.

Required UI members (illustrative names):

- `Button`, `Link`, `Spinner`, `Badge`, `Tooltip` — primitives the shell composes.
- `statusPalette` — maps a neutral status token to badge styling. Use design tokens (CSS custom properties), not literal colors.

statusPalette shape (illustrative — not required):

| Status token | Intent | Token example |
|---|---|---|
| `neutral` | default / informational | `var(--badge-neutral)` |
| `pending` | awaiting action | `var(--badge-pending)` |
| `active` | in progress / ok | `var(--badge-active)` |
| `warning` | needs attention | `var(--badge-warning)` |
| `error` | failed / blocked | `var(--badge-error)` |

Rules: never hard-code hex values in skill output; map status tokens through `statusPalette`; collapsed-sidebar styling and active/hover states must also resolve through tokens.

## RTL locale list

The adapter lists locale codes that render right-to-left so the shell can flip layout direction.

- **Type:** `string[]`; default `[]`.
- When the active locale is in the list, set `dir="rtl"` on the shell root and mirror directional spacing/affordances (sidebar side, chevrons, breadcrumb order).
- Direction is a presentation concern only; it never affects access control or navigation filtering.

## Illustrative adapter object shape

Labeled illustrative — not required. A project supplies one object of this shape; values shown are placeholders using neutral entities and roles.

```ts
// Example (illustrative — not required):
const adminPanelAdapter = {
  panelBasePath: "/workspace",

  roleModel: {
    adminKey: "platform",            // grant that implies all areas
    levels: ["read", "full", "manager"],
    priority: ["platform", "orders", "tickets", "records"], // section order
  },

  buildNavigation(grants, flags) {
    // returns { sections: NavSection[] }, already filtered by `hasAccess`
    return buildNav(grants, flags);
  },

  auth: {
    useIdentity,                     // () => { id, displayName } | null
    useGrants,                       // () => Record<string, "read"|"full"|"manager">
    useAuthStatus,                   // () => "loading" | "authenticated" | "anonymous"
    hasAccess,                       // (grants, key, level) => boolean
    defaultRouteFor,                 // (grants) => string
    loginRoute: (returnTo) => `/sign-in?returnTo=${encodeURIComponent(returnTo)}`,
  },

  audit: (event) => recordAudit(event),  // optional; default is a no-op

  dataClient: { useQuery, useMutation, invalidate },

  ui: {
    Button, Link, Spinner, Badge, Tooltip,
    statusPalette: {
      neutral: "var(--badge-neutral)",
      pending: "var(--badge-pending)",
      active:  "var(--badge-active)",
      warning: "var(--badge-warning)",
      error:   "var(--badge-error)",
    },
  },

  rtlLocales: ["ar", "he", "fa", "ur"],
};
```

## Adapter completeness checklist

- [ ] `panelBasePath` set; all routes composed under it.
- [ ] `roleModel` declares admin key, level order, and section priority.
- [ ] `buildNavigation` is pure, memoizable, and returns pre-filtered sections.
- [ ] `auth` exposes identity, grants, status, `hasAccess`, `defaultRouteFor`, `loginRoute`.
- [ ] `audit` provided or intentionally defaulted to no-op.
- [ ] `dataClient` binds query/mutation/invalidate.
- [ ] `ui` provides primitives plus a token-based `statusPalette`.
- [ ] `rtlLocales` listed (or empty array) and wired to shell direction.
