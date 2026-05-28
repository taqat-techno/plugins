---
name: admin-import-export
description: Safe admin-side import (CSV / Excel / JSON) and export. Owns the upload → parse → preview → confirm → commit pipeline, the row-cap-by-default rule, the typed-per-row-error contract, the idempotency-via-external-id rule, the no-auto-create-related-entities rule, and the export filename + filter-context convention. Activates when adding any admin import (bulk create / bulk update / migrate) or export (download / report).
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - upload → parse → preview → confirm → commit pipeline
  - row-cap default (10k) + configurable per import
  - typed per-row error report (row index, field, code, message)
  - idempotency via external_id column
  - no-auto-create-related-entities rule
  - dry-run vs commit phases
  - export filename convention (entity + filter context + timestamp)
defers_to:
  - admin-roles-and-permissions (who can import / export, audit-log entries)
  - admin-dangerous-actions (commit phase is destructive when it replaces rows)
  - admin-forms (the upload form itself)
  - admin-states (per-phase progress affordances)
  - project file-upload safety (magic-byte validation, virus scan, storage path)
user_invocable: false
---

# admin-import-export

## Purpose

Imports look easy and corrupt data quietly. A single bad CSV with a stray semicolon can re-shape every record on a table. This skill makes imports survive: preview before commit, cap row count, per-row errors with row + field + code, idempotent by external id, refuse to silently auto-create related entities.

Exports are simpler but still get wrong: missing timezone, filename collisions, leaked filters in the filename. This skill covers the export filename convention too.

## When to use

Activate when:

- Adding any admin import flow (upload CSV / Excel / JSON to create or update many records).
- Adding any admin export flow (download a CSV / Excel / JSON of records).
- Modifying an existing import to add a new column or change parsing.
- Reviewing an admin PR that touches `import`, `bulk_create`, `bulk_update`, `migrate`, `seed`, `export`, `report`, `download`.

Skip when:

- Single-record create (`admin-forms`).
- Bulk update from row selection (`admin-forms` bulk action — does not parse a file).

## Inputs (adapter)

1. **Entity** being imported (its plural name).
2. **Column map** — file column → entity field. Includes type, required, validation.
3. **External-id column** — which file column uniquely identifies a record across runs (the idempotency key). If none exists in the source data, the import generates one.
4. **Row cap** — default 10,000; override per import if justified.
5. **Related entity policy** — when a row references a non-existent related record (e.g., a user row references a team that does not exist), the policy is one of:
   - `error` (default) — row fails with a clear message.
   - `skip` — row is omitted from commit.
   - `create-after-confirm` — only with explicit user confirmation in the preview phase.
   - `auto-create` — **forbidden** without explicit per-import sign-off.
6. **File format** — CSV (most common), Excel (`.xlsx`), JSON. Pick one per import; do not support all three on the same flow.
7. **Audit entries** — `<entity>.import.preview`, `<entity>.import.commit`, `<entity>.export`.

## Read-only investigation steps

Before adding an import:

1. **Where is the schema defined?** Same place the form uses (see `admin-forms`).
2. **Is there already an external_id column on this entity?** If not, decide before building.
3. **What does the API do on a partial-failure batch?** "All-or-nothing" vs "per-row" — they need different UX.
4. **What is the maximum file size the upload endpoint accepts?** Match the row cap to it (e.g., 10k rows × ~500 bytes = ~5 MB).
5. **Are related entities in scope?** If yes, run through the related-policy decision before designing.

## Decision framework

### The pipeline

```
1. UPLOAD         user picks file → magic-byte + size validated → temp storage (server)
2. PARSE          rows + schema mapped → typed errors per row
3. PREVIEW        first N rows + summary + total counts (created / updated / skipped / errored)
4. CONFIRM        user reviews; sees consequence; explicit "Commit N rows" button
5. COMMIT         server applies changes in a transaction or in safe batches
6. REPORT         per-row outcome download + audit-log entry
```

- Phases 1–4 do NOT mutate target data. The user can cancel at any time without effect.
- Phase 5 mutates. Until it runs, nothing changes.
- Phase 6 produces a downloadable per-row report and writes the audit-log entry.

### Row cap (default 10k)

