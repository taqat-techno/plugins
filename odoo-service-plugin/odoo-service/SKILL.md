---
name: odoo-service
description: |
  Complete Odoo server lifecycle manager — run, deploy, initialize, and manage Odoo across local venv, Docker, and any IDE. Handles server startup/shutdown, environment initialization, database management, Docker orchestration, and IDE configuration for Odoo 14-19.


  <example>
  Context: User wants to start the Odoo server
  user: "Start the Odoo 17 server for my project"
  assistant: "I will activate the virtual environment, locate the config, and start the server with the correct addons path."
  <commentary>Server start trigger.</commentary>
  </example>

  <example>
  Context: User wants to stop the server
  user: "Stop the Odoo server"
  assistant: "I will find and kill the process on port 8069/8072."
  <commentary>Server stop trigger.</commentary>
  </example>

  <example>
  Context: User wants database backup
  user: "Backup the myproject17 database"
  assistant: "I will use pg_dump to create a backup with custom format."
  <commentary>Database operation trigger.</commentary>
  </example>

  <example>
  Context: User wants IDE configuration
  user: "Set up VSCode for my Odoo 17 project with debug configs"
  assistant: "I will generate .vscode/launch.json, tasks.json, settings.json, and extensions.json with Odoo-specific configurations."
  <commentary>IDE config trigger.</commentary>
  </example>

  <example>
  Context: User wants to initialize a new environment
  user: "Initialize a new Odoo 17 environment with database"
  assistant: "I will create a venv, install requirements, configure PostgreSQL, generate .conf, and create the database."
  <commentary>Environment init trigger.</commentary>
  </example>

  <example>
  Context: User wants to create a new module
  user: "Create a new module called hr_overtime in my project"
  assistant: "I will scaffold a complete module with models, views, security, and tests."
  <commentary>Module scaffold trigger.</commentary>
  </example>
license: "MIT"
metadata:
  version: "3.0.0"
  author: "TaqaTechno"
  odoo-versions: ["14", "15", "16", "17", "18", "19"]
  environments: ["local-venv", "docker", "bare-python"]
  ide-support: ["pycharm", "vscode", "any"]
  categories: [server-management, deployment, database, docker, ide-integration]
---

# Odoo Service Skill

## Overview

The `odoo-service` skill manages the full Odoo server lifecycle:

- **Server**: Start, stop, restart Odoo (Windows, Linux, macOS)
- **Environment**: Auto-detect venv, Docker, or bare Python; initialize new environments
- **Database**: Backup, restore, create, drop, list, reset admin passwords
- **Docker**: Generate Dockerfiles, manage containers, exec into shells
- **IDE**: Generate PyCharm run configs and VSCode workspace settings
- **Modules**: Install, update, scaffold Odoo modules

## Supported Odoo Versions

| Version | Python | Notes |
|---------|--------|-------|
| 14 | 3.7-3.10 | Legacy |
| 15 | 3.8-3.11 | |
| 16 | 3.9-3.12 | |
| 17 | 3.10-3.13 | Primary dev version |
| 18 | 3.10-3.13 | cbor2 required |
| 19 | 3.10-3.13 | libmagic1 required |

## Environment Detection

Priority: Docker > venv > bare Python.

- `docker-compose.yml` or `Dockerfile` → **Docker mode**
- `.venv/`, `venv/`, or `env/` with python executable → **Local venv**
- Neither → **Bare Python**

Override with `--env venv`, `--env docker`, or `--docker`.

## Key Commands

| Task | Command |
|------|---------|
| Start (dev) | `python -m odoo -c conf/PROJECT.conf --dev=all` |
| Start (prod) | `python -m odoo -c conf/PROJECT.conf --workers=4` |
| Stop (Windows) | `FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :8069') DO taskkill /PID %P /F` |
| Stop (Linux) | `lsof -ti:8069 \| xargs kill -9` |
| Install module | `python -m odoo -c conf/PROJECT.conf -d DB -i MODULE --stop-after-init` |
| Update module | `python -m odoo -c conf/PROJECT.conf -d DB -u MODULE --stop-after-init` |
| Backup DB | `pg_dump -U odoo -Fc DB > backups/DB_DATE.dump` |
| Restore DB | `pg_restore -U odoo -d DB backup.dump` |
| Scaffold | `python odoo-bin scaffold MODULE projects/PROJECT/` |

Always use `--stop-after-init` with `-u` or `-i` operations.

## Scripts Reference

Located in `scripts/` within the plugin directory. All are standalone CLI tools:

| Script | Purpose |
|--------|---------|
| `server_manager.py` | Start, stop, status, restart, install, update modules |
| `env_initializer.py` | Create venv, generate .conf, check prerequisites |
| `db_manager.py` | Backup, restore, create, drop, list, reset-admin |
| `docker_manager.py` | Docker lifecycle, Dockerfile generation |
| `ide_configurator.py` | PyCharm and VSCode config generation |

Usage: `python scripts/server_manager.py start --config conf/myproject.conf --dev`

## User Configuration

Users can create `.claude/odoo-service.local.md` in their project root to customize defaults:

```yaml
---
author: "Your Company"
website: "https://your-website.com"
license: "LGPL-3"
db_user: "odoo"
db_password: "odoo"
---
```

These values are used by scaffold and init commands. If not present, sensible defaults apply.

## Version-Specific Notes

- **Odoo 14-16**: Use `longpolling_port` in config (not `gevent_port`)
- **Odoo 17+**: Use `gevent_port` in config
- **Odoo 19**: `<list>` replaces `<tree>` in views, `type='jsonrpc'` replaces `type='json'` in controllers, inline `invisible` expressions replace `attrs` dict
