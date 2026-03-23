---
name: odoo-docker
description: |
  Docker infrastructure manager for Odoo — production deployment, nginx proxy, CI/CD pipelines, performance tuning, multi-version image management, container debugging, and centralized workspace orchestration for Odoo 14-19 Enterprise. v2.0 consolidates nginx, debug, and perf into natural language triggers alongside the /odoo-docker sub-command interface.


  <example>
  Context: User wants to deploy Odoo to production with Docker
  user: "Deploy my Odoo 17 project to production using Docker"
  assistant: "I will use the odoo-docker skill to generate a production docker-compose.yml with Odoo, PostgreSQL, and nginx containers, with proper volume mounts and restart policies."
  <commentary>Core trigger - production Docker deployment.</commentary>
  </example>

  <example>
  Context: User wants nginx reverse proxy configuration
  user: "Set up nginx as a reverse proxy in front of my Odoo Docker container"
  assistant: "I will use the odoo-docker skill to generate an nginx.conf with SSL termination, WebSocket longpolling proxy, and proper cache headers for Odoo static assets."
  <commentary>Infrastructure trigger - nginx configuration for Odoo.</commentary>
  </example>

  <example>
  Context: User has a crashing Docker container
  user: "My Odoo Docker container keeps restarting - how do I debug it?"
  assistant: "I will use the odoo-docker skill to check container logs, verify environment variables, inspect the Odoo config, and identify the startup failure cause."
  <commentary>Debugging trigger - container crash diagnosis.</commentary>
  </example>

  <example>
  Context: User needs nginx reverse proxy for Odoo
  user: "Generate nginx config for my Odoo Docker setup"
  assistant: "I will use the odoo-docker skill to generate an optimized nginx.conf with gzip, WebSocket proxy, caching, and rate limiting."
  <commentary>Nginx trigger - reverse proxy configuration.</commentary>
  </example>

  <example>
  Context: User's container keeps crashing
  user: "My Odoo container keeps restarting, help me debug it"
  assistant: "I will use the odoo-docker skill to check container status, logs, health, network, and volumes systematically."
  <commentary>Debug trigger - container troubleshooting.</commentary>
  </example>

  <example>
  Context: User wants performance optimization
  user: "Analyze and tune my Odoo Docker performance"
  assistant: "I will use the odoo-docker skill to analyze Docker config, PostgreSQL tuning, resource limits, and generate recommendations."
  <commentary>Performance trigger - Docker tuning analysis.</commentary>
  </example>

  <example>
  Context: User wants to build Docker images
  user: "Build Docker image for Odoo 17 with my custom modules"
  assistant: "I will use the odoo-docker skill to create a Dockerfile and build the image with proper layer caching."
  <commentary>Build trigger - Docker image creation.</commentary>
  </example>
license: "MIT"
metadata:
  version: "2.1.0"
  author: "TaqaTechno"
  mode: codebase
  odoo-versions: ["14", "15", "16", "17", "18", "19"]
  categories: [docker, infrastructure, deployment, nginx, ci-cd, performance-tuning, troubleshooting]
---

# Odoo Docker Infrastructure Skill

## 1. Overview

Docker infrastructure and deployment expert for multi-version Odoo Enterprise environments. Handles production deployment, nginx configuration, CI/CD pipelines, performance tuning, security hardening, and container troubleshooting.

> **v2.1**: Nginx config, debugging, and performance tuning are handled via natural language.
> For project init, compose generation, deployment, and builds, use `/odoo-docker` sub-commands.

### What This Skill Does

- **Production Deployment**: docker-compose with nginx, SSL, PostgreSQL tuning, resource limits, warm-up
- **CI/CD Pipelines**: Build and push multi-version Docker images via GitHub Actions
- **Performance Tuning**: Data-driven recommendations from real stress tests
- **Nginx Configuration**: Optimized configs with gzip (90% CSS reduction), WebSocket, asset caching
- **Container Debugging**: Systematic troubleshooting using known issue patterns
- **Project Setup**: Auto-detect Odoo version, scan modules, generate all configs + IDE integration
- **Compose Generation**: Smart compose for dev/staging/production scenarios
- **Image Management**: Build, tag, push images for Odoo 14-19 (amd64 + arm64)

### When to Use This Skill vs `odoo-service`

| Use `odoo-service` for... | Use `odoo-docker` for... |
|---|---|
| Starting/stopping servers | Deploying to production |
| Basic `docker up/down/logs` | Configuring nginx reverse proxy |
| Database backup/restore | CI/CD pipeline setup |
| IDE configuration | Performance analysis & tuning |
| Environment initialization | Container debugging & troubleshooting |
| Module install/update | Building & pushing Docker images |

