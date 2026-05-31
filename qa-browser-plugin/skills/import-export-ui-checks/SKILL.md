---
name: import-export-ui-checks
description: Browser-side QA for admin import (CSV / Excel / JSON upload → preview → commit → result) and export (filter → download → verify). Owns the upload-fixture pattern, the preview-then-cancel pattern (verifies preview-without-commit), the row-cap rejection check, the per-row-error visibility check, the idempotency-via-rerun check, and the export filename + content-shape verification.
version: 0.2.0
last_reviewed: 2026-05-28
owns:
  - upload-fixture pattern (golden file + bad-row file + over-cap file + duplicate-of-existing file)
  - preview-without-commit verification (Pattern 1 — open → preview → cancel)
  - commit verification on a disposable target only (Pattern 2)
  - row-cap rejection check
  - per-row error visibility check (the preview surfaces errors with row/field/code)
  - idempotency via rerun (same file twice → 0 changes the second time)
  - export filename convention check + content-shape check
defers_to:
  - runtime-reality-check (must pass first)
  - browser-qa-discipline (status vocabulary)
  - safe-destructive-testing (commit only on disposable target)
  - modal-and-action-walkthroughs (the upload + commit IS a confirm-pattern flow)
  - console-and-network-capture (capture upload progress + response)
user_invocable: false
---

# import-export-ui-checks

## Purpose

Imports look easy and corrupt data quietly. An import-UI QA pass catches the bugs that hurt most: commit-on-upload (no preview), missing row cap, silent partial failure, missing per-row error visibility, broken idempotency. This skill makes those checks routine.

Exports are simpler but have their own bugs: missing filter context in filename, broken stream on large export, included PII even when "masked" was the requirement.

## When to use

Activate when:

- A change touches an import flow (new entity, new column, new validation).
- A change touches an export flow (new format, new columns, new filter).
- A new admin import is shipped (the first end-to-end QA).
- A bug report mentions import data loss / silent failure / duplicate creation.

## Inputs

- Reality-check passed.
- Role with import / export permission for the entity under test.
- **Upload-fixture set** — a collection of files the QA pass uploads:

  | Fixture | Contents | Expected outcome |
  |---|---|---|
  | `golden.csv` | A handful of valid rows on a disposable entity | Preview shows N new; commit creates N |
  | `bad-rows.csv` | Mix of valid and invalid rows | Preview shows N new + M errors with row/field/code |
  | `over-cap.csv` | Row count above the configured cap | Rejected at upload or parse with clear error |
  | `duplicate-of-existing.csv` | Rows whose external_id matches existing records | Preview shows N updates (not N new) |
  | `idempotency-rerun.csv` | Same as `golden.csv` | After committing `golden.csv` and then re-uploading: preview shows 0 changes |

  Fixtures live under `tests/fixtures/qa-browser/<entity>/` (gitignored if they contain realistic data; checked-in if fully synthetic).

## The upload-preview-commit pattern

### Pattern 1 — Preview then cancel (any fixture, non-destructive)

```
1. Login as a role with import permission.
2. Navigate to the import page for the entity.
3. Upload <fixture>.
4. ASSERT: preview phase reached (no commit yet, no data change in target).
5. ASSERT: preview shows total counts (new / update / skip / error).
6. ASSERT: preview shows first N rows with their classification.
7. ASSERT: for fixtures with errors, errors are grouped by code with counts.
8. Click Cancel.
9. ASSERT: no commit happened (no audit row, no records changed).
```

PASS criteria: preview was rendered; cancel was clean; no data mutation.

### Pattern 2 — Preview then commit (golden / duplicate / idempotency-rerun only; disposable target)

```
1–7 as above.
8. Capture pre-state of the target collection (API count; sample record).
9. Click "Commit N rows".
10. ASSERT: commit fires; progress shown for large fixtures.
11. ASSERT: response is success with per-row outcomes (succeeded / failed).
12. Download or view the per-row report.
13. Capture post-state (API count; sample record; audit query).
14. ASSERT: count delta matches what preview promised.
15. ASSERT: audit-log row appeared for the import action.
```

PASS criteria: commit matched preview; audit present; per-row report downloadable.

## Cap rejection check

Upload the `over-cap.csv` fixture:

```
EXPECT: server returns 4xx with a clear "row cap exceeded" message
   OR: client rejects upload before sending, with the same message

FAIL: server accepts the upload and starts processing (cap missing)
FAIL: server accepts and silently truncates (cap missing AND silently lossy)
```

## Per-row error visibility check

Upload the `bad-rows.csv` fixture:

```
EXPECT: each invalid row appears in the preview with:
  - 1-indexed row number matching the source file
  - the offending field name
  - a stable error code
  - a human-readable message
  - (optionally) the raw value (masked if the field is sensitive)
EXPECT: errors aggregated by code with counts in the preview summary
EXPECT: a downloadable per-row report after commit

FAIL: single-string error "import failed" with no per-row detail
FAIL: errors shown only after commit (preview was useless for triage)
FAIL: raw PII values echoed unmasked
```

## Idempotency check

Two-step:

