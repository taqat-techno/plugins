---
name: fastapi-migrations
description: Safe Alembic migration workflow for FastAPI/SQLAlchemy projects and zero-downtime schema-change sequencing — autogenerate review discipline, reversibility (a real downgrade), splitting schema vs data, and the multi-deploy expand-contract patterns for adding/renaming/dropping columns without breaking a running app. Activates when creating/editing an Alembic revision, running autogenerate/upgrade, reviewing a migration, planning a schema change against a live database, or resolving a migration conflict/branch. Owns the migration-safety gate; defers field/relationship choices to fastapi-database.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - the autogenerate -> review -> upgrade gate (never auto-trust a generated revision)
  - reversibility rule (every revision must have a real downgrade(); data migrations reverse too)
  - schema-vs-data split rule (one concern per revision; data backfills are separate)
  - zero-downtime / expand-contract sequencing for add / rename / drop / type-change
  - migration-branch & multi-head resolution (merge revisions, down_revision integrity)
  - locking-risk rules (operations that take ACCESS EXCLUSIVE / rewrite a table)
defers_to:
  - fastapi-database (what the column/constraint/index/relationship should be)
  - fastapi-async-performance (whether a backfill needs batching/throttling)
  - project deploy pipeline (how/when `alembic upgrade` runs relative to code rollout — adapter input)
user_invocable: false
---

# fastapi-migrations

## Purpose

Alembic's `--autogenerate` is a *proposal*, not a verified change — and it's a partial one: it reliably detects added/removed tables and columns but **misses or mis-guesses** many things (server defaults, constraint/index renames, type changes, `CHECK` constraints, enum alterations). The dangerous revisions look identical to safe ones in the diff. This skill owns the review gate and the sequencing patterns that keep a schema change from locking a live table or breaking the previously-deployed code mid-rollout.

## When to use

Activate when:

- Running `alembic revision --autogenerate` or `alembic upgrade`, or about to.
- Creating, editing, or reviewing a revision file (`versions/*.py`).
- Planning a schema change against a database with real data / live traffic.
- Backfilling data (populate a new column, transform existing rows).
- Hitting multiple heads, a branch, or `down_revision` confusion.

Do NOT use to decide the column/relationship itself (→ `fastapi-database`) or how to batch a huge backfill efficiently (→ `fastapi-async-performance`).

## Inputs (adapter)

1. **Database backend** — Postgres locking semantics differ from MySQL; SQLite rewrites the whole table for most `ALTER`s (and Alembic uses "batch" mode / table-copy there).
2. **Deploy model** — single-instance vs rolling deploy, and whether `alembic upgrade` runs *before* or *after* the new code is live. This decides whether expand-contract is mandatory.
3. **Table sizes** — "live traffic on a large table" is the trigger for the zero-downtime patterns; a tiny table can take the simple path.
4. **Alembic invocation** — the project's command prefix (`alembic`, `python -m alembic`, `poetry run alembic`, container exec) and whether `target_metadata` is wired so autogenerate sees the models.

## The gate (never skip)

1. **`alembic revision --autogenerate -m "..."`** → it writes a revision file.
2. **Read the generated file. Every time.** Confirm `upgrade()` matches your intent — and check for what autogenerate **missed**: a server default it ignored, a column type change it didn't detect, a constraint/index it rendered as drop+add. Add the missing operations by hand.
3. **Write/verify `downgrade()`** — autogenerate fills it in for simple cases; confirm it actually reverses `upgrade()`. An empty `pass` downgrade means the revision is irreversible.
4. **Preview the SQL** with `alembic upgrade <rev> --sql` (offline mode) to see the exact DDL before running it against anything that matters. Identify locking operations.
5. **`alembic upgrade head`** — apply. Then verify reversibility: `alembic downgrade -1` on a scratch DB should cleanly roll back.

## Reversibility rule

Every revision must be reversible.

