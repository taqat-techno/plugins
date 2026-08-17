---
name: admin-forms
description: Admin form patterns — field components, validation, save / cancel / dirty handling, rich-text (ProseMirror / Tiptap) fields, row actions, bulk actions, optimistic vs pessimistic update, prop-derived-state hardening. Owns the "client validation mirrors server, server is authoritative" rule, the dirty-state warn-on-leave pattern (derive dirty from the form's OWN change handlers — never by DOM-sniffing a wrapper's onInput/onChange, never from an on-mount onValuesChange; guard the browser Back button with a popstate sentinel-history entry; portal editor dialogs out of a sticky/stacking-context toolbar via createPortal(dialog, document.body)), the "state initialized from a prop does not re-init when the prop changes" pitfall (sync via effect or keyed remount), and the bulk-action batching contract. Activates when building or reviewing any admin form, edit page, rich-text / ProseMirror / Tiptap field, unsaved-changes / beforeunload / popstate guard, row action, or bulk action, or when unsaved edits are silently lost. Generic and portable — form library and field types are project-supplied.
version: 0.5.0
last_reviewed: 2026-07-23
owns:
  - field-component-per-type pattern
  - client-side validation mirrors server-side
  - submit / dirty / cancel flow
  - row-action and bulk-action contract
  - optimistic-update reconciliation rule
  - sections / tabs split for long forms (one form, one save)
  - read-only vs editable field resolution (permission + state)
  - relation-picker behavior (async search, cascade clear, create-related guardrails)
  - file / attachment staging (no auto-commit before save)
  - archive / delete / reset flow distinct from save / cancel
  - audit-metadata read-only display
  - dirty derived from the form's own change signal (not DOM-sniffing a wrapper, not an on-mount onValuesChange)
  - unsaved-changes guard across beforeunload AND the browser Back button (popstate sentinel-history entry)
  - editor dialogs portaled out of a sticky / stacking-context toolbar (createPortal to document.body)
  - prop-initialized state re-sync (effect sync or keyed remount)
defers_to:
  - admin-roles-and-permissions (which fields the actor can edit; per-action authorization)
  - admin-dangerous-actions (confirmation flow for destructive submits)
  - admin-states (loading / error / success affordances during submit)
  - project validation library (zod, yup, joi, valibot, hand-rolled — all work)
user-invocable: false
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

### Dirty state for rich-text and portal fields

The dirty flag is only honest if it observes every edit. Two derivation mistakes silently break it — one loses the actor's work, one nags on a form they never touched.

**Derive dirty from the form's OWN change signal, not from DOM sniffing.** Wrapping the form in a `<div onInput onChange>` and treating any bubbled event as "edited" misses every edit that does not surface as a DOM input/change event on that wrapper:

- **Rich-text toolbar commands.** A ProseMirror / Tiptap command (bold, heading, list, link, **image-insert**) mutates the document through the editor's transaction API — it fires no DOM `input`/`change` on the wrapper. **Paste**, **drop**, and drag-reorder inside the editor are the same.
- **Portaled picker changes.** A Radix (or any) Select / Combobox / DatePicker renders its listbox in a portal at `document.body`, OUTSIDE the form's DOM subtree — its change never bubbles up to the wrapper, so a field the actor demonstrably changed reads as clean.

The result is the worst failure mode: the guard never arms, the actor navigates away, and the edit is gone with no warning — **silent data loss**. Instead, derive dirty from each field's real change source — the editor's own update callback (Tiptap `onUpdate`, ProseMirror's dispatch), the form library's `watch` / `onChange`, the picker's `onValueChange` — and compare current values against the initial snapshot (the reference's snapshot-compare rule).

**Never fire dirty from an on-mount `onValuesChange` (phantom-dirty).** Several form libraries emit one `onValuesChange` / `onChange` during mount or hydration carrying the INITIAL values. Marking the form dirty on that first emission arms the unsaved-changes guard on a form the actor never touched — every clean edit page then blocks navigation with a false "discard changes?". Gate dirty on an actual diff against the initial snapshot, or ignore the first emission; never treat "a value event fired" as "the actor edited".

**Guard the browser Back button, not just unload.** `beforeunload` fires on tab-close, reload, and hard navigation — it does NOT fire on an in-app client-side Back (SPA router history pop). A dirty form guarded only by `beforeunload` loses data on Back. Push a **sentinel history entry** when the form becomes dirty, listen for `popstate`, and on a pop while dirty run the same confirm; if the actor cancels the leave, **re-push the sentinel** so the next Back is caught too.

