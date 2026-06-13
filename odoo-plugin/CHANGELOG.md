# Changelog

All notable changes to `odoo-plugin` are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

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
