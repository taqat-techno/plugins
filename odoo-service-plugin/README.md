# Odoo Service Manager Plugin

[![Version](https://img.shields.io/badge/version-3.0.0-blue)](https://github.com/taqat-techno/plugins)
[![Odoo](https://img.shields.io/badge/odoo-14--19-green)](https://www.odoo.com)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

Complete Odoo server lifecycle manager for Claude Code. Run, deploy, initialize, and manage Odoo servers across any environment and any IDE.

---

## What It Does

- **Start and stop** Odoo servers across Windows, Linux, and macOS
- **Initialize** complete Odoo environments (venv, Docker, or bare Python)
- **Manage databases** — backup, restore, create, drop, list, reset passwords
- **Orchestrate Docker** — generate Dockerfiles, docker-compose files, manage containers
- **Configure IDEs** — generate PyCharm and VSCode configs with debug support
- **Scaffold modules** — generate complete module skeletons with views, security, tests
- **Smart hooks** — context-aware suggestions when you edit Odoo files

---

## Quick Start

### Start an existing project
```
/odoo-service start TAQAT17.conf --dev
```

### New project from scratch
```
/odoo-init --version 17 --project myproject
/odoo-ide vscode
/odoo-start myproject17.conf --dev
```

### Database operations
```
/odoo-db backup --db mydb
/odoo-db restore --file backups/mydb.dump --db mydb_restored
/odoo-db reset-admin --db mydb --password newpass
```

### Docker deployment
```
/odoo-docker init --version 17 --project myproject
/odoo-docker up
/odoo-docker logs
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/odoo-service` | Status + help (dispatcher) |
| `/odoo-start` | Start Odoo server |
| `/odoo-stop` | Stop Odoo server |
| `/odoo-init` | Initialize environment (venv, config, dirs) |
| `/odoo-db` | Database backup, restore, create, drop, list |
| `/odoo-docker` | Docker lifecycle management |
| `/odoo-ide` | Generate PyCharm/VSCode configurations |
| `/odoo-scaffold` | Scaffold new module skeleton |

All commands also work as `/odoo-service <sub-command>`.

---

## Smart Hooks

The plugin fires context-aware suggestions when you edit Odoo-relevant files:

| File Edited | Suggestion |
|-------------|-----------|
| `requirements*.txt` | Run `pip install -r requirements.txt` |
| `conf/*.conf` | Restart Odoo server |
| `docker-compose*.yml` | Recreate containers |
| `Dockerfile*` | Rebuild Docker image |
| `models/*.py` (new file) | Update module + check `__init__.py` imports |
| `__manifest__.py` | Update module + bump version |

Hooks only fire for matching file patterns — no noise on unrelated edits.

---

## Supported Environments

| Environment | Best For |
|-------------|---------|
| Local venv | Active development |
| Docker | Deployment, team onboarding |
| Bare Python | Quick testing |

## Supported Odoo Versions

| Version | Python | Notes |
|---------|--------|-------|
| 14 | 3.7-3.10 | Legacy |
| 15 | 3.8-3.11 | |
| 16 | 3.9-3.12 | |
| 17 | 3.10-3.13 | Primary dev version |
| 18 | 3.10-3.13 | cbor2 required |
| 19 | 3.10-3.13 | libmagic1 required |

---

## Architecture

```
odoo-service-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── odoo-service/
│   ├── SKILL.md                 # Skill definition (~140 lines)
│   └── scripts/
│       ├── server_manager.py    # Start/stop/status/restart
│       ├── env_initializer.py   # Venv, PostgreSQL, conf setup
│       ├── db_manager.py        # Backup/restore/create/drop
│       ├── docker_manager.py    # Docker lifecycle + Dockerfile gen
│       └── ide_configurator.py  # PyCharm/VSCode config gen
├── commands/
│   ├── odoo-service.md          # Dispatcher + status
│   ├── odoo-start.md            # Start server
│   ├── odoo-stop.md             # Stop server
│   ├── odoo-init.md             # Initialize environment
│   ├── odoo-db.md               # Database operations
│   ├── odoo-docker.md           # Docker management
│   ├── odoo-ide.md              # IDE configuration
│   └── odoo-scaffold.md         # Module scaffolding
├── hooks/
│   ├── hooks.json               # PostToolUse hook config
│   └── post_tool_use.py         # File-pattern-aware hook script
└── README.md
```

---

## Python Scripts

All scripts in `odoo-service/scripts/` are standalone CLI tools using only Python stdlib + optional `psutil`. They work without Odoo installed.

```bash
python server_manager.py start --config conf/myproject.conf --dev
python server_manager.py stop --port 8069
python server_manager.py status
python db_manager.py backup --db mydb --output backups/
python db_manager.py list
python docker_manager.py init --version 17 --project myproject
python ide_configurator.py --ide vscode --env local --config myproject.conf
```

---

## User Configuration

Create `.claude/odoo-service.local.md` in your project to customize defaults:

```yaml
---
author: "Your Company"
website: "https://your-website.com"
license: "LGPL-3"
db_user: "odoo"
db_password: "odoo"
---
```

These values are used by scaffold and init commands. Without this file, sensible defaults apply.

---

## Troubleshooting

### Port 8069 Already In Use
```bash
/odoo-stop
# or manually: lsof -ti:8069 | xargs kill -9
```

### PostgreSQL Not Running
```bash
# Windows: net start postgresql-x64-15
# Linux: sudo systemctl start postgresql
# Verify: pg_isready -h localhost -p 5432
```

### Module Not Appearing
```bash
python -m odoo -c conf/proj.conf -d mydb --update-list
```

---

## License

MIT License — See LICENSE file.

*Built by TaqaTechno — Odoo development specialists*
*Plugin v3.0.0*
