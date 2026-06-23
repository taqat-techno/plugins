---
name: fastapi-database
description: SQLAlchemy / SQLModel data layer for FastAPI — model & relationship design, session lifecycle (request-scoped, dependency-injected, async vs sync), the N+1 / lazy-loading rule (selectinload vs joinedload), loading strategies, transaction boundaries (commit/rollback/begin), bulk operations, and the async-session correctness traps (no implicit lazy load under asyncio). Activates when defining an ORM model/relationship, writing or reviewing a query, managing a session, choosing a loader strategy, or diagnosing duplicated/slow queries. Defers migrations to fastapi-migrations and caching/async-offload to fastapi-async-performance.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - ORM model & relationship modeling (FK, relationship(), cascade, back_populates, indexes/constraints)
  - session lifecycle rules (request-scoped session via dependency; one session per request; close/rollback)
  - the N+1 detection + fix decision (selectinload for collections, joinedload for many-to-one)
  - loading-strategy rules (lazy/select/selectin/joined/subquery; when each fits)
  - transaction-boundary rules (commit/rollback, session.begin, flush vs commit)
  - async-session correctness (no implicit lazy I/O under asyncio; eager-load before leaving the session)
defers_to:
  - fastapi-migrations (how a model change becomes a safe Alembic revision)
  - fastapi-async-performance (caching, connection-pool sizing, async-driver choice, pagination at scale)
  - fastapi-pydantic (the request/response schema the ORM object maps to)
  - project base-model & session-factory conventions (adapter input)
user_invocable: false
---

# fastapi-database

## Purpose

Most FastAPI data bugs are decided at two moments: how a model and its relationships are shaped, and how the session and its queries are scoped per request. The classic failures are a session that lives too long or leaks across requests, an N+1 from lazy-loaded relationships serialized in a list response, and — on the async stack — an implicit lazy load firing after the session context has closed (a `MissingGreenlet`/detached-instance error). This skill owns the model, the session, and the query discipline.

## When to use

Activate when:

- Defining or editing an ORM model, a relationship, a constraint, or an index.
- Writing or reviewing a query (in a route, a dependency, a CRUD helper, a service).
- Managing the DB session — its creation, scope, commit/rollback.
- A response is slow or issues duplicated queries (N+1), or you're choosing a loader strategy.

Do NOT use for: the Alembic migration that ships a model change (→ `fastapi-migrations`), caching / pool sizing / async-driver selection (→ `fastapi-async-performance`), or the Pydantic schema (→ `fastapi-pydantic`).

## Inputs (adapter)

1. **ORM + sync/async** — SQLAlchemy 2.0 sync (`Session`), SQLAlchemy async (`AsyncSession` + `asyncpg`/`aiosqlite`), or SQLModel (Pydantic-flavored SQLAlchemy). The session API and the lazy-loading rules differ sharply between sync and async.
2. **Session factory** — `sessionmaker` / `async_sessionmaker`, and how the request-scoped session is provided (almost always a `yield`-dependency, → `fastapi-routing`).
3. **Database backend** — Postgres / MySQL / SQLite. Determines available constraints, index types, and locking semantics.

## Model & relationship design

- **`relationship()` needs `back_populates`** (or `backref`) named on both sides — implicit/ambiguous relations bite when a model has two FKs to the same target.
- **`ForeignKey` + `ondelete`** at the DB level (`ForeignKey("parent.id", ondelete="CASCADE"/"RESTRICT")`) plus the matching `relationship(cascade=...)` at the ORM level — they're different layers and both matter. Never silently cascade-delete audit/financial rows.
- **Push invariants to the DB** — `UniqueConstraint`, `CheckConstraint`, `Index` in `__table_args__`. A uniqueness rule enforced only by a pre-insert `SELECT` races under concurrency.
- **Index the columns you filter/order/join on**; don't index everything (each index is write cost). Index changes ship as Alembic revisions (→ `fastapi-migrations`).
- **SQLModel caveat:** the table model is also a Pydantic model — do not expose it directly as a response (→ `fastapi-pydantic`); define a separate read schema.

