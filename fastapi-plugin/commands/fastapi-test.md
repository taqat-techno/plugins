---
description: Run the FastAPI tests for what changed (default) or --all, with pytest, the right test client and dependency overrides, and report results.
argument-hint: "[path | --all] [--cov] [--failed] [--async] [-k EXPR]"
author: TaqaTechno
version: 0.1.0
allowed-tools: Read, Glob, Grep, Bash, Write, Edit
---

# /fastapi-test — Run and reason about the test suite

You run the project's tests with the **correct client, settings, and dependency overrides** and interpret the results. Apply `fastapi-testing` for client/override/fixture judgments and `fastapi-database` for query-count expectations.

## Step 0 — Context

Read `.fastapi-kit.local.json` for `runPrefix`, `testClient` (testclient/httpx-async), `asyncStack`, `settingsModule`, `localPackages`. If absent, detect them yourself (read-only): locate the test directory and `pytest`/`pyproject`/`pytest.ini` config, whether the app is async (async routes/sessions → `httpx.AsyncClient` + `ASGITransport` under `pytest-asyncio`/`anyio`), the test settings/overrides, and the run prefix (`pytest`, `poetry run pytest`, `uv run pytest`). Confirm a **test settings/DB** is wired (overrides point `get_session` at a test DB) — running against the dev/prod DB is a flag.

## Step 1 — Build the command

- **Scope first (bare invocation = what changed):** with no `path` and no `--all`, collect
  the files edited this session (or `git status` + `git diff --name-only`). Map each to its
  tests: a test file maps to itself; `app/services/orders.py` maps to
  `tests/**/test_orders.py`, or to whatever greps for the module. Run those (T1). If they
  pass, run the test package of each changed area once (T2). Widen when models,
  migrations, settings, dependencies or `conftest.py` changed. `--all` runs everything,
  only when the user asked (the test-scope hook then needs `FULL_SUITE=1`). Report per the
  `test-scope` report block.
- `<runPrefix> pytest [path]` with the test settings honored via `pytest.ini`/`pyproject`/`conftest`.
- `--failed` → `--lf` (last failed). `-k EXPR` passes through. `--cov` → `--cov=<localPackages> --cov-report=term-missing`.
- For an async app, confirm `asyncio_mode = auto` (pytest-asyncio) or the `anyio` plugin is configured so `async def` tests actually run — silently-skipped async tests are a common false "pass".

## Step 2 — Run

Execute the scoped selection (or the whole suite for `--all`). A path that collects
0 tests is a failed invocation, not a pass. Capture full output. Do not hide failures or summarize away errors — report exit status faithfully.

## Step 3 — Interpret failures

For each failure, classify:

- **Real regression** — the code broke. Point to the assertion and the likely cause.
- **Test fragility** — real network/clock/order dependency; sync `TestClient` masking an async-session/loop bug; `dependency_overrides` not cleared (leaking across tests); shared DB state with no rollback. Recommend the `fastapi-testing` fix.
- **Environment** — missing test DB, wrong settings, missing async plugin (async tests erroring/skipped), missing service. Fix the invocation/config, don't paper over it.

## Step 4 — Coverage gaps (when asked or when failures reveal them)

If `--cov` or the user wants gaps surfaced, identify untested boundaries: unauthenticated/other-user paths on endpoints (IDOR), validation `422` paths, constraint violations on models, and list endpoints with no query-count assertion. Offer to add focused tests (apply `fastapi-testing`): at minimum one negative-path and, for query-sensitive code, one query-count test that overrides `get_session`/`get_current_user`. Plan before writing.

## Step 5 — Report

```
TEST RUN  (httpx-async · async app · scope: tests/test_item_api.py)
  Result:   FAILED — 38 passed, 2 failed, 1 error in 6.1s
  Failures:
    ✗ test_item_total_excludes_deleted   → real regression (total includes soft-deleted; app/services/item.py:44)
    ✗ test_other_user_cannot_read_item    → real regression: returns 200 for non-owner (IDOR; app/routers/item.py:51)
  Errors:
    ! test_create_item_async              → env: pytest-asyncio not configured; async test errored
  Coverage:  app/routers/item 81% (missing: 51-58 ownership path)
  Suggested: add a query-count assertion to test_list_items (loads .customer)
```

State plainly when the suite passes. Never report success when there are failures or errors.
