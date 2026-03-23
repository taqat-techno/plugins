---
title: 'Odoo Service Manager'
read_only: false
type: 'command'
description: 'Odoo server lifecycle — start, stop, init, database, Docker, and IDE configuration'
argument-hint: '[start|stop|init|db|docker|ide|scaffold] [args...]'
---

# /odoo-service — Unified Odoo Service Manager

One command for the entire Odoo server lifecycle. Supports Odoo 14-19, local venv, Docker, and bare Python.

## Routing

Parse the first argument and dispatch to the appropriate sub-command:

| Input | Action | Sub-command |
|-------|--------|-------------|
| *(none)* | Show status + help | (this file) |
| `start` | Start server | `/odoo-start` |
| `stop` | Stop server | `/odoo-stop` |
| `init` | Initialize environment | `/odoo-init` |
| `db` | Database operations | `/odoo-db` |
| `docker` | Docker management | `/odoo-docker` |
| `ide` | IDE configuration | `/odoo-ide` |
| `scaffold` | Scaffold module | `/odoo-scaffold` |

Natural language also routes: "start odoo" → `start`, "backup database" → `db backup`, "set up vscode" → `ide vscode`.

## Environment Detection (All Sub-commands)

Before any operation, detect the environment:

1. `docker-compose.yml` or `Dockerfile` found? → **Docker mode**
2. `.venv/` or `venv/` with python executable? → **Local venv mode**
3. Neither → **Bare Python mode**

Override with: `--docker`, `--env local`, `--env docker`.

Also detect:
- **Odoo version**: from `odoo/release.py` or directory name `odoo{14-19}`
- **Config file**: scan `conf/` for `.conf` files
- **Running server**: check port 8069

## No Arguments — Status

When invoked with no arguments, show:

```
Odoo Service Manager
====================
Environment: Local venv (.venv/)
Odoo Version: 17.0
Server: RUNNING on port 8069 (PID 12345)
Config: conf/PROJECT17.conf

Sub-commands:
  /odoo-service start [config] [--dev]
  /odoo-service stop [--port PORT]
  /odoo-service init --version N --project NAME
  /odoo-service db <backup|restore|create|drop|list>
  /odoo-service docker <up|down|build|logs|shell>
  /odoo-service ide [vscode|pycharm|all]
  /odoo-service scaffold <name> <project>
```

## Scripts

All operations use standalone Python scripts in the plugin's `scripts/` directory:

| Script | Used By |
|--------|---------|
| `server_manager.py` | start, stop |
| `env_initializer.py` | init |
| `db_manager.py` | db |
| `docker_manager.py` | docker |
| `ide_configurator.py` | ide |
