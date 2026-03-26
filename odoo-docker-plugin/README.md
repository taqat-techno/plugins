# odoo-docker Plugin

> **v2.1.0** — Path-scoped hooks, user configuration, slimmed skill, extensible templates

Docker infrastructure manager for Odoo — production deployment, nginx proxy, CI/CD pipelines, performance tuning, multi-version image management, and container debugging for Odoo 14-19 Enterprise.

## Installation

Add to your Claude Code settings:
```json
{
  "odoo-docker@plugins": true
}
```

## First-Time Setup

After installation, copy the configuration example and customize it:

```bash
cp <plugin-path>/odoo-docker.local.md.example ~/.claude/odoo-docker.local.md
```

Edit `~/.claude/odoo-docker.local.md` to set your Docker Hub org, default version, and other preferences. The plugin will use these values when generating configs.

## Command

| Command | Description |
|---------|-------------|
| `/odoo-docker` | Show status + help |
| `/odoo-docker init` | Interactive project setup with auto-detection |
| `/odoo-docker compose` | Generate docker-compose for dev/staging/production |
| `/odoo-docker deploy` | Production deployment (nginx, SSL, workers, resource limits) |
| `/odoo-docker build` | Build and push Docker images (single version or all) |

## Natural Language Triggers

No slash command needed — just describe what you need:

| Category | Example Prompts |
|----------|----------------|
| **Nginx** | "Generate nginx config for my Odoo Docker setup", "Add reverse proxy with SSL" |
| **Debugging** | "My Odoo container keeps restarting", "Help me debug Docker 500 errors" |
| **Performance** | "Analyze and tune my Odoo Docker performance", "Optimize workers and PostgreSQL" |
| **Build** | "Build Docker image for Odoo 17 with my custom modules" |
| **Deploy** | "Deploy my Odoo 17 project to production using Docker" |

## Architecture

```
One base image --> Many containers --> No rebuilding per project

{image_prefix}:19.0-enterprise  (pre-built, published to Docker Hub)
  + source code (mounted read-only)
  + custom modules (mounted)
  + config file (mounted read-only)
  = Running Odoo container
```

## Plugin Structure

```
odoo-docker-plugin/
  .claude-plugin/plugin.json       # Plugin manifest
  odoo-docker/SKILL.md             # Skill — decision logic, config notes, perf data
  commands/odoo-docker.md           # /odoo-docker command with 4 sub-commands
  hooks/hooks.json                  # SessionStart detection + 7 PostToolUse file watchers
  templates/                        # 7 proven template files (compose, Dockerfile, nginx, etc.)
  reference/                        # Troubleshooting, version matrix, production checklist, patterns
  odoo-docker.local.md.example      # User configuration template
```

## Hooks

| Event | Trigger | What It Does |
|-------|---------|-------------|
| SessionStart | Session begins | Detects Docker compose files and running containers |
| PostToolUse | Edit docker-compose*.yml | Suggests recreating containers |
| PostToolUse | Edit Dockerfile* | Suggests rebuilding image |
| PostToolUse | Edit nginx*.conf | Suggests reloading nginx |
| PostToolUse | Edit .env | Reminds that `down`+`up` is needed (not just restart) |
| PostToolUse | Edit entrypoint*.sh | Reminds about chmod +x and rebuild |
| PostToolUse | Edit requirements*.txt | Suggests rebuilding image for new dependencies |
| PostToolUse | Edit conf/*.conf | Suggests container restart + key settings checklist |

All PostToolUse hooks are path-scoped — they only fire when the relevant file type is modified.

## Templates

| File | Purpose |
|------|---------|
| `docker-compose.dev.yml` | Development compose |
| `docker-compose.prod.yml` | Production with nginx, tuned PostgreSQL, resource limits |
| `nginx.conf` | Optimized reverse proxy (gzip, WebSocket, caching, rate limiting) |
| `Dockerfile.template` | Multi-version base image builder |
| `entrypoint.sh` | Universal startup script (v14-19, dev mode, debugger) |
| `odoo.conf.template` | Docker-specific Odoo configuration |
| `.env.template` | Environment variables with documentation |

## Reference Docs

| File | Purpose |
|------|---------|
| `reference/version-matrix.md` | Python, PostgreSQL, Debian, wkhtmltopdf per Odoo version |
| `reference/troubleshooting.md` | Issue-to-solution map + error patterns + diagnostic commands |
| `reference/production-checklist.md` | Pre-deployment and post-deployment verification |
| `reference/docker-patterns.md` | Performance patterns and lessons from stress tests |
| `reference/advanced-topics.md` | Deep-dive: security, SSL, CI/CD, debugging, workspace layout |
| `reference/CHANGELOG.md` | Version history and update guide for new Odoo versions |

## Customization

Users can override defaults without editing plugin files:

1. **Image prefix**: Set `image_prefix` in `~/.claude/odoo-docker.local.md`
2. **Default version**: Set `default_version` in the same file
3. **Templates**: Templates use `{placeholder}` syntax — the skill fills them in based on user config and project context
4. **Hooks**: Path matchers can be adjusted in `hooks/hooks.json` if your project uses non-standard file names

## Relationship with odoo-service

| Use `odoo-service` for... | Use `odoo-docker` for... |
|---|---|
| Start/stop server | Production deployment |
| Basic docker up/down/logs | Nginx reverse proxy |
| Database backup/restore | CI/CD pipelines |
| IDE configuration | Performance tuning |
| Environment init | Container debugging |

## Author

**TaqaTechno** — info@taqatechno.com
