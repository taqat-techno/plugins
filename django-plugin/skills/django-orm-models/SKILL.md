---
name: django-orm-models
description: Django model design and ORM query discipline — field/relation modeling, database constraints and indexes, transaction boundaries, and the N+1 / over-fetch query rules (select_related vs prefetch_related, only/defer, bulk operations, QuerySet laziness). Activates when designing or editing a Django model, writing or reviewing ORM queries, diagnosing slow or duplicated queries, choosing select_related vs prefetch_related, or deciding where a transaction boundary belongs. Defers migration mechanics to django-migrations and caching to django-performance.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - model field & relation modeling rules (FK/M2M/O2O, on_delete, related_name, null vs blank)
  - database-level integrity rules (CheckConstraint, UniqueConstraint, db_index, Meta.indexes)
  - the N+1 detection + fix decision (select_related for FK/O2O, prefetch_related for M2M/reverse FK)
  - over-fetch rules (only/defer, values/values_list, exists/count vs len/bool)
  - bulk-operation rules (bulk_create/bulk_update/in_bulk, update() vs save() loops)
  - transaction-boundary rules (atomic scope, select_for_update, on_commit)
defers_to:
  - django-migrations (how a model change becomes a safe migration)
  - django-performance (caching, denormalization, async, pagination at scale)
  - django-views-drf (serializer-side query shaping for API responses)
  - project model layout & base-model conventions (adapter input)
user_invocable: false
---

# django-orm-models

## Purpose

Most Django performance and correctness bugs are decided at two moments: how a model is shaped, and how its rows are fetched. This skill owns both — the field/relation/constraint choices that make bad states unrepresentable at the database level, and the QuerySet discipline that keeps a request from issuing hundreds of queries.

## When to use

Activate when:

- Designing a new model or editing fields/relations on an existing one.
- Writing or reviewing ORM queries (views, serializers, managers, management commands).
- A page or endpoint is slow and the query count looks suspicious (N+1).
- Choosing between `select_related` and `prefetch_related`, or whether to add `only`/`defer`.
- Deciding where a transaction boundary belongs or whether a row needs locking.

Do NOT use for: writing the migration file itself (→ `django-migrations`), caching strategy (→ `django-performance`), or DRF serializer structure (→ `django-views-drf`).

## Inputs (adapter)

1. **Database backend** — PostgreSQL, MySQL, SQLite, etc. Determines which constraints/index types are available (e.g. partial indexes, `GinIndex`, deferrable constraints are Postgres-only).
2. **Base model convention** — does the project use an abstract `TimeStampedModel` / `UUIDModel` base? New models should inherit it.
3. **Django version** — affects available APIs (`Meta.constraints`, `bulk_update`, `QuerySet.alias`, async ORM `aget`/`acreate`).

## Model design rules

### Relations

- **`on_delete` is mandatory and meaningful.** Choose deliberately: `CASCADE` (child owned by parent), `PROTECT` (block deletion — referential safety), `SET_NULL` (requires `null=True`), `RESTRICT`. Never default to `CASCADE` for financial/audit rows.
- **Always set `related_name`** (or `related_name="+"` to disable the reverse accessor). Unnamed reverse accessors (`foo_set`) are ambiguous when a model has two FKs to the same target.
- **`null` vs `blank`**: `null` is database-level (column nullable), `blank` is validation-level (form/serializer allows empty). For string fields prefer `blank=True` without `null=True` — Django convention is empty string, not NULL, to avoid two "empty" states.
- **M2M with extra data → explicit `through` model.** The moment a relationship needs its own attributes (role, quantity, joined-at), model the join table, don't bolt fields elsewhere.

### Integrity at the database, not just in Python

Push invariants down to the DB so concurrent writers can't violate them:

