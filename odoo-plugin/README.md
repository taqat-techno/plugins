# odoo-plugin

Unified Odoo development toolkit for Claude Code — covering upgrade, frontend themes, testing, security auditing, i18n, reports, Docker infrastructure, and server lifecycle management across Odoo 14-19.

## Commands

| Command | Domain | Description |
|---------|--------|-------------|
| `/odoo-upgrade <path> [version]` | upgrade | Full module upgrade pipeline |
| `/odoo-precheck <path> [version]` | upgrade | Read-only compatibility scan |
| `/odoo-quickfix <path>` | upgrade | Safe mechanical fixes |
| `/odoo-frontend` | frontend | Environment status and capabilities |
| `/create-theme <name> <path>` | frontend | Scaffold complete theme module |
| `/odoo-docker [sub]` | docker | Docker infrastructure management |
| `/odoo-service` | service | Server lifecycle overview |
| `/odoo-start [config]` | service | Start Odoo server |
| `/odoo-stop` | service | Stop Odoo server |
| `/odoo-init` | service | Initialize environment |
| `/odoo-db [operation]` | service | Database operations |
| `/odoo-ide [target]` | service | IDE configuration |
| `/odoo-scaffold <name> <project>` | service | New module skeleton |
| `/odoo-test [sub] <model>` | test | Testing workflows |
| `/odoo-security <module>` | security | Security audit |
| `/odoo-i18n [sub]` | i18n | Translation management |
| `/odoo-report [sub]` | report | Email templates and QWeb reports |

## Safety Hooks

| Hook | Event | Behavior |
|------|-------|----------|
| Core file guard | PreToolUse | **BLOCKS** edits to core Odoo framework files |
| Inline JS check | PreToolUse | **BLOCKS** inline JavaScript in XML templates |
| Version detection | SessionStart | Detects Odoo version for context |

## Domains

- **docker** — Production deployment, nginx, CI/CD, performance tuning
- **frontend** — Theme creation, SCSS variables, snippets, Figma integration
- **i18n** — String extraction, translation validation, Arabic/RTL
- **report** — Email templates, QWeb PDF reports
- **security** — Access rules, route auth, sudo() audit, SQL injection scan
- **service** — Server lifecycle, database ops, IDE config, module scaffold
- **test** — Test generation, mock data, coverage analysis, E2E
- **upgrade** — Version migration 14→19, pattern transforms, compatibility checks

## License

LGPL-3.0-or-later (see LICENSES.md for component provenance)
