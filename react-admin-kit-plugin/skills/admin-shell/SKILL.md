---
name: admin-shell
description: Admin layout shell — sidebar, header, content slot, i18n context provider, language toggle, locale persistence, and route-guard composition. Activates when building or modifying the admin layout, sidebar, header, locale switcher, breadcrumb, or any shared chrome. Generic and portable — menu items, role-aware filtering, brand, and i18n keys are project-supplied.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - admin shell composition (sidebar + header + content slot)
  - i18n context provider placement at shell level
  - language toggle pattern (persisted locale)
  - sidebar collapse state (persisted UI preference)
  - shell-level route guard composition (auth → role → render)
  - breadcrumb derivation pattern
defers_to:
  - project auth layer (login / session / role claim)
  - admin-roles-and-permissions (which menu items each role sees)
  - admin-rtl-ltr (direction-aware utilities applied at shell level)
  - admin-states (loading / error states the shell itself shows during auth bootstrap)
user_invocable: false
---

# admin-shell

## Purpose

The admin shell is the chrome that wraps every admin page — sidebar, header, content slot, i18n context, language toggle. The shell exists to keep page code focused on data and behavior, not layout. This skill owns the **structure** of the shell, not its visual styling and not its business logic.

The shell is layout-only. **No data fetching, no business rules, no per-page state should live here.** When this rule slips, every page is forced to re-implement the shell's leaks, and the shell becomes the change-coupling bottleneck.

## When to use

Activate when:

- Creating the admin layout file (`layout.tsx`, `_layout.tsx`, `AdminLayout`, equivalent).
- Adding a menu item to the sidebar.
- Building or modifying the header (user menu, language toggle, role badge, notification bell).
- Wiring i18n context — translation provider, locale persistence.
- Implementing a route guard at the layout level (auth check, role check before rendering children).
- Adding breadcrumb support.
- Persisting a UI preference (collapsed sidebar, theme, locale).

Skip when:

- Editing a single admin page that does not affect the chrome.
- Editing public pages (the shell is admin-only).

## Inputs (adapter)

1. **Admin base path** — where admin pages live (`app/admin`, `src/admin`, `pages/admin`).
2. **Auth helper import** — function that returns the current session + role.
3. **i18n library** — react-i18next, next-intl, lingui, formatjs, or a hand-rolled context. The shell adapts to whichever you use.
4. **RTL languages list** — locales that flip layout direction. Empty if the app is LTR-only.
5. **Brand assets path** — logo, favicon (the shell renders them; this plugin does not author them).
6. **Menu definition source** — single file that declares all menu items with their `allowedRoles`. (Owned by `admin-roles-and-permissions`.)

## Read-only investigation steps

Before adding a feature to the shell, confirm:

1. **Does this belong in the shell, or in a page?** If only one page needs it, it goes in the page. The shell is shared chrome.
2. **Is the existing shell composing or coupling?** Composing = the shell takes children and renders them inside a layout. Coupling = the shell knows what page is rendered and changes behavior accordingly. The first is correct; the second is a smell.
3. **Where does the role claim come from?** The shell should read role from the session helper, never from a context populated by a page (causes flicker, race, and incorrect-during-bootstrap state).
4. **Is the i18n provider rendered above the menu?** If not, menu translation keys break on first render.

## Decision framework

### Composition shape

```tsx
// layout.tsx (server component if your framework supports it)
const session = await getSession()
if (!session) redirect('/login')
if (!isAdminRole(session.role)) redirect('/unauthorized')

return (
  <AdminI18nProvider locale={session.locale}>
    <DirectionWrapper locale={session.locale}>
      <div className="admin-shell">
        <AdminSidebar role={session.role} />
        <div className="admin-shell-main">
          <AdminHeader user={session.user} />
          <main>{children}</main>
        </div>
      </div>
    </DirectionWrapper>
  </AdminI18nProvider>
)
```

Key choices in this shape:

- **Auth check is server-side** (when the framework supports it). Pages never see the layout if the user is not allowed.
- **i18n provider is highest** so menu, header, and pages all share one context.
- **Direction wrapper is just below i18n** — direction depends on locale.
- **Sidebar is fed `role`**, not the entire session. The sidebar's only job is to render menu items the role can see (per `admin-roles-and-permissions`).
- **Children render in `<main>`** — the shell does not wrap them in extra layout (extra wrappers leak into page styling).

### Sidebar pattern

```tsx
function AdminSidebar({ role }: { role: Role }) {
  const items = ALL_MENU_ITEMS.filter(i => i.allowedRoles.includes(role))
  const t = useT()
  return (
    <nav aria-label={t('admin.sidebar.label')}>
      {items.map(item => (
        <SidebarLink
          key={item.href}
          href={item.href}
          icon={item.icon}
          label={t(item.labelKey)}
        />
      ))}
    </nav>
  )
}
```

- Single menu source (`ALL_MENU_ITEMS`) lives next to the matrix from `admin-roles-and-permissions`.
- Labels are i18n keys, not literal strings. The shell never hard-codes language.
- Icons are imported once; the menu source picks them by name.
- Active link state derives from current URL, not from a context the sidebar mutates.

### Header pattern

The header carries:

- Brand (logo / app name) on the leading edge.
- Breadcrumb (derived from route segments — `/admin/users/123/edit` → `Admin / Users / 123 / Edit`).
- Language toggle.
- User menu (avatar, role badge, logout).
- Optional: notification bell, environment badge (dev / staging).

