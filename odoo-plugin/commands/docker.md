---
title: 'Odoo Docker'
read_only: false
type: 'command'
description: 'Docker infrastructure and container management for Odoo 14-19'
argument-hint: '[init|compose|deploy|build|up|down|logs|shell|status|update] [args...]'
---

# /docker — Docker Infrastructure & Container Management

Parse `$ARGUMENTS` and route to the appropriate operation:

## Infrastructure Operations

| Sub-command | Description | Example |
|-------------|-------------|---------|
| `init --project NAME [--version N]` | Initialize Docker project (Dockerfile, compose, .env, nginx) | `/docker init --project relief_center` |
| `compose <dev\|staging\|prod> [--version N]` | Generate docker-compose for environment | `/docker compose dev --version 19` |
| `deploy --domain DOMAIN` | Full production deployment with nginx + SSL | `/docker deploy --domain example.com` |
| `build [--all] [--no-cache]` | Build, tag, and push Docker images | `/docker build 19` |

## Container Operations

| Sub-command | Description | Example |
|-------------|-------------|---------|
| `up [--build]` | Start containers | `/docker up` |
| `down` | Stop and remove containers (keeps data) | `/docker down` |
| `start` / `stop` / `restart` | Container lifecycle | `/docker restart` |
| `logs [--tail N]` | Follow container logs | `/docker logs --tail 50` |
| `shell` | Bash shell in Odoo container | `/docker shell` |
| `odoo-shell --db DB` | Odoo interactive shell | `/docker odoo-shell --db mydb` |
| `update --db DB --module MOD` | Update module inside container | `/docker update --db mydb --module sale` |
| `install --db DB --module MOD` | Install module inside container | `/docker install --db mydb --module hr` |
| `status` | Show container status | `/docker status` |

## Status (no args)

Run diagnostics and display a summary:
1. Docker engine version and daemon status
2. Compose files found in workspace
3. Running containers and health status
4. Port mappings (8069, 8072)
5. Disk usage (`docker system df`)
6. Odoo config files found

## Execution

Use the odoo-docker skill (`skills/docker/SKILL.md`) for architecture decisions, version matrix, template placeholders, performance tuning, security, CI/CD, and troubleshooting.

Templates are in `${CLAUDE_PLUGIN_ROOT}/templates/docker/`.
Check `~/.claude/odoo-docker.local.md` for user-specific settings.

## Critical Safety Rules

- **NEVER pass `--volumes` or `-v` to `down`** unless intentionally destroying all data (database + filestore)
- **Always use the project-specific compose file** (`docker-compose.{project}.yml`) -- switching compose files switches volumes
- **DEV_MODE=0 by default** -- only enable `DEV_MODE=1` temporarily when editing Python/XML (causes 6-8s page loads on Docker Desktop)
- **On Windows Git Bash**: prefix Docker commands with `MSYS_NO_PATHCONV=1` to prevent path mangling
- **Backups must include BOTH database AND filestore** -- filestore is on disk only, not in the database