### Natural Language Triggers

- "deploy to production", "production docker setup", "deploy odoo with nginx"
- "configure nginx for odoo", "add reverse proxy", "enable gzip"
- "optimize docker performance", "slow containers", "tune workers"
- "build docker image", "push to docker hub", "ci/cd pipeline"
- "container won't start", "500 errors in docker", "debug container"
- "set up docker for this project", "initialize docker environment"
- "generate docker-compose", "create compose file"

---

## 2. User Configuration

Users can customize this plugin by creating `~/.claude/odoo-docker.local.md` with YAML frontmatter.
See `odoo-docker.local.md.example` in the plugin root for the full template.

Key settings:
- `image_prefix`: Docker Hub org/image prefix (default: `myorg/odoo`)
- `default_version`: Default Odoo version when not auto-detected (default: `17`)
- `git_org`: GitHub organization for source clone suggestions

When generating configs, check for user overrides in `.local.md` first. If not found, use template defaults and prompt the user for their image prefix on first use.

---

## 3. Architecture

### Core Principle: Source Mounted, Not Baked

```
Docker Hub:  {image_prefix}:19.0-enterprise   (pre-built base image)

Workspace:
  sources/odoo-19/          <-- Odoo Enterprise source (git clone, mounted read-only)
  projects/relief_center/   <-- Custom modules (git clone, mounted)
  compose/relief_center.yml <-- Per-project Docker Compose
  conf/relief_center.conf   <-- Per-project Odoo config

One image --> Many containers. No rebuilding per project.
```

### Key Design Decisions

1. **Source code is NOT baked into the image** — mounted at runtime via Docker volumes (read-only)
2. **Two deployment models**: Standalone workspaces (per-version Dockerfile) and centralized workspace (pre-built images from Docker Hub)
3. **Container isolation**: Each project gets its own Docker network, named volumes, port mappings

### Container Directory Structure

```
/opt/odoo/source/           <-- Odoo source (mounted, read-only)
/opt/odoo/custom-addons/    <-- Custom modules (mounted)
/etc/odoo/odoo.conf         <-- Configuration (mounted, read-only)
/var/log/odoo/              <-- Log files (mounted)
/var/lib/odoo/              <-- Filestore + compiled assets (named volume)
```

### Exposed Ports

| Port | Purpose |
|------|---------|
| **8069** | HTTP — Odoo web interface |
| **8072** | Gevent/Longpolling — WebSocket, live chat, bus |
| **5678** | Remote debugger (debugpy, optional) |

---

## 4. Template Files

All templates are in `${CLAUDE_PLUGIN_ROOT}/templates/`. Read them with the Read tool when generating configs.

| Template | Use For | Key Placeholders |
|----------|---------|-----------------|
| `docker-compose.dev.yml` | Development compose | `{postgres_image}`, `{version}`, `{project_name}` |
| `docker-compose.prod.yml` | Production compose with nginx | + `{odoo_image}` |
| `Dockerfile.template` | Building base images | `PYTHON_VERSION`, `ODOO_VERSION` (build args) |
| `nginx.conf` | Reverse proxy | `{server_name}` |
| `entrypoint.sh` | Container startup script | Environment variables (see section 7) |
| `odoo.conf.template` | Odoo configuration | `{project_name}`, `{addons_paths}`, `{gevent_or_longpolling_key}`, `{admin_password}` |
| `.env.template` | Environment variables | Copy and customize |

### Placeholder Convention

- `{placeholder}` — Must be replaced by the user/skill before use
- `${ENV_VAR:-default}` — Resolved automatically by Docker Compose at runtime

---

## 5. Version Matrix

Full version matrix is in `${CLAUDE_PLUGIN_ROOT}/reference/version-matrix.md`. Key lookup table:

| Version | PostgreSQL | Gevent Key | Entry Point | Python |
|---------|-----------|------------|-------------|--------|
| 14-16 | postgres:12 | `longpolling_port` | `odoo-bin` | 3.8-3.10 |
| 17 | postgres:15 | `gevent_port` | `odoo-bin` | 3.10 |
| 18 | postgres:15 | `gevent_port` | `odoo-bin` | 3.11 |
| 19 | postgres:15 | `gevent_port` | `setup/odoo` | 3.12 |

### Build Workarounds (Applied Automatically)

