---
name: django-performance
description: Django performance and scale — query optimization beyond N+1 (annotate/aggregate at the DB, indexing for real query shapes, pagination strategy at scale), the caching layers (per-view, template fragment, low-level cache API, queryset/object cache, cache invalidation), database connection reuse, offloading slow work to Celery/async, and finding the actual bottleneck before changing anything. Activates when an endpoint/page/job is slow, when adding caching, when planning for scale/load, or when batching a large backfill. Defers per-query select_related rules to django-orm-models.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - measure-first rule (profile/identify the real bottleneck before optimizing)
  - DB-side computation rules (annotate/aggregate/F-expressions vs Python-side loops)
  - indexing-for-query-shape rules (index the actual filter/order/join, not every column)
  - caching-layer selection + invalidation rules (per-view / fragment / low-level / object)
  - connection reuse (CONN_MAX_AGE) & pagination-at-scale (keyset vs offset)
  - offloading rule (move slow/blocking work to Celery/async; throttle large backfills)
defers_to:
  - django-orm-models (select_related/prefetch/only/defer per-query rules; N+1 mechanics)
  - django-migrations (how an index/backfill becomes a safe migration)
  - django-settings-config (cache backend wiring & CONN_MAX_AGE values)
  - project infra (cache server, broker, worker topology — adapter input)
user_invocable: false
---

# django-performance

## Purpose

Performance work goes wrong when it starts from a guess. This skill owns the discipline of finding the real bottleneck first, then the levers that actually move it at scale: computing in the database instead of Python, indexing for the queries you actually run, caching at the right layer with correct invalidation, reusing connections, and offloading slow work off the request path. N+1 mechanics live in `django-orm-models`; this is everything past that.

## When to use

Activate when:

- An endpoint, page, query, or background job is slow (and you've gone past the obvious N+1).
- Adding caching anywhere.
- Planning for scale / a load increase / a large dataset.
- Batching a large backfill or bulk operation.

Defer the per-query `select_related`/`prefetch_related`/`only` rules to `django-orm-models` — assume those are already applied; this skill is the next layer.

## Inputs (adapter)

1. **Where the bottleneck is** — DB, Python, external call, or N+1 (resolve N+1 via `django-orm-models` first). Don't optimize without this.
2. **Cache + broker infra** — Redis/Memcached presence, Celery/RQ/Dramatiq or async, and what's shared vs per-process.
3. **Data scale** — table sizes and growth; "slow on 10M rows" needs different answers than "slow on 1k".

## Measure-first rule

Never optimize on intuition. Identify the bottleneck with evidence:

- `django-debug-toolbar` (query count, duration, duplicate queries) for request-path work.
- `QuerySet.explain()` / `EXPLAIN ANALYZE` for query plans (seq scan vs index scan, row estimates).
- `connection.queries` count + timing, or `assertNumQueries` to characterize.
- A profiler (`cProfile`, `py-spy`, `silk`) when the time is in Python, not SQL.

State the measured bottleneck before proposing a change, and re-measure after. A "fix" with no before/after number is unverified.

## Compute in the database, not in Python

- **`annotate()` / `aggregate()`** to compute sums/counts/averages in one query instead of looping in Python. Pulling rows to Python to sum them is the most common avoidable cost.
- **`F()` expressions** for field-relative updates (`F("views") + 1`) — atomic, no read-modify-write race, no row fetch.
- **Conditional aggregation** (`Count(..., filter=Q(...))`, `Case/When`) to get grouped breakdowns in a single query.
- **`Subquery`/`OuterRef`** to attach a per-row computed value without a second round-trip per row.

## Indexing for the real query shape

- Index the columns you actually filter, order, and join on — read the slow query's `WHERE`/`ORDER BY`/`JOIN`, then index that. A composite index's column order must match the query's leading filter/sort.
- Use **partial/conditional indexes** (`condition=`) for queries that always filter the same predicate (e.g. `is_active=True`).
- Don't over-index: every index slows writes and consumes storage. Verify an index is actually used (`EXPLAIN`) — an unused index is pure write tax.
- Index changes ship as migrations — large tables need concurrent index creation (→ `django-migrations`).

## Caching layers (and invalidation)

Pick the narrowest layer that solves it:

| Layer | Granularity | Best for |
|---|---|---|
| Low-level cache API (`cache.get/set`) | arbitrary values | expensive computed results, fragments of logic — most control |
| Template fragment (`{% cache %}`) | template region | expensive-to-render, slow-changing UI blocks |
| Per-view cache (`cache_page`) | whole response | anonymous, slow-changing pages (careful with auth/per-user) |
| Cached property / `Prefetch` | per-instance | repeated access within one request |

- **Invalidation is the hard part.** Prefer key-based/versioned keys or signal-driven invalidation over guessing TTLs. A stale cache serving wrong data is worse than a slow one.
- **Never `cache_page` a per-user or auth-varying response** without varying the key on the user — you'll serve one user's data to another. This is both a perf and a security bug.
- Use a real shared backend (Redis/Memcached) in prod; `locmem` is per-process and won't be consistent across workers (→ `django-settings-config`).

## Connection reuse & pagination at scale

- **`CONN_MAX_AGE`** > 0 to reuse DB connections instead of opening one per request (or use a pooler like PgBouncer). Connection setup cost dominates many small-query endpoints.
- **Offset pagination degrades on deep pages** (`OFFSET 100000` scans and discards). For large/infinite scroll use **keyset (cursor) pagination** — filter on `WHERE id > last_seen` with an index. DRF `CursorPagination` implements this.
- Stream large exports with `iterator()` + a streaming response; don't materialize the whole result set.

## Offload slow work

- Anything slow or blocking on the request path (email, PDF, third-party calls, image processing) → **Celery/RQ/async task**. The user shouldn't wait on it.
- Enqueue with **`transaction.on_commit`** so the task only runs after the row is committed and visible (→ `django-orm-models`).
- **Batch and throttle large backfills** — chunk by PK ranges, `bulk_update` per chunk, and pause between chunks to avoid saturating the DB/replication. A single `update()` over 50M rows locks and lags replicas.

## Red flags

- An optimization proposed with no profiling/measurement behind it.
- Python-side summation/counting where `aggregate`/`annotate` would do it in SQL.
- Read-modify-write counters instead of `F()` (lost-update race + extra query).
- `cache_page` / fragment cache on per-user content without keying on the user.
- TTL-only caching of data that must be correct, with no invalidation path.
- `OFFSET` pagination on deep pages of a large table.
- `CONN_MAX_AGE = 0` (default) under high request volume with no pooler.
- A multi-million-row `update()`/backfill in one statement, unbatched.

## Report format

Always lead with the **measured bottleneck** (the number), then the change, then the **re-measured result**. For scale work, state the data size the recommendation assumes. Don't present a caching layer without naming its invalidation strategy.
