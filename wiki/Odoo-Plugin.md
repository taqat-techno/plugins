# Odoo Plugin

**Package:** `odoo` · **Version:** `1.0.0` · **Category:** development · **License:** LGPL-3.0-or-later · **Source:** [`odoo-plugin/`](../../odoo-plugin/)

## Purpose

Unified Odoo development toolkit for Claude Code. Consolidates **eight previously separate Odoo plugins** (upgrade, frontend, report, test, security, i18n, service, docker) into a single plugin with sub-skills per domain area. Supports Odoo 14, 15, 16, 17, 18, and 19.

The plugin exists because Odoo-specific Claude workflows share enough infrastructure (version detection, module structure, path resolution, `__manifest__.py` parsing) that eight narrow plugins were paying the same tax eight times. Consolidation happened during the Feb 2026 refactor (commit `ef9befe` — `feat: merge 8 Odoo plugins into unified odoo-plugin`).

## What it does

| Capability area | Sub-skill | Representative commands |
|---|---|---|
| **Version upgrade** (14 → 19 migrations) | `skills/upgrade/` | `/odoo-upgrade <path> [version]`, `/odoo-precheck <path> [version]`, `/odoo-quickfix <path>` |
| **Frontend / theme development** | `skills/frontend/` | `/odoo-frontend`, `/create-theme <name> <path>` |
| **Email templates & QWeb reports** | `skills/report/` | `/odoo-report [sub]` |
| **Security auditing** | `skills/security/` | `/odoo-security <module>` |
| **Internationalization** | `skills/i18n/` | `/odoo-i18n [sub]` |
| **Testing** | `skills/test/` | `/odoo-test [sub] <model>` |
| **Server lifecycle management** | `skills/service/` | `/odoo-service`, `/odoo-start [config]`, `/odoo-stop`, `/odoo-init`, `/odoo-db [op]`, `/odoo-ide [target]`, `/odoo-scaffold <name> <project>` |
| **Docker infrastructure** | `skills/docker/` | `/odoo-docker [sub]` |

## How it works (high level)

- **Commands are thin dispatchers.** Each `/odoo-*` command routes to the appropriate sub-skill under `skills/<area>/`. Commands expose flags but do not implement behavior.
- **Sub-skills own their domain.** Upgrade patterns live in `skills/upgrade/` with 150+ transformation patterns covering Odoo 14→19 (documented to have 95–98% success rate per `PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`). Frontend owns Bootstrap integration, theme scaffolding, SCSS variables, publicWidget patterns.
- **Data files store the knowledge.** 150+ upgrade patterns, 50+ email patterns, 30+ QWeb patterns are in `data/` — behavior reads the data, it is not hardcoded in skills.
- **Agents handle heavy analysis.** `upgrade-analyzer`, `security-auditor`, `test-analyzer`, `theme-generator` are specialized sub-agents for tasks that need more reasoning capacity than a skill should consume.
- **Hooks enforce safety.** `guard_core_odoo.py` (PreToolUse, **blocking**) prevents editing core Odoo framework files. `license-audit.py` scans for license compatibility issues.
- **References library.** Long-form companion docs live under `reference/` — loaded on demand by skills, not at session start.

## Commands (17 total)

### Upgrade area

| Command | Purpose |
|---|---|
| `/odoo-upgrade <path> [version]` | Full upgrade pipeline — detect current version, apply patterns, run validator, offer fixes |
| `/odoo-precheck <path> [version]` | **Read-only** compatibility scan — what would change, what would break |
| `/odoo-quickfix <path>` | Apply safe mechanical fixes only — no judgment calls |

### Frontend area

| Command | Purpose |
|---|---|
| `/odoo-frontend` | Environment status + theme capabilities |
| `/create-theme <name> <path>` | Scaffold a complete theme module |

### Service lifecycle area

| Command | Purpose |
|---|---|
| `/odoo-service` | Server lifecycle overview |
| `/odoo-start [config]` | Start the Odoo server |
| `/odoo-stop` | Stop the Odoo server |
| `/odoo-init` | Initialize a fresh environment (venv, PostgreSQL, configs) |
| `/odoo-db [operation]` | Database ops: backup, restore, create, drop |
| `/odoo-ide [target]` | Generate IDE configs (PyCharm, VSCode) |
| `/odoo-scaffold <name> <project>` | Create a new module skeleton |

