---
name: django-testing
description: Django testing strategy — pytest-django vs Django's test runner, the TestCase/TransactionTestCase distinction, fixtures vs factory_boy, the test database lifecycle, mocking external calls and time, assertNumQueries for query regressions, and DRF APIClient endpoint tests. Activates when writing or reviewing Django tests, choosing a test base class or fixture strategy, setting up the test runner/DB, deciding to run the constraint-sensitive suite against Postgres instead of SQLite (varchar length, partial/deferrable constraints are Postgres-only and invisible on SQLite), reproducing deployed behavior against a reachable staging DB with a rolled-back force_authenticate + transaction.atomic script, diagnosing flaky/slow/leaky tests, or adding query-count or API-contract coverage. Defers production query design to django-orm-models.
version: 0.1.0
last_reviewed: 2026-07-23
owns:
  - test-runner choice (pytest-django vs manage.py test) and its config
  - TestCase vs TransactionTestCase vs SimpleTestCase selection rule
  - test-data strategy (factory_boy over static fixtures; per-test isolation)
  - test-DB lifecycle rules (rollback isolation, --keepdb, parallel, fast hashers)
  - external-dependency & time mocking rules (mock at boundary; freeze time; no real network)
  - backend parity (run the constraint-sensitive suite on the engine you deploy)
  - CI environment parity (an early-step failure masks the suite; task-eager gating)
  - rolled-back live-DB repro recipe (force_authenticate + atomic with forced rollback)
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

## Backend parity — test on the engine you deploy

A suite that runs on SQLite for speed while production runs Postgres **cannot** catch a whole class of constraint bugs, because SQLite silently ignores them:

- **`max_length` on a `CharField` is not enforced by SQLite** — an over-length string saves fine under test and is rejected (or truncated) only on Postgres.
- **Partial/conditional unique indexes** (`UniqueConstraint(condition=…)`), **`DEFERRABLE INITIALLY DEFERRED`** FKs, `ExclusionConstraint`, and other Postgres-only integrity exist only on Postgres — on SQLite the constraint is a no-op, so a test "proving" uniqueness or deferral passes for the wrong reason.
- Lookup/datatype differences (case-sensitivity, `JSONField`/`ArrayField`, `distinct("field")`) diverge too.
- **SQLite takes one global write lock**, regardless of which rows or tables are touched, where Postgres locks per row. So a feature that writes concurrently raises `database is locked` under test and passes in production — and this is *not* dismissible as dev-only, because E2E suites typically run on SQLite, so shipping it breaks every local run of the feature (→ `django-orm-models` for the contention and retry rules).

Rule: **run the constraint-sensitive suite against Postgres in CI** — the same engine and, ideally, the same major version as prod. A fast SQLite loop locally is fine, but the authoritative run, and every test that asserts a DB constraint, must be on Postgres. Point the test settings' `DATABASES` at Postgres in CI (→ `django-settings-config`). A green SQLite suite is not evidence that a Postgres-only constraint holds.

## CI environment parity — read the failing step, not the summary

- **A CI job that dies at an early step (install, `migrate`, `collectstatic`) never runs the suite behind it.** Every test after that step is *unrun*, not passing. So a red job is not a "known false failure" until you have read the failed-step log, named the failing step, and shown the suite would otherwise be green — a missing key or service in the CI environment can mask real breakage for as long as the job has been dying early. Expect a backlog when you fix the early death: the first genuinely-complete run typically unmasks tests that have been broken for weeks, and those are not a regression from the fix.
- **Gate "run tasks eagerly" on *being under test*, never on whether a broker URL happens to be set.** Enabling `CELERY_TASK_ALWAYS_EAGER` only when the broker URL is *unset* works locally (no broker → eager on) and breaks in CI, where a broker **service** exists so the URL resolves, but **no worker** runs: eager turns off, `.delay()` enqueues into a queue nobody drains, and every test asserting a task side effect fails with an empty `mail.outbox` or `0 != 1`. Key it off the test settings module (or `"test" in sys.argv`) so local and CI can't diverge. The same shape applies to any "if the dependency looks configured, use the real one" toggle — presence of a URL is not evidence anything is consuming it.

## Mocking discipline

- **No real network in tests.** Mock external HTTP at the boundary (`responses`, `requests-mock`, or patch the client). A test that calls a real API is flaky and slow by definition.
- **Mock where it's used, not where it's defined** (`patch("myapp.services.payment_client")`, not `patch("stripe.Charge")`) — the import location is what your code resolves.
- **Freeze time** (`freezegun` / `time-machine`) for anything date/`now()`-dependent; never assert against the real clock.
- Mock the *boundary* (third-party SDK, email send, task enqueue), not your own logic — over-mocking tests the mock, not the code.

