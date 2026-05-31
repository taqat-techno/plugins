# Admin form pattern

A reusable pattern for create/edit admin forms in any domain. It covers grouped sections and tabs, inline plus server validation, dirty-state warn-on-leave, the save/cancel/reset/archive/delete flow, read-only versus editable by permission and state, relation pickers with async search, file and attachment inputs, and audit-metadata display. Throughout, the neutral entity is a `Record` (e.g. a Customer or a Product). No business logic is assumed — substitute your own entity, fields, and roles.

## Core principles

- Keep the page component thin: it routes, loads the entity (edit mode), shows loading/error states, and delegates all field logic to a composable form component.
- The form component owns fields, validation, and the action flow. It accepts an optional entity (`null` = create mode) and derives `isEdit = entity != null`.
- Commit only on explicit user action. Never auto-save on blur or on every keystroke.
- Drive presentation (page vs dialog, section vs tab) and access (read-only vs editable) from props and computed state, never from hardcoded conditions baked into fields.

## Layer responsibilities

| Layer | Owns | Must not do |
|---|---|---|
| Page / route | Navigation, loading and error UI, permission gate, passing initial data | Hold field state or build payloads |
| Form component | Field state, validation, save/cancel/reset flow, action callbacks | Fetch the entity itself, route directly |
| Data hook | Create/update/archive/delete calls, cache invalidation, error surfacing | Render UI or own field state |
| Field components | One input concern each (text, relation, file, rich text) | Know about the overall entity |

## Form layout: grouped sections and tabs

Group related fields into labeled sections so a long form stays scannable. For entities with many fields, promote top-level groups to tabs.

- Prefer **sections** (a titled fieldset with a short caption) when the whole form fits comfortably on one screen.
- Promote to **tabs** when groups are independent and the form is long (e.g. General, Details, Relations, Attachments, Audit).
- Each section/tab is a presentational container only — it never owns validation. Validation belongs to the form.
- Show a per-tab indicator (dot or count) when a tab contains invalid or required-but-empty fields, so users do not miss errors hidden on another tab.

Example (illustrative — not required): a Customer form with tabs `Profile` (name, status), `Contacts` (repeating rows), `Attachments` (files), `Audit` (read-only metadata).

## Field state and modes

- Initialize state from the entity in edit mode, or from defaults in create mode. Sync entity → form state when the loaded entity changes, then leave it under user control.
- Track the initial snapshot so dirty state and reset both have a reference point.
- Title and primary action label follow the mode: create shows "Create Record" / "Save"; edit shows "Edit Record" / "Save Changes".

| Mode | Detected by | Initial state | Primary action |
|---|---|---|---|
| Create | entity is null | defaults / empty | Create Record |
| Edit | entity present | entity field values | Save Changes |

## Validation: inline and server

Use two complementary layers. Neither replaces the other.

- **Inline (client) validation** is for immediate, cheap feedback: required fields present, formats well-formed, dependent relations satisfied. Compute a derived `isValid` and disable the primary action until `isValid && !isPending`.
- **Server validation** is authoritative. On submit, send the payload and surface returned field errors next to their fields, plus a form-level message for non-field errors.
- Validate on submit, not on every character. Optionally validate a field on blur after first submit attempt.
- Do not block the form on a server error — re-enable inputs so the user can correct and retry. Never clear inputs on error.

| Validation layer | When it runs | On failure |
|---|---|---|
| Inline / client | As fields change; gates the submit button | Disable primary action, show inline hints |
| Server | On submit | Map field errors inline, show form-level error, keep inputs |

## Dirty state and warn-on-leave

- Track `isDirty` by comparing current values to the initial snapshot.
- Surface dirty state in the UI: enable the primary action only when `isDirty` (and valid); optionally show an unsaved-changes marker.
- Register a before-unload / navigation guard that warns the user only when `isDirty`. Skip the warning entirely when the form is clean or after a successful save.
- Do not persist dirty state across navigation; reset it on successful save.

## Action flow: save, cancel, reset, archive, delete

| Action | Precondition | Effect | Confirmation |
|---|---|---|---|
| Save | valid and dirty and not pending | Build payload, run create/update, invalidate cache, fire onSuccess | None |
| Cancel | always | Discard local edits, fire onCancel (usually navigate back) | Confirm only if dirty |
| Reset | dirty | Revert all fields to the initial snapshot | Optional confirm if many edits |
| Archive | edit mode, permitted | Soft state change (reversible), keep the record | Confirm |
| Delete | edit mode, permitted | Hard removal (irreversible) | Required, type-to-confirm for high-value records |

