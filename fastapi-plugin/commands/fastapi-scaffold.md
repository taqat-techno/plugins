---
description: Scaffold a FastAPI resource surface (SQLAlchemy/SQLModel model + Pydantic Create/Read/Update schemas + APIRouter with CRUD + an Alembic revision through the gate + tests) applying the fastapi plugin's skill set. Plans the file diff and waits for approval before writing.
argument-hint: "[resource-name] [--crud] [--no-crud] [--async] [--sync]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# /fastapi-scaffold — Scaffold a FastAPI resource surface

You are scaffolding FastAPI code that matches the project's existing conventions. Apply the plugin skills throughout:

- `fastapi-database` — model/relationship choices, `ForeignKey`/`ondelete`, constraints, indexes, base-model inheritance, the session dependency.
- `fastapi-pydantic` — separate `*Create` / `*Read` / `*Update` schemas (never one model both ways, never expose the table model); explicit fields; no privileged field accepted.
- `fastapi-routing` — `APIRouter` with `prefix`/`tags`, injected session + auth dependencies, `response_model` on every route, correct status codes, bounded pagination.
- `fastapi-migrations` — generate the Alembic revision through the gate; never hand-trust autogenerate.
- `fastapi-config` — register the router (`include_router`) in the app; no new config secrets inline.
- `fastapi-testing` — tests use the project's client (async → `httpx.AsyncClient`), override `get_session`/`get_current_user`, include a negative-path test and, for the list route, a query-count assertion.
- `fastapi-security-audit` — no privileged field (`id`, `owner_id`, `is_admin`, `price`, `status`) writable from the API by default; ownership-scoped queries.

## Step 0 — Load context

Read `.fastapi-kit.local.json`. If absent, detect the project yourself first (read-only — don't ask the user to do it manually). You need: `appEntrypoint`, `routersDir`, `orm` (sqlalchemy/sqlmodel/none), `asyncStack` (bool), `migrationTool` (alembic?), `settingsModule`, `testClient`, `runPrefix`, base-model convention. Cache non-secret inputs back to `.fastapi-kit.local.json`.

## Step 1 — Decide async vs sync & CRUD

- **Async vs sync** — default to the project's stack (detected: async session/driver → async routes + `AsyncSession`; otherwise sync). `--async`/`--sync` override. Don't mix a sync driver into an async route (→ `fastapi-async-performance`).
- **CRUD** — default to full CRUD (`--no-crud` for model+schemas only). CRUD = list (paginated) + create + retrieve + update + delete.

## Step 2 — Model intake

Argument `resource-name` is the singular resource (e.g. `item`). If absent, ask. Then gather:

- **Fields** — for each: `name`, `type` (str/int/Decimal/bool/date/datetime/EmailStr/UUID/JSON/enum/FK), nullability, default, `unique`, indexed, constraints.
- **Relationships** — for each FK: target model, `ondelete` (make the user choose — never default `CASCADE` silently), `back_populates`, loader strategy the read path will need (`selectinload`/`joinedload`).
- **Constraints** — uniqueness (incl. conditional), check constraints, composite indexes (`__table_args__`).
- **Server-controlled fields** — `id`, timestamps, `owner_id`, status — these go in `*Read` only, never in `*Create`.
- **Base model** — inherit the project's declarative base / timestamp mixin if one exists.

## Step 3 — Plan the file diff

Before writing, list every file you will create or modify:

```
PLAN  (resource: item, async: yes, crud: yes)
  CREATE  app/models/item.py                  ← Item ORM model
  CREATE  app/schemas/item.py                 ← ItemCreate / ItemRead / ItemUpdate
  CREATE  app/routers/item.py                 ← APIRouter (CRUD, response_model, IsAuthenticated)
  MODIFY  app/main.py                          ← include_router(item.router)
  CREATE  tests/test_item_api.py              ← contract + permission + query-count
  GEN     alembic/versions/xxxx_item.py        ← via autogenerate (Step 5)
```

Tailor paths to the detected layout. **Wait for the user to approve the plan before writing.**

## Step 4 — Write the code

- Model: explicit `ForeignKey`/`ondelete`/`back_populates`, DB-level constraints (not just Python checks), indexes on filtered columns, `__tablename__`, `__table_args__`.
- Schemas: separate `*Create`/`*Read`/`*Update`; `*Read` has `model_config = ConfigDict(from_attributes=True)`; no privileged field in `*Create`; typed fields (`EmailStr`, `Field(gt=...)`); secrets never in `*Read`.
- Router: `response_model=ItemRead` on each route; injected `Depends(get_session)` + `Depends(get_current_user)`; bounded `limit`/`offset`; `selectinload`/`joinedload` on the list/detail queries for serialized relations; `201` on create, `204` on delete; ownership-scoped `get_object` (404 for the wrong user, not 403-leak).
- Tests: contract (status + body matches `*Read`), `401` unauthenticated + other-user `404`, validation `422`, and a query-count assertion on the list route.
- Do NOT write business logic — leave clearly-marked `# TODO` where the user adds domain rules.

## Step 5 — Migration through the gate

Run `<runPrefix> alembic revision --autogenerate -m "add item"`, then **read the generated revision** and check what autogenerate missed (server defaults, types, constraints). Confirm `upgrade()` matches intent and `downgrade()` is real (not `pass`). Preview with `alembic upgrade <rev> --sql`. Do not run `alembic upgrade` — that's `/fastapi-migrate`'s job. Report the revision path and what it does.

## Step 6 — Verify & report

1. Grep your output for: the table model used as a `response_model`, a single model used both ways, writable privileged fields, missing `response_model`, unbounded list, `async def` with a blocking call — fix any hit.
2. Confirm the router is included and the migration is reviewed.
3. Report:

```
SCAFFOLDED Item
  Files created:  4     Files modified: 1
  Schemas:        ItemCreate / ItemRead / ItemUpdate  (no privileged field writable)
  Router:         /items  (async, response_model, IsAuthenticated, owner-scoped, paginated)
  Migration:      alembic/versions/ab12_item.py  (reviewed, reversible, NOT yet applied)
  Tests:          4 (incl. 1 negative-path, 1 query-count)
  TODO markers:   2     ← app/routers/item.py:22, app/models/item.py:18
  Next:           /fastapi-migrate   then   /fastapi-test tests/test_item_api.py
```
