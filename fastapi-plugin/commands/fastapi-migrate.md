---
description: Run the safe Alembic migration workflow for a FastAPI/SQLAlchemy project — autogenerate, review the generated revision and its SQL, check reversibility (a real downgrade), then upgrade — with zero-downtime sequencing for risky changes against live data. Refuses to blindly auto-apply.
argument-hint: "[--make] [--apply] [--plan] [--check]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Edit
---

# /fastapi-migrate — Safe Alembic migration workflow

You drive Alembic migrations through the safety gate from the `fastapi-migrations` skill. You do **not** run `alembic upgrade` until the generated revision has been read and its SQL inspected. Apply `fastapi-migrations` (sequencing/reversibility) and, for backfills, `fastapi-database` (no live-model import) and `fastapi-async-performance` (batching).

## Step 0 — Context

Read `.fastapi-kit.local.json` for `runPrefix`, `dbBackend`, `migrationTool`. If absent, detect them yourself (read-only): locate `alembic.ini` and the `versions/` directory, the invocation prefix (`alembic`, `python -m alembic`, `poetry run alembic`), the database backend, and confirm `target_metadata` is wired so autogenerate sees the models. Determine whether the target DB has real/live data (ask if unknown) — that decides whether zero-downtime sequencing is mandatory.

## Modes

- **`--check`** (default if nothing else given) — run `<runPrefix> alembic check` (detects models out of sync with migrations, where supported) and `alembic current` / `alembic heads`. Report whether models and revisions are in sync and whether there are multiple heads. Makes no files.
- **`--make`** — `alembic revision --autogenerate`, then **stop and review** (do not upgrade).
- **`--plan`** — show `alembic history` and the path from `current` to `head` (what is unapplied, in order). Read-only.
- **`--apply`** — upgrade, but only after the review gate below has passed in this session.
- No mode → run `--check`, then offer the next step.

## The gate (for `--make` / `--apply`)

1. **Make:** `<runPrefix> alembic revision --autogenerate -m "<message>"`. List the revision file(s) created.
2. **Read every generated revision.** Confirm `upgrade()` matches intent — and explicitly check what autogenerate **missed**: server defaults, column **type** changes, `CHECK`/named constraints rendered as drop+add, enum alterations. Add missing operations by hand. Flag any unexpected operation (a stray drop, a `RemoveColumn` that loses data).
3. **Verify `downgrade()`.** It must actually reverse `upgrade()` — not an empty `pass`. Fix it if autogenerate left it incomplete.
4. **Inspect SQL:** `<runPrefix> alembic upgrade <rev> --sql` (offline) to see the exact DDL. Identify locking operations (index creation, `NOT NULL` add, constraint add, FK add, type change) and table-rewrite risks for the detected backend (note SQLite batch-mode table copies).
5. **Risk classification:**
   - **Safe** (additive nullable column, new table, new index on small table) → upgrade.
   - **Risky against live data** (rename, drop, `NOT NULL` retrofit, type change, index on large table) → produce an **expand-contract step plan** instead of applying in one shot. Map each revision to a deploy phase, name the lock each takes, and give the rollback. Get explicit confirmation before applying any phase.
6. **Upgrade** (only `--apply`, only after the above): `<runPrefix> alembic upgrade head` (or to a specific rev). Then confirm with `alembic current` and, on a scratch/staging DB where possible, verify `alembic downgrade -1` rolls back cleanly.

## Data migrations / backfills

If a revision backfills data:

- Confirm it uses **core SQL / `op.execute` / a local lightweight table**, not an import of the live ORM models.
- Confirm it is a **separate** revision from the schema change.
- For large tables, require batching/throttling (chunk by PK, bounded updates) per `fastapi-async-performance` — do not run one unbounded `UPDATE` over a huge table.

## Refusals & guards

- Never suggest `alembic stamp` to resolve drift unless the schema is *proven* to match; if you do, state the proof.
- If a column rename / drop / `NOT NULL` add is proposed against live data with no expand-contract plan, stop and produce the plan first.
- The plugin's bash guard **blocks** `alembic downgrade base` and `dropdb`/`DROP DATABASE` without the override token, and flags `alembic stamp` — treat its output as confirmation, not noise.

## Report

```
MIGRATION RUN
  Made:        ab12_add_item.py
  Autogen gaps: server_default on item.status added by hand
  SQL review:  CREATE TABLE (safe) · CREATE INDEX (small table, ok)
  Reversible:  ✅  downgrade drops table
  Risk:        SAFE — applied
  Applied:     ✅  (alembic current → ab12 head)
```

For risky changes, output the phased step plan and the per-phase rollback instead of an "applied" line, and stop for confirmation.