| Version | Issue | Fix |
|---------|-------|-----|
| 14 | Buster EOL | archive.debian.org mirrors |
| 14-15 | gevent compilation | Cython<3, no-build-isolation |
| 16-17 | gevent compilation | Cython<3, no-build-isolation |
| 18 | cbor2 build | PIP_CONSTRAINT="setuptools<81" |
| 19 | No `__init__.py` | PYTHONPATH=/opt/odoo/source |
| All | setuptools 80+ | PIP_CONSTRAINT="setuptools<81" |

---

## 6. Critical Configuration Notes

These are the most important settings. Getting any of them wrong causes hard-to-diagnose failures.

| Setting | Why It Matters |
|---------|---------------|
| `data_dir = /var/lib/odoo` | **CRITICAL.** Without this, filestore defaults to `~/.local/share/Odoo/` (ephemeral). JS assets return HTTP 500. |
| `workers = 0` | Single-threaded. OK for dev. At 50 users: P50 = 10s, 10% errors. Minimum production: `workers=2`. |
| `proxy_mode = True` | Required behind nginx. Without it, IP logging and URL generation are wrong. |
| `list_db = False` | Production security. Prevents database name enumeration. |
| `gevent_port` vs `longpolling_port` | v14-16: `longpolling_port`. v17+: `gevent_port`. Wrong key = WebSocket broken. |
| `db_maxconn = 16` | Without limit, 51+ idle connections accumulate under stress. Pool exhaustion risk. |

---

## 7. Environment Variables

### Entrypoint Variables

| Variable | Default | Values | Purpose |
|----------|---------|--------|---------|
| `DEV_MODE` | `0` | `0`, `1` | Enables `--dev=all` for auto-reload |
| `ENABLE_DEBUGGER` | `0` | `0`, `1` | Starts debugpy on port 5678, waits for IDE |
| `WAIT_FOR_DB` | `0` | `0`, `1` | Waits up to 30s for PostgreSQL before starting |
| `LOG_LEVEL` | (none) | `debug`, `info`, `warn`, `error`, `critical` | Overrides odoo.conf log level |
| `ODOO_EXTRA_ARGS` | (none) | Any CLI args | Passed directly to Odoo CLI |

### Port Allocation Convention

| Port | Calculation | Project 1 | Project 2 |
|------|-------------|-----------|-----------|
| HTTP | `HTTP_PORT` | 8069 | 8169 |
| Gevent | `HTTP_PORT + 3` | 8072 | 8172 |
| Debug | `HTTP_PORT + 609` | 8678 | 8778 |

---

## 8. Performance Tuning

### Workers Configuration

| Setting | Response at 50 Users | Use Case |
|---------|---------------------|----------|
| `workers=0` | P50 = 9,068ms, 10% errors | **Dev only** |
| `workers=2` | P50 ~ 800ms | Minimum production |
| `workers=4` | P50 ~ 400ms | Heavy load |

**Formula:** `workers = (CPU cores * 2) + 1` (capped at available RAM / 512MB per worker)

### PostgreSQL Tuning

| Setting | Default | 4 GB RAM | 16 GB RAM |
|---------|---------|----------|-----------|
| `shared_buffers` | 128 MB | 1 GB | 4 GB |
| `work_mem` | 4 MB | 16 MB | 32 MB |
| `effective_cache_size` | 4 GB | 3 GB | 12 GB |
| `maintenance_work_mem` | 64 MB | 128 MB | 512 MB |
| `random_page_cost` | 4.0 | 1.1 | 1.1 |

### Gzip Compression (Nginx)

| Configuration | CSS Size | Reduction |
|---------------|----------|-----------|
| Dev (Werkzeug, no gzip) | 894 KB | — |
| Prod (nginx, gzip level 6) | 89 KB | **90%** |

### Asset Warm-Up

First request after restart compiles all assets (25-120s). The production compose template includes a warm-up service that pre-loads `/web/login` and `/shop`.

---

## 9. Security Hardening

### High-Risk Issues (Fix Before Production)

| Issue | Default | Fix |
|-------|---------|-----|
| Database enumeration | `list_db = True` | `list_db = False` |
| Weak master password | `admin_passwd = 123` | Strong 32+ character password |
| No SSL/TLS | Plaintext HTTP | Nginx + Let's Encrypt |
| Default DB credentials | `odoo` / `odoo` | Custom credentials per environment |
| Proxy mode disabled | `proxy_mode = False` | `proxy_mode = True` behind nginx |

### Volume Security

- Odoo source: Always mount `:ro` (read-only)
- Config files: Always mount `:ro`
- Filestore and logs: Read-write (necessary for operation)

### Network Isolation

