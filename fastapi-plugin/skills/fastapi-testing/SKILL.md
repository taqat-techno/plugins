---
name: fastapi-testing
description: Use when writing or reviewing FastAPI tests, choosing TestClient (sync) vs httpx.AsyncClient + ASGITransport (async), running lifespan startup in tests (ASGITransport does not; use asgi-lifespan's LifespanManager or a TestClient context), overriding a dependency with dependency_overrides, building a transactional test-DB fixture with rollback, mocking external calls or time, adding query-count or endpoint-contract assertions, scoping a run to what changed, running the constraint-sensitive suite on Postgres instead of SQLite, or diagnosing flaky, slow, leaky or silently skipped async tests. Defers production query design to fastapi-database.
version: 0.1.0
user-invocable: false
metadata:
  last_reviewed: 2026-07-23
  owns:
    - test-client choice (TestClient sync vs httpx.AsyncClient+ASGITransport for async apps) and config
    - dependency_overrides strategy (swap get_session / get_current_user / get_settings under test)
    - test-DB lifecycle rules (transactional rollback per test; isolated, not shared, state)
    - external-dependency & time mocking rules (mock at boundary; freeze time; no real network)
    - regression-coverage rules (query-count assertions for N+1; contract tests for status/body/authz)
    - async-test correctness (pytest-asyncio/anyio; awaiting the async client; async fixtures)
  defers_to:
    - fastapi-database (what the production query/loader should be; this skill locks it with a count test)
    - fastapi-routing (the endpoint contract being asserted)
    - fastapi-config (the test settings/overrides)
    - project test conventions & coverage targets (adapter input)
---

# fastapi-testing

## Purpose

FastAPI tests fail in characteristic ways: they hit the real network, they leak DB state between cases because nothing rolls back, they use the sync `TestClient` against async internals and miss event-loop bugs, and they pass while the code regresses to an N+1 because nothing counts queries. This skill owns the client/override/fixture choices that make a suite fast, isolated, and able to catch the regressions that matter.

## When to use

Activate when:

- Writing or reviewing FastAPI tests (routes, dependencies, services, models).
- Choosing the test client, overriding a dependency, or setting up the test DB.
- Diagnosing flaky, slow, order-dependent, or state-leaking tests.
- Adding query-count regression coverage or endpoint-contract tests.

Defer *what the production query/loader should be* to `fastapi-database` — this skill's job is to lock it with a query-count assertion.

## Inputs (adapter)

1. **Sync vs async app** — a sync app can use Starlette's `TestClient`; an **async** app (async routes/sessions) is best tested with `httpx.AsyncClient(transport=ASGITransport(app=app))` under `pytest-asyncio`/`anyio`, so the same event loop drives app and test.
2. **Test DB strategy** — a dedicated test database / a transactional fixture that rolls back per test, or an in-memory SQLite where the schema allows. The override that points `get_session` at it.
3. **Data & mocking libs** — `factory_boy`/`model_bakery`, `freezegun`/`time-machine`, `respx`/`httpx` mocking, `coverage`.

## Test-client choice

```python
# Async app — same loop drives app + client:
import pytest, httpx
from httpx import ASGITransport

@pytest.mark.anyio
async def test_list_items():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/items", headers=auth(user))
        assert r.status_code == 200
```

- **Async app → `httpx.AsyncClient` + `ASGITransport`.** The sync `TestClient` runs the app in a worker thread with its own loop; for genuinely async DB sessions and dependencies, the async client keeps everything on one loop and surfaces event-loop bugs the sync client hides.
- **Sync app → `TestClient`** is fine and simplest.
- Configure `pytest-asyncio` (`asyncio_mode = auto`) or `anyio` so `async def` tests run.
- **`ASGITransport` does not run the app's lifespan.** Startup never happens, so whatever the `lifespan` creates (engine, session maker, HTTP client, `app.state.*`) is missing, and tests fail with `AttributeError` on `app.state` or, worse, silently fall back to a module-level default that points at the wrong database. Wrap the app in `asgi_lifespan.LifespanManager` (package `asgi-lifespan`) and pass the manager's app to the transport:

```python
from asgi_lifespan import LifespanManager

@pytest.fixture
async def client():
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            yield c
```

  The sync `TestClient` runs the lifespan only when used as a context manager (`with TestClient(app) as client:`); a bare `TestClient(app)` skips startup and shutdown too. Override the lifespan's resources (point the engine at the test DB) before entering it.

## Dependency overrides (the key lever)

FastAPI's `app.dependency_overrides` swaps a dependency's implementation under test — this is how you point at a test DB and bypass/forge auth without touching production code:

```python
app.dependency_overrides[get_session] = lambda: test_session
app.dependency_overrides[get_current_user] = lambda: test_user
# ... run tests ...
app.dependency_overrides.clear()   # reset between tests, or via a fixture
```

- Override **`get_session`** to inject the transactional test session; **`get_current_user`** to authenticate as a specific user (or to test the unauthenticated path by *not* overriding it); **`get_settings`** to inject test config.
- **Clear overrides between tests** (a fixture that sets then `clear()`s) so they don't leak across cases.

## Test-DB lifecycle

- **Roll back per test.** Wrap each test in a transaction/savepoint bound to the session you inject, and roll it back in teardown — the DB is clean between tests with no manual delete. (With SQLite-in-memory, a fresh schema per test or a shared connection.)
- Each test **creates its own data** (factories) and relies on rollback for isolation — never depend on execution order or leftover rows.
- **Speed:** reuse the schema across the run where possible; a fast password hasher in test config; build the *minimum* data a test needs.

## Scoped runs during development

Test the change, not the project. Run the narrowest tier that proves the change, stop
at the first red tier and fix it before widening, and report which tiers ran (with
counts) and that the full suite did not. If the `agent-safety-guards` plugin is
installed, its `test-scope` skill owns this tier policy in more detail. These are the
pytest selectors for each tier:

| Tier | Run |
|---|---|
| T0 | `python -m py_compile` on changed files; a schema/migration check when models changed |
| T1 | `pytest tests/api/test_orders.py::test_create_rejects_negative` or `-k "orders and create"` |
| T2 | the test package of each changed area (`pytest tests/api/orders/`), widened to the packages that import a changed model, dependency, settings or `conftest.py` |
| T3 | Everything: **only when the user asks, or in CI** (with agent-safety-guards installed, its hook may want `FULL_SUITE=1` in the command). Postgres-parity runs belong in CI (see Backend parity) |

- After a red run: `pytest --lf --lfnf=none -x`, then the whole T1 set.
- A path or `-k` that collects nothing reports "no tests ran" (exit 5). That is a failed
  invocation. Async tests silently skipped by a missing asyncio/anyio config are the same
  false pass.
- Extend the existing test module before creating one; repro scripts live outside the repo.

## Backend parity — test on the engine you deploy

A suite that runs on SQLite for speed while production runs Postgres **cannot** catch a whole class of constraint bugs, because SQLite silently ignores them:

- **String length limits are not enforced by SQLite** — a `String(length=n)` / `VARCHAR(n)` over-length value inserts fine under test and is rejected only by Postgres.
- **Partial/conditional unique indexes**, **`DEFERRABLE INITIALLY DEFERRED`** foreign keys, exclusion constraints, and other Postgres-only integrity exist only on Postgres — on SQLite the constraint is a no-op, so a test "proving" uniqueness or deferral passes for the wrong reason.
- Datatype/function/lookup differences (case-sensitivity, `JSONB`/array columns, `ON CONFLICT`) diverge too, and Alembic migrations authored for Postgres may not even run on SQLite.

Rule: **run the constraint-sensitive suite against Postgres in CI** — the same engine and, ideally, the same major version as prod. A fast SQLite-in-memory loop locally is fine, but the authoritative run, and every test that asserts a DB constraint, must point the test engine / `get_session` override at Postgres. A green SQLite suite is not evidence that a Postgres-only constraint holds.

## Mocking discipline

- **No real network in tests.** Mock external HTTP at the boundary (`respx` for httpx, or patch the client). A test that calls a real API is flaky and slow by definition.
- **Mock where it's used, not where it's defined** (`patch("app.services.payment.client")`, not `patch("stripe.Charge")`) — the import location is what your code resolves.
- **Freeze time** (`freezegun`/`time-machine`) for anything `datetime.now()`-dependent; never assert against the real clock — also matters for JWT `exp` tests.
- Mock the *boundary* (third-party SDK, email send, task enqueue), not your own logic.

## Regression coverage that matters

- **Query-count assertions** around list/detail paths to pin counts — this is how an N+1 regression is caught in CI instead of production. Count statements via a SQLAlchemy event listener (`event.listen(engine, "after_cursor_execute", ...)`) or `echo` capture, assert the expected number. When `fastapi-database` fixes an N+1, lock it with a count test.
- **Contract tests** per endpoint: status code, response shape (matches the read schema — catches field leaks), permission enforcement (authenticated vs not, owner vs other user → catches IDOR), pagination bounds, validation errors (`422`).
- Test the **boundaries**: empty results, `401` unauthenticated, `403`/`404` for the wrong user, validation failure — not just the happy path.

## Red flags

- A sync `TestClient` used against an async-session app where it hides loop/session bugs.
- Tests that don't roll back / share DB state (order-dependent, leaky).
- `dependency_overrides` set but never cleared (leaks across tests).
- Real network/API/email calls in tests.
- No query-count assertion anywhere on list endpoints known to load relationships.
- Endpoint tests that check `200` but never the unauthenticated / other-user path.
- Asserting a Postgres-only constraint (varchar length, partial/deferrable unique) against a SQLite test DB → the constraint is a no-op there; the test passes for the wrong reason.
- `async def` tests with no `pytest-asyncio`/`anyio` configured (silently skipped or erroring).

## Report format

When reviewing a suite, report: **client fit (sync vs async), override hygiene (set+cleared, DB pointed at test), real-IO leakage, isolation hazards, and coverage gaps on boundaries/permissions/query-counts** — with specific files. When adding tests, state which client and why, override `get_session`/`get_current_user` explicitly, and include at least one negative-path and (for query-sensitive code) one query-count test.
