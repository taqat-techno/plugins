---
name: admin-dangerous-actions
description: Confirmation patterns for destructive admin operations — delete, suspend, impersonate, force-logout, mass-update, irreversible state transitions. Owns the type-to-confirm pattern, the two-step button pattern, the consequence-summary requirement, the audit-on-action rule, and the "the more destructive, the more friction" rule. Activates when adding any destructive action button, link, modal, row action, or bulk action.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - friction-proportional-to-blast-radius rule
  - confirmation modal contract (consequence summary, type-to-confirm, audit-on-action)
  - two-step button pattern
  - destructive-action affordance (color, position, label, never the default focus)
  - undo-window pattern (where reversible)
  - bulk-destructive confirmation requirements
defers_to:
  - admin-roles-and-permissions (who can perform the action; audit-log shape)
  - admin-forms (the form a destructive submit lives in)
  - admin-crud (where the action appears in a row / bulk bar)
  - project audit-log helper
user_invocable: false
---

# admin-dangerous-actions

## Purpose

A destructive action is one whose effect is hard or impossible to reverse: delete a user, suspend an account, force-logout a session, transition an order to refunded, impersonate a user, drop an index, run a migration. The most expensive admin-panel incidents come from one-click destruction with no confirmation, no audit, no undo. This skill makes friction proportional to blast radius.

## When to use

Activate when:

- Adding any button labelled Delete, Remove, Archive, Suspend, Disable, Revoke, Force, Drop, Reset, Wipe, Migrate, Refund, Cancel, Terminate, Impersonate, Empty, Clear, Purge.
- Adding a transition that cannot be undone via the same UI (e.g., "Approve" if there is no "Unapprove").
- Adding a bulk action that mutates more than one record at once.
- Adding a row action that mutates the record permanently.

Skip when:

