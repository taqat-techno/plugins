---
description: Scaffold a Django app or a single model surface (model + admin + migration + tests, and optionally DRF serializer/viewset/urls) applying the django plugin's skill set. Plans the file diff and waits for approval before writing.
argument-hint: "[app-name] [--model Name] [--api] [--no-api]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# /django-scaffold — Scaffold a Django app or model surface

You are scaffolding Django code that matches the project's existing conventions. Apply the plugin skills throughout:

- `django-orm-models` — field/relation choices, `on_delete`, constraints, indexes, base-model inheritance.
- `django-views-drf` — if `--api`, explicit serializer fields (never `__all__`), viewset, router, paginated list, default-deny permission.
- `django-migrations` — generate the migration through the gate; never hand-write or auto-trust it.
- `django-settings-config` — register the app in `INSTALLED_APPS` in the right settings module.
- `django-testing` — tests use the project's runner/factories; include a negative-path test and, for list endpoints, an `assertNumQueries`.
- `django-security-audit` — no privileged field (`is_staff`, `owner`, `price`, `status`) writable from the API by default.

## Step 0 — Load context

Read `.django-kit.local.json`. If absent, detect the project yourself first (read-only — don't ask the user to do it manually). You need: `managePrefix`, `localApps`, `settingsModules`, `dbBackend`, `drf.present`, `testRunner`, base-model convention.

## Step 1 — Decide what to scaffold

- **New app** (`app-name` not in `localApps`): scaffold the app skeleton via the project's own tooling (`<managePrefix> startapp <app-name>`) so layout matches Django's, then layer the model/admin/tests/API onto it. Register it in `INSTALLED_APPS` in the correct settings module.
- **New model in an existing app** (`--model Name`, or `app-name` is an existing app): add the model + admin + migration + tests to it.

API generation: default to the project norm — if DRF is present, include API unless `--no-api`; if DRF is absent, skip API unless `--api` (and if `--api` without DRF, tell the user DRF isn't installed and stop short of inventing it).

## Step 2 — Model intake

Argument `--model Name` is the singular model name. If absent, ask. Then gather:

- **Fields** — for each: `name`, `type` (char/text/int/decimal/bool/date/datetime/email/url/file/image/FK/M2M/O2O/JSON/UUID), `null`/`blank`, `default`, `choices`, `unique`, indexed.
- **Relations** — for each FK/M2M/O2O: target model, `on_delete` (make the user choose — never default `CASCADE` silently for it), `related_name`.
- **Constraints** — uniqueness (incl. conditional), check constraints, composite indexes.
- **`__str__`** and `Meta` (`ordering`, `verbose_name`).
- **Base model** — inherit the project's abstract base (timestamped/uuid) if one exists.

## Step 3 — Plan the file diff

Before writing, list every file you will create or modify:

```
PLAN  (app: orders, model: Order, api: yes)
  CREATE  orders/models.py                    ← Order model
  MODIFY  orders/admin.py                     ← register OrderAdmin
  CREATE  orders/serializers.py               ← OrderSerializer (explicit fields)
  CREATE  orders/views.py                     ← OrderViewSet (paginated, IsAuthenticated)
  CREATE  orders/urls.py                      ← router registration
  MODIFY  config/urls.py                      ← include orders.urls
  MODIFY  config/settings/base.py            ← add "orders" to INSTALLED_APPS  (new app only)
  CREATE  orders/tests/test_models.py         ← model + constraint tests
  CREATE  orders/tests/test_api.py            ← API contract + permission + assertNumQueries
  GEN     orders/migrations/000X_order.py     ← via makemigrations (Step 5)
```

Tailor paths to the detected layout. **Wait for the user to approve the plan before writing.**

## Step 4 — Write the code

- Model: explicit `on_delete`/`related_name`, DB-level constraints (not just validators), indexes on filtered fields, `__str__`, `Meta`.
- Serializer: list fields **explicitly**; `read_only` for server-set fields; no privileged field writable.
- ViewSet: `get_queryset()` with `select_related`/`prefetch_related` for serialized relations; pagination; `IsAuthenticated` (or stricter) by default; object-level permission stub where ownership applies.
- Admin: `list_display`, `search_fields`, `list_filter`, `readonly_fields` for computed fields.
- Tests: model/constraint test, API happy-path + 401/403 + validation-error, and `assertNumQueries` on the list endpoint.
- Do NOT write business logic — leave clearly-marked `# TODO` where the user adds domain rules.

## Step 5 — Migration through the gate

Run `<managePrefix> makemigrations <app>`, then **read the generated migration** and `sqlmigrate` it. Confirm it matches intent and is reversible. Do not run `migrate` — that's `/django-migrate`'s job. Report the migration file path and what it does.

## Step 6 — Verify & report

1. Grep your output for `fields = "__all__"`, writable privileged fields, missing `on_delete`, and missing pagination — fix any hit.
2. Confirm the app is registered (new app) and URLs are wired (API).
3. Report:

```
SCAFFOLDED orders.Order
  Files created:  6     Files modified: 3
  Migration:      orders/migrations/0003_order.py  (reviewed, reversible, NOT yet applied)
  API:            OrderViewSet  (paginated, IsAuthenticated, owner-scoped queryset)
  Tests:          3 (incl. 1 negative-path, 1 assertNumQueries)
  TODO markers:   2     ← orders/views.py:18, orders/models.py:24
  Next:           /django-migrate   then   /django-test orders
```
