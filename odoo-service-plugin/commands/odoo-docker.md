---
title: 'Odoo Docker Management'
read_only: false
type: 'command'
description: 'Generate Docker files and manage Odoo containers'
argument-hint: '<init|build|up|down|logs|shell|status|update> [options]'
---

# /odoo-docker — Docker Management

```
/odoo-docker <operation> [options]
```

## Operations

| Operation | Action |
|-----------|--------|
| `init --version N --project NAME` | Generate Dockerfile + docker-compose.yml + .env |
| `build [--no-cache]` | `docker-compose build` |
| `up [--build]` | `docker-compose up -d` |
| `down [--volumes]` | `docker-compose down` |
| `start` / `stop` / `restart` | Container lifecycle |
| `logs [--tail N]` | `docker-compose logs -f` |
| `shell` | `docker-compose exec odoo bash` |
| `odoo-shell --db DB` | `docker-compose exec odoo python -m odoo shell -d DB` |
| `update --db DB --module MOD` | Update module inside container |
| `install --db DB --module MOD` | Install module inside container |
| `status` | `docker-compose ps` |

## Init

Generates a version-appropriate Dockerfile with: Python base image, system deps, wkhtmltopdf, rtlcss, pip requirements. Plus docker-compose.yml with PostgreSQL service and volumes.

## Script

Use `docker_manager.py <operation> [options]` from the plugin scripts directory.