## Regression coverage that matters

- **`assertNumQueries(n)`** around list/detail paths to pin query counts — this is how an N+1 regression gets caught in CI instead of in production. When `django-orm-models` fixes an N+1, lock it with a count test.
- **DRF `APIClient`** for endpoint contracts: status code, response shape, permission enforcement (authenticated vs not, owner vs other user → catches IDOR), pagination, validation errors. `force_authenticate` to set the user.
- **Assert a key's presence and value, not just a 2xx.** A test that checks `status_code == 200` — or that only reads keys which happen to be present — cannot catch a field DRF dropped: a read-only serializer field whose `source` doesn't resolve becomes `SkipField` and disappears from the payload with no error. For every field that drives a user-visible surface, assert `assertIn("field", data)` **and** the value (→ `django-views-drf`). "The request succeeded" is not a contract.
- **A zero-write preview/dry-run path proves nothing about the write path.** Preview endpoints and `--dry-run` importers never INSERT, so they never exercise column length, FK existence, or unique constraints — those fire only on the real write. When preview passes and execute 500s, that gap *is* the diagnosis: go straight to the write-side traceback from the environment that actually failed instead of re-debugging the preview. Cover it properly by making the two paths incapable of diverging: when a value is generated in two places (a model's own `save()` and an import/bulk path that sets the field directly), route both through **one shared bounded helper** and unit-test the bound — otherwise the import path writes a value the model could never produce and Postgres raises `value too long for character varying(N)` while SQLite, which ignores varchar length, keeps the local suite green.
- Test the **boundaries**: empty results, permission denied, validation failure, not-found — not just the happy path.

## Reproducing deployed behavior against a live DB (fully rolled back)

When a bug reproduces only against real (staging) data and the frontend is walled (SSO/401) but the **database is reachable**, reproduce it in-process with a script that authenticates as the affected role, exercises the real view, and **always rolls back** so it persists nothing:

- Wrap the whole exercise in `transaction.atomic()` and force a rollback at the end — `transaction.set_rollback(True)`, or raise a sentinel exception you catch outside the block. The script drives write code paths but must be read-only *in effect*.
- Use DRF's **`force_authenticate(request, user=…)`** (via `APIRequestFactory`/`APIClient`) to become the affected user without real credentials or the SSO wall — this runs the *actual* view, permission, and serializer code, not a reimplementation.
- **Expand the database URL only inside the subprocess/script, from the environment, at connection time** — never bake a staging DSN into committed code or a fixture. Read it from the same secret source the app uses and scope it to the single run; prefer a read replica when one exists.
- Confirm autocommit is off and the rollback actually happened (assert the row count is unchanged) so an early exception can't leave a partial write. Log what the view returned, not what you assumed.

This yields a faithful repro of the deployed code path with zero persistent effect. (The "verify in the target environment" framing is `release-safety`'s; this is the Django-side recipe.)

## Red flags

- DB-touching tests on `SimpleTestCase`, or `TransactionTestCase` used everywhere "to be safe" (slow).
- A test asserting `on_commit`/`select_for_update` behavior under plain `TestCase` (silently never runs the callback).
- Real network/API/email calls in tests.
- Order-dependent tests or shared mutable fixture state.
- No `assertNumQueries` anywhere on list endpoints known to join relations.
- Endpoint tests that check 200 but never check the unauthorized/other-user path.
- Asserting a Postgres-only constraint (varchar length, partial/deferrable unique) on a SQLite test DB → the constraint is a no-op there; the test passes for the wrong reason.
- The production password hasher used under test (slow suite).
- A red CI job written off as a "known false failure" without reading the failing step → every test behind it is unrun, not green.
- Eager task execution keyed on the absence of a broker URL rather than on the test settings → tasks silently never run in CI.
- An endpoint test that asserts only the status code for a response whose fields drive a UI surface → a dropped key passes.
- A "preview passed" treated as evidence the write will succeed → the zero-write path never touched a single constraint.

## Report format

When reviewing a suite, report: **base-class fit per test class, data strategy, any real-IO leakage, isolation hazards, and coverage gaps on boundaries/permissions/query-counts** — with specific files. When adding tests, state which base class and why, and include at least one negative-path and (for query-sensitive code) one `assertNumQueries` test.