- **`UniqueConstraint`** (with `condition=` for partial uniqueness, e.g. "one active row per user") over the older `unique_together`.
- **`CheckConstraint`** for value invariants (`amount >= 0`, `end_date >= start_date`).
- **`db_index=True`** on fields you filter/order by frequently; `Meta.indexes` for composite/conditional indexes. Don't index everything — each index is write cost.
- Validators (`MinValueValidator`, etc.) are convenience, not a substitute for constraints — they run only when `full_clean()` is called, which `save()` does NOT call automatically.

## Query discipline — the N+1 rule

A loop that touches a related object on each iteration issues one query per row. Fix by fetching relations up front:

| Relation being accessed | Fix |
|---|---|
| Forward FK / OneToOne (single related object) | `select_related("author")` — SQL JOIN, one query |
| Reverse FK / ManyToMany (set of related objects) | `prefetch_related("comments")` — second query + Python join |
| Nested / filtered prefetch | `prefetch_related(Prefetch("comments", queryset=Comment.objects.filter(...)))` |

```python
# N+1: one query for posts, then one per post for .author
for post in Post.objects.all():
    print(post.author.name)

# Fixed: 1 query total
for post in Post.objects.select_related("author"):
    print(post.author.name)
```

**Diagnose, don't guess.** Confirm an N+1 with evidence before "fixing" it: `len(connection.queries)` under `DEBUG`, `django-debug-toolbar`, `assertNumQueries` in a test, or `QuerySet.explain()`. Adding `prefetch_related` where it isn't needed adds a query.

## Over-fetch rules

- **`only(...)` / `defer(...)`** when you read a few columns off wide rows — but accessing a deferred field triggers a per-row query (a new N+1). Only defer fields you truly won't touch.
- **`values()` / `values_list()`** when you need dicts/tuples, not model instances (reports, exports) — skips model instantiation entirely.
- **`exists()`** instead of `if queryset:` (which evaluates the whole set). **`count()`** instead of `len(queryset)` when you don't need the rows.
- **`iterator()`** for large reads you process once, to avoid caching the whole result set in memory.

## Bulk operations

- **`bulk_create(objs)`** / **`bulk_update(objs, fields)`** instead of a `save()` loop. Note: `bulk_create` does NOT call `save()`, send `pre_save`/`post_save` signals, or (on most backends) populate PKs unless supported.
- **`QuerySet.update(...)`** for set-based writes — one UPDATE statement, but also bypasses `save()` and signals and does not call `auto_now`. Choose consciously.
- **`in_bulk()`** to fetch a set of PKs into a dict in one query.

## Transactions & concurrency

- Wrap multi-write invariants in **`transaction.atomic()`** so partial failure rolls back. Keep the atomic block as small as the invariant requires — long transactions hold locks.
- **`select_for_update()`** (inside `atomic`) to lock rows you read-then-modify, preventing lost updates under concurrency (e.g. decrementing stock).
- **`transaction.on_commit(callback)`** for side effects that must only fire if the transaction commits (enqueue a Celery task, send an email) — never enqueue inside the transaction, or the worker may run before the row is visible.
- Beware: signals and `save()` inside `atomic` still run; only the DB write rolls back, not external side effects already performed.

## Red flags to call out in review

- A `for` loop with `.author` / `.related_set.all()` inside and no `select_related`/`prefetch_related` upstream → N+1.
- `len(qs)` / `if qs:` used only to check presence/size → use `count()`/`exists()`.
- `Model.objects.get(...)` without handling `DoesNotExist` / `MultipleObjectsReturned`.
- A `save()` loop over many rows → `bulk_create`/`bulk_update`/`update`.
- Enqueuing a task or sending mail inside `atomic()` without `on_commit`.
- `on_delete=CASCADE` on a reference to audit/financial data.
- A uniqueness/invariant enforced only in Python (or only in a serializer) with no DB constraint.

## Report format

When reviewing queries, report each finding as: **location → symptom (with query-count evidence) → fix → estimated query reduction**. Do not claim an N+1 without showing how you counted.
