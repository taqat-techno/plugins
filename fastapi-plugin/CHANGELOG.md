# Changelog

All notable changes to the `fastapi` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

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