The header is otherwise empty. Action buttons that are page-specific (e.g., "+ New User" on the Users list) belong in the page, not the header.

### i18n context

- Provider wraps the entire admin tree (above sidebar, above header).
- `useT()` (or your library's equivalent) is the only API pages use.
- Locale is read from the user's session (server-known) or `localStorage` (client persistence).
- Switching locale: write to session AND `localStorage`, then either trigger a route refresh (for server components) or update context (for client-only setups).
- Translation key convention: dotted namespace (`admin.users.list.title`), not flat strings. Keys are stable; values are translatable.

### Language toggle pattern

```tsx
function LanguageToggle() {
  const { locale, setLocale, availableLocales } = useI18n()
  return (
    <select
      value={locale}
      onChange={e => setLocale(e.target.value)}
      aria-label="Language"
    >
      {availableLocales.map(l => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  )
}
```

- The toggle shows ALL configured locales, not "EN / AR" hardcoded. The locale list is configuration, not code.
- Persists choice (cookie for SSR, `localStorage` for CSR, both ideally).
- After switching, page re-renders in the new locale. Do not refresh the whole window unless the framework requires it.

### Sidebar collapse state

- Persisted in `localStorage` under a stable key (e.g., `admin.sidebar.collapsed`).
- Restored on mount synchronously to avoid the layout-shift flicker.
- The collapse state is a UI preference, not part of the session. Multiple devices may have different states.

### Breadcrumb derivation

Two strategies:

1. **Route-segment derivation** (default): split the URL on `/`, lookup label per segment, render.
2. **Route-metadata derivation**: each route declares its breadcrumb label; the shell reads it.

Pick one and stay consistent. Mixing both leads to "why does this page have no breadcrumb" bugs.

## Safety gates

- The shell does NOT render anything when `session` is missing — it redirects.
- The shell does NOT call backend APIs for business data. Pages do that.
- The shell does NOT store secrets, tokens, or PII in component state.
- The shell does NOT mutate global state on render (no `useEffect` to write `localStorage` unconditionally).
- The shell does NOT skip authorization for `/admin/login` and `/admin/unauthorized` — those are NOT under the admin shell; they have their own layout (the public layout).
- The shell does NOT include analytics scripts, marketing pixels, or third-party widgets that exfiltrate admin behavior.

## Validation checklist

Before committing a shell change:

- [ ] Auth check runs server-side (or on first render if the framework forces client rendering).
- [ ] Unauthorized users are redirected, not shown an empty shell.
- [ ] i18n provider wraps menu + header + content.
- [ ] No business data fetched in the layout.
- [ ] No PII printed to console in shell components.
- [ ] Menu items derive from the single menu source; no inline `if (role === 'admin')` in the sidebar.
- [ ] Locale persistence works for both first render (SSR) and language switch (CSR).
- [ ] Sidebar collapse state restored without flicker.
- [ ] Tested in both LTR and RTL locales if any RTL locale is configured.

## Output format

When generating a new shell, output:

```
ADMIN SHELL
  Auth check: server-side via <getSession>
  Role check: <isAdminRole> redirects non-admin
  i18n provider: wraps sidebar + header + content
  Direction wrapper: applied; locales [<locale>, <locale>] flip
  Menu source: <path/to/menu.ts>
  Header items: brand, breadcrumb, language toggle, user menu
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Shell fetches "current notifications" on every page load | Couples shell to a feature; one slow API stalls every page | Notification bell is a self-contained client component that fetches its own data |
| Page sets `document.title` and the header also reads it | Two sources of truth; race-y | Page sets title via the framework's metadata API; shell does not duplicate |
| Sidebar `if (user.role === 'admin') return adminMenu; else if ...` | Role logic scattered; one new role becomes a multi-file change | Menu source declares `allowedRoles`; sidebar filters |
| Locale stored only in client state | Lost on refresh; SSR renders the wrong language | Store in cookie + `localStorage` |
| Hard-coded "EN / AR" toggle | Adding a third locale becomes a UI hunt | Toggle reads from configured locales list |
| Shell renders children inside `<div className="page-wrapper">` | Page styling now fights the wrapper | Render children directly in `<main>` |
| Shell exposes a context that pages push state into | Reverse coupling; shell becomes a god-object | Shell takes session + children; pages own their state |

## Portability rationale

The shape (provider → wrapper → sidebar + main with header + content) maps cleanly to:

- Next.js App Router (`layout.tsx`)
- Next.js Pages Router (custom `_app.tsx` wrapper)
- Remix (root or nested layout route)
- Vite + React (a `<Layout>` component wrapping `<Outlet/>`)
- Create React App (the App component wraps routed children)

The skill does not depend on:

- A specific i18n library
- A specific routing library
- A specific CSS framework (Tailwind, CSS Modules, vanilla CSS all work)
- A specific session/auth helper

## Cross-references

- `admin-roles-and-permissions` — single menu source + matrix; this skill only renders.
- `admin-rtl-ltr` — the `DirectionWrapper` and which utilities to use inside the shell.
- `admin-states` — what the shell shows while auth bootstraps (skeleton, never blank).
- `admin-route-auditor` (agent) — checks that pages do not duplicate the shell's chrome.
