---
description: Run the Django test suite with the project's detected runner (pytest-django or manage.py test), using the test settings module, and report results — with options to scope to an app/path and to add missing regression coverage.
argument-hint: "[app-or-path] [--keepdb] [--parallel] [--cov] [--failed]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

# /django-test — Run and reason about the test suite

You run the project's tests with the **correct runner and settings** and interpret the results. Apply `django-testing` for base-class/data/mocking judgments and `django-orm-models` for query-count expectations.

## Step 0 — Context

Read `.django-kit.local.json` for `testRunner`, `managePrefix`, `settingsModules.test`. If absent, detect like `/django-init`. Confirm the **test settings module** (fast hasher, appropriate backends) — running tests on dev/prod settings is a flag.

## Step 1 — Build the command

- **pytest-django:** `pytest [app-or-path]` with `DJANGO_SETTINGS_MODULE` (from cache) honored via `pytest.ini`/`pyproject`. Add `-p no:cacheprovider` only if asked. `--failed` → `--lf` (last failed). `--cov` → `--cov=<localApps> --cov-report=term-missing`.
- **manage.py test:** `<managePrefix> test [app-or-path] --settings=<test settings>`. `--keepdb`, `--parallel`, `--failed` → re-run named failures. `--cov` → wrap with `coverage run` + `coverage report`.

Always pass the test settings module explicitly if the runner doesn't pick it up. Use `--keepdb`/`--parallel` when requested (and note when the suite would benefit from them).

## Step 2 — Run

Execute the suite (or the scoped subset). Capture full output. Do not hide failures or summarize away errors — report exit status faithfully.

## Step 3 — Interpret failures

For each failure, classify:

- **Real regression** — the code broke. Point to the assertion and the likely cause.
- **Test fragility** — real network/clock/order dependency, wrong base class (e.g. `on_commit` under plain `TestCase`), shared-state leak. Recommend the `django-testing` fix.
- **Environment** — missing DB, wrong settings, missing service. Fix the invocation, don't paper over it.

## Step 4 — Coverage gaps (when asked or when failures reveal them)

If `--cov` or the user wants gaps surfaced, identify untested boundaries: permission/negative paths on endpoints, constraint violations on models, and list endpoints with no `assertNumQueries`. Offer to add focused tests (apply `django-testing`): at minimum one negative-path and, for query-sensitive code, one query-count test. Plan before writing.

## Step 5 — Report

```
TEST RUN  (pytest-django · config.settings.test · scope: orders)
  Result:   FAILED — 42 passed, 2 failed, 1 error in 8.3s
  Failures:
    ✗ test_order_total_excludes_cancelled   → real regression (sum includes cancelled; orders/models.py:51)
    ✗ test_webhook_fires_on_commit          → fragile: on_commit under TestCase; needs TransactionTestCase
  Errors:
    ! test_export_endpoint                   → env: test DB missing CITEXT extension
  Coverage:  orders 78% (missing: views.py 30-44 permission paths)
  Suggested: add assertNumQueries to test_order_list (joins customer)
```

State plainly when the suite passes. Never report success when there are failures or errors.
