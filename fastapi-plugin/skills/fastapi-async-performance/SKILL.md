---
name: fastapi-async-performance
description: FastAPI async correctness and performance at scale — the sync-def-vs-async-def path-operation decision, never blocking the event loop (run_in_threadpool for blocking I/O, async drivers, no sync requests/time.sleep/sync-DB in async routes), background tasks vs a real task queue, caching layers + invalidation, database connection-pool sizing, pagination at scale (cursor vs offset), and measuring the real bottleneck before changing anything. Activates when an endpoint/task is slow, when a route blocks under load, when adding caching or background work, or when planning for scale. Defers per-query loader rules to fastapi-database.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - the sync-def vs async-def path-operation rule (and why a sync def runs in the threadpool)
  - event-loop-safety rule (no blocking I/O in async; run_in_threadpool; async drivers/clients)
  - background-work rule (BackgroundTasks for light, Celery/RQ/arq for heavy/durable/retryable)
  - caching-layer selection + invalidation rules
  - connection-pool sizing (pool_size/max_overflow vs worker/concurrency count) and pagination at scale
  - measure-first rule (find the real bottleneck before optimizing)
defers_to:
  - fastapi-database (selectinload/joinedload per-query rules; N+1 mechanics; session semantics)
  - fastapi-migrations (how an index/backfill becomes a safe revision)
  - fastapi-config (where pool sizes / cache backend URLs are configured)
  - project infra (cache server, broker, worker topology — adapter input)
user_invocable: false
---

# fastapi-async-performance

## Purpose