- Each project gets its own Docker network
- Database containers are NOT exposed to host in production
- Only nginx exposes ports to the outside

---

## 10. SSL/TLS Configuration

For production HTTPS, the nginx template (`${CLAUDE_PLUGIN_ROOT}/templates/nginx.conf`) has commented SSL blocks. Uncomment and configure:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    # ... (same location blocks as HTTP config)
}
```

Add Let's Encrypt volume to production compose:
```yaml
nginx:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
  ports:
    - "443:443"
```

---

## 11. CI/CD Pipeline

### GitHub Actions Overview

- **Triggers:** Push to `main` (Dockerfile/entrypoint/requirements changes) or manual dispatch
- **Matrix:** Builds all 6 versions in parallel
- **Multi-platform:** `linux/amd64` + `linux/arm64`
- **Cache:** GitHub Actions layer cache per version
- **Tags:** `{image_prefix}:{version}.0-enterprise` + SHA suffix

### Required Secrets

| Secret | Purpose |
|--------|---------|
| `DOCKERHUB_USERNAME` | Docker Hub login |
| `DOCKERHUB_TOKEN` | Docker Hub access token |

The full GitHub Actions workflow template is generated by `/odoo-docker build --generate-ci`.

---

## 12. Centralized Multi-Project Workspace

### Layout

```
~/odoo-docker/
├── sources/         <-- Git clones of Odoo Enterprise (per version)
├── projects/        <-- Git clones of custom modules (per project)
├── conf/            <-- Generated Odoo configs
├── compose/         <-- Generated Docker Compose files
├── logs/            <-- Runtime logs
├── scripts/         <-- start.sh, stop.sh, logs.sh, shell.sh
├── .env             <-- Global config
└── .env.local       <-- Machine-specific overrides
```

### Daily Commands

```bash
./scripts/start.sh <project>            # Start containers
./scripts/start.sh <project> --dev      # Start with auto-reload
./scripts/stop.sh <project>             # Stop containers
./scripts/logs.sh <project>             # Odoo logs
./scripts/shell.sh <project> 19         # Bash into container
```

### Running Multiple Projects

Assign unique ports per project in `.env`:
```env
RELIEF_CENTER_HTTP_PORT=8069
SOQYA_HTTP_PORT=8169
TAQAT_HTTP_PORT=8269
```

---

## 13. Database Management in Docker

### Create Database via API

```bash
curl -s -X POST http://localhost:8069/web/database/create \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"master_pwd":"changeme","name":"my_db","lang":"en_US","password":"admin","login":"admin"}}'
```

### Access from Host

```bash
psql -h localhost -p 5433 -U odoo -d my_database
```

### Backup and Restore

```bash
docker exec {db_container} pg_dump -U odoo my_database > backup.sql
docker exec -i {db_container} psql -U odoo -d my_database < backup.sql
```

---

## 14. Debugging & Development

### Dev Mode

```bash
DEV_MODE=1 docker compose up -d
```

### Remote Debugger (debugpy)

1. Set `ENABLE_DEBUGGER=1` in `.env`
2. Expose port `5678:5678` in docker-compose
3. Container waits for IDE attach
4. VS Code config:
```json
{
  "name": "Attach to Odoo Docker",
  "type": "debugpy",
  "request": "attach",
  "connect": { "host": "localhost", "port": 5678 },
  "pathMappings": [
    { "localRoot": "${workspaceFolder}", "remoteRoot": "/opt/odoo/source" }
  ]
}
```

### Module Management Inside Container

```bash
python -m odoo -c /etc/odoo/odoo.conf -d {db} -u {module} --stop-after-init
python -m odoo -c /etc/odoo/odoo.conf -d {db} -i {module} --stop-after-init
```

---

## 15. Troubleshooting

For the full troubleshooting reference with all known issue patterns and diagnostic commands, read `${CLAUDE_PLUGIN_ROOT}/reference/troubleshooting.md`.

For performance-related patterns and lessons learned from stress tests, read `${CLAUDE_PLUGIN_ROOT}/reference/docker-patterns.md`.

For the production deployment checklist, read `${CLAUDE_PLUGIN_ROOT}/reference/production-checklist.md`.

---

## 16. Quick Command Reference

```bash
# Build local image
docker compose build

# Pull pre-built image
docker pull {image_prefix}:19.0-enterprise

# Start / Stop
docker compose up -d
docker compose down

# Logs / Shell
docker compose logs -f odoo
docker compose exec odoo bash

# Module update inside container
python -m odoo -c /etc/odoo/odoo.conf -d {db} -u {module} --stop-after-init
```
