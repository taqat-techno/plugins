# Changelog

All notable changes to the `fastapi` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-09-27

### Fixed
- **Advisories now reach Claude.** `pre_bash_guard.py` (`alembic stamp`) and
  `pre_write_guard.py` (blocking calls in async code, hardcoded secrets, wildcard CORS with
  credentials, empty `downgrade()`) now emit their nudges as PreToolUse `additionalContext`
  JSON instead of stderr.
  On `PreToolUse`, stdout and stderr from a hook that exits 0 never reach the model, so
  Claude never saw these advisories. Only `hookSpecificOutput.additionalContext` with
  `hookEventName: "PreToolUse"` does (checked against Claude Code 2.1.282 and the hooks
  docs). Claude receives it next to the tool result, so the advisory informs its next
  step. It cannot stop the call. No `permissionDecision` is emitted, so permissions are unchanged.
- Hook stdin is decoded as UTF-8 explicitly (Windows defaulted it to cp1252), and
  stdout/stderr are reconfigured to UTF-8 (HR-5). Exit-2 blocks are unchanged.
- `tests/test_hooks.py` asserts advisories on the JSON channel and the channel contract.

## [0.3.0] - 2026-09-27

### Changed
- **Bare `/fastapi-test` tests what changed.** It maps the edited files to test modules
  (T1), then runs the test package of each changed area (T2), widening on model, migration,
  dependency, settings or `conftest.py` changes. `--all` runs everything, only on request.
  A path that collects 0 tests is a failed invocation.
- `fastapi-testing`: new "Scoped runs during development" tier table (T0-T3), with
  `--lf --lfnf=none` for red runs and the silently-skipped async test trap. The tier policy
  lives in agent-safety-guards `test-scope`.

## [0.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (2 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-alembic-rename-column-live-table` targets `fastapi-migrations`
- `fires-on-async-route-freezes-under-load` targets `fastapi-async-performance`
- `ignores-swagger-docs-cosmetic-customization` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 8 skills (previously inert).

## [0.1.0] - 2026-06-23

### Added

- Initial release of the FastAPI engineering toolkit.
- **8 skills** (auto-activating from natural-language symptoms, none user-invocable):
  - `fastapi-pydantic` — Pydantic v2 schema design: request/response separation, validation layering, read/write field discipline, mass-assignment & field-leak prevention, ORM serialization.
  - `fastapi-routing` — path operations, `APIRouter`, the `Depends()` dependency-injection system (incl. `yield` lifecycle deps), `response_model`/status codes, error shaping, bounded pagination.
  - `fastapi-database` — SQLAlchemy/SQLModel models & relationships, request-scoped sessions, the N+1 / lazy-loading rule (`selectinload`/`joinedload`), transactions, and the async-session correctness traps.
  - `fastapi-migrations` — safe Alembic workflow (autogenerate review, what it misses), reversibility (a real `downgrade`), schema-vs-data split, zero-downtime expand-contract.
  - `fastapi-config` — typed `pydantic-settings` `BaseSettings`, 12-factor env-driven config, secret management, per-environment correctness, cached settings dependency.
  - `fastapi-security-audit` — auth/JWT (signature/expiry/alg), authz (missing dependency, IDOR, mass-assignment), injection, CORS, secret/docs/debug exposure, upload safety, dependency CVEs.
  - `fastapi-testing` — sync `TestClient` vs `httpx.AsyncClient`+`ASGITransport`, `dependency_overrides`, transactional test DB, boundary mocking, query-count regression coverage.
  - `fastapi-async-performance` — sync-vs-async `def`, never blocking the event loop (`run_in_threadpool`), background tasks vs a task queue, caching + invalidation, connection-pool sizing, pagination at scale.
- **4 commands**: `/fastapi-scaffold`, `/fastapi-migrate`, `/fastapi-test`, `/fastapi-security`. Each detects the project layout on first run (no separate init step needed).
- **3 agents**: `alembic-migration-analyzer`, `fastapi-security-auditor`, `async-query-optimizer`.
- **3 hooks**:
  - SessionStart — detect FastAPI/Pydantic/SQLAlchemy/Alembic version + project layout (sync vs async), inject context.
  - PreToolUse (Write/Edit) — advisory guard on event-loop-blocking calls inside `async def`, hardcoded config secrets, wildcard-CORS-with-credentials, and empty Alembic `downgrade()`.
  - PreToolUse (Bash) — destructive-command guard (`alembic downgrade base`, `dropdb`/`DROP DATABASE`, advisory on `alembic stamp`).
- **pytest suite** under `tests/` — plugin-structure tests + behavioral tests for all three hooks. Run with `pytest fastapi-plugin/tests/ -q`.
