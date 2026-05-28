---
name: admin-roles-and-permissions
description: Role-aware admin UI rules. Owns the "UI hide is NOT authorization" contract, the role-aware menu pattern, PII masking in admin views, audit visibility, and the paired UI-gate / API-gate rule. Activates when building any admin route, modifying a sidebar/menu, adding a role-conditional render, masking a sensitive field, or rendering an audit log. Generic and portable — role names, PII fields, and audit helpers are project-supplied adapter inputs.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - the paired-gate rule (every UI gate has a matching API gate)
  - role-aware menu pattern
  - PII masking pattern in admin views (mask by default, reveal on explicit user action + audit)
  - audit-log visibility scoping
  - the "UI hide is not authorization" anti-pattern catalogue
defers_to:
  - project security/privacy SOP (canonical PII list, redaction rules, secret handling)
  - project auth layer (how sessions / tokens / role claims are produced)
  - admin-shell (where the role-aware menu is rendered)
  - admin-dangerous-actions (confirmation flow for destructive actions)
  - admin-import-export (import is itself a high-privilege admin action)
user_invocable: false
---

# admin-roles-and-permissions

## Purpose

Most admin-panel security bugs come from the same mistake: hiding a button in the UI and forgetting to re-check authorization in the API. This skill makes the "paired gate" rule explicit, gives the admin-panel author a checklist for role-aware UI, and refuses to let PII render unmasked by default.

This skill is **foundation-tier inside the plugin** — every other `admin-*` skill defers to it on authorization, PII, and audit questions.

## When to use

Activate when:

- Building or modifying any admin route, page, or component.
- Adding a menu item, sidebar entry, or header button.
- Rendering a list of users, audit-log entries, or any record with sensitive fields.
- Implementing a role-conditional render (`if (role === 'X')`).
- Building a destructive action (delete / archive / suspend / impersonate).
- Reviewing an admin PR for missing role gates or PII leaks.

Skip when:

