---
name: django-views-drf
description: Django view and Django REST Framework API patterns — FBV vs CBV vs generic views, DRF serializers (validation, nested writes, read/write field split), ViewSets & routers, permission/authentication classes, pagination, filtering, throttling, and consistent error/response shaping. Activates when writing or reviewing a Django view, a DRF serializer/viewset/api endpoint, an API permission or pagination choice, or diagnosing why an endpoint over-fetches, leaks fields, mis-validates, returns a 200 unfiltered list despite declared filterset_fields/search_fields/ordering_fields (no filter_backends, and DEFAULT_FILTER_BACKENDS defaults to empty), or silently drops an inherited permission when a get_permissions override omits super(). Defers query shaping to django-orm-models and auth hardening to django-security-audit.
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - view-style choice (FBV / CBV / DRF generic / ViewSet) and when each fits
  - DRF serializer rules (validation layering, read_only/write_only, nested create/update)
  - permission & authentication-class placement (object-level vs view-level)
  - pagination / filtering / ordering / throttling configuration rules
  - router/URL registration order (specific prefixes before any catch-all or empty prefix)
  - response & error-shaping consistency (status codes, error envelope, ValidationError use)
defers_to:
  - django-orm-models (get_queryset shaping, select_related/prefetch for the endpoint)
  - django-security-audit (auth model hardening, permission-bypass review, rate-limit policy)
  - django-performance (caching of responses, pagination at very large scale)
  - project API conventions (base serializer, error envelope, auth scheme — adapter input)
user-invocable: false
---

# django-views-drf

## Purpose

The request/response layer is where data shape, validation, and authorization meet. Bugs here leak fields, accept fields they shouldn't, validate in the wrong layer, or quietly N+1 on every list call. This skill owns the view-style decision and the DRF serializer/viewset/permission patterns that keep endpoints correct, paginated, and authorized by default.

## When to use

Activate when:

- Writing or reviewing a Django view (function- or class-based) or a DRF serializer, ViewSet, or API endpoint.
- Choosing a view style, permission class, pagination scheme, or filter backend.
- An endpoint over-fetches, leaks/accepts unexpected fields, returns inconsistent errors, or mis-validates input.

Do NOT use for the queryset's `select_related`/`prefetch` shaping (→ `django-orm-models`), the project's auth/permission *hardening* review (→ `django-security-audit`), or response caching (→ `django-performance`).

## Inputs (adapter)

1. **Is DRF in use?** Plain Django views/templates vs DRF API — the patterns diverge. If DRF, which version (affects `pagination`, `SearchFilter`, async views).
2. **Auth scheme** — session, token, JWT, OAuth. Determines the `authentication_classes` and the default permission posture.
3. **Base serializer / response conventions** — does the project have a base serializer, an error envelope, a standard pagination class? Match them.

## View-style choice

| Need | Use |
|---|---|
| One-off logic, full control, simple | Function-based view (`@api_view` for DRF) |
| Standard CRUD on one model | DRF `ModelViewSet` + router (least code, consistent URLs) |
| CRUD but you need to override pieces | Generic views (`ListCreateAPIView`, `RetrieveUpdateDestroyAPIView`) |
| Shared behavior across many views | CBV / mixins / a base ViewSet |
| Non-CRUD action on a resource | `@action` on a ViewSet |

Don't reach for a `ModelViewSet` when the endpoint isn't CRUD — forcing custom behavior through the viewset lifecycle is harder than a plain view.

