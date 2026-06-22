---
name: django-migrations
description: Safe Django migration workflow and zero-downtime schema-change sequencing — makemigrations/migrate discipline, reversibility, data migrations (RunPython with a reverse), splitting schema vs data, and the multi-deploy patterns for adding/renaming/dropping columns without breaking a running app. Activates when creating/editing a migration, running makemigrations or migrate, reviewing a migration diff, planning a schema change against a live database, or diagnosing a migration conflict/drift. Owns the migration-safety gate; defers model field choices to django-orm-models.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - the makemigrations -> review -> migrate gate (never auto-trust a generated migration)
  - reversibility rule (every migration must be reversible; RunPython needs a reverse_code)
  - schema-vs-data split rule (one concern per migration; data migrations are separate)
  - zero-downtime / expand-contract sequencing for add / rename / drop / type-change
  - migration-conflict & drift resolution (--merge, squashmigrations, --fake hazards)
  - locking-risk rules (operations that take ACCESS EXCLUSIVE / rewrite a table)
defers_to:
  - django-orm-models (what the field/constraint/index should be)
  - django-performance (whether a backfill needs batching/throttling)
  - project deploy pipeline (how/when migrate runs relative to code rollout — adapter input)
user_invocable: false
---

# django-migrations

## Purpose

A generated migration is a *proposal*, not a verified change. The dangerous ones look identical to safe ones in the diff — a column rename, a `NOT NULL` add, and a type change all read as one tidy operation but behave very differently against a table with live traffic. This skill owns the workflow gate and the sequencing patterns that keep schema changes from locking the table or breaking the previous code version mid-deploy.

## When to use

Activate when:

- Running `makemigrations` or `migrate`, or about to.
- Creating, editing, or reviewing a migration file.
- Planning a schema change against a database that has real data / live traffic.
- A data backfill is needed (populate a new column, transform existing rows).
- Hitting a migration conflict, "inconsistent history", or model/migration drift.

Do NOT use to decide the field/constraint itself (→ `django-orm-models`) or how to batch a huge backfill efficiently (→ `django-performance`).

## Inputs (adapter)

1. **Database backend** — Postgres locking semantics differ from MySQL; SQLite rewrites the whole table for most `ALTER`s (and runs migrations in a single transaction).
2. **Deploy model** — single-instance vs rolling deploy, and whether `migrate` runs *before* or *after* new code is live. This decides whether expand-contract is mandatory.
3. **Table sizes** — "live traffic on a large table" is the trigger for the zero-downtime patterns; a tiny table can take the simple path.
4. **`manage.py` invocation** — the project's command prefix (e.g. `python manage.py`, `poetry run ./manage.py`, container exec).

## The gate (never skip)

1. **`makemigrations`** → it writes a file.
2. **Read the generated file.** Every time. Confirm the operations match your intent and nothing unexpected was picked up (a stray model change, a reordered field).
3. **`makemigrations --check --dry-run`** in CI to fail builds where models changed but no migration was committed.
4. **`sqlmigrate <app> <number>`** to see the exact SQL before running it against anything that matters.
5. **`migrate`** — apply. Then verify reversibility: `migrate <app> <previous>` on a scratch DB should cleanly roll back.

## Reversibility rule

Every migration must be reversible.

- Schema operations are auto-reversible. **`RunPython` is NOT** unless you supply `reverse_code`. If a data step genuinely can't be reversed, pass `migrations.RunPython.noop` *explicitly* — that's a documented decision, not an accident.
- Never write business logic against your live model classes inside a data migration. Use the historical model via `apps.get_model("app", "Model")` — the real model may have moved on by the time the migration runs.

```python
def forwards(apps, schema_editor):
    Order = apps.get_model("shop", "Order")          # historical model
    Order.objects.filter(status="").update(status="draft")

def backwards(apps, schema_editor):
    Order = apps.get_model("shop", "Order")
    Order.objects.filter(status="draft").update(status="")

class Migration(migrations.Migration):
    dependencies = [("shop", "0012_order_status")]
    operations = [migrations.RunPython(forwards, backwards)]
```

## Schema-vs-data split rule

One concern per migration. Keep schema operations and data backfills in **separate** migrations:

- Mixing them risks a transaction that holds a schema lock while running a slow row-by-row backfill.
- A data migration that fails is far easier to re-run / fix when it isn't entangled with the DDL.
- Add the column (schema) → backfill it (data) → enforce constraints (schema). Three migrations, not one.

## Zero-downtime / expand-contract

When `migrate` runs while the old code is still serving (rolling deploy), the schema must be compatible with **both** the old and new code at every step. Use expand → migrate code → contract:

### Add a column
1. Add it **nullable** (or with a DB default) — old code ignores it, new code can write it. Safe.
2. Backfill existing rows (separate, batched data migration).
3. Add `NOT NULL` only after every row has a value **and** old code is gone. (Adding `NOT NULL` with a default on a large table can rewrite/lock — on Postgres ≥11 a constant default is cheap, a volatile/`NOT NULL` retrofit may not be.)

### Rename a column / field
Never a single `RenameField` against live traffic — the old code references the old name.
1. Add the new column, write to **both** (app-level dual-write or DB trigger).
2. Backfill new from old.
3. Switch reads to new column; deploy.
4. Drop the old column once no code references it.

### Drop a column
1. Deploy code that no longer references it (the column still exists — old code is fine).
2. In the *next* deploy, drop the column. Dropping a column still referenced by the previously-deployed version breaks it.

### Change a column type
Treat as add-new-column + backfill + swap + drop-old, same as a rename. In-place type changes rewrite the table.

## Locking hazards to flag

- Adding an index on a large table → on Postgres use `AddIndexConcurrently` (in a non-atomic migration: `atomic = False`) to avoid holding a write lock.
- Adding a `NOT NULL` constraint, a `CHECK`/`UNIQUE` constraint, or a foreign key → can take an `ACCESS EXCLUSIVE` lock and/or full-table scan. Prefer `NOT VALID` + later `VALIDATE` patterns on Postgres for big tables.
- Any operation Django can't run concurrently must set `atomic = False` on the `Migration` class.

## Conflict & drift resolution

- **Conflicting leaf migrations** (two branches both numbered 00xx): `makemigrations --merge` creates a merge migration. Read it; merges can mask logical conflicts even when they apply cleanly.
- **`squashmigrations`** to collapse a long history — but keep the old migrations until every environment has applied the squashed one; squashing then deleting too early breaks environments mid-history.
- **`--fake` / `--fake-initial`** mark migrations as applied without running them. This is a foot-gun: it desynchronizes the DB from migration state. Use only when you have *proven* the schema already matches, and say so explicitly.

## Red flags

- A `RunPython` with no `reverse_code` and no explicit `noop`.
- A data migration importing the real model (`from app.models import X`) instead of `apps.get_model`.
- One migration that both alters schema and loops over rows.
- `RenameField` / column drop / `NOT NULL` add proposed against a live large table with a rolling deploy, with no expand-contract plan.
- `migrate --fake` suggested to "fix" a drift without proving the schema matches.
- An index add on a big table without `concurrently` / `atomic = False`.

## Report format

For any schema change against live data, output a **step plan**: ordered migrations, which deploy each belongs to, what locks each takes, and the rollback for each. Don't present a single migration as the answer when the change needs expand-contract.
