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
| Core file guard | PreToolUse (Write/Edit) | **BLOCKS** edits to core Odoo framework files |
| Inline JS check | PreToolUse (Write/Edit) | **BLOCKS** inline JavaScript in XML templates |
| Volume-destruction guard | PreToolUse (Bash) | **BLOCKS** `compose down -v`, `docker volume rm/prune` on Odoo-stack volumes unless an explicit override token (`ALLOW_VOLUME_DELETE` / `--i-understand-data-loss`) is present |
| Restart/clone guard | PreToolUse (Bash) | **ADVISORY** (never blocks; always exits 0) — nudges on an unbounded `curl --retry-connrefused` readiness poll, a `pkill … && … odoo-bin` chain (self-kill / exit 144), and a `psql … TEMPLATE` clone (breaks the filestore) |
| Version detection | SessionStart | Detects Odoo version for context |

## Audit / Doctor Skills

These activate from natural-language symptoms (no command needed) and encode the
gettext-discipline and stack-safety rules:

| Skill | Activates when… |
|-------|-----------------|
| `odoo-i18n-audit` | A translation's `msgstr` is filled but the UI still shows the source language; reviewing a `.po` diff; after editing a translatable label/selection/help/view term; before shipping a second language |
| `odoo-stack-doctor` | A volume-destruction command is about to run; a mount-point change orphaned data; Postgres won't boot after regeneration; an upgrade "ran" but nothing changed; a theme is selected but renders blank; a standalone Postgres won't start; a restart self-kills (exit 144) or ports collide; a `-i`/`-u` was reported "exit 0" but is broken; a readiness poll or DB clone/drop is about to run |

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
