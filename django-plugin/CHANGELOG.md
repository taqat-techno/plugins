# Changelog

All notable changes to the `django` plugin are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); this plugin uses [Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-09-27

### Fixed
- **Advisories now reach Claude.** `pre_bash_guard.py` (`migrate --fake`) and
  `pre_write_guard.py` (hardcoded DEBUG/secrets, irreversible `RunPython`, `fields =
  "__all__"`) now emit their nudges as PreToolUse `additionalContext` JSON instead of stderr.
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
- **Bare `/django-test` tests what changed.** It maps the edited files to apps and test
  labels, runs T1 with `--keepdb`, then each changed app once (T2). It widens when a model,
  migration, settings, permissions, a shared base class or `conftest.py` changed.
- `--all` runs the whole project, only on request. An explicit app or path runs exactly
  that. `--keepdb` is the default for scoped runs. The command warns that `--parallel` is
  unreliable on native Windows and that a label matching nothing runs 0 tests.
- `django-testing`: new "Scoped runs during development" tier table (T0-T3). The tier policy
  lives in agent-safety-guards `test-scope`.

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