- Hard cap enforced both client-side (reject upload) and server-side (reject parse).
- Cap configurable per import — but every override requires justification in the import's PR description.
- For larger imports, either:
  - **Chunk**: user uploads multiple files, each capped.
  - **Background job**: file is queued, processed async, user is emailed on completion. Different UX, different skill scope.

### Preview shape

```
Preview — first 20 of 1,247 rows

  Row | username    | email                | role     | team_id   | Status
   1  | ahmed.s     | ahmed@example.com    | manager  | engineering | NEW — will be created
   2  | sara.k      | sara@example.com     | viewer   | (missing)   | ERROR — team_id required
   3  | omar.l      | omar@example.com     | admin    | sales       | UPDATE — will overwrite role: viewer → admin
   ...

Summary:
  1,160 new
    42 updates (12 with field changes)
    18 unchanged (idempotent re-import)
    27 errors (cannot commit)

Errors by code:
  team_id_missing            18
  email_format_invalid        7
  role_unknown                2

[ Cancel ]                                              [ Commit 1,220 rows ]
                                                          (errors will be skipped)
```

- The Commit button explicitly states the count (changes if user re-uploads).
- The Commit button label changes based on policy (commit-N, commit-N-skip-errors, commit-N-fail-on-any-error).
- The user can download the preview as a CSV (for offline review of large previews).

### Typed per-row error

Server returns per-row errors with stable codes:

```json
{
  "row": 47,
  "field": "email",
  "code": "email_format_invalid",
  "message": "Email is not a valid address",
  "raw": "ahmed@@example.com"
}
```

- `row` is the 1-indexed row in the source file (matches the user's spreadsheet view).
- `field` is the file's column name (not the entity's internal field name).
- `code` is a stable string for filtering / counting.
- `message` is human-readable; can be i18n-keyed.
- `raw` echoes the offending value (be careful with PII — mask if the field is sensitive).

Errors aggregate in the preview (group by code, show counts). The per-row report (phase 6) is the detailed view.

### Idempotency via external_id

```
external_id, name, role
"sso:ahmed.s",   "Ahmed S",   "manager"
"sso:sara.k",    "Sara K",    "viewer"
```

- The import looks up existing records by `external_id`.
- If found, the row is an **update** (only changed fields written).
- If not found, the row is a **create**.
- Re-running the same file is idempotent: second run shows 0 changes if nothing changed in the source.
- The `external_id` is stored on the entity. Without it, the user cannot safely re-run.

If the source data has no natural external_id, the importer can derive one (e.g., `import-2026-05-28-row-N`) but it must be stable across runs of the same file. Document the derivation.

### No auto-create related entities (default)

```
Row 5: username=ahmad, team_id="engineering"
Status: ERROR — team "engineering" not found
```

NOT:

```
Row 5: username=ahmad, team_id="engineering"
Status: NEW — created team "engineering" and user "ahmad"
```

The second silently creates entities the user did not intend. The first surfaces and refuses.

When auto-create is intentional: the preview phase shows a separate "These records will also be created" section with explicit user confirmation per related entity.

### Commit transaction strategy

| Strategy | When | Note |
|---|---|---|
| All-or-nothing transaction | Small imports (≤ ~1k rows); referential integrity matters | One bad row aborts everything; user sees clear error |
| Per-row with rollback-on-failure | Each row is independent | Failed rows logged; successful rows committed |
| Batched (N at a time) | Large imports | Trade-off: partial commit on failure of a batch, but bounded blast |

The choice is per-import. Default to per-row for ≥ ~1k rows.

### Export filename convention

```
<entity>__<filter-summary>__<YYYY-MM-DD-HHmm>__<actor-id>.<ext>
```

Examples:

```
users__status-active__role-manager__2026-05-28-1430__u-7421.csv
orders__date-2026-05-01_to_2026-05-28__2026-05-28-1431__u-7421.xlsx
audit-log__2026-05-01_to_2026-05-28__2026-05-28-1432__u-7421.csv
```

