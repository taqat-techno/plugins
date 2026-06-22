---
name: django-testing
description: Django testing strategy — pytest-django vs Django's test runner, the TestCase/TransactionTestCase distinction, fixtures vs factory_boy, the test database lifecycle, mocking external calls and time, assertNumQueries for query regressions, and DRF APIClient endpoint tests. Activates when writing or reviewing Django tests, choosing a test base class or fixture strategy, setting up the test runner/DB, diagnosing flaky/slow/leaky tests, or adding query-count or API-contract coverage. Defers production query design to django-orm-models.
version: 0.1.0
last_reviewed: 2026-06-22
owns:
  - test-runner choice (pytest-django vs manage.py test) and its config
  - TestCase vs TransactionTestCase vs SimpleTestCase selection rule
  - test-data strategy (factory_boy over static fixtures; per-test isolation)
  - test-DB lifecycle rules (rollback isolation, --keepdb, parallel, fast hashers)
  - external-dependency & time mocking rules (mock at boundary; freeze time; no real network)
  - regression-coverage rules (assertNumQueries for N+1; APIClient for endpoint contracts)
defers_to:
  - django-orm-models (what the production query should be; this skill locks it with a count test)
  - django-views-drf (the endpoint contract being asserted)
  - django-settings-config (the test settings module itself)
  - project test conventions & coverage targets (adapter input)
user_invocable: false
---

# django-testing

## Purpose

Django tests fail in characteristic ways: they hit the network, they leak state between cases because the wrong base class was chosen, they're slow because every test rebuilds data, and they pass while the code regresses to an N+1 because nothing counts queries. This skill owns the base-class/runner/data choices that make a suite fast, isolated, and able to catch the regressions that matter.

## When to use

Activate when:

- Writing or reviewing Django tests (models, views, serializers, tasks, management commands).
- Choosing a test base class, fixture strategy, or runner.
- Setting up the test database, parallelism, or CI test config.
- Diagnosing flaky, slow, order-dependent, or state-leaking tests.
- Adding query-count regression coverage or API-contract tests.

Defer *what the production query should be* to `django-orm-models` — this skill's job is to lock it with `assertNumQueries`.

## Inputs (adapter)

1. **Runner** — pytest-django (`pytest`, fixtures, `@pytest.mark.django_db`) or Django's `manage.py test` (`unittest`-style). Match what the project uses; don't introduce pytest into a unittest suite unasked.
2. **Test settings module** — the dedicated settings used under test (→ `django-settings-config`); fast password hasher, appropriate cache/email backends.
3. **Coverage target & data libs** — `factory_boy`, `model_bakery`, `freezegun`, `responses`/`requests-mock`, `coverage`.

## Base-class selection

| Base | Isolation mechanism | Use when |
|---|---|---|
| `SimpleTestCase` | none (DB access disallowed) | pure logic, no DB — fastest |
| `TestCase` | wraps each test in a transaction, rolls back | the default for DB tests |
| `TransactionTestCase` | truncates tables between tests (slower) | testing `transaction.atomic`, `on_commit`, `select_for_update`, or actual commit behavior |
| `LiveServerTestCase` | live server thread | Selenium/Playwright end-to-end |

The trap: `TestCase`'s outer transaction means **`on_commit` callbacks never fire** and you can't observe real commit/rollback. Tests that need those require `TransactionTestCase` (or `captureOnCommitCallbacks`). pytest equivalent: `@pytest.mark.django_db(transaction=True)`.

## Test-data strategy

- Prefer **`factory_boy`/`model_bakery`** over static JSON fixtures. Factories are explicit about what each test needs, survive model changes, and avoid the shared-fixture coupling where one test's data assumptions silently depend on another's.
- Build the *minimum* data a test needs; don't load a 500-row fixture for a one-row assertion.
- Each test creates its own data and relies on per-test rollback for isolation — never depend on test execution order or leftover rows.

## Test-DB lifecycle

- Each `TestCase` rolls back, so the DB is clean between tests without manual teardown.
- **Speed:** `--keepdb` (reuse the test DB across runs), `--parallel` (split across processes), and a fast password hasher in test settings (`MD5PasswordHasher`) — hashing is a top hidden cost in auth-heavy suites.
- Use `setUpTestData` (classmethod) for read-only data shared across a class's tests — created once per class, not per test.

## Mocking discipline

- **No real network in tests.** Mock external HTTP at the boundary (`responses`, `requests-mock`, or patch the client). A test that calls a real API is flaky and slow by definition.
- **Mock where it's used, not where it's defined** (`patch("myapp.services.payment_client")`, not `patch("stripe.Charge")`) — the import location is what your code resolves.
- **Freeze time** (`freezegun` / `time-machine`) for anything date/`now()`-dependent; never assert against the real clock.
- Mock the *boundary* (third-party SDK, email send, task enqueue), not your own logic — over-mocking tests the mock, not the code.

## Regression coverage that matters

- **`assertNumQueries(n)`** around list/detail paths to pin query counts — this is how an N+1 regression gets caught in CI instead of in production. When `django-orm-models` fixes an N+1, lock it with a count test.
- **DRF `APIClient`** for endpoint contracts: status code, response shape, permission enforcement (authenticated vs not, owner vs other user → catches IDOR), pagination, validation errors. `force_authenticate` to set the user.
- Test the **boundaries**: empty results, permission denied, validation failure, not-found — not just the happy path.

## Red flags

- DB-touching tests on `SimpleTestCase`, or `TransactionTestCase` used everywhere "to be safe" (slow).
- A test asserting `on_commit`/`select_for_update` behavior under plain `TestCase` (silently never runs the callback).
- Real network/API/email calls in tests.
- Order-dependent tests or shared mutable fixture state.
- No `assertNumQueries` anywhere on list endpoints known to join relations.
- Endpoint tests that check 200 but never check the unauthorized/other-user path.
- The production password hasher used under test (slow suite).

## Report format

When reviewing a suite, report: **base-class fit per test class, data strategy, any real-IO leakage, isolation hazards, and coverage gaps on boundaries/permissions/query-counts** — with specific files. When adding tests, state which base class and why, and include at least one negative-path and (for query-sensitive code) one `assertNumQueries` test.
