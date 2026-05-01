---
title: 'Initialize Odoo Environment'
read_only: false
type: 'command'
description: 'Create venv, config file, directories, and check prerequisites for a new Odoo project'
argument-hint: '[--version VERSION] [--project NAME] [--port PORT] [--docker] [--db DATABASE] [--no-venv]'
---

# /init — Initialize Odoo Environment

## Bare-invocation behavior (no args)

When invoked with no arguments, gather the missing pieces interactively rather than refusing:

1. **`--version`** — if `$CWD/odoo/release.py` exists, parse `version_info` from it. Otherwise default to `19` (the latest Odoo version this plugin knows about) and confirm.
2. **`--project`** — if `$CWD` looks like a project root (contains `projects/` or has a `__manifest__.py` in a child), use the basename of `$CWD` as the project name. Otherwise prompt for a name.
3. **`--port`**, **`--docker`**, **`--db`**, **`--no-venv`** — apply documented defaults (port `8069`, no docker, db = project name, venv enabled).

Show the resolved configuration and ask for confirmation before creating any files. This makes `/init` work from any reasonable starting point without forcing the user to type every flag.

## Explicit form

```
/init [--version VERSION] [--project NAME] [--port PORT] [--docker] [--db DATABASE] [--no-venv]
```

## What It Creates

**Local venv mode** (default):
```
PROJECT/
├── .venv/                    # Virtual environment
├── conf/
│   └── PROJECT{VER}.conf     # Generated config
├── logs/
├── data/
├── backups/
├── projects/PROJECT/         # Addon directory
└── .gitignore
```

**Docker mode** (`--docker`): Additionally creates `Dockerfile`, `docker-compose.yml`, `.env`, `.env.example`.

## Generated Config

```ini
[options]
addons_path = odoo/addons,projects/PROJECT
admin_passwd = 123
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
dbfilter = PROJECT{VER}.*
http_port = 8069
gevent_port = 8072
workers = 0
```

Database credentials read from `odoo-service.local.md` if it exists, otherwise uses defaults above.

## Steps

1. Create directory structure
2. Create virtual environment (unless `--no-venv` or `--docker`)
3. Install `requirements.txt`
4. Check PostgreSQL connection
5. Generate configuration file
6. Create `.gitignore`
7. Check wkhtmltopdf

## Script

Use `env_initializer.py init --version N --project NAME` from the plugin scripts directory.
