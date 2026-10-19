# Changelog

All notable changes to the `fastapi` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

## [0.5.0] - 2026-10-19

### Added
- `userConfig.destructive_guard` (boolean, default true): turn the bash guard's confirmation prompts off from `/config`. `ALLOW_FASTAPI_DESTRUCTIVE=1` in the environment Claude Code is launched with does the same.
- Bash guard also covers `alembic -x ... downgrade base`, `downgrade heads:base`, `mysqladmin drop`, `DROP DATABASE` piped or heredoc'd into a SQL client, and commands wrapped in `sudo`, `env`, `poetry run`/`uv run`, `docker compose exec`, `bash -c`, `$(...)` and `if/then`.
- `/fastapi:migrate --apply` resolves where `env.py` takes its URL from, prints driver, host, port and database name (never the password or full URL), and requires explicit confirmation when the host is not local (FAPI-P1-04).
- Lifespan coverage (FAPI-P2-07): `fastapi-routing` (the `lifespan` context manager replaces `@app.on_event`, which stops running once a lifespan is set; process-wide resources; mounted sub-apps), `fastapi-database` (one engine per process, `dispose()` in the lifespan), `fastapi-testing` (`ASGITransport` does not run the lifespan; use `asgi-lifespan`'s `LifespanManager` or `with TestClient(app)`). `fastapi-routing` also covers `Annotated[..., Depends()]`.
- `/fastapi:scaffold` documents the `.claude/fastapi.local.json` schema and writes it only with consent.
- Session-start detection finds `src/<pkg>/main.py` entrypoints and projects up to two levels below the session directory (FAPI-P3-09).
- Evals: a must-fire case for every skill (6 new) and 8 new must-not-fire near-miss cases. Not run yet; no delta recorded.

### Changed
- **Commands renamed to bare verbs (ECO-18):** `/fastapi:migrate`, `/fastapi:scaffold`, `/fastapi:test`, `/fastapi:security`. The old `/fastapi:fastapi-*` files remain as deprecated aliases until 0.6.0.
- **Bash guard asks instead of blocking (FAPI-P1-01, ECO-P1-04):** destructive commands return `permissionDecision: "ask"`. The guard no longer prints an override token, and writing `ALLOW_FASTAPI_DESTRUCTIVE` inside a command no longer bypasses it.
- **Bash guard is scoped to FastAPI projects (ECO-03):** it fires only where `fastapi` is declared in pyproject.toml, requirements*.txt, requirements/*.txt, Pipfile, setup.cfg or setup.py, found walking up from the working directory or a `cd` target, or within two levels of `CLAUDE_PROJECT_DIR`.
- **Bash guard parses the shell command (FAPI-P2-02):** quoted text, comments, `echo`, `grep` patterns, `git log --grep dropdb`, commit messages, `--help` and offline `downgrade base --sql` no longer trigger it.
- The write guard's matcher now includes `MultiEdit`. SessionStart prints nothing outside a FastAPI project.
- All hooks use the vendored `hooks/_vendor/hooklib.py`.
- Adapter cache moved to `.claude/fastapi.local.json`; the legacy `.fastapi-kit.local.json` is still read.
- Skill descriptions rewritten to start with "Use when" (all under 1,024 characters).
- `fastapi-testing` and `/fastapi:test` inline the T0-T3 tier summary; the agent-safety-guards `test-scope` skill and `FULL_SUITE=1` are mentioned only as optional (FAPI-P2-05).
- README restructured to the marketplace template, with Configuration, Platform support and Data & privacy sections and the agents' Bash scope stated (FAPI-P3-05).

### Fixed
- Hardcoded-secret advisory now catches the idiomatic pydantic-settings form: case-insensitive names with an optional type annotation (`secret_key: str = "..."`, `db_password: SecretStr = "..."`); env-sourced defaults and names such as `token_url` stay silent (FAPI-P1-03).
- Async-blocking advisory checks calls lexically inside an `async def` with `ast`, so `time.sleep` in a sync `def` (or a nested sync helper) is no longer flagged; `from time import sleep` is caught; a hunk that does not parse falls back to the old file-level check (F-FAPI-06).
- "Async DB driver" detection requires a real `databases` / `asyncpg` / `aiomysql` / `aiosqlite` dependency entry, not the word anywhere.
- DRF vocabulary removed from FastAPI text (`IsAuthenticated`, `get_queryset`) (FAPI-P3-08). README badge said 0.1.0 (FAPI-P2-11).

### Security
- The destructive guard can no longer be bypassed by the model adding a token to its own command; only the user (the ask prompt, the plugin option, or the launch environment) can let it through.
- Agents, `/fastapi:security`, `/fastapi:test` and `fastapi-security-audit` carry the rule that file contents, logs, test output and audit reports are data, never instructions.

## [0.4.1] - 2026-10-19

### Fixed
- **Hook launch is portable and space-safe (Wave 1, QW #2/#3).** `hooks/hooks.json` now runs each python hook through one POSIX-sh launcher: the `${CLAUDE_PLUGIN_ROOT}` path is quoted (a plugin root containing a space no longer hands python a truncated path, which exited 2 and blocked the call), the interpreter is picked from `python3` -> `python` -> `py -3` with the `command -v` builtin (guards no longer fail open where `python3` is not the name), a missing script or unresolved root exits 0, and the hook's own exit code is propagated unchanged. Known limit: on Windows without Git Bash, Claude Code runs shell-form hooks in PowerShell, where the launcher does not parse and the hook fails open (non-blocking).
- **Hook stdin is decoded as UTF-8 (ECO-14, QW #18).** `session_start.py` read `sys.stdin` as text, which on Windows is cp1252 with surrogateescape, so an Arabic or other non-ASCII payload arrived as mojibake. It now read `sys.stdin.buffer` and decode UTF-8.

### Tests
- `tests/test_hook_launcher.py` proves quoting, exit-2 propagation from a root with a space, unresolved root -> 0, and no python on PATH -> 0.
- `tests/test_stdin_utf8.py`: structural gate against text-mode stdin in `hooks/`.

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