- Editing public marketing pages, login screens (covered by your project's auth skill), or non-admin user-facing UI.

## Inputs (adapter)

The plugin makes no assumption about your project's roles or PII. Before applying this skill, you need:

1. **Role list** — the role enum the app uses. Example: `['admin', 'manager', 'support', 'viewer']`. The plugin does not bake in any role names.
2. **Permission matrix** — for each (role × resource × operation) cell, allow / deny. Generated or validated by `/admin-role-matrix`.
3. **PII field list** — which fields are sensitive. Example: `['email', 'phone', 'national_id', 'date_of_birth']`. Sourced from your project's security/privacy SOP.
4. **Auth helper import** — how the current user + role is obtained server-side. Example: `getServerSession()` (NextAuth), `auth()` (Clerk), custom `getUser()`.
5. **Audit helper import** — how an audit-log row is written. Example: `await auditLog.write({ actor, action, target, meta })`. If your project has none yet, the skill includes a minimal shape.

These are asked once by `/admin-scaffold` and cached locally so you do not re-answer.

## Read-only investigation steps

Before adding a new role check or PII render, confirm:

1. **Where is authorization actually enforced?** Read the route handler / API endpoint. Look for `if (!session || !hasRole(...))`. If the only check is in the page component, this is the bug — fix it server-side first.
2. **Is the role claim signed?** Decoded from a verified JWT / session cookie / equivalent. If the role comes from a header the client controls, it is not a role claim — it is user input.
3. **What does the API return for an unauthorized request?** `401` vs `403` vs `200 with empty list` matters. List endpoints that "filter by visible-to-role" must NOT return rows the role cannot see — even with no UI consumer.
4. **What does the audit-log row look like for this action?** Look at one prior entry. If audit is silent on the same action class, that is the bug — add audit before adding UI.

## Decision framework

### The paired-gate rule (non-negotiable)

Every visible-or-not UI decision MUST have a matching server-side gate:

| UI surface | UI gate | Required matching server gate |
|---|---|---|
| Menu item in sidebar | `role === 'admin' && <MenuItem/>` | Route handler returns 403 for non-admin |
| Disabled "Delete" button | `disabled={!canDelete}` | DELETE endpoint returns 403 if `!canDelete(actor, target)` |
| Row visible in list | filtered client-side | List endpoint excludes those rows server-side |
| Field hidden in detail | `{canSeePII && <Phone/>}` | API response omits the field for unauthorized callers |
| Form input hidden | `{role === 'admin' && <SuperFlag/>}` | PATCH endpoint rejects `superFlag` for non-admin |

The UI gate is for ergonomics (cleaner screens, less confusion). The server gate is for security. **Removing the UI gate must NEVER expose data or actions** — if it does, the server gate is missing.

### Role-aware menu pattern

```tsx
// Provided by your project's auth layer
const session = useSession()

const menuItems = ALL_MENU_ITEMS.filter(item =>
  item.allowedRoles.includes(session.role)
)
```

- The `allowedRoles` list lives next to the menu definition, not scattered across components.
- A user who is not in `allowedRoles` for an item does not see it AND if they navigate to the URL directly, the route handler returns 403. (Paired gate.)
- The matrix is the source of truth: `allowedRoles` is generated from the matrix, not hand-edited per menu.

### PII masking — mask by default

```tsx
// Default: mask
<MaskedField value={user.phone} mask={maskPhone} />

// Reveal: user-initiated, audited
<RevealOnClick
  value={user.phone}
  mask={maskPhone}
  onReveal={() => auditLog.write({
    actor: session.userId,
    action: 'admin.pii.reveal',
    target: { type: 'user', id: user.id, field: 'phone' },
  })}
/>
```

- Sensitive fields are masked at render time (`+9665••••1234`, `••••@example.com`, `••••-••••-1234`).
- Reveal is per-field, per-row, on explicit user click. NOT a global "show PII" toggle (those leak to screenshots, logs, screen recordings, OS clipboard).
- Every reveal writes an audit-log row with actor + target + field. If you cannot write an audit row, you cannot reveal.
- Lists DO NOT auto-reveal on hover. Lists DO NOT bulk-reveal.

### Audit visibility

Audit-log readers are themselves audited:

| Reader role | What they see | What they don't |
|---|---|---|
| Highest-privilege admin role | Full audit log including their own | (nothing hidden) |
| Other admin roles | Audit log of resources they own or in their scope; their own audit visible | Other admins' actions in unrelated scopes |
| Non-admin | No audit log access at all | — |

The pattern: scope the audit query by `actor_visible_to(reader_role)` — never `WHERE actor_id = current_user_id` (that hides oversight from supervisors).

### When a role check is conditional on data

`canEditUser(actor, target)` (e.g., "manager can edit users in their team, not others") is **not** a role check — it is a per-record permission. Live rule: **never compute this on the client.** The server is the source of truth; the UI reads the computed `canEdit` boolean back from the API or runs the same predicate against client-cached data **with the server result as the tiebreaker**.

## Safety gates

- **Never** trust a role claim that came from the URL, a query parameter, request body, or a client-supplied header.
- **Never** ship a "show all PII" admin toggle — even gated to one role.
- **Never** log full PII to console / browser devtools / Sentry / observability backend. Mask before log.
- **Never** write a role-conditional render without verifying the server gate exists. The plugin's `/admin-audit` command catches this; the agent `admin-route-auditor` catches it.
- **Never** make audit-log writes optional or fire-and-forget. If audit write fails, the action fails.
- **Never** weaken an existing role check ("temporarily allow X to do Y") without an audit-log entry on the change itself AND an expiry date.

## Validation checklist

Before committing an admin change involving roles, permissions, or PII:

- [ ] Every new conditional render has a documented server gate (file path + function name).
- [ ] Every new menu item has its role list in the matrix.
- [ ] Every new PII field renders masked by default.
- [ ] Every reveal action writes an audit-log row before exposing the value.
- [ ] The matrix and the code agree (run `/admin-role-matrix --validate`).
- [ ] No role string compared as `==` to a user-controlled value.
- [ ] No PII passed to `console.log`, `toast`, `alert`, or unredacted error reports.
- [ ] Audit-log writer is awaited (not fire-and-forget).
- [ ] Tests cover at least one allowed-role and one denied-role path.

## Output format

When generating a role-aware admin component, output:

```
ROLE-AWARE COMPONENT
  Component: <name>
  Allowed roles: [<role>, <role>]
  Server gate: <file>:<function>   ← MUST exist before merge
  PII rendered: [<field>, <field>] (masked by default)
  Audit events: [<action-code>]
```

When auditing an existing route, output the Markdown table defined by `admin-route-auditor`.

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| `{role === 'admin' && <Button/>}` as the only access control | Anyone who edits the page in devtools sees the button. The API is wide open. | Pair with server gate in the handler. |
| `if (user.role === userInputRole)` | `userInputRole` came from the client. Always false-or-always-true depending on the comparison direction; either way, useless. | Take role from verified session only. |
| Global "Show PII" toggle | Leaks to screenshots / screen recordings / clipboard / observability. | Per-field reveal on explicit click, audited. |
| `console.log(user)` during debugging | Logs PII; survives merge; leaks to prod observability. | Use a redacting logger; never log full records. |
| Hiding sensitive fields with `display: none` | The field is still in the DOM / Redux store / React tree / network response. | Omit on the server. |
| `try { await audit(...) } catch {}` | Audit silently fails; you lose the forensic trail. | Let audit failure fail the action. |
| Role list duplicated in 12 components | One forgotten place becomes a bypass. | Single matrix, single derivation. |

## Portability rationale

This skill assumes:

- A web framework that has server-side route handlers (any of Next.js, Remix, Rails, Django, Express, FastAPI, Laravel, …).
- A session or token mechanism that provides a verified role claim.
- A logging surface that supports writing audit rows.

It does **not** assume any specific:

- Auth library
- ORM
- Role names
- PII fields
- Audit storage
- UI framework (the React examples are illustrative; the rules are framework-agnostic)

Substitute your project's specifics via the adapter inputs above. The rules do not move.

## Cross-references

- `admin-shell` — where the role-aware menu is rendered.
- `admin-crud` — list/detail rendering respects per-row visibility from this skill.
- `admin-dangerous-actions` — confirmation flow combines with audit-on-action from here.
- `admin-import-export` — import is itself a high-privilege admin action and is audited per this skill.
- `admin-route-auditor` (agent) — automates the validation checklist above.