**Router registration order matters the moment any prefix is empty.** A catch-all `router.register("", SettingsViewSet)` generates a detail route `^(?P<pk>[^/.]+)/$` that matches *any* single path segment, so every route registered after it is swallowed as a pk lookup on the catch-all — the new endpoint answers 400/404 from the wrong ViewSet, and nothing warns about the collision because both patterns are legal. Register specific prefixes **before** the empty one (or don't use an empty prefix at all), and smoke the new route right after wiring it rather than assuming registration means reachable.

## DRF serializer rules

- **Validation lives in the serializer, layered:** field-level `validate_<field>` for single-field rules, `validate(self, attrs)` for cross-field rules. Don't validate in the view. Raise `serializers.ValidationError` — DRF turns it into a 400 with the right shape.
- **Never expose the model blindly.** `fields = "__all__"` is a leak waiting to happen — it auto-includes new fields (including sensitive ones) on every model change. List fields explicitly.
- **Read vs write split:** `read_only=True` for server-computed/derived fields (ids, timestamps, status); `write_only=True` for inputs that must never echo back (passwords, tokens). A field that's writable when it shouldn't be is a mass-assignment bug.
- **Nested writes are not free.** Nested serializers are read-only by default; to create/update through them you must override `create()`/`update()` and handle the nested objects + transaction explicitly. Decide whether the nested resource should instead be its own endpoint.
- **`SerializerMethodField`** for computed read-only output; keep it cheap or it becomes a per-row N+1.
- **`source=`** to decouple the API field name from the model attribute — but a `source` that doesn't resolve fails **invisibly** on a read-only field. `read_only=True` implies `required=False`, so DRF turns the `AttributeError` from the missing attribute into `SkipField` and **omits the key from the response entirely**: 200, a well-formed payload, and the client reads `undefined`. Nothing raises, nothing logs, and a sibling field can be dead the same way for months. Check the `source` path against the real column name (a field renamed to `<name>_html` is the classic), and when a block "never appears" on a surface, suspect the serializer contract before a CSS or ordering cause. Lock it with a test that asserts the key is **present** and carries the expected value, not just that the request succeeded (→ `django-testing`).
- **Widening what a reference is allowed to point at makes every reader of it reachable in a new state.** Once a parent can be archived (or soft-deleted, or left unapproved) without taking its children, the child's update serializer starts refusing a resubmission that **changed nothing** — its related field validates against a live-only/default manager, so an untouched save returns `400 Invalid pk` naming a field the UI renders blank. Widen only that field's queryset to admit the instance's *own current value*, so an untouched round-trip passes while newly filing onto an archived parent is still refused. Then sweep every other writer, validator, and guard that reads the reference: survivors are now reachable in a state the write path was never written for. Delete/purge guards are the common miss — one that refuses only when the *root* has live dependents still lets a grandparent's purge destroy a live grandchild through the collector (→ `django-orm-models` on enumerating delete mechanisms).
- **DRF's auto `UniqueTogetherValidator` ignores a partial condition.** When a model's uniqueness is a partial `UniqueConstraint(condition=…)` (e.g. "unique name among *active* rows", "unique slug *per parent*"), `ModelSerializer` does not produce a correct validator for it — it derives `UniqueTogetherValidator` from `unique_together`/full unique constraints and **drops the `condition`**, so the auto-validator either never fires or rejects rows the DB would happily accept. Add a scope-aware `validate()` (or an explicit `UniqueTogetherValidator` whose `queryset` you filter to the same condition) on the serializer. The DB-side "a partial constraint is really a partial *index*" caveat → `django-orm-models`.

## Queryset shaping (defer the *how* to orm-models)

- Override **`get_queryset()`**, not a class-level `queryset`, when results depend on the request user (multi-tenant scoping, ownership). A class-level queryset evaluated once can leak across requests/tenants.
- Add `select_related`/`prefetch_related` for the relations the serializer touches — a list endpoint serializing a FK without `select_related` is an N+1 on every page. (The *rules* for which to use → `django-orm-models`.)

## Permissions & authentication

- **Default deny.** Set a restrictive `DEFAULT_PERMISSION_CLASSES` (e.g. `IsAuthenticated`) globally and loosen per-view — not the reverse. An endpoint with no permission class declared and a permissive default is an accidental public endpoint.
- **Object-level permissions** (`has_object_permission`) for "can this user touch *this* row" — view-level `has_permission` alone does not protect detail/update/delete of a specific object. Generic views call `check_object_permissions` via `get_object()`; if you fetch the object yourself, call it yourself.
- **A `get_permissions` override must keep the inherited classes.** Building the list from scratch — `return [IsAuthenticated()]` — silently drops any permission a base class or mixin contributed (an owner check, a tenant scope); the endpoint still answers 200, the guard is just gone. Extend, don't replace — start from `super().get_permissions()` (or `[p() for p in self.permission_classes]`) and append. The same trap hits `get_authenticators`/`get_throttles` overrides.
- **Personal, user-owned data is owner-scoped, not role/module-gated.** Saved searches, drafts, private notes and notification preferences belong to exactly one user: scope `get_queryset()` to `owner_id=request.user` behind a plain `IsAuthenticated`, and deliberately keep the model **out of any admin/module access registry** — an entry there means an admin-level bypass can read everyone's private rows, which is a privacy breach rather than an access-control convenience. Prove it with a test that runs as a **non-admin** and asserts a second user sees zero rows, *and* that a superuser also sees zero; a test written as an admin passes for the wrong reason. Enforce per-owner uniqueness in the serializer (owner is implicit in the request, so the DB's `(owner, key, name)` constraint would otherwise surface as a 500 instead of a 400).
- **Don't authorize in the serializer.** Serializers shape data; permissions decide access. Mixing them hides bypasses.

## Pagination, filtering, throttling

