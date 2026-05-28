---
name: admin-forms
description: Admin form patterns — field components, validation, save / cancel / dirty handling, row actions, bulk actions, optimistic vs pessimistic update. Owns the "client validation mirrors server, server is authoritative" rule, the dirty-state warn-on-leave pattern, and the bulk-action batching contract. Activates when building any admin form, edit page, row action, or bulk action. Generic and portable — form library and field types are project-supplied.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - field-component-per-type pattern
  - client-side validation mirrors server-side
  - submit / dirty / cancel flow
  - row-action and bulk-action contract
  - optimistic-update reconciliation rule
defers_to:
  - admin-roles-and-permissions (which fields the actor can edit; per-action authorization)
  - admin-dangerous-actions (confirmation flow for destructive submits)
  - admin-states (loading / error / success affordances during submit)
  - project validation library (zod, yup, joi, valibot, hand-rolled — all work)
user_invocable: false
---

# admin-forms

## Purpose

Admin forms differ from public forms: actors are trusted-ish but high-stakes, fields are often sensitive, and the cost of a wrong save is asymmetric (saving wrong data is worse than failing to save). This skill owns the patterns that protect admin actors from their own mistakes — typed fields, real validation, dirty-state warnings, optimistic updates that reconcile, and bulk actions that batch.

## When to use

Activate when:

- Building or modifying any admin form (create, edit, settings).
- Adding a per-row action that mutates data.
- Adding a bulk action that mutates the selected rows.
- Wiring optimistic UI updates.
- Reviewing an admin PR that touches form submission.

Skip when:

- Building read-only views (no form).
- Building search inputs (covered by `admin-crud`).

## Inputs (adapter)

1. **Validation library** — zod, yup, joi, valibot, hand-rolled. The skill adapts.
2. **Form library** — React Hook Form, Formik, TanStack Form, plain `useState`. The skill adapts.
3. **Field type → component map** — text, number, select, multiselect, date, datetime, file, rich text, code, JSON. Project provides the components; skill describes the patterns.
4. **Mutation API shape** — REST PATCH, tRPC mutation, GraphQL mutation, server action.
5. **Optimistic update policy** — which mutations are safe to apply optimistically (low-blast-radius edits) vs which require pessimistic flow (destructive, money, state-machine transitions).

## Read-only investigation steps

Before touching a form:

1. **Where is the server-side validation?** Find it. If the only validation is client-side, that is the gating bug — fix the server first.
2. **What does the API return on validation failure?** Field-level errors (`{ fields: { email: 'invalid' } }`) is correct. A single string is hard to display. Surface this if missing.
3. **Are sensitive fields part of the form payload?** If so, are they masked in the form? Are they sent only when changed (vs always)?
4. **Does the existing form clear unsaved changes on accidental navigation?** If not, that is the most common admin-form bug.

## Decision framework

### Field-component-per-type

A small, predictable set of field components:

| Type | Component | Notes |
|---|---|---|
| string (short) | `<TextField>` | Trim on blur; length limits enforced |
| string (long) | `<TextArea>` | Resize off (predictable layout); char counter if limited |
| number | `<NumberField>` | Locale-aware separators; clamp min/max |
| boolean | `<Switch>` or `<Checkbox>` | Switch for settings, Checkbox for forms |
| enum | `<Select>` | Searchable above ~12 options |
| enum (multi) | `<MultiSelect>` or `<Checkboxes>` | Multi-select for compact; Checkboxes for visibility |
| date | `<DatePicker>` | Locale-aware format; explicit input also allowed |
| datetime | `<DateTimePicker>` | Always store UTC; render in user's tz |
| file | `<FileField>` | Validate magic bytes, not just extension; show progress on upload |
| sensitive | `<SecretField>` | Masked input; reveal-on-click button; never autocomplete |
| relation | `<EntityPicker>` | Searchable; lazy-loads options |
| JSON | `<JsonField>` | Code editor; validates JSON before submit |

