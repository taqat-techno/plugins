---
name: fastapi-routing
description: FastAPI routing and dependency-injection patterns — path operations, APIRouter organization, the Depends() injection system (including yield-dependencies for resource lifecycle), response_model and status_code declaration, HTTPException/error shaping, and pagination. Activates when writing or reviewing a path operation, an APIRouter, a dependency, a response/status declaration, or diagnosing inconsistent errors, missing pagination, or a wrong status code. Defers schema fields to fastapi-pydantic, auth hardening to fastapi-security-audit, and query shaping to fastapi-database.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - route organization (APIRouter per resource, prefix/tags, route ordering, path vs query params)
  - dependency-injection rules (Depends, shared deps, yield-deps for session/resource lifecycle, sub-dependencies)
  - response declaration (response_model, status_code, response_model_exclude_none, 201/204 correctness)
  - error shaping (HTTPException with correct status, consistent error envelope, exception handlers)
  - pagination / filtering parameter rules (default-bounded limit, offset/cursor params)
defers_to:
  - fastapi-pydantic (the request/response model fields and validation)
  - fastapi-database (get_queryset/session shaping, select/loader strategy for the endpoint)
  - fastapi-security-audit (auth model hardening, permission-bypass review, rate-limit policy)
  - fastapi-async-performance (sync-vs-async def choice, response caching, scale)
  - project API conventions (base router, error envelope, auth scheme — adapter input)
user_invocable: false
---

# fastapi-routing

## Purpose

The path-operation layer is where the request meets validation, dependencies, and the response contract. Bugs here return the wrong status code, hand-format errors inconsistently, forget to bound a list endpoint, leak a session because a dependency didn't clean up, or shadow a route by ordering. This skill owns route organization, the dependency-injection system, and the response/error contract — it assumes the schema fields (→ `fastapi-pydantic`) and queries (→ `fastapi-database`) are handled elsewhere.

## When to use

Activate when:

- Writing or reviewing a path operation (`@router.get/post/...`) or an `APIRouter`.
- Designing a dependency (`Depends`), especially a `yield`-dependency that manages a resource.
- Declaring `response_model` / `status_code`, or shaping errors.
- An endpoint returns the wrong status, inconsistent errors, an unpaginated list, or a route is shadowed.

Do NOT use for: the schema's fields/validation (→ `fastapi-pydantic`), the DB session/loader strategy (→ `fastapi-database`), auth *hardening* (→ `fastapi-security-audit`), or whether the route should be `async def` (→ `fastapi-async-performance`).

## Inputs (adapter)

1. **App layout** — single `main.py` vs an `app/` package with `routers/` per resource and an app factory. Match it; routers are included via `app.include_router(...)`.
2. **Auth scheme** — OAuth2 password bearer / JWT, API key, session. Determines the security dependency (`Depends(get_current_user)`) and the default-deny posture.
3. **Error envelope** — does the project use a custom exception handler / standard error body? Route errors through it instead of hand-formatting per route.

## Route organization

- **One `APIRouter` per resource**, with `prefix="/items"` and `tags=["items"]`, included into the app. Keeps URLs consistent and docs grouped.
- **Route ordering matters** — a static path must be declared before a parameterized one that would match it (`/items/featured` before `/items/{item_id}`), or the dynamic route shadows it.
- **Path vs query params** — path for resource identity (`/items/{id}`), query for filtering/pagination/optional modifiers. Declare query params with types and defaults so they're validated and documented.
- Put cross-cutting dependencies at the router level (`APIRouter(dependencies=[Depends(...)])`) rather than repeating them on every operation.

## Dependency injection

- **`Depends()` is the seam** for shared logic: the DB session, the current user, pagination params, feature flags. Inject them as parameters; don't reach for globals.
- **`yield`-dependencies manage lifecycle** — acquire before `yield`, release after. The canonical DB-session dependency:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session            # released/closed after the response, even on error
```

  The cleanup after `yield` runs even if the path operation raises — this is how sessions/files/locks are guaranteed to close (→ `fastapi-database` owns the session semantics).
- **Sub-dependencies compose** — `get_current_active_user` depends on `get_current_user` depends on `oauth2_scheme`. Build authz as a chain of small dependencies, not one big function.
- **Dependencies are cached per-request** by default — the same `Depends(get_session)` resolves once per request. Rely on that rather than re-creating resources.

## Response & status declaration

- **Declare `response_model`** on every operation that returns data — it filters output to the declared (read) schema, so an ORM object with extra columns can't leak (→ `fastapi-pydantic`). Returning a model FastAPI doesn't filter is how fields escape.
- **Correct status codes:** `201` on create (`status_code=status.HTTP_201_CREATED`), `204` on delete (no body — return `None`), `200` default. Don't return `200` with an `{"error": ...}` body.
- **`response_model_exclude_none` / `response_model_exclude_unset`** when partial responses are intended — but prefer an explicit schema over excludes where you can.

## Error shaping

- **Raise `HTTPException(status_code=..., detail=...)`** with the right status: `400` bad input the schema can't express, `401` unauthenticated, `403` unauthorized, `404` not found, `409` conflict, `422` is FastAPI's automatic validation error (don't hand-roll it).
- **One error envelope across the API.** If the project has a custom exception handler (`@app.exception_handler(...)`), route errors through it; don't hand-format `{"error": ...}` in some routes and use `detail` in others.
- **Don't catch-and-swallow** into a generic `500` — let validation raise `422`, let `HTTPException` carry the status. A bare `except: return {"error": ...}` hides the real failure.

## Pagination & filtering

- **Every list endpoint is bounded.** Accept `limit` and `offset` (or a cursor) as query params with a **default and a hard cap** — an unbounded list dumps the whole table per request (availability + memory risk):

```python
def pagination(limit: int = Query(50, le=200, ge=1), offset: int = Query(0, ge=0)):
    return {"limit": limit, "offset": offset}
```

- Filtering/ordering params should be an **allowlist** — never let the client order by or filter on an arbitrary column name passed through to SQL.
- For deep pagination at scale, prefer cursor/keyset over `offset` (→ `fastapi-async-performance`).

## Red flags

- A path operation that returns data with **no `response_model`** (output unfiltered → field leak).
- A list endpoint with no `limit`/cap (unbounded result set).
- Validation logic in the route body instead of the Pydantic model (→ `fastapi-pydantic`).
- A DB session created inside the route instead of injected via a `yield`-dependency (leak/no cleanup).
- Hand-formatted error bodies inconsistent with the rest of the API; `200` returned with an error payload.
- A parameterized route declared before the static route it shadows.
- `204` responses returning a body, or `201` not set on a create.
- Ordering/filtering on a client-supplied column name with no allowlist.

## Report format

For an endpoint review, report per route: **method/path → dependencies (auth + session present?) → response_model (declared? leaks?) → status code correctness → pagination (bounded?) → error shape**. Flag every route missing `response_model`, every unbounded list, and every session not injected via a dependency.