- Schema ops Alembic generates are usually reversible — confirm the `downgrade()` is real, not an empty `pass`.
- **Data migrations must reverse too.** A revision that backfills/transforms rows needs a `downgrade()` that undoes it (or a documented, explicit reason it can't). Use `op.execute(...)` or the connection (`op.get_bind()`) with **core SQL / a lightweight table definition** — never import your live ORM models into a migration; the real model may have changed by the time the revision runs.

```python
def upgrade() -> None:
    op.add_column("orders", sa.Column("status", sa.String(), nullable=True))

def downgrade() -> None:
    op.drop_column("orders", "status")
```

## Schema-vs-data split rule

One concern per revision. Keep schema operations and data backfills in **separate** revisions:

- Mixing them risks a transaction holding a schema lock while a slow row-by-row backfill runs.
- A data migration that fails is far easier to re-run / fix when it isn't entangled with the DDL.
- Add the column (schema) → backfill it (data) → enforce constraints (schema). Three revisions, not one.

## Zero-downtime / expand-contract

When `alembic upgrade` runs while the old code is still serving (rolling deploy), the schema must be compatible with **both** old and new code at every step. Use expand → migrate code → contract:

### Add a column
1. Add it **nullable** (or with a server default) — old code ignores it, new code can write it. Safe.
2. Backfill existing rows (separate, batched data revision).
3. Add `NOT NULL` only after every row has a value **and** old code is gone. (On Postgres ≥11 a constant server default is cheap; a volatile default or a `NOT NULL` retrofit on a large table may rewrite/scan.)

### Rename a column
Never a single `alter_column ... new_column_name` against live traffic — the old code references the old name.
1. Add the new column; dual-write old+new in code.
2. Backfill new from old.
3. Switch reads to new; deploy.
4. Drop the old column once no code references it.

### Drop a column
1. Deploy code that no longer references it (the column still exists — old code is fine).
2. In the *next* deploy, drop the column. Dropping a column the previously-deployed version still reads breaks it.

### Change a column type
Treat as add-new + backfill + swap + drop-old, same as a rename. In-place type changes rewrite the table.

## Locking hazards to flag

- Adding an index on a large Postgres table → use `op.create_index(..., postgresql_concurrently=True)` in a revision with `op.get_context()` non-transactional (`# revision is non-transactional`; Alembic: don't wrap in the implicit transaction).
- Adding `NOT NULL`, a `CHECK`/`UNIQUE` constraint, or an FK → can take `ACCESS EXCLUSIVE` and/or scan the table. Prefer the Postgres `NOT VALID` + later `VALIDATE CONSTRAINT` pattern (`op.execute`) on big tables.
- SQLite can't `ALTER` most things in place — Alembic uses **batch mode** (`with op.batch_alter_table(...)`) which copies the table; note the rewrite.

## Branch & multi-head resolution

- **Multiple heads** (two revisions sharing a `down_revision`): `alembic heads` to see them, `alembic merge -m "merge" <head1> <head2>` to create a merge revision. Read it.
- Keep `down_revision` integrity — never hand-edit a revision id mid-history; a broken chain makes `upgrade`/`downgrade` unrunnable.
- **`alembic stamp`** marks the DB at a revision **without running it** — a foot-gun that desynchronizes the DB from migration state. Use only when the schema is *proven* to already match, and say so.

## Red flags

- A revision applied without reading the autogenerated `upgrade()` (autogenerate misses defaults/types/constraints).
- A `downgrade()` that's just `pass` / `...` (irreversible).
- A data migration importing the live ORM models instead of using core SQL / a local table def.
- One revision that both alters schema and loops over rows.
- A column rename / drop / `NOT NULL` add against a live large table with a rolling deploy and no expand-contract plan.
- `alembic stamp` suggested to "fix" drift without proving the schema matches.
- An index add on a big table without `postgresql_concurrently` / a non-transactional revision.

## Report format

For any schema change against live data, output a **step plan**: ordered revisions, which deploy each belongs to, what locks each takes, and the `downgrade` for each. Don't present a single autogenerated revision as the answer when the change needs expand-contract — and always note what autogenerate may have missed.