The set is small on purpose. Custom one-off components are a smell — they grow inconsistent across forms.

### Validation: client mirrors server, server is authoritative

```ts
// Shared schema (preferred)
const userSchema = z.object({
  email: z.string().email().max(254),
  phone: z.string().regex(/^\+\d{6,15}$/).optional(),
  role: z.enum(['admin', 'manager', 'support', 'viewer']),
})

// Server uses it to validate the request
// Client uses it for instant feedback
```

- **Same schema, both sides** if your stack supports it (TypeScript end-to-end, tRPC, shared package).
- **Otherwise**: client schema is a maintained mirror of the server's; treat divergence as a bug, not a feature.
- **Server response on failure** returns field-level errors. Client maps them onto the form's field-level error state.
- **Client validation is for ergonomics** (instant feedback). It is never the security boundary.

### Submit / dirty / cancel flow

```
        idle  ───────► submitting  ──► success ── reset ──► idle
          ▲                  │
          │                  └─► error ─► (show errors, stay in submitting=false)
          │
   user edits
          │
          ▼
        dirty
```

- **Dirty state** tracks whether any field has been edited since last save.
- **Cancel** when dirty: confirm "discard changes?" before leaving. Never silent.
- **Beforeunload warning** when dirty: prevent accidental browser close / navigation away.
- **Submit when dirty**: send the full record (or the patch — project choice), show "saving…" affordance, disable submit until response.
- **On success**: clear dirty state, reset form to the saved values (so further edits know their baseline).
- **On error**: keep form values, show field-level errors next to fields, show a global error summary at top.

### Optimistic vs pessimistic updates

| Mutation class | Strategy | Reason |
|---|---|---|
| Toggle a non-critical flag (e.g., "favorite") | Optimistic | Failure is recoverable; UX wins |
| Edit a record's editable fields | Pessimistic by default | Server returns canonical state |
| Destructive (delete, suspend) | Pessimistic always + confirmation | No "oops, I optimistically deleted" |
| State-machine transition (approve, publish) | Pessimistic always | Server may reject for reasons the client cannot know |
| Money / inventory / counts | Pessimistic always | Race conditions are real |

Optimistic update rule: **always reconcile** with the server response. If the server returns different values than the client predicted, the server wins — do not silently keep the client prediction.

### Row actions

Per-row mutations (Edit, Archive, Delete, Impersonate, Approve, …):

