# Changelog

All notable changes to the `django` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

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
- **5 commands**: `/django-init`, `/django-scaffold`, `/django-migrate`, `/django-test`, `/django-security`.
- **3 agents**: `migration-safety-analyzer`, `django-security-auditor`, `orm-query-optimizer`.
- **3 hooks**:
  - SessionStart — detect Django/DRF version + project layout, inject context.
  - PreToolUse (Write/Edit) — advisory guard on risky migration ops and hardcoded settings secrets.
  - PreToolUse (Bash) — destructive-management-command guard (`flush`, `sqlflush`, `reset_db`, `migrate --fake`, raw `DROP`/`DROP DATABASE`).
- **pytest suite** under `tests/` — plugin-structure tests + behavioral tests for all three hooks (67 tests). Run with `pytest django-plugin/tests/ -q`.