- Keep archive (reversible) distinct from delete (irreversible). Prefer archive as the default destructive action and gate delete behind stronger confirmation.
- On save success, navigate or close rather than re-rendering an empty form. Let navigation handle cleanup.

## Read-only vs editable by permission and state

A field's editability is the AND of two gates: the user has permission, and the entity state allows it.

- **Permission gate:** check capability (e.g. `canUpdate`, `canDelete`) before rendering editable controls. Without write capability, render values read-only and hide destructive actions.
- **State gate:** some fields are immutable after creation (e.g. a key that other records reference) or locked once the record enters a terminal state. Render these read-only in edit mode and show the current value as static text or a badge.
- A viewer-level role sees everything read-only; an operator can edit permitted fields; a manager or admin additionally sees archive/delete.

| Role | View | Edit fields | Archive | Delete |
|---|---|---|---|---|
| viewer | yes | no | no | no |
| operator | yes | yes (non-locked) | no | no |
| manager | yes | yes | yes | yes |
| admin | yes | yes | yes | yes |

Disable, do not hide, an action the user could plausibly expect — and explain why (tooltip: "locked after creation", "requires manager"). Surface a permission error from the server as a clear "Permission denied" message rather than a silent failure.

## Relation pickers (async search)

For foreign-key / many-to-one fields, use a searchable async picker; for hierarchical relations use a tree picker that indents by level.

- Fetch options on demand and debounce search input; do not refetch the full list on every render.
- Show distinct states: placeholder ("Select Record"), loading (spinner, disabled), populated (selected label), open (focused search, filtered list, keyboard navigation with arrow keys and Enter), disabled (dimmed, not clickable).
- **Cascade clear:** when a parent relation changes, clear dependent child selections so the form never holds an inconsistent combination.
- Prevent circular relations in hierarchical pickers (a record cannot be its own ancestor).
- If a relation is immutable in edit mode (state gate above), disable the picker and show the current value as a badge.

## File and attachment inputs

- **Enforce limits up front:** allowed types, max file size, and max count. Reject invalid files at selection with a clear message.
- **Preview before commit:** show selected files (thumbnail for images, name + size for others) and allow removal before the form is submitted.
- **No pre-save commit:** do not upload to permanent storage on selection. Stage files in form state and send them only when the user saves. If a staged upload step is unavoidable, treat it as temporary and clean up on cancel.
- Show per-file progress and error state during the save upload; on save failure, keep the staged files so the user can retry.

| Constraint | Enforced where | On violation |
|---|---|---|
| Allowed types | At selection (client) + server | Reject with message, do not stage |
| Max size | At selection (client) + server | Reject with message |
| Max count | At selection (client) | Block adding beyond limit |
| Commit timing | On save only | — |

## Repeating field arrays

For variable-length sub-records (e.g. contact rows, links), keep an array in form state with add / remove / update handlers.

- Each row is inline-editable with its own inputs and a remove control. Use stable keys (IDs) where possible, index otherwise.
- Filter out empty rows before building the payload; never serialize sparse or null entries.
- Provide a sensible visible limit and confirm removal only for high-value rows. Do not require confirmation for every delete.
- Drag-to-reorder belongs on list views, not inside a form field unless order is itself meaningful data.

## Audit metadata display

Show provenance fields read-only — they are never user-editable.

- Display created-by, created-at, updated-by, updated-at, and version where available.
- Render in a dedicated read-only section or an "Audit" tab, clearly separated from editable fields.
- Use absolute plus relative time (e.g. a timestamp with a "2 days ago" hint) and resolve actor IDs to names.
- Never include audit fields in the editable payload; they are server-managed.

## Page vs dialog layout

The same form component should serve both a full page and a modal via a single layout prop.

- `layout="page"`: wider container, full-width inputs, taller rich-text editors, room for tabs.
- `layout="dialog"`: compact spacing, narrower controls, shorter editors; favor sections over tabs.
- The wrapper (page or modal) controls outer padding and width; the form fills its container. Do not hardcode padding inside fields — let the layout mode drive spacing.

## Anti-patterns

- Inlining form/field logic in the page component, or fetching the entity inside the form.
- Auto-saving on blur or on every keystroke; auto-validating live against the server.
- Disabling the entire form on error — disable only the primary action while pending, and re-enable on error so the user can retry.
- Clearing inputs after a failed save.
- Committing file uploads to permanent storage before the user saves.
- Leaving a dependent relation populated after its parent changed.
- Hiding (rather than disabling-and-explaining) an action the user expects, or letting a permission error fail silently.
- Conflating archive (reversible) with delete (irreversible), or skipping confirmation on irreversible actions.
- Hardcoding page-vs-dialog spacing instead of driving it from the layout prop.