- One button or one menu per row (per `admin-crud`).
- Click → if destructive, route through `admin-dangerous-actions`.
- Click → if benign, fire the mutation, show inline "saving" → reflect new state in the row.
- Row stays in place after action (do not re-sort or move it under the user's cursor).

### Bulk actions

Bulk mutations on selected rows:

- **Selection**: header checkbox selects all on the current page only by default. A separate explicit affordance selects across all pages.
- **Bulk action bar**: appears above the table when any row is selected. Shows count: "3 selected — Archive | Export | Assign…".
- **Batch endpoint required**: `POST /api/<entity>/bulk { action, ids[] }`. Never N parallel `PATCH` calls.
- **Per-item progress**: long batches stream progress. "Processed 200 / 1247". User sees they can wait.
- **Per-item failure report**: not every item succeeds. Return `{ succeeded: [ids], failed: [{id, error}] }`. UI shows which failed and lets the user retry just those.
- **Bulk destructive actions**: even with confirmation, prefer a slower opt-in flow ("type DELETE 1247 to confirm").

### File upload fields

- Show file size before upload starts; reject above limit before sending.
- Validate MIME by magic bytes server-side (extension is not enough).
- Show progress bar on upload.
- After upload, show preview where possible (image thumb, PDF first page, file icon otherwise).
- On replace: confirm "Replace existing file?" if a file is already attached.

## Safety gates

- Never submit credentials, OTPs, or tokens via a form that browser autocomplete can capture (`autocomplete="off"` on sensitive fields; specific autocomplete tokens otherwise).
- Never echo a sensitive field value back into the URL on validation failure (form remembers field state in component, not URL).
- Never silently truncate field values to fit a column limit — surface the limit to the user.
- Never auto-save destructive changes (no autosave on "delete reason", no autosave on settings that disable features).
- Never accept a file upload above the configured cap; reject client-side AND server-side.
- Never apply a bulk action without an explicit "I am about to affect N records" affordance.

## Validation checklist

Before committing a form change:

- [ ] Server-side validation exists and is the security boundary.
- [ ] Client-side validation matches the server schema.
- [ ] Field-level errors render next to the field.
- [ ] Global error summary at the top when any error exists.
- [ ] Dirty state tracked; cancel and beforeunload warn.
- [ ] On success, form resets to saved values; dirty cleared.
- [ ] Submit button disabled while in flight; double-click cannot double-submit.
- [ ] Optimistic updates (if any) reconcile with server response.
- [ ] Sensitive fields are masked; `autocomplete` set conservatively.
- [ ] Row actions: destructive go through `admin-dangerous-actions`.
- [ ] Bulk actions call a batch endpoint with per-item progress + per-item failure report.
- [ ] No PII logged on submit / failure / success.

## Output format

When scaffolding a form, output:

```
ADMIN FORM
  Entity: <singular>
  Fields:
    - <name>: <type>      [required] [sensitive]
    - <name>: <type>      [required]
  Validation: shared <schema-path>
  Submit endpoint: <method> <path>
  Optimistic: <list of fields safe to optimistic-update>
  Dirty warning: enabled
```

When scaffolding a bulk action, output:

```
BULK ACTION
  Entity: <plural>
  Action: <name>
  Endpoint: POST /api/<plural>/bulk
  Per-item progress: streamed
  Per-item failures: shown with retry-just-failed affordance
  Confirmation: required when destructive
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Client validation only | Anyone with a debugger bypasses it; server is the boundary | Server validates first; client mirrors for UX |
| Field-level errors shown only as a global toast | User cannot tell which field is wrong | Show inline next to the field AND in a global summary |
| No dirty-state warning on accidental navigation | Hours of work lost on one stray click | Track dirty; warn on cancel / beforeunload |
| Submit button stays enabled during in-flight | Double-submit creates duplicate records | Disable while in flight |
| Optimistic update keeps client value when server differs | UI lies | Reconcile to server response |
| Bulk action = N PATCH calls in parallel | Server overload; partial-failure invisible | Batch endpoint with per-item result |
| `autocomplete="on"` on password / token fields | Browser stores credentials in plain text profile | `autocomplete="new-password"` or `"off"` |
| Toast says "Saved!" before the server confirms | UI lies on failure | Wait for response |
| Auto-save destructive settings | One stray click disables a feature | Explicit save for destructive |
| File upload validated by extension only | `.jpg` rename of `.exe` accepted | Magic-byte validation server-side |

## Portability rationale

Field types and validation patterns apply to:

- Any form library (or none)
- Any validation library (or hand-rolled)
- Any UI framework that has React components for inputs

The submit / dirty / cancel flow applies to any framework that lets you intercept form submit and `beforeunload`.

The skill does not depend on:

- A specific UI kit
- A specific date library
- A specific upload library
- A specific state-management approach

## Cross-references

- `admin-roles-and-permissions` — which fields the actor can edit; per-action authorization; PII masking inside forms.
- `admin-crud` — the list/detail context the form lives in; the Edit tab on the detail page.
- `admin-dangerous-actions` — confirmation flow for destructive submits.
- `admin-states` — loading affordances during submit; error display catalogue.
- `admin-import-export` — bulk create / update via file is a related but distinct flow.
- `admin-route-auditor` (agent) — checks for missing server validation, missing dirty warning, fire-and-forget submits.