FastAPI's performance story is an async story, and the failure mode is specific: one blocking call inside an `async def` route stalls the entire event loop, so every concurrent request waits — the framework's concurrency silently collapses to serial. This skill owns async correctness first (it's the bug that dwarfs the others), then the usual levers: offloading work, caching with correct invalidation, sizing the connection pool, and paginating at scale — all after measuring the real bottleneck. Per-query loader mechanics live in `fastapi-database`; this is the layer around them.

## When to use

Activate when:

- An endpoint, task, or query is slow, or throughput collapses under concurrency.
- A route makes a blocking call (HTTP, file, sleep, sync DB) and you're deciding how to run it.
- Adding caching, a background task, or offloading work to a queue.
- Planning for scale / a load increase / a large dataset.

Defer per-query `selectinload`/`joinedload`/session rules to `fastapi-database` — assume those are applied; this skill is the next layer.

## Inputs (adapter)

1. **Async or sync stack** — async routes + async driver (`asyncpg`/`aiosqlite` + `AsyncSession`), or sync routes + sync driver. The event-loop rules apply to the async stack; a fully sync app is a different (threadpool) model.
2. **Where the bottleneck is** — event-loop blocking, DB, Python CPU, external call, or N+1 (resolve N+1 via `fastapi-database` first). Don't optimize without this.
3. **Infra** — cache backend (Redis), broker/worker (Celery/RQ/arq), worker/process count, and what's shared vs per-process.

## The sync-def vs async-def rule

FastAPI runs path operations two ways:

- **`async def`** — runs **on the event loop**. Everything inside must be non-blocking: `await` async I/O only. A blocking call here freezes *all* concurrent requests.
- **`def`** (sync) — FastAPI runs it in an **external threadpool**, so a blocking call there doesn't freeze the loop (but threadpool size bounds concurrency).

The decision:

- All-`await` async libraries (async DB session, `httpx.AsyncClient`) → **`async def`**.
- Only blocking libraries available (a sync SDK, sync DB driver, CPU work) and you don't want to manage threads → a plain **`def`** route is correct and safe (threadpool handles it).
- **The trap is the mix:** `async def` with a blocking call inside. That's the worst of both — pick one. Either make the call async, or move it off the loop with `run_in_threadpool`.

## Never block the event loop

Inside `async def` (or any code on the loop):

- **No `time.sleep`** → `await asyncio.sleep`.
- **No sync HTTP** (`requests`, `urllib`) → `httpx.AsyncClient` with `await`.
- **No sync DB driver / `Session`** → async driver + `AsyncSession` (→ `fastapi-database`).
- **No blocking file / CPU-bound work** on the loop → `await run_in_threadpool(fn, ...)` (Starlette) for blocking I/O; a process pool / external worker for CPU-bound.

```python
from starlette.concurrency import run_in_threadpool

@router.post("/render")
async def render(payload: In):
    # heavy sync library that has no async variant
    result = await run_in_threadpool(render_pdf, payload)   # off the loop
    return result
```

The plugin's write-guard flags `time.sleep`/`requests.*`/blocking `urlopen` inside files containing `async def` — treat that as a real finding, not noise.

## Offload slow work

- **`BackgroundTasks`** for light, fire-after-response work that can tolerate being lost on a crash (send a confirmation email, write a log) — it runs in the same process after the response is sent.
- **A real task queue** (Celery / RQ / arq) for anything heavy, durable, retryable, or scheduled (PDF generation, third-party sync, long jobs). `BackgroundTasks` is **not** durable — a process restart drops it; don't use it for must-not-lose work.
- Enqueue **after** the DB transaction commits, so the worker doesn't read a row that isn't visible yet (→ `fastapi-database`).

## Caching layers (and invalidation)

Pick the narrowest layer that solves it:

| Layer | Granularity | Best for |
|---|---|---|
| In-process / `lru_cache` | per-process function results | pure, small, stable computations (e.g. settings) |
| Distributed cache (Redis) | arbitrary keyed values | expensive query/computed results shared across workers |
| HTTP caching (ETag / Cache-Control) | whole response | cacheable GETs, CDN/proxy in front |

- **Invalidation is the hard part.** Prefer key-based/versioned keys or event-driven invalidation over guessing TTLs. A stale cache serving wrong data is worse than a slow one.
- **`lru_cache` is per-process** — fine for settings/constants, wrong for shared mutable data across workers (use Redis).
- **Never cache a per-user/auth-varying response** without keying on the user — you'll serve one user's data to another (a perf *and* security bug).

## Connection pool & pagination at scale

- **Size the DB pool to the workers/concurrency, not arbitrarily.** `pool_size` + `max_overflow` per process × number of processes must stay under the database's connection limit, or you exhaust it. Tune deliberately (→ `fastapi-config` holds the values); a pooler (PgBouncer) helps at high process counts.
- **Offset pagination degrades on deep pages** (`OFFSET 100000` scans and discards). For large/infinite scroll use **keyset/cursor pagination** — `WHERE id > :last_seen ORDER BY id LIMIT :n` with an index. (→ `fastapi-routing` owns the param shape.)
- Stream large exports (`StreamingResponse` + an async generator) instead of materializing the whole result set in memory.

## Measure-first rule

Never optimize on intuition. Identify the bottleneck with evidence:

- Count and time DB statements (SQLAlchemy `echo` / an event listener / a query-count test) — is it N+1, slow SQL, or pool waits?
- `EXPLAIN ANALYZE` for query plans (seq scan vs index).
- A profiler (`py-spy`, `cProfile`) when time is in Python; check whether the loop is blocked (latency spikes under concurrency that vanish single-threaded ⇒ a blocking call).

State the measured bottleneck before proposing a change, and re-measure after. A "fix" with no before/after number is unverified.

## Red flags

- An `async def` route containing `time.sleep`, `requests.*`, `urlopen`, or a sync DB session — blocks the loop for all requests.
- A blocking/CPU-bound call on the loop with no `run_in_threadpool` / worker offload.
- `BackgroundTasks` used for must-not-lose or heavy/retryable work (should be a queue).
- A task enqueued before the transaction commits.
- Caching a per-user response without keying on the user; TTL-only caching of data that must be correct.
- `lru_cache` used for shared mutable data across workers.
- A DB pool sized without regard to process/worker count (connection exhaustion).
- `OFFSET` pagination on deep pages of a large table.
- An optimization proposed with no measurement behind it.

## Report format

Always lead with the **measured bottleneck** (the number — query count, latency, whether the loop was blocked), then the change, then the **re-measured result**. For async findings, state explicitly whether the route is `async def` and what blocks the loop. For scale work, state the data size and worker/pool assumptions. Don't present a caching layer without naming its invalidation strategy.