- `entity` is the plural name.
- `filter-summary` is a kebab-case compaction of the active filters at export time.
- `YYYY-MM-DD-HHmm` is the export's wall-clock in the actor's timezone (the filename's purpose is human, not machine).
- `actor-id` (optional) helps when multiple admins export the same view at the same time.

### Export contents

- Same columns as the visible list by default; respect "include masked PII" only if the actor is allowed AND explicitly opts in (and audit-log on opt-in).
- UTC timestamps in cells if the export is for machine consumption; tz-converted with explicit tz suffix if for human use.
- Header row with field names; consistent with import column map so round-trip works.
- For large exports: stream (chunked) rather than building in memory.

## Safety gates

- **Never** commit on upload. Preview is mandatory.
- **Never** silently auto-create related entities.
- **Never** accept files above the row cap or size cap; reject on both client and server.
- **Never** ship an importer without a per-row error report.
- **Never** write the actor's audit log only on success — write on commit attempt with `outcome: success|partial|failed`.
- **Never** export PII unmasked without an explicit actor opt-in + audit-log entry.
- **Never** put the search query (which may contain a token / email / phone) verbatim in the export filename.
- **Never** include sensitive fields in a preview's `raw` echo (mask first).
- **Never** trust the file's MIME header; validate by magic bytes.

## Validation checklist

Before committing an import or export change:

- [ ] Pipeline phases 1–4 are non-mutating; only phase 5 changes data.
- [ ] Row cap enforced client AND server.
- [ ] Preview shows total counts (new / update / skip / error) + first N rows.
- [ ] Errors grouped by code with counts; per-row report downloadable.
- [ ] External-id strategy documented; re-import is idempotent.
- [ ] Related-entity policy is explicit (`error` / `skip` / `create-after-confirm`); `auto-create` requires sign-off.
- [ ] Commit phase writes audit-log entry with actor / file hash / counts / outcome.
- [ ] Export filename includes entity + filter summary + timestamp.
- [ ] PII opt-in for export is explicit and audited.
- [ ] File magic-byte validated server-side.
- [ ] Large export uses streaming; large import uses chunking or background job.

## Output format

When scaffolding an import, output:

```
ADMIN IMPORT
  Entity: <plural>
  Format: <csv | xlsx | json>
  Row cap: <N>     (default 10000)
  Column map:
    <file col> → <entity field>   [required] [type]
  External-id column: <name>      ← idempotency key
  Related entity policy: <error | skip | create-after-confirm>
  Pipeline: upload → parse → preview → confirm → commit → report
  Audit events: <entity>.import.preview, <entity>.import.commit
```

When scaffolding an export, output:

```
ADMIN EXPORT
  Entity: <plural>
  Format: <csv | xlsx | json>
  Columns: <list> (matches list view)
  Filter context: <list>            ← inlined into filename
  PII masking: <on by default; opt-in to unmask requires audit>
  Streaming: <yes | no>
  Audit event: <entity>.export
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Commit-on-upload | One bad file silently corrupts production | Preview phase mandatory |
| Auto-create related entities | Hidden inserts; user does not see what was created | Refuse; surface; require explicit confirmation |
| Single string error: "import failed" | User cannot find which row | Per-row typed error with code |
| No row cap | Multi-million-row CSV brings down the API | Hard cap enforced both sides |
| Filename `export.csv` for every download | Files clobber in Downloads folder; user loses context | Entity + filter + timestamp |
| Export contains raw PII because the list contains masked PII | Inconsistent treatment of sensitive data | Mask in export too unless explicit opt-in |
| External-id derived from row index | Non-stable across re-uploads; idempotency broken | External id is the source-data key, or derived stably |
| Background job sends "import done" email with the file as attachment | PII over email | Email contains a link to the in-app report |
| Importer trusts file extension only | `.csv` rename of `.exe`, or `.csv` with embedded formulas | Validate magic bytes; strip formula prefixes (`=`, `+`, `-`, `@`) on CSV cell start |

## Portability rationale

The pipeline (upload → preview → confirm → commit) is independent of:

- File format library
- Storage backend (local / S3 / Azure Blob / equivalent)
- Background job runner
- Transaction strategy

The skill does not depend on a specific UI library, validation library, or persistence layer.

## Cross-references

- `admin-roles-and-permissions` — who can import / export; audit shape.
- `admin-forms` — the upload form for phase 1.
- `admin-dangerous-actions` — commit is destructive when it replaces existing rows.
- `admin-states` — per-phase progress affordances (uploading, parsing, committing).
- `admin-crud` — the list the export inherits its filter context from.
- `admin-route-auditor` (agent) — flags missing preview phase, missing row cap, auto-create-on, unmasked PII export.