**Portal editor dialogs out of a sticky toolbar.** A `position: sticky` toolbar (also any `transform`, `filter`, `opacity < 1`, or `z-index` applied to it) establishes a new stacking context. An editor dialog rendered as a DOM child of that toolbar — link editor, image picker, emoji/mention menu — is trapped inside the context: it clips at the toolbar bounds and paints under adjacent content regardless of its own `z-index`. Render it with `createPortal(dialog, document.body)` so it escapes the toolbar's stacking context and layers above the page.

### State initialized from a prop does not re-init

`useState(props.value)` — or any state seeded from a prop / loaded entity — reads that prop ONLY on the component's first render. When the prop later changes (the parent loads a different record into the same mounted form, a selection swaps the entity), the state keeps the STALE first value and the form shows the old record's data over the new one. This is a genuine bug, distinct from the linter's "don't sync props into state" hint, which is often a false positive for an intentional snapshot — see `react-lint-triage`.

Two correct fixes; pick by how much should reset:

- **Keyed remount** — give the form a `key` that changes with the record's identity (`<RecordForm key={record.id} … />`). React unmounts and remounts on a new key, so ALL state (including the dirty snapshot) re-initializes from the new prop. Prefer this when a new entity should blow away every field.
- **Effect sync** — when only some fields track the prop, re-seed them in an effect keyed on the prop, then leave them under user control (the reference's "sync entity → form state when the loaded entity changes, then leave it under user control").

Do not "fix" this by making the field fully controlled off the prop — that discards the actor's in-progress edits on every parent render.

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

### File / attachment inputs

- Show file size before upload starts; reject above limit before sending.
- Enforce both type and size limits client-side AND server-side. Validate MIME by magic bytes server-side (extension is not enough).
- Show progress bar on upload.
- After staging, show preview where possible (image thumb, document first page, file icon otherwise).
- **No auto-commit before save.** Selecting / staging a file is part of the dirty form state — it must not persist on the server until the form's explicit save. If your storage requires a pre-upload (e.g., to a temp/staging bucket), the *record* still does not reference the file until save succeeds; orphaned staged files are cleaned up out-of-band, never auto-attached.
- On replace: confirm "Replace existing file?" if a file is already attached. Removal of an existing attachment is a dirty-state edit, committed on save — not an immediate destructive action.

### Sections and tabs (long forms)

Short forms (≤ ~8 fields) are a single flat list — do not over-structure them. Split only when length or grouping genuinely helps the actor.

| Structure | When to use | Notes |
|---|---|---|
| Flat list | Few fields, one logical group | Default. No headings needed. |
| Grouped sections | One long form, fields fall into 2–4 clear groups (e.g., "Details", "Contact", "Settings") | Section headings on one scrolling page; all fields submit together as one record. |
| Tabs | Many fields across distinct concerns, or the actor rarely touches all of them at once | One form, multiple tabs; **still one save**. |

Rules when splitting:

- **One form, one save.** Sections and tabs are presentational grouping — they do not become separate forms or separate submits unless the project explicitly models them as separate records.
- **Dirty state spans all sections/tabs.** A change on tab 1 must keep the single Save active and must not be lost when the actor switches to tab 2.
- **Surface errors across hidden tabs.** On submit, if a field on a non-active tab fails validation, mark that tab (badge / dot) and focus the first invalid tab — never leave the actor staring at a valid-looking tab while save silently fails.
- **Do not lazy-discard.** Switching tabs must not unmount and reset field state for the inactive tab.

### Read-only vs editable fields

A field's editability is decided by two independent axes; resolve both before rendering:

1. **Permission** — may this actor edit this field at all? This is authorization. **Defer to `admin-roles-and-permissions`** for who-can-edit-what and PII masking. The form only *consumes* the resolved per-field decision; it does not invent its own role logic.
2. **State** — is this field editable in the record's *current* state? Some fields are immutable after creation (an identifier, an immutable relation), or locked once the record reaches a terminal/processed state.

Rendering rules:

- A field the actor cannot edit renders **read-only** (shown as a value/badge), not as a disabled-but-present input that hints it could be edited.
- Read-only fields are **excluded from the submit payload** — never send a value the actor was not allowed to change.
- A field that is editable-for-this-actor but locked-by-state shows the value plus a short reason ("locked after processing"), not a silent disabled input.
- Do not gate on the client alone. The server re-checks both axes on submit; client read-only is ergonomics, not the boundary (same rule as validation).

### Relation pickers

A field that selects a related record (single or multiple). Project supplies the picker component; this skill owns the behavior.

- **Async search.** Above a small option count, do not preload every option — search server-side as the actor types. Debounce input, show a loading affordance, and never block the rest of the form while options load.
- **Dependent / cascading relations.** When a parent selection narrows a child's options, changing the parent **clears the dependent child** rather than leaving a now-invalid value. Cascade clears downward through the chain.
- **Immutable relations.** A relation that cannot change after creation (or after a state transition) renders read-only per the rules above — show the current value as a badge, disable the picker.
- **Create-related guardrails.** A "create new related record" affordance inside a picker is convenient but dangerous:
  - It must respect the actor's permission to create that related record (defer to `admin-roles-and-permissions`).
  - The newly created related record is itself a real write — confirm it the same as any create, do not silently persist it as a side effect of editing the parent.
  - Never let inline-create produce orphaned/half-valid related records if the parent form is then cancelled. Either the related record is fully valid on its own, or its creation is deferred until parent save.
- **No circular relations.** A picker must not allow selecting the record itself (or an ancestor) as its own relation.

### Archive / delete / reset (distinct from save / cancel)

Save and cancel manage the *edit*. Archive, delete, and reset act on the *record or the form* and must be visually and behaviorally separate from the primary Save / Cancel pair.

| Action | Acts on | Reversible? | Routing |
|---|---|---|---|
| **Save** | Pending edits → record | n/a | Primary submit (above) |
| **Cancel** | Pending edits (discards) | yes (re-edit) | Confirm if dirty |
| **Reset** | The *form*, back to last-saved baseline | yes | Confirm if dirty; does **not** touch the server |
| **Archive** | The *record* (soft, recoverable) | yes (unarchive) | Destructive-lite → confirm |
| **Delete** | The *record* (hard, often irreversible) | usually no | **Defer to `admin-dangerous-actions`** |

Rules:

- **Reset ≠ Cancel.** Reset reverts the form's fields to the loaded baseline and stays on the page (actor keeps editing); Cancel leaves. Reset never calls the server.
- **Destructive actions are not the Save button's siblings in prominence.** Place Archive / Delete apart from Save / Cancel (e.g., a separate menu or a "danger zone"), so they are not fat-fingered.
- **Confirmation for destructive submits is owned by `admin-dangerous-actions`** — this skill routes to it and does not re-implement the confirmation UX.
- A destructive action on a dirty form must tell the actor their unsaved edits will be lost (or are irrelevant, for delete) before proceeding.

### Audit metadata display

Most records carry provenance: who created/updated them and when. Display it, read-only.

- Show **created by / created at** and **updated by / updated at** (and last-action actor if the project tracks it) in a clearly read-only region — a footer strip or a side panel, never as editable inputs.
- Render timestamps in the actor's timezone; store/transport UTC (consistent with the datetime field rule).
- Audit metadata is **never** part of the submit payload and is **never** editable from the form, regardless of the actor's permission level.
- If the record is new (create mode), audit metadata is absent — do not render empty "created by —" placeholders.

## Safety gates

- Never submit credentials, OTPs, or tokens via a form that browser autocomplete can capture (`autocomplete="off"` on sensitive fields; specific autocomplete tokens otherwise).
- Never echo a sensitive field value back into the URL on validation failure (form remembers field state in component, not URL).
- Never silently truncate field values to fit a column limit — surface the limit to the user.
- Never auto-save destructive changes (no autosave on "delete reason", no autosave on settings that disable features).
- Never accept a file upload above the configured cap; reject client-side AND server-side.
- Never apply a bulk action without an explicit "I am about to affect N records" affordance.
- Never derive the dirty flag by DOM-sniffing a wrapper's `onInput`/`onChange` — rich-text commands, paste/drop/image-insert, and portaled picker changes do not bubble there and are lost.
- Never arm the unsaved-changes guard from an on-mount `onValuesChange` emission — diff against the initial snapshot so a pristine form does not block navigation.
- Never rely on `beforeunload` alone for a dirty form — it does not fire on an in-app Back; add a `popstate` sentinel-history guard.
- Never render an editor dialog inside a `sticky` / stacking-context toolbar — portal it to `document.body` with `createPortal`.
- Never seed form state with `useState(prop)` and assume it re-initializes when the prop changes — re-sync via effect or remount with a `key`.

## Validation checklist

Before committing a form change:

- [ ] Server-side validation exists and is the security boundary.
- [ ] Client-side validation matches the server schema.
- [ ] Field-level errors render next to the field.
- [ ] Global error summary at the top when any error exists.
- [ ] Dirty state tracked; cancel and beforeunload warn.
- [ ] Dirty is derived from each field's own change source (editor `onUpdate`, form `watch`, picker `onValueChange`) vs the initial snapshot — not from DOM-sniffing a wrapper, not from an on-mount `onValuesChange`.
- [ ] The unsaved-changes guard covers the browser Back button (a `popstate` sentinel-history entry re-pushed on cancel), not only `beforeunload`.
- [ ] Rich-text / editor dialogs render via `createPortal(dialog, document.body)`, not inside a sticky / stacking-context toolbar.
- [ ] Form state seeded from a prop/entity re-initializes when that prop changes (effect sync or keyed remount).
- [ ] On success, form resets to saved values; dirty cleared.
- [ ] Submit button disabled while in flight; double-click cannot double-submit.
- [ ] Optimistic updates (if any) reconcile with server response.
- [ ] Sensitive fields are masked; `autocomplete` set conservatively.
- [ ] Row actions: destructive go through `admin-dangerous-actions`.
- [ ] Bulk actions call a batch endpoint with per-item progress + per-item failure report.
- [ ] Long forms split into sections/tabs still submit as one record; errors surface across hidden tabs.
- [ ] Read-only fields render as values (not disabled inputs) and are excluded from the submit payload.
- [ ] Relation pickers search async, cascade-clear dependents, and gate inline-create on permission.
- [ ] File/attachment selection does not auto-commit before save; removal is a dirty-state edit.
- [ ] Archive/delete/reset are separated from Save/Cancel; destructive ones route through `admin-dangerous-actions`.
- [ ] Audit metadata (created/updated by/at) is read-only and never in the payload.
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
| File auto-attached to the record on selection | Cancelling the form leaves an orphaned/committed file | Staging only; attach on save |
| Read-only field rendered as a disabled input | Hints it could be edited; may still ride along in payload | Render as a value/badge; drop from payload |
| Each tab is its own form with its own save | Dirty state and validation fragment; partial saves | One form, one save; group presentationally |
| Submit succeeds-looking while an error sits on a hidden tab | Actor can't find the broken field | Badge the failing tab and focus it |
| Reset wired to the Cancel/leave action | Actor loses the page when they wanted to revert in place | Reset reverts fields and stays; never calls server |
| Inline "create related" persists silently on parent save | Orphaned/half-valid related records | Confirm the create; defer or fully validate it |
| Audit fields shown as editable inputs | Actor can rewrite provenance | Read-only region; never in payload |
| Dirty flag derived by DOM-sniffing a wrapper `onInput`/`onChange` | Toolbar commands, paste/drop/image-insert, and portaled picker changes don't bubble there — edits lost with no unsaved warning | Derive dirty from each field's own change signal vs the initial snapshot |
| Firing dirty from an on-mount `onValuesChange` | Marks a pristine form dirty; every clean edit page blocks navigation | Diff against the initial snapshot; ignore the first mount emission |
| Only a `beforeunload` guard on a dirty form | An in-app Back (SPA history pop) doesn't fire beforeunload; edits lost on Back | Add a `popstate` sentinel-history guard, re-pushed if the leave is cancelled |
| Editor dialog rendered inside a `sticky` toolbar | The toolbar's stacking context clips/traps the dialog under the page | `createPortal(dialog, document.body)` |
| `useState(prop)` assumed to re-init when the prop changes | State keeps the stale first value; the form shows the old record | Re-sync via effect, or remount with a `key` |

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
- `react-lint-triage` — the linter's "don't sync props into state" hint is often a false positive (intentional form-reset / snapshot); this skill owns the inverse genuine bug — prop-seeded state that never re-inits when the prop changes.
- `admin-route-auditor` (agent) — checks for missing server validation, missing dirty warning, fire-and-forget submits.
- `references/admin-form-pattern.md` — the worked reference for the form-view pieces above (sections/tabs split, read-only resolution, relation-picker behavior, file staging, archive/delete/reset routing, audit-metadata display). Consult it when implementing a concrete form.
