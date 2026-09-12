# Changelog

All notable changes to the `django` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

## [0.2.1] - 2026-09-12

Adds a behavioural eval suite under `evals/` (2 must-fire cases + 1 must-not-fire case), so this plugin's value claim is measured as
`Delta` against a no-plugin baseline instead of asserted. Each must-fire case
pairs a namespace-tolerant `tool_used: Skill` indicator with an `llm` rubric
that demands a fact this plugin uniquely teaches, so a no-plugin run fails it.

- `fires-on-inflated-group-by-counts` targets `django-orm-models`
- `fires-on-rename-column-live-postgres-table` targets `django-migrations`
- `ignores-custom-template-filter` asserts no skill of this plugin fires (`min: 0`, `max: 0`, `arm: both`)

Pilot with `claude plugin eval . --case <case> --runs 1 --ablation none`,
then measure with `claude plugin eval .`. No runtime behaviour changed.

## [0.2.0] - 2026-08-18

Marketplace-wide architecture upgrade. Skill discovery, invocation-mode metadata, and identity consistency were corrected across the marketplace; no skill, command, agent, hook, or MCP behaviour was removed.

Fixed `user_invocable` -> `user-invocable` on 7 skills (previously inert).

## [0.1.0] - 2026-06-22

### Added

- Initial release of the Django / Django REST Framework engineering toolkit.
- **7 skills** (auto-activating from natural-language symptoms, none user-invocable):
  - `django-orm-models` — model design + ORM query discipline (N+1, `select_related`/`prefetch_related`, transactions, constraints, indexes).
  - `django-migrations` — safe migration workflow + zero-downtime sequencing + data migrations.
  - `django-views-drf` — views (FBV/CBV) and DRF serializers / viewsets / permissions / pagination / throttling.
  - `django-settings-config` — 12-factor settings split, env-driven config, secret management.
  - `django-security-audit` — settings hardening, `DEBUG`/`SECRET_KEY`, CSRF, SQLi, mass-assignment, auth/permissions, dependency CVEs.
  - `django-testing` — pytest-django + `factory_boy` patterns, DB/transaction test strategy, coverage.
  - `django-performance` — query optimization, caching layers, pagination at scale, async.
- **4 commands**: `/django-scaffold`, `/django-migrate`, `/django-test`, `/django-security`. Each detects the project layout on first run (no separate init step needed).
- **3 agents**: `migration-safety-analyzer`, `django-security-auditor`, `orm-query-optimizer`.
- **3 hooks**:
  - SessionStart — detect Django/DRF version + project layout, inject context.
  - PreToolUse (Write/Edit) — advisory guard on risky migration ops and hardcoded settings secrets.
  - PreToolUse (Bash) — destructive-management-command guard (`flush`, `sqlflush`, `reset_db`, `migrate --fake`, raw `DROP`/`DROP DATABASE`).
- **pytest suite** under `tests/` — plugin-structure tests + behavioral tests for all three hooks (65 tests). Run with `pytest django-plugin/tests/ -q`.