## Session lifecycle

- **One session per request**, provided by a `yield`-dependency, closed when the request ends (→ `fastapi-routing` owns the dependency wiring):

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()      # or commit explicitly in the handler
        except Exception:
            await session.rollback()
            raise
```

- **Never a module-level/global session shared across requests** — sessions aren't concurrency-safe and will bleed state and transactions between requests.
- **Commit once, at a clear boundary** — at the end of the unit of work, not after every statement. Roll back on error. `flush()` sends SQL and assigns PKs without committing; `commit()` ends the transaction.

## The N+1 / lazy-loading rule

A relationship accessed per row issues one query per row. Eager-load the relations the response touches:

| Relationship being accessed | Loader |
|---|---|
| Many-to-one / one-to-one (single related object) | `joinedload(Model.parent)` — JOIN, one query |
| One-to-many / many-to-many (collection) | `selectinload(Model.children)` — second IN query, no row fan-out |
| Nested / filtered | chain loaders (`selectinload(...).selectinload(...)`) |

```python
# N+1: one query for orders, then one per order for .customer
orders = (await session.scalars(select(Order))).all()
for o in orders:
    print(o.customer.name)

# Fixed: 2 queries total
orders = (await session.scalars(
    select(Order).options(selectinload(Order.customer))
)).all()
```

- **`joinedload` for to-one, `selectinload` for collections.** `joinedload` on a collection multiplies rows (the cartesian fan-out) and breaks `LIMIT`; `selectinload` issues a clean second query. Prefer `selectinload` for collections, especially with pagination.
- **Diagnose, don't guess** — turn on `echo` in a scratch run, count statements, or assert query counts in a test (→ `fastapi-testing`). Adding a loader that isn't needed adds a query.

## Async-session correctness (the trap)

On the **async** stack, lazy loading does **not** work implicitly — accessing an un-loaded relationship after the awaited query (or after the session closes) raises (`MissingGreenlet` / detached instance). So:

- **Eager-load everything the response needs *before* the object leaves the session** (`selectinload`/`joinedload` in the `select`). You can't rely on attribute access to lazy-fetch later.
- **`expire_on_commit=False`** on the async sessionmaker so objects stay usable after `commit()` while serializing the response (otherwise attributes expire and re-trigger a load that can't happen).
- Use an **async driver** end-to-end (`asyncpg`/`aiosqlite`) with `AsyncSession`; a sync driver under `async def` blocks the event loop (→ `fastapi-async-performance`).

## Transactions & bulk ops

- Wrap multi-write invariants in a transaction (`async with session.begin():` or commit/rollback around the unit) so partial failure rolls back. Keep it as small as the invariant requires — long transactions hold locks.
- **Bulk:** `session.execute(insert(Model), [rows])` / `update(Model).where(...).values(...)` for set-based writes instead of a per-row `add`+`commit` loop. Note these bypass ORM events/`__init__` — choose consciously.
- For side effects that must only fire after commit (enqueue a task, send mail), do them after the commit succeeds, not mid-transaction.

## Red flags

- A relationship accessed in a loop / serialized in a list response with no `selectinload`/`joinedload` upstream → N+1.
- A module-level or app-level session shared across requests.
- `joinedload` on a *collection* combined with `LIMIT`/pagination (row fan-out corrupts the page).
- On async: attribute access to an un-eager-loaded relationship after the query → `MissingGreenlet`/detached error; missing `expire_on_commit=False`.
- A sync DB driver/`Session` used inside an `async def` route (blocks the loop).
- A uniqueness/invariant enforced only by a pre-check `SELECT` with no DB constraint.
- `commit()` after every statement in a loop; no `rollback()` on the error path.
- `cascade`/`ondelete` set on only one of the two layers, or `CASCADE` on audit data.

## Report format

When reviewing queries, report each finding as: **location → symptom (with how the query count was/Would be observed) → fix (which loader / session change) → expected query count after**. For async code, explicitly flag any relationship not eager-loaded before leaving the session. Don't assert an N+1 without stating how it's counted.
