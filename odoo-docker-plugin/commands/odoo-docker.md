---
title: 'Odoo Docker Infrastructure'
read_only: false
type: 'command'
description: 'Docker infrastructure for Odoo - init, compose, deploy, build, and status'
argument-hint: '[init|compose|deploy|build] [args...]'
---

# /odoo-docker - Unified Docker Infrastructure

Parse `$ARGUMENTS` and route to the appropriate operation:

| Sub-command | Description | Example |
|-------------|-------------|---------|
| `init` | Initialize Docker project structure | `/odoo-docker init --project relief_center` |
| `compose` | Generate docker-compose for dev/staging/prod | `/odoo-docker compose dev --version 19` |
| `deploy` | Full production deployment with nginx + SSL | `/odoo-docker deploy --domain example.com` |
| `build` | Build, tag, and push Docker images | `/odoo-docker build 19` or `build --all` |
| *(none)* | Show Docker status + help | `/odoo-docker` |

## Status (no args)

Run these diagnostics and display results in a summary:

1. **Docker engine**: Run `docker --version` and check if Docker daemon is running
2. **Compose files**: Glob for `**/docker-compose*.{yml,yaml}` — list found files
3. **Running containers**: Run `docker compose ps` (if compose file exists) or `docker ps --filter name=odoo`
4. **Container health**: Show health status for each running container
5. **Port usage**: Show which ports are mapped (8069, 8072, etc.)
6. **Disk usage**: Run `docker system df` — show images, containers, volumes size
7. **Config files**: Glob for `**/conf/*.conf` — list Odoo configs found

End with the sub-command help table above.

## Validation (built into deploy)

When running `/odoo-docker deploy`, always validate before starting containers:

1. Run `docker compose config` to validate the compose file syntax
2. Start containers with `docker compose up -d`
3. After nginx is running, run `docker compose exec nginx nginx -t` to validate nginx config
4. If either check fails, show the error and stop — do not proceed

## Execution

Use the odoo-docker skill for:
- Architecture decisions (source-mounted vs baked-in)
- Version matrix (PostgreSQL versions, Python versions per Odoo 14-19)
- Template placeholders and configuration notes
- Performance tuning (workers, PostgreSQL, gzip)
- Security hardening and SSL/TLS
- CI/CD pipeline patterns
- Troubleshooting and debugging

Check `~/.claude/odoo-docker.local.md` for user-specific `image_prefix`, `default_version`, and other settings. Replace `{image_prefix}` in generated configs with the user's value (or ask on first use).

Templates are in `${CLAUDE_PLUGIN_ROOT}/templates/`.
