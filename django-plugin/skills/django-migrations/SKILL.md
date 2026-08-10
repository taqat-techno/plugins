---
name: django-migrations
description: Safe Django migration workflow and zero-downtime schema-change sequencing — makemigrations/migrate discipline, reversibility, data migrations (RunPython with a reverse), splitting schema vs data, and the multi-deploy patterns for adding/renaming/dropping columns without breaking a running app. Activates when creating/editing a migration, running makemigrations or migrate, reviewing a migration diff, planning a schema change against a live database, or diagnosing a migration conflict/drift. Owns the migration-safety gate; defers model field choices to django-orm-models.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - the makemigrations -> review -> migrate gate (never auto-trust a generated migration)
  - reversibility rule (every migration must be reversible; RunPython needs a reverse_code)
  - idempotency rule for migrations that restore schema objects some environments already have
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

After any *bulk* regeneration (a squash, a re-generate across the whole project), diff the **per-app file counts** against `INSTALLED_APPS` before trusting it. `makemigrations` can produce nothing at all for one app — managed models, in `INSTALLED_APPS`, no exclusions — and a second run still reports **"No changes detected"**; only an explicit `makemigrations <app>` surfaces it. Believing the summary line ships a schema that, for that app, does not exist.

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

## Idempotency rule (when environments have diverged)

Long-lived databases drift from freshly-built ones: a constraint, index, or trigger can exist on staging and be absent everywhere else — a reconciled migration history, a hand-applied hotfix, a squash that dropped raw SQL. A migration that *restores* such an object must be **idempotent**, or it fails on boot in precisely the environment that already has it.

- **Guard the DDL instead of asserting the state.** Emit `RunSQL` with a `DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '…') THEN ALTER TABLE … ADD CONSTRAINT …; END IF; END $$;` block, so the already-present environment is a no-op and a fresh deploy gains the object.
- **Validate both paths against the real engine**, in rolled-back transactions: present → no-op (1 → 1), absent → created (0 → 1), and a re-run after creation. The suite cannot do this for you — on SQLite the object being restored never existed, so a green run is silent about both paths.
- **Pre-apply it to the diverged environment and record the migration**, rather than trusting the deploy's boot-`migrate` to be a harmless no-op. A migration on the critical path should never depend on "it will probably do nothing".

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
- **`squashmigrations`** to collapse a long history — but keep the old migrations until every environment has applied the squashed one; squashing then deleting too early breaks environments mid-history. **A squash regenerated from model state silently drops everything that is not model state**: `RunSQL` constraints, triggers, and grants and `RunPython` backfills simply vanish, while the model docstring and `Meta.constraints` still read as though the guarantee exists. The divergence is undetectable by the usual checks *by construction* — the test DB is built from the same squashed migrations, so it loses the object symmetrically and the whole suite stays green, and `makemigrations --check` only ever compares model state. Before regenerating, **grep the pre-squash history for `RunSQL`/`RunPython`** and re-add each one explicitly; afterwards **diff the live schema against a freshly-migrated database** (`pg_constraint`, `pg_indexes`, triggers), because an environment whose bookkeeping you reconciled rather than rebuilt still carries the object and now has a different schema from a fresh deploy.
- **Detect schema drift up front, once, for the whole plan — never by try/except.** Before running anything that touches many models against a database you did not build (a wipe, a reconciliation, a broad backfill), enumerate the real schema with `connection.introspection.table_names()` / `get_table_description()` and pick one strategy for the entire run. Probing with `try: … except: …` is worse than useless on Postgres: a failed statement **aborts the surrounding `atomic()`**, so one missing column becomes a total rollback. Two further traps: with `post_delete` receivers connected Django cannot fast-delete, so `.delete()` SELECTs full rows first and names a column the old schema lacks; and drift on one model poisons every *parent* that cascades to it, so per-model handling isn't enough.
- **Running local code against a remote database is what turns drift into cascading failures.** A CLI that injects the remote `DATABASE_URL` into a local process runs your **new** models against the **old** schema, and the failures arrive in order: missing tables first (a `COUNT(*)` blows up), then missing columns. It is the right tool for landing a bookkeeping reconciliation *ahead* of the code push — just know that is what it's doing before you use it.
- **A migration with a data-precondition guard dictates deploy ORDER.** A destructive migration that refuses to run while the old table is non-empty is behaving correctly — that guard is what stops it destroying real data. But it also means the cleanup *cannot* follow the deploy; it must precede it. Work the ordering out before scheduling anything, because the obvious order (deploy, then clean up) is the impossible one.
- **Tolerance in a destructive tool must be asymmetric.** "Survive a missing table" is right for **delete targets** (absent = nothing to delete) and dangerous for **preserved** tables — a missing users/accounts table means you are pointed at the wrong database entirely. Same mechanism, opposite verdict: split the set first, then skip one and abort on the other.
- **Run reconciliation scripts with `runpy`, not `manage.py shell < script.py`.** Piping into `shell` runs the REPL, where a **blank line inside an indented block ends the block** — a `with transaction.atomic():` DELETE commits and everything after the blank line is parsed as fresh top-level input and silently skipped, giving you the exact half-state the transaction existed to prevent, with exit code 0 and no traceback. Use `manage.py shell -c "import runpy; runpy.run_path('script.py')"` for anything with control flow, and re-query the end state instead of trusting the exit code.
- **`--fake` / `--fake-initial`** mark migrations as applied without running them. This is a foot-gun: it desynchronizes the DB from migration state. Use only when you have *proven* the schema already matches, and say so explicitly.

## Red flags

- A `RunPython` with no `reverse_code` and no explicit `noop`.
- A data migration importing the real model (`from app.models import X`) instead of `apps.get_model`.
- One migration that both alters schema and loops over rows.
- `RenameField` / column drop / `NOT NULL` add proposed against a live large table with a rolling deploy, with no expand-contract plan.
- `migrate --fake` suggested to "fix" a drift without proving the schema matches.
- An index add on a big table without `concurrently` / `atomic = False`.
- A squash regenerated from model state with `RunSQL`/`RunPython` in the pre-squash history and no explicit re-add → raw constraints gone, suite still green.
- A migration that restores a constraint/index without an `IF NOT EXISTS` guard, shipped to environments that don't all share the same schema.
- Schema drift probed by try/except against Postgres → the failed statement aborts the transaction and one missing column rolls back everything.
- A destructive or reconciliation script run as `manage.py shell < script.py` → a blank line silently truncates the block.
- A bulk `makemigrations` accepted on its "No changes detected" summary without a per-app file-count diff.

## Report format

For any schema change against live data, output a **step plan**: ordered migrations, which deploy each belongs to, what locks each takes, and the rollback for each. Don't present a single migration as the answer when the change needs expand-contract.
