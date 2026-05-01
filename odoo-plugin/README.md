# odoo-plugin

Unified Odoo development toolkit for Claude Code — covering upgrade, frontend themes, testing, security auditing, i18n, reports, Docker infrastructure, and server lifecycle management across Odoo 14-19.

## Commands

| Command | Domain | Description |
|---------|--------|-------------|
| `/upgrade <path> [version]` | upgrade | Full module upgrade pipeline |
| `/precheck <path> [version]` | upgrade | Read-only compatibility scan |
| `/quickfix <path>` | upgrade | Safe mechanical fixes |
| `/frontend` | frontend | Environment status and capabilities |
| `/create-theme <name> <path>` | frontend | Scaffold complete theme module |
| `/docker [sub]` | docker | Docker infrastructure management |
| `/service` | service | Server lifecycle overview |
| `/start [config]` | service | Start Odoo server |
| `/stop` | service | Stop Odoo server |
| `/init` | service | Initialize environment |
| `/db [operation]` | service | Database operations |
| `/ide [target]` | service | IDE configuration |
| `/scaffold <name> <project>` | service | New module skeleton |
| `/test [sub] <model>` | test | Testing workflows |
| `/security <module>` | security | Security audit |
| `/i18n [sub]` | i18n | Translation management |
| `/report [sub]` | report | Email templates and QWeb reports |

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