- The action is reversible by the same UI within a normal flow (e.g., a draft document's Save = reversible).

## Inputs (adapter)

1. **Action catalogue** — list of destructive actions the admin panel supports, with their blast radius (low / medium / high / extreme).
2. **Audit-log helper** — function that writes an audit-log row.
3. **Undo support** — whether the backend supports a "restore" within a window (e.g., soft delete + 30-day restore).
4. **Per-action permission predicate** — `canPerform(actor, action, target)` from `admin-roles-and-permissions`.

## Read-only investigation steps

Before adding a destructive action:

1. **Is it actually destructive?** "Cancel" on a draft is not destructive; "Cancel" on a confirmed order with money attached is.
2. **Is it reversible?** If yes, how? In the same UI? Within how long? By whom?
3. **What is the blast radius?** Single record? Many records? Other users' data? Money? Account access?
4. **Does an audit-log entry already exist for this action class?** If not, add audit before adding the UI.
5. **Is the API endpoint idempotent?** Repeated clicks must not produce extra effects (avoids confirmation-bypass via network retry).

## Decision framework

### Friction-proportional-to-blast-radius

| Blast radius | Examples | Required friction |
|---|---|---|
| Low | toggle a non-critical flag, archive a draft, dismiss a banner | Single click — no modal |
| Medium | delete a record with soft-delete + 30-day restore | Two-step button OR modal with summary; audit |
| High | delete with hard-delete; suspend an account; force-logout all sessions; refund | Modal with consequence summary; explicit "I understand" or type the entity name; audit; success undo affordance if available |
| Extreme | mass-delete; drop a table; run a migration; impersonate a high-privilege user | Type-to-confirm with the entity name AND the count; second confirmation; audit BEFORE the action; no undo expected |

The friction is non-negotiable per row of this table. "Just this once, it's faster without the modal" is the path to the incident.

### Confirmation modal contract

A confirmation modal for any high-blast action must include:

1. **Title** that names the action and target. "Delete user `ahmed`" — not "Are you sure?".
2. **Consequence summary** — 1–3 sentences describing what happens.
   - "All open sessions will be terminated."
   - "Their 412 attached records will be archived."
   - "This action is logged in the audit trail."
3. **Affirmation affordance** appropriate to blast radius:
   - Medium: explicit "Delete user" button (NOT "Confirm"; NOT the modal's default focus).
   - High: a checkbox "I understand this cannot be undone" that must be checked.
   - Extreme: text input that requires the user to type the entity's name or `DELETE` literally.
4. **Cancel** is the default focus. Hitting `Esc` cancels.
5. **Destructive button** is never blue / never the primary brand color. Red / orange / outlined-with-red.
6. **Audit** is written when the action fires, not before (cancellation should not produce an audit-log row).

### Two-step button pattern (for medium blast)

```
[Delete]   →  click  →  [Click again to confirm  (3s)]   →  click  →  fires
                              │
                              └── timeout → reverts to [Delete]
```

- Useful for high-frequency medium-blast actions where a modal would be friction overkill.
- Timeout (3–5s) prevents accidental commitment from old hover.
- Button label changes; color may change.
- Still writes audit on fire.

### Type-to-confirm pattern (for high / extreme blast)

```
+----------------------------------------------+
| Delete user "ahmed.shafiq"?                  |
|                                              |
| This will permanently:                       |
|  - Remove the user                           |
|  - Terminate 3 open sessions                 |
|  - Archive 412 records                       |
|                                              |
| Type "ahmed.shafiq" to confirm:              |
| [____________________________]               |
|                                              |
|                  [Cancel]  [Delete (disabled)]
+----------------------------------------------+
```

- The "Delete" button is disabled until the typed string exactly matches.
- The string is the entity's natural identifier (username, slug, name) — not its UUID.
- Case sensitivity: prefer case-sensitive for emphasis.

### Bulk destructive confirmation

Bulk delete of N records is its own category:

```
"Delete 1,247 users — type DELETE 1247 to confirm"
```

- The number is part of the confirmation string. Changing the selection invalidates the typed confirmation.
- Per-item failure report is required after the action — some may fail.
- Bulk destructive should default to soft delete with restore where the data model allows.

### Undo window (where supported)

If the backend supports restore-within-window (soft delete):

- After the action, show a non-modal toast: "User `ahmed` deleted — Undo (29s)".
- Clicking Undo within the window restores.
- The toast does not block; the user can move on.
- After the window expires, the data is hard-deleted by a backend job.

### Affordance placement

- Destructive buttons go on the **trailing** side (right in LTR; left in RTL — see `admin-rtl-ltr`).
- Destructive buttons are **never** the default focus.
- Destructive buttons in a row's action menu go at the **bottom** of the menu, after a divider.
- "Save" and "Delete" are never adjacent without a separator.
- A destructive action does not auto-close a parent modal — the user explicitly dismisses.

### Audit-on-action

For every destructive action:

```ts
await auditLog.write({
  actor: session.userId,
  action: '<entity>.<verb>',           // e.g., 'user.delete', 'order.refund'
  target: { type: '<entity>', id: <id> },
  meta: {
    blastRadius: '<low|medium|high|extreme>',
    reversible: <bool>,
    summary: '<what changed>',
  },
  ip: getRequestIp(),
  userAgent: getRequestUA(),
  at: new Date().toISOString(),
})
```

- Audit writes happen **server-side**, not from the client.
- Audit writes happen **before** the action's permanent effect when possible (so a failed audit cancels the action).
- Audit writes are awaited — never fire-and-forget.

## Safety gates

- **Never** ship a destructive action without confirmation friction proportional to blast radius (see table).
- **Never** ship a destructive action without an audit-log entry.
- **Never** make the destructive button the modal's default focus.
- **Never** use the brand's primary color for destructive buttons.
- **Never** place "Delete" and "Save" adjacent without a separator.
- **Never** bulk-delete without a per-item failure report.
- **Never** trust the client to enforce the action permission — server re-checks.
- **Never** write the audit-log row only on success — write it on the attempt, with `outcome: success|failed`.
- **Never** auto-close the modal on success without showing the undo affordance (where supported).

## Validation checklist

Before committing a destructive action:

- [ ] Blast radius classified (low / medium / high / extreme).
- [ ] Friction matches blast radius per the table.
- [ ] Modal title names the action AND the target.
- [ ] Consequence summary lists 1–3 concrete effects.
- [ ] Affirmation affordance present and appropriate.
- [ ] Cancel is the default focus; `Esc` cancels.
- [ ] Destructive button color is not the primary brand color.
- [ ] Audit-log row written server-side, awaited, with actor / action / target / meta / ip / UA / outcome.
- [ ] Server re-checks the per-action permission predicate.
- [ ] Undo affordance present if backend supports restore.
- [ ] Bulk variant has per-item failure report.

## Output format

When scaffolding a destructive action, output:

```
DESTRUCTIVE ACTION
  Action: <entity>.<verb>
  Blast radius: <low|medium|high|extreme>
  Reversible: <yes (window: <duration>) | no>
  Friction: <single-click | two-step | modal-summary | type-to-confirm>
  Confirmation string: "<expected literal>"           ← if type-to-confirm
  Audit event: <entity>.<verb>
  Server permission predicate: <canPerform-fn>
  Undo affordance: <yes | no>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| `<button onClick={() => fetch('DELETE', ...)}>Delete</button>` | One-click destruction; no confirmation, no audit | Modal with consequence + audit-on-action |
| Confirmation modal with "Are you sure?" and no detail | User does not know what they are confirming | Title names target; body lists consequences |
| Destructive button is the modal's primary action | Easy mis-click on Enter | Cancel is default focus; destructive is secondary |
| Audit written client-side via `await fetch('/audit')` | Client can omit, fail silently, lie | Server writes audit during the action |
| Bulk delete with one fire-and-forget call | No per-item visibility on failure | Batch endpoint with per-item result |
| Soft-delete + no undo affordance | User knows they can restore but cannot find how | Toast with Undo for the duration |
| Type-to-confirm using the record's UUID | Users do not type UUIDs; they paste — bypasses the safeguard | Use the natural identifier (name / username / slug) |
| Same modal style for "archive draft" and "delete account" | Drains attention; users dismiss the dangerous one as routine | Friction matches blast radius |
| Audit log not written on cancellation | Fine | (cancellation is not an action) |
| Audit log written only on success | Lost forensic trail when the action failed mid-flight | Write at attempt with outcome field |

## Portability rationale

The friction table and confirmation patterns apply to any web app with destructive admin actions. The skill does not depend on:

- A specific UI library (modals exist everywhere)
- A specific backend (audit log is a server-side write of any persistence shape)
- A specific permission model

## Cross-references

- `admin-roles-and-permissions` — who can perform the action; audit-log shape.
- `admin-forms` — destructive submit from a form.
- `admin-crud` — destructive row + bulk actions in lists.
- `admin-import-export` — large imports are destructive when they replace existing rows.
- `admin-route-auditor` (agent) — flags one-click destructions, missing audit, missing consequence summary.
