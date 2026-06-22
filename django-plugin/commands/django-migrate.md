---
description: Run the safe Django migration workflow — makemigrations, review the generated SQL, check reversibility, then apply — with zero-downtime sequencing for risky changes against live data. Refuses to blindly auto-apply.
argument-hint: "[app] [--make] [--apply] [--plan] [--check]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# /django-migrate — Safe migration workflow

You drive Django migrations through the safety gate from the `django-migrations` skill. You do **not** run `migrate` until the generated migration has been read and its SQL inspected. Apply `django-migrations` (sequencing/reversibility) and, for backfills, `django-orm-models` (historical model) and `django-performance` (batching).

## Step 0 — Context

Read `.django-kit.local.json` for `managePrefix`, `dbBackend`, `settingsModules`. If absent, detect them yourself (read-only): locate `manage.py` and its invocation prefix, the database backend, and the settings modules. Determine whether the target DB has real/live data (ask if unknown) — that decides whether zero-downtime sequencing is mandatory.

## Modes

- **`--check`** (default if nothing else given) — run `<managePrefix> makemigrations --check --dry-run`. Report whether models and migrations are in sync. Makes no files.
- **`--make`** — create migrations, then **stop and review** (do not apply).
- **`--plan`** — show `<managePrefix> showmigrations --plan` (or `migrate --plan`): what is unapplied and in what order. Read-only.
- **`--apply`** — apply, but only after the review gate below has passed in this session.
- No mode → run `--check`, then offer the next step.

## The gate (for `--make` / `--apply`)

1. **Make:** `<managePrefix> makemigrations [app]`. List the files created.
2. **Read every generated migration file.** Confirm the operations match intent — flag any unexpected operation (a stray field change, a `RenameField`, a data-loss `RemoveField`).
3. **Inspect SQL:** `<managePrefix> sqlmigrate <app> <number>` for each. Identify locking operations (index creation, `NOT NULL` add, constraint add, FK add, type change) and table-rewrite risks for the detected backend.
4. **Reversibility check:** every `RunPython` must have `reverse_code` (or explicit `noop`); flag any that don't. Confirm schema ops are reversible.
5. **Risk classification:**
   - **Safe** (additive nullable column, new table, new index on small table) → apply.
   - **Risky against live data** (rename, drop, `NOT NULL` retrofit, type change, index on large table) → produce an **expand-contract step plan** instead of applying in one shot. Map each migration to a deploy phase, name the lock each takes, and give the rollback. Get explicit confirmation before applying any phase.
6. **Apply** (only `--apply`, only after the above): `<managePrefix> migrate [app]`. Then confirm with `showmigrations` and, on a scratch/staging DB where possible, verify the down-migration.

## Data migrations / backfills

If a migration backfills data:

- Confirm it uses `apps.get_model(...)` (historical model), not a direct import.
- Confirm it is a **separate** migration from the schema change.
- For large tables, require batching/throttling (chunk by PK, `bulk_update` per chunk) per `django-performance` — do not run an unbatched `update()` over a huge table.

## Refusals & guards

- Never suggest `migrate --fake` to resolve drift unless the schema is *proven* to match; if you do, state the proof.
- If a `RenameField` / column drop / `NOT NULL` add is proposed against live data with no expand-contract plan, stop and produce the plan first.
- The plugin's migration-safety hook may also flag these on write — treat its output as confirmation, not noise.

## Report

```
MIGRATION RUN  (app: orders)
  Made:        0003_order.py
  SQL review:  CREATE TABLE (safe) · CREATE INDEX CONCURRENTLY (non-atomic, ok)
  Reversible:  ✅
  Risk:        SAFE — applied
  Applied:     ✅  (showmigrations confirms 0003 applied)
```

For risky changes, output the phased step plan and the per-phase rollback instead of an "applied" line, and stop for confirmation.