```
1. Commit `golden.csv`.
2. Wait for the commit to complete (audit row visible).
3. Upload `idempotency-rerun.csv` (same content).
4. ASSERT: preview shows 0 NEW / 0 UPDATE / N UNCHANGED.
5. Click Cancel (no need to commit a no-op).

FAIL: preview shows N NEW (creates duplicates — external_id strategy broken)
FAIL: preview shows N UPDATE (every field "changed" — comparison wrong)
```

## Auto-create-related-entities check

If the entity has relations (e.g., a User row references a Team by name):

```
1. Upload a fixture with a row referencing a non-existent related entity.
2. ASSERT: preview shows ERROR ("Team X not found") — does NOT silently create the Team.

FAIL: preview shows NEW and silently lists the related entity as also-created without explicit confirmation.
```

## Export verification

For each export the admin offers:

```
1. Apply a representative set of filters to the list page.
2. Click Export.
3. Wait for download.
4. Inspect the downloaded file:
   - Filename includes entity + filter context + timestamp (per react-kit/admin-import-export).
   - File parses cleanly in the expected format.
   - Row count matches the list's totalCount.
   - PII fields masked unless the export was an explicit "include PII" opt-in (which writes an audit row).
   - Header row present and matches the import column map (round-trip works).
5. For large exports (>10k rows), confirm streaming did not OOM the browser; first bytes arrived quickly.
```

## Safety gates

- **Never** commit on production. Staging / UAT only.
- **Never** commit using a real entity as the target. Use a disposable entity (test seeded data, a separate tenant, a sandbox project).
- **Never** upload a fixture containing real customer data — even to staging — without an explicit data-handling sign-off.
- **Never** mark PASS for Pattern 2 if the audit row is missing.
- **Never** mark PASS for the export check if the filename is bare (`export.csv`).
- **Never** include exported file paths from another actor in the report (their PII / their filter context).

## Validation checklist

Before sending an import-export report:

- [ ] Reality-check PASS row.
- [ ] Pattern 1 ran for every fixture (preview verification).
- [ ] Pattern 2 ran on disposable data only.
- [ ] Cap rejection check ran.
- [ ] Per-row error visibility check ran.
- [ ] Idempotency check ran (`golden.csv` committed → `idempotency-rerun.csv` previewed as 0 changes).
- [ ] Auto-create check ran if the entity has relations.
- [ ] Export filename + content verified.
- [ ] No real customer data in fixtures.
- [ ] No PII visible in screenshots.

## Output format

```
IMPORT / EXPORT CHECKS — <env-name> — <date> — entity=<plural>

[PASS] reality-check

IMPORT — Pattern 1 (preview then cancel)
  [PASS] golden.csv                     <preview rendered; no commit>
  [PASS] bad-rows.csv                   <errors grouped; row/field/code visible>
  [PASS] over-cap.csv                   <rejected at upload>
  [PASS] duplicate-of-existing.csv      <preview showed N updates, not N new>

IMPORT — Pattern 2 (preview then commit; disposable)
  [PASS] golden.csv                     <commit; audit row present; count delta correct>

IMPORT — idempotency
  [PASS] rerun                          <0 changes shown in preview>

IMPORT — auto-create check
  [PASS] related-missing.csv            <error surfaced; no silent create>

EXPORT
  [PASS] users — filters [status=active] — filename users__status-active__2026-05-28-1430.csv
  [FAIL] orders — filename was orders.csv (missing filter context + timestamp)
    Severity: LOW

SUMMARY
  Checks: <N>
  PASS: <n>   FAIL: <n>
  Highest-severity finding: <link>
  Recommended action: <top fix>
```

## Anti-patterns (and why)

| Anti-pattern | Why it's wrong | Correct |
|---|---|---|
| Commit `bad-rows.csv` to see what happens | Pollutes the database with bad data | Preview phase tells you; do not commit bad data |
| Upload a fixture containing real customer rows | Real PII in test pipeline | Use fully synthetic fixtures |
| Pattern 2 against a real entity as target | Real data destroyed / changed | Disposable target only |
| Skip the idempotency check | Most common import bug; duplicates created on re-upload | Always check |
| Trust the preview's count without sampling a row | Preview can lie if the parser is buggy | Sample at least one row's expected outcome |
| Export check looks at "did the file download" only | Filename / content / streaming issues missed | Verify filename + content + size |
| Run import on production "to verify it works there" | Production data is not test data | Stage / UAT only |
| Mark the audit-log gap as "minor" | Compliance failure | HIGH severity |

## Portability rationale

The upload-preview-commit pattern applies to any import flow that follows the contract from `react-kit/admin-import-export` (or equivalent). The skill does not depend on:

- A specific file format (CSV / Excel / JSON all work)
- A specific upload library
- A specific server framework

## Cross-references

- `runtime-reality-check` — required first.
- `browser-qa-discipline` — status vocabulary.
- `safe-destructive-testing` — Pattern 2 commit + disposable target rule.
- `modal-and-action-walkthroughs` — the upload-commit flow IS a confirm pattern.
- `console-and-network-capture` — capture upload progress, commit response, error payloads.
- `uat-readiness-report` — import / export rows feed the final report.
- `react-kit/admin-import-export` — the contract this skill verifies against.