### Domain-specific area

| Command | Purpose |
|---|---|
| `/odoo-test [sub] <model>` | Generate test skeletons, run suites, mock data, coverage analysis |
| `/odoo-security <module>` | Model access rule audit, HTTP route auth audit, `sudo()` usage analysis |
| `/odoo-i18n [sub]` | Extract translatable strings to `.po`, validate completeness, Arabic/RTL support |
| `/odoo-report [sub]` | Email templates + QWeb PDF reports, version-aware syntax |
| `/odoo-docker [sub]` | Docker infrastructure: nginx, CI/CD, production configs |

## Agents (4)

| Agent | Used by | Role |
|---|---|---|
| `upgrade-analyzer` | `/odoo-upgrade` | Deep analysis of what will change during a version jump |
| `security-auditor` | `/odoo-security` | Walks access rules, routes, `sudo()` calls |
| `test-analyzer` | `/odoo-test` | Coverage analysis and test-skeleton generation |
| `theme-generator` | `/create-theme` | Complete theme module scaffolding |

## Inputs and outputs

**Inputs:** path to a module or project, optional target Odoo version, optional subcommand.
**Outputs:** modified files (upgrade/quickfix), status reports (precheck/security/test), new module skeleton (scaffold/create-theme), or structured analysis text.

Write operations go through confirmation gates per the house convention. Upgrades always produce a backup before touching files.

## Configuration

- **`config/`** directory holds area-specific configs. Most are auto-managed.
- **`memories/`** holds session-learning artifacts — not user-configurable.
- **Environment:** Python 3.10+ for the plugin's own scripts. Odoo itself has its own Python requirements (documented per Odoo version).
- **PostgreSQL:** required for server lifecycle commands. `/odoo-init` bootstraps a dev PostgreSQL if missing.
- **Docker:** required for `/odoo-docker` and `/odoo-service` Docker paths.

## Dependencies

- Odoo source tree (this plugin does not ship Odoo itself).
- PostgreSQL for service commands.
- Docker for Docker-area commands.
- The upgrade area's pattern library is embedded in the plugin — no external DB.

## Usage examples

```
"Upgrade my_module from Odoo 16 to Odoo 19"
→ /odoo-upgrade ~/projects/my_module 19

"Create a new Odoo 17 website theme"
→ /create-theme my_theme ~/projects

"Audit my_module for security issues"
→ /odoo-security my_module

"Generate tests for the sale.order model"
→ /odoo-test generate sale.order
```

## Known limitations

- **Odoo 19 coverage** is documented at ~95% in the upgrade area's pattern library (per `PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md` §3). OWL 2.0 migration and Odoo 18 intermediary paths have known gaps.
- **Controller type migration** (`type='json'` → `type='jsonrpc'` for Odoo 17/18 → 19) is documented but the auto-fix coverage has been identified as a gap in the enhancement report. Verify manually after upgrade.
- **`attrs={}` removal** (deprecated in Odoo 17, removed in 19) — upgrade patterns mention `tree→list` but `attrs` migration is a known area to verify.
- **`guard_core_odoo.py` hook is blocking** — it will refuse edits to core Odoo paths. This is intentional; override only when you're certain the edit is correct.
- **Dev-mode assumes Odoo source is available** on the local filesystem. No remote-Odoo editing.

## Related plugins and integrations

- **devops** — track Odoo work items and sprints in Azure DevOps.
- **ntfy** — notify when long-running `/odoo-upgrade` completes.
- **pandoc** — export QWeb reports to PDF/Word from the same workflow.

## See also

- Source: [`odoo-plugin/README.md`](../../odoo-plugin/README.md) (terse; this wiki page is the richer narrative)
- `odoo-plugin/LICENSES.md` — LGPL-3.0-or-later for plugin code, attribution for embedded patterns
- `odoo-plugin/reference/` — the knowledge base loaded by skills
- `PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md` at repo root — historical gap analysis
