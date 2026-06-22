---
name: django-views-drf
description: Django view and Django REST Framework API patterns — FBV vs CBV vs generic views, DRF serializers (validation, nested writes, read/write field split), ViewSets & routers, permission/authentication classes, pagination, filtering, throttling, and consistent error/response shaping. Activates when writing or reviewing a Django view, a DRF serializer/viewset/api endpoint, an API permission or pagination choice, or diagnosing why an endpoint over-fetches, leaks fields, or mis-validates. Defers query shaping to django-orm-models and auth hardening to django-security-audit.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - view-style choice (FBV / CBV / DRF generic / ViewSet) and when each fits
  - DRF serializer rules (validation layering, read_only/write_only, nested create/update)
  - permission & authentication-class placement (object-level vs view-level)
  - pagination / filtering / ordering / throttling configuration rules
  - response & error-shaping consistency (status codes, error envelope, ValidationError use)
defers_to:
  - django-orm-models (get_queryset shaping, select_related/prefetch for the endpoint)
  - django-security-audit (auth model hardening, permission-bypass review, rate-limit policy)
  - django-performance (caching of responses, pagination at very large scale)
  - project API conventions (base serializer, error envelope, auth scheme — adapter input)
user_invocable: false
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

## DRF serializer rules

- **Validation lives in the serializer, layered:** field-level `validate_<field>` for single-field rules, `validate(self, attrs)` for cross-field rules. Don't validate in the view. Raise `serializers.ValidationError` — DRF turns it into a 400 with the right shape.
- **Never expose the model blindly.** `fields = "__all__"` is a leak waiting to happen — it auto-includes new fields (including sensitive ones) on every model change. List fields explicitly.
- **Read vs write split:** `read_only=True` for server-computed/derived fields (ids, timestamps, status); `write_only=True` for inputs that must never echo back (passwords, tokens). A field that's writable when it shouldn't be is a mass-assignment bug.
- **Nested writes are not free.** Nested serializers are read-only by default; to create/update through them you must override `create()`/`update()` and handle the nested objects + transaction explicitly. Decide whether the nested resource should instead be its own endpoint.
- **`SerializerMethodField`** for computed read-only output; keep it cheap or it becomes a per-row N+1.
- **`source=`** to decouple the API field name from the model attribute.

## Queryset shaping (defer the *how* to orm-models)

- Override **`get_queryset()`**, not a class-level `queryset`, when results depend on the request user (multi-tenant scoping, ownership). A class-level queryset evaluated once can leak across requests/tenants.
- Add `select_related`/`prefetch_related` for the relations the serializer touches — a list endpoint serializing a FK without `select_related` is an N+1 on every page. (The *rules* for which to use → `django-orm-models`.)

## Permissions & authentication

- **Default deny.** Set a restrictive `DEFAULT_PERMISSION_CLASSES` (e.g. `IsAuthenticated`) globally and loosen per-view — not the reverse. An endpoint with no permission class declared and a permissive default is an accidental public endpoint.
- **Object-level permissions** (`has_object_permission`) for "can this user touch *this* row" — view-level `has_permission` alone does not protect detail/update/delete of a specific object. Generic views call `check_object_permissions` via `get_object()`; if you fetch the object yourself, call it yourself.
- **Don't authorize in the serializer.** Serializers shape data; permissions decide access. Mixing them hides bypasses.

## Pagination, filtering, throttling

- **Every list endpoint is paginated.** An unpaginated list is an availability risk — one big table dumps the whole table per request. Set `DEFAULT_PAGINATION_CLASS` + `PAGE_SIZE`; cap `max_page_size` on client-controlled page sizes.
- **Filtering** via `django-filter` (`FilterSet`) or `filterset_fields`; **ordering** via `OrderingFilter` with an explicit `ordering_fields` allowlist (never allow ordering by arbitrary columns); **search** via `SearchFilter`.
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
- A writable field that should be `read_only` (mass-assignment of `is_staff`, `owner`, `status`).

## Report format

For an endpoint review, report per-endpoint: **method/route → permission posture → fields exposed/accepted (flag any leak/over-accept) → pagination → query count for the list path → error shape**. Flag every default-permissive or unpaginated endpoint explicitly.
