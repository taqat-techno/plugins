---
title: 'Initialize Odoo Environment'
read_only: false
type: 'command'
description: 'Create venv, config file, directories, and check prerequisites for a new Odoo project'
argument-hint: '--version VERSION --project NAME [--port PORT] [--docker]'
---

# /odoo-init — Initialize Odoo Environment

```
/odoo-init --version VERSION --project NAME [--port PORT] [--docker] [--db DATABASE] [--no-venv]
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
