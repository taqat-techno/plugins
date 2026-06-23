---
name: fastapi-pydantic
description: Pydantic v2 model design for FastAPI — request vs response model separation, field validation (field_validator/model_validator), constraints (Field, EmailStr, conint), read/write field discipline, the input/output split that stops field leaks and mass-assignment, ORM serialization (from_attributes), and aliasing. Activates when defining or editing a Pydantic model/schema, validating request input, shaping a response body, or diagnosing why an endpoint leaks/over-accepts fields or mis-validates. Defers routing wiring to fastapi-routing and the ORM model to fastapi-database.
version: 0.1.0
last_reviewed: 2026-06-23
owns:
  - request-vs-response model separation (distinct schemas per direction; never one model both ways)
  - field discipline (explicit fields; never echo the ORM/DB model directly as a response)
  - validation layering (field_validator for single-field, model_validator for cross-field)
  - read/write split (response-only computed fields, write-only/never-echoed inputs, mass-assignment prevention)
  - constraint rules (Field(gt/le/min_length/max_length/pattern), EmailStr, typed fields over str)
  - ORM serialization config (from_attributes / model_config) and field aliasing (alias, serialization_alias)
defers_to:
  - fastapi-routing (response_model wiring, status codes, dependency injection)
  - fastapi-database (the SQLAlchemy/SQLModel ORM model the schema maps to)
  - fastapi-security-audit (the security verdict on a field leak / mass-assignment)
  - project schema conventions (base schema, naming, error envelope — adapter input)
user_invocable: false
---

# fastapi-pydantic

## Purpose

In FastAPI the Pydantic model *is* the contract — it decides what the API accepts, what it returns, and what it validates. The recurring bugs are structural: one model reused for input and output (so the create body accepts `id`/`is_admin` and the response echoes a password hash), validation pushed into the route body, and the ORM object handed straight back as the response (every column, including the ones added next week). This skill owns schema shape, validation layering, and the input/output split.

## When to use

Activate when:

- Defining or editing a Pydantic model / schema (request body, response, query params object).
- Adding validation to request input, or deciding which layer a rule belongs in.
- Shaping a response body — choosing which fields to expose and which to compute.
- An endpoint leaks a field it shouldn't, accepts a field it shouldn't, or mis-validates input.

Do NOT use for: wiring `response_model` / status codes onto the route (→ `fastapi-routing`), the SQLAlchemy/SQLModel ORM model itself (→ `fastapi-database`), or the security verdict on a leak (→ `fastapi-security-audit`).

## Inputs (adapter)

1. **Pydantic major version** — v2 (`field_validator`, `model_validator`, `ConfigDict`, `model_config = ConfigDict(from_attributes=True)`) vs v1 (`validator`, `class Config`, `orm_mode`). The APIs differ; match the project's version. This skill assumes **v2** unless the project is on v1.
2. **ORM in use** — SQLAlchemy, SQLModel (where the table model *is* a Pydantic model — extra care not to expose it directly), or none. Decides whether `from_attributes` is needed.
3. **Base schema / naming convention** — does the project use a base `Schema`/`CamelModel`, a `*Create`/`*Read`/`*Update` suffix scheme, an error envelope? Match it.

## Request-vs-response separation (the core rule)

One model per direction, never one model for both:

```python
class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price: Decimal = Field(gt=0)

class ItemCreate(ItemBase):           # request: what a client may set
    pass

class ItemUpdate(BaseModel):          # request: all-optional for PATCH
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price: Decimal | None = Field(default=None, gt=0)

class ItemRead(ItemBase):             # response: what the server returns
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

- The **create** schema excludes server-controlled fields (`id`, `created_at`, `owner_id`, `is_admin`) — if it's writable, a client can set it. This is the mass-assignment boundary.
- The **read** schema is the only thing that should ever be returned. Never return the ORM object directly as a response — set `response_model=ItemRead` (→ `fastapi-routing`) so output is filtered to declared fields.
- The **update** schema is typically all-optional (`X | None` with defaults) so PATCH can send a subset; use `exclude_unset=True` when applying it.

## Field discipline

- **List fields explicitly via typed schemas.** The FastAPI analogue of "expose every column" is returning the SQLAlchemy/SQLModel table model as the response or setting `response_model` to it — new/sensitive columns then leak automatically. Define an explicit `*Read` model.
- **Never include secrets in a response model** — `hashed_password`, tokens, internal flags. If a field must be accepted but never returned, keep it out of the read schema entirely (a write-only input field that has no place in output).
- **Prefer typed fields over bare `str`** — `EmailStr`, `AnyUrl`, `Decimal`, `conint`/`Field(gt=...)`, `UUID`, enums. The type *is* the validation; a bare `str` for an email validates nothing.
- **`extra="forbid"`** on request models (`model_config = ConfigDict(extra="forbid")`) to reject unknown fields instead of silently ignoring them — surfaces client mistakes and blocks smuggled fields.

## Validation layering

- **`@field_validator("field")`** for single-field rules (normalize, range, format beyond the type).
- **`@model_validator(mode="after")`** for cross-field rules (`end_date >= start_date`, "exactly one of A/B set"). Use `mode="after"` so you validate parsed, typed values.
- **Validate in the schema, not the route.** A route body doing `if not body.x: raise HTTPException(...)` is validation in the wrong layer — move it into the model so it runs everywhere the model is used and returns a consistent 422.
- Raise `ValueError`/`AssertionError` inside validators — Pydantic turns them into a 422 with the correct error shape. Don't raise `HTTPException` from a validator.

## Computed & aliased output

- **`@computed_field`** (v2) for derived read-only output (a `full_name`, a `total`). Keep it cheap — a computed field that hits the DB per item is an N+1 (→ `fastapi-async-performance`).
- **`Field(alias=...)` / `serialization_alias`** to decouple the wire name from the attribute (e.g. accept `camelCase` JSON into snake_case fields via `populate_by_name=True`). Decide aliasing once, in a base model.
- **`model_config = ConfigDict(from_attributes=True)`** (v2; `orm_mode=True` in v1) is required for a response model to read from ORM objects' attributes.

## Red flags

- A single model used as both the request body and the `response_model`.
- A SQLAlchemy/SQLModel **table** model returned directly or used as `response_model` (leaks every column, including ones added later).
- `hashed_password` / token / internal flag present on a response model.
- A create/update schema that accepts `id`, `owner_id`, `is_admin`, `is_staff`, `role`, `status`, `price` from the client when the server should set it (mass-assignment).
- Validation logic in the route function instead of a `field_validator`/`model_validator`.
- Bare `str` where `EmailStr`/`AnyUrl`/enum/`Decimal`/constrained `Field` is meant.
- `HTTPException` raised from inside a validator (wrong layer; breaks the 422 shape).

## Report format

When reviewing schemas, report per model: **direction (request/response) → fields exposed/accepted (flag any leak or over-accept) → validation coverage (which layer each rule is in) → typing gaps**. Flag every model used in both directions and every table model exposed as a response. When designing, output the `*Create` / `*Read` / `*Update` split explicitly and name which fields are server-controlled.