- **Every list endpoint is paginated.** An unpaginated list is an availability risk — one big table dumps the whole table per request. Set `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE`; cap `max_page_size` on client-controlled page sizes.
- **Filtering** via `django-filter` (`FilterSet`) or `filterset_fields`; **ordering** via `OrderingFilter` with an explicit `ordering_fields` allowlist (never allow ordering by arbitrary columns); **search** via `SearchFilter`.
- **Declaring filter fields without a backend is a silent no-op.** `filterset_fields`, `search_fields`, and `ordering_fields` do nothing unless the matching backend is active — `DjangoFilterBackend`, `SearchFilter`, and `OrderingFilter` respectively. If neither the ViewSet's own `filter_backends` nor the global `DEFAULT_FILTER_BACKENDS` includes them, the endpoint returns **200 with the full, unfiltered queryset** and no error — a `?search=`/`?ordering=` that looks wired but isn't, and a potential data-exposure bug. `DEFAULT_FILTER_BACKENDS` defaults to `[]`, so a project that never sets it globally must set `filter_backends` on each ViewSet (or a shared base). Prove it with a test that a filtered request returns *fewer* rows than the unfiltered one — a 200 alone means nothing here.
- **OR-within-a-facet needs an explicit `FilterSet`.** The `filterset_fields` shorthand cannot express a comma-separated `in`, so a multi-select UI has nothing to talk to. Declare `class CharInFilter(filters.BaseInFilter, filters.CharFilter)` (and a `UUIDInFilter(BaseInFilter, UUIDFilter)` for FKs) plus an explicit `status__in = CharInFilter(field_name="status", lookup_expr="in")`. Each `__in` ORs its own values while django-filter ANDs across filters — OR within a facet, AND across facets. **Keep the old exact lookups in `Meta.fields`**: single-value callers and any drill-down that sends `?status=published` break the moment you replace them, so add a regression test asserting the plain exact filter still works.
- **`filterset_fields` list → dict is backward compatible.** A list `["status"]` is exactly `{"status": ["exact"]}`, so converting to the dict form to add range/isnull lookups (`{"created_at": ["gte", "lt"], "created_by_id": ["exact", "isnull"]}`) changes no existing exact-filter behavior. That is the safe way to make date-bucket and null-FK drill-downs work through the existing list endpoint instead of adding a second one — re-run the app's filter tests to confirm nothing regressed.
- **Throttling** on auth, write, and expensive endpoints (`ScopedRateThrottle`). (Policy/limits → `django-security-audit`.)

## Response & error shaping

- Use correct status codes: 201 on create, 204 on delete (no body), 400 validation, 401 unauthenticated, 403 unauthorized, 404 not found, 409 conflict. Don't return 200 with an `{"error": ...}` body.
- Keep one error envelope across the API. If the project has a custom exception handler, route errors through it; don't hand-format errors in some views and use DRF defaults in others.
- Raise DRF exceptions (`ValidationError`, `PermissionDenied`, `NotFound`) rather than returning ad-hoc `Response(status=...)` — they're consistent and handler-aware.

## Red flags

- `fields = "__all__"` on a `ModelSerializer`.
- A list endpoint with no pagination class and no per-view pagination.
- A detail/update/delete view with only view-level permissions and no object-level check.
- Validation logic in the view body instead of the serializer.
- A class-level `queryset` that should be user-scoped via `get_queryset()`.
- A serializer FK/nested field rendered in a list view with no `select_related`/`prefetch_related` → N+1.
- `OrderingFilter` / filtering exposed without an allowlist of fields.
- `filterset_fields`/`search_fields`/`ordering_fields` declared but no `filter_backends` and no `DEFAULT_FILTER_BACKENDS` → filtering silently ignored, the full queryset returned 200.
- A `get_permissions`/`get_throttles` override returning a hand-built list without `super()` → an inherited permission/throttle mixin silently dropped.
- A partial `UniqueConstraint(condition=…)` relied on for validation with no serializer-side scoped validator → the auto `UniqueTogetherValidator` drops the condition (→ `django-orm-models`).
- A writable field that should be `read_only` (mass-assignment of `is_staff`, `owner`, `status`).
- A read-only field whose `source=` path doesn't resolve → DRF `SkipField`s it and the key vanishes from a 200 response with no error.
- A catch-all/empty-prefix router registration placed before more specific routes → the later routes are swallowed as pk lookups.
- A multi-value `__in` filter added by *replacing* the exact lookups in `Meta.fields` → single-value callers and drill-downs break silently.
- Personal, user-owned data registered in an admin/module access registry, or its privacy test written as an admin.
- A related-field queryset restricted to a live-only manager on a model whose parent can now be archived → untouched resubmits 400.

## Report format

For an endpoint review, report per-endpoint: **method/route → permission posture → fields exposed/accepted (flag any leak/over-accept) → pagination → query count for the list path → error shape**. Flag every default-permissive or unpaginated endpoint explicitly.
