# Changelog

All notable changes to `odoo-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [2.5.0] — 2026-06-23 — Enhance the testing skill (`odoo-test`) with a classification-first test-units workflow

### Added

- `skills/test/SKILL.md` (`odoo-test`, skill v2.0.0 → v2.1.0) gains a **"Test Strategy Workflow (classify → write → review → run → diagnose)"** section at the top of the body — a test-units brain grafted onto the existing pattern library. It mirrors how Odoo's own standard addons (`base`, `account`, `stock`, `sale`, `mail`, `web`, `portal`) test Odoo. Adds:
  - **Classification-first Step 1** — inspect `__manifest__.py` / `models` / `views` / `security` (`ir.model.access.csv` + `ir.rule`) / `wizard` / `controllers` / `report` / `data` / existing `tests` (and an issue's Required Changes / Acceptance Criteria) **before** writing, then answer the version / artifacts / category / runtime / phase / multi-company / regression questions.
  - **Step 2 base-class + tag + file matrix** mapping each work type (computed, `@api.constrains`, `_sql_constraints`, onchange, workflow, access rights, record rules, wizard, controller, report, mail) to `TransactionCase`/`HttpCase`, `at_install`/`post_install`, the target `test_*.py`, and the key assertion.
  - **Modern patterns** the existing skill lacked: the **`Form`** helper for onchange/view-driven tests, **`assertRecordValues`**, and the **`Command` API** (Odoo 13+) over legacy tuples.
  - A **Security & access discipline** that corrects the prior "bypass security with `sudo()`" guidance: test as a non-admin (`with_user` / `@users`), assert both the forbidden (`AccessError`) and allowed paths, invalidate cache between privilege levels, and reserve `sudo()` for deliberate bypass / fixture setup only.
  - **Four workflows** (Generate / Review / Diagnose / Requirements→tests), **quality gates**, a consolidated **anti-pattern** list, and the **four output templates** (Test Plan / Test Review / Implementation Report / Failure Diagnosis).
- `skills/test/references/` — four new reference files: `test-pattern-catalogue.md` (reusable per-pattern structures incl. record-rule, `@users`, report/QWeb `_render_qweb_html`, mail, multi-company, regression), `custom-module-test-blueprint.md` (recommended `tests/` layout + per-file skeletons + the `tests/__init__.py` discovery rule), `review-checklist.md` (review checklist A–I + anti-pattern catalogue with fixes), and `odoo-version-matrix.md` (base classes, `Command`, `<list>`/`<tree>`, `json`/`jsonrpc`, helper availability across 14–19).

### Changed

- `skills/test/SKILL.md` frontmatter — `description` now advertises planning / reviewing / diagnosing / security / regression / requirements→tests triggers + three new `<example>` blocks (review, diagnose, security); `version` 2.0.0 → 2.1.0; `metadata.categories` add `security-tests`, `record-rules`, `test-review`, `regression`, `diagnosis`; last-updated date refreshed.
- The existing pattern library, running, coverage, CI, version-table, and troubleshooting sections are **unchanged** (single-owner: the new workflow references them rather than duplicating). No existing example or command was removed.
- `.claude-plugin/plugin.json` — version 2.4.0 → 2.5.0.
- `README.md` — `test` domain line expanded with the new capabilities.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- Genericness sweep over `skills/test/references/` and the added SKILL.md section → 0 client/project/host/credential tokens (placeholders only: `<module_name>`, etc.).

## [2.4.0] — 2026-06-14 — Consolidate the Odoo code-review knowledge base (`odoo-reviewer` skill)

### Added

- `skills/reviewer/` (`odoo-reviewer`) — Authoritative Odoo 17 + 19 code-review and technical-debt knowledge base, moved in from the standalone `odoo-reviewer` plugin (Taqat-Trading-Business-Solutions/Plugins) and folded into this unified toolkit. Auto-activates on review/audit/tech-debt phrasing and whenever a `.py` / `.xml` / `__manifest__.py` from an Odoo addon is in scope. Ships:
  - **12-section review checklist** in `SKILL.md` (manifest hygiene, module layout & file naming, XML conventions, Python style, symbols & class-attribute order, ORM patterns & inheritance, security, performance, views, JS/Owl/assets, testing, translation `_()`), v17 baseline with v19 deltas inlined.
  - **8 reference files** — `coding_guidelines.md`, `orm_patterns.md`, `security_pitfalls.md`, `performance.md`, `module_manifest.md`, `testing.md`, `severity_model.md` (BLOCKER/MAJOR/MINOR/STYLE rubric + effort table), and `v19_deltas.md` (every reviewer-relevant 17→19 change + mixed-version cluster checklist).
  - Every rule traces back to the official Odoo 17/19 documentation and cites its source.

### Changed

- Skill **normalized to the plugin's naming convention**: folder `odoo-17-reviewer` → `reviewer`, frontmatter `name: odoo-17-reviewer` → `odoo-reviewer` (the skill already covers 17+19, matching sibling skills `odoo-i18n-audit` / `odoo-stack-doctor`).
- Skill content **genericized** for this fleet-agnostic toolkit: workspace-specific tokens (`TAQAT`, `Cluster1/Shared/Hub`) replaced with generic mixed-version / multi-cluster wording. No rule, citation, or severity changed.
- `.claude-plugin/plugin.json` — version 2.3.0 → 2.4.0; description now leads with "code review & technical-debt".
- `README.md` — `odoo-reviewer` added to the Audit/Doctor skills table and a `reviewer` domain added to the Domains list.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- Genericness sweep over `skills/reviewer/` → 0 `TAQAT`/`Cluster1` tokens.

## [2.3.0] — 2026-06-13 — Odoo stack & DB lifecycle safety (restart/clone advisory + stack-doctor expansion)

### Added

- `hooks/pre_odoo_restart_guard.py` — PreToolUse hook on the **Bash** tool. **Advisory only** (stdlib-only, fail-OPEN, **always exits 0**, never blocks, never mutates files, never kills processes). Prints a one-line nudge to stderr on three documented-dangerous shapes: an unbounded Odoo readiness poll (`curl --retry-connrefused` against an Odoo-like port/endpoint with no `--max-time`/`--retry-max-time`/`--retry-delay`); a combined `pkill … && … odoo-bin` chain (the pkill self-matches and SIGTERMs the chain → exit 144); and a raw Odoo DB clone (`CREATE DATABASE … TEMPLATE` / `createdb -T`, which copies SQL only and breaks the filestore). Stays silent on bounded curls, split stop/start, `odoo-bin db duplicate`, and non-Odoo commands.
- `skills/stack-doctor/references/db-safety.md` — snapshot backup + sha256 before regeneration; real Odoo uninstall/upgrade (not SQL hacks); filestore-aware clone (`odoo-bin db duplicate` / `exp_duplicate_database`) vs the `psql TEMPLATE` trap; re-inventory + `pg_stat_activity` before destructive DB action on a shared instance; multi-instance isolation (own hostname / HTTP+gevent port pair / `db_filter` / filestore / log / addons_path); separate local config from the Docker config.

### Changed

- `skills/stack-doctor/SKILL.md` (`odoo-stack-doctor`, 0.1.0 → 0.2.0) — added a **Stack & DB lifecycle safety** section: standalone-Postgres-via-its-own-`pg_ctl` (a WAL-recovery timeout/exit is not failure — verify with `pg_isready`/log); shared-instance re-inventory before destructive DB actions; restart hygiene (kill by PID, never `pkill && odoo-bin`, split stop/start, free the port, tail the right log); bounded readiness polling only; verify install/upgrade from the LOG not the wrapper/background exit code; filestore-aware clone; separate local config. Updated frontmatter (description, `owns`, `defers_to`, metadata), When-to-use triggers, Doctor checklist, and Anti-patterns.
- `hooks/hooks.json` — added the Bash-matched advisory restart/clone guard to `PreToolUse` (all existing hooks — core-file, inline-JS, volume-destruction, session-start — unchanged).
- `README.md` — Safety Hooks table documents the new advisory guard.

### Validation

- `python validate_plugin.py odoo-plugin` → 0 errors.
- `python -m py_compile hooks/pre_odoo_restart_guard.py` → clean; hook self-tested across 12 cases (every case exits 0; warns only on the three risky shapes).

## [2.2.0] — 2026-06-13 — volume-destruction Bash guard + audit/doctor skills

### Added

- `hooks/pre_odoo_volume_guard.py` — PreToolUse hook on the **Bash** tool. Hard-blocks (exit 2) `docker compose down -v`/`--volumes` (and legacy `docker-compose down -v`), `docker volume rm`, and `docker volume prune`, which destroy the Postgres DB + Odoo filestore volumes. Passes silently unless an explicit override token (`ALLOW_VOLUME_DELETE` or `--i-understand-data-loss`) is present in the same command. Stdlib-only, fail-OPEN on internal error/timeout. Reads and non-destructive docker commands (`down` without `-v`, `volume ls/inspect`, `run -v` bind mounts, `--volumes-from`) pass silently.
- `skills/i18n-audit/SKILL.md` (`odoo-i18n-audit`) — audit checklist for translations that look complete but fall back to source: typed PO references (not source paths), source-string-edit → msgid invalidation, explicit-UTF-8 decode (no latin-1 / unicode_escape), one-arch/one-.po-per-language pipeline (no forked `_<lang>` views). Version-aware 14-19.
- `skills/stack-doctor/SKILL.md` (`odoo-stack-doctor`) — diagnostic checklist for a stack that "comes up clean but is wrong": mount-point change orphans the old volume (copy forward, never `down -v`), preserve the running Postgres major (forward-incompatible data dir), upgrade via `odoo-bin --stop-after-init` not the RPC button (website configurator hijack silently skips reload), theme-load post-copy after languages are active, theme-translated-fields mapping completeness. Version-aware 14-19.

### Changed

- `hooks/hooks.json` — added the Bash-matched volume-destruction guard to `PreToolUse` (existing core-file and inline-JS guards unchanged).
- `README.md` — Safety Hooks table documents the new volume-destruction guard.

### Validation

- `python validate_plugin.py odoo-plugin` -> 0 errors.
- Hook self-test: 22/22 classification cases pass (8 blocks, 3 override-allows, 11 safe-allows including bind-mount/`--volumes-from`/bare-`down` false-positive guards).
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [2.1.0] — 2026-05-31 — i18n/PO + volume/PG + theme-load references

### Added

- `skills/i18n/references/po-gettext-discipline.md` — typed PO references, source-string-invalidation audit, .pot/msgmerge workflow, UTF-8 decode (no unicode_escape).
- `skills/docker/references/volume-and-pg-safety.md` — never blind `down -v`, orphan-volume drift, preserve Postgres major version.
- `skills/upgrade/references/theme-load-and-cli-upgrade.md` — `_theme_load` after website/languages, prefer odoo-bin CLI over RPC immediate-upgrade, declare all translatable theme fields.

### Validation

- `python validate_plugin.py odoo-plugin` -> 0 errors.
- Genericness sweep: 0 project-specific tokens outside labeled examples.

## [2.0.0] — 2026-05-01 — BREAKING command rename + bare-invocation discipline

Two binding rules adopted across the marketplace are now applied to odoo-plugin:

1. **Command file names must not include the plugin name as a prefix.** Claude Code already namespaces plugin commands as `/<plugin-name>:<command>`, so `commands/odoo-init.md` produced the awkward `/odoo-plugin:odoo-init`. All sixteen `odoo-*` command files renamed to drop the prefix.
2. **Every command must run sensibly with no arguments.** Bare `/foo` always works; flags are optional shortcuts, never required. The eight commands that previously required positional arguments now auto-detect the target module from the working directory or prompt for the missing piece.

### Renamed (file → new file → invocation form)

| Before | After | Plugin-namespaced |
|---|---|---|
| `commands/odoo-db.md` | `commands/db.md` | `/odoo-plugin:db` |
| `commands/odoo-docker.md` | `commands/docker.md` | `/odoo-plugin:docker` |
| `commands/odoo-frontend.md` | `commands/frontend.md` | `/odoo-plugin:frontend` |
| `commands/odoo-i18n.md` | `commands/i18n.md` | `/odoo-plugin:i18n` |
| `commands/odoo-ide.md` | `commands/ide.md` | `/odoo-plugin:ide` |
| `commands/odoo-init.md` | `commands/init.md` | `/odoo-plugin:init` |
| `commands/odoo-precheck.md` | `commands/precheck.md` | `/odoo-plugin:precheck` |
| `commands/odoo-quickfix.md` | `commands/quickfix.md` | `/odoo-plugin:quickfix` |
| `commands/odoo-report.md` | `commands/report.md` | `/odoo-plugin:report` |
| `commands/odoo-scaffold.md` | `commands/scaffold.md` | `/odoo-plugin:scaffold` |
| `commands/odoo-security.md` | `commands/security.md` | `/odoo-plugin:security` |
| `commands/odoo-service.md` | `commands/service.md` | `/odoo-plugin:service` |
| `commands/odoo-start.md` | `commands/start.md` | `/odoo-plugin:start` |
| `commands/odoo-stop.md` | `commands/stop.md` | `/odoo-plugin:stop` |
| `commands/odoo-test.md` | `commands/test.md` | `/odoo-plugin:test` |
| `commands/odoo-upgrade.md` | `commands/upgrade.md` | `/odoo-plugin:upgrade` |

`commands/create-theme.md` was already prefix-free and is unchanged.

### Bare-invocation fixes (no args required)

Eight commands that previously required positional arguments now auto-detect from the working directory:

- **`/precheck`**, **`/quickfix`**, **`/upgrade`**, **`/security`** — walk up from `$CWD` to find `__manifest__.py`; if `$CWD` has multiple direct subdirectories with manifests, list them and ask which.
- **`/test`** — auto-detects the module the same way and runs the full workflow (coverage → generate-missing → run) instead of "show help".
- **`/init`** — detects Odoo version from `odoo/release.py` if present; uses `$CWD` basename for the project name when reasonable; prompts only for what's actually missing.
- **`/scaffold`** — module name has no filesystem-derivable default, so the bare form prompts interactively rather than refusing. Still does something useful with no args.

Each command's `argument-hint` now uses `[brackets]` for everything since nothing is strictly required.

### Cross-reference rewrites

- 92 internal `/odoo-X` references rewritten across `odoo-plugin/` (commands, skills, scripts, references, tests).
- 7 marketplace-level files updated (`README.md`, `HOOK_AUDIT_REPORT.md`, `wiki/Contribution-Guide.md`, `wiki/Ntfy-Plugin.md`, `wiki/Odoo-Plugin.md`, `wiki/Plugin-Catalog.md`, `wiki/Troubleshooting.md`).
- Plugin manifest version `1.0.0` → `2.0.0` (BREAKING — old `/odoo-X` invocations no longer resolve).

### Migration

Replace any `/odoo-X` muscle memory with the bare command name:
- `/odoo-init --version 19 --project foo` → `/init` (auto-detect) or `/init --version 19 --project foo`
- `/odoo-test mymodule` → `/test mymodule` (or just `/test` from inside the module dir)
- `/odoo-upgrade ./addons/foo 19` → `/upgrade ./addons/foo 19` (or just `/upgrade` from inside the module)

Plugin-namespaced forms are always correct: `/odoo-plugin:init`, `/odoo-plugin:test`, etc.

### Verification

- `python validate_plugin_simple.py odoo-plugin` — passes.
- All 17 commands now run sensibly with no arguments.
