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
  model: sonnet
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

All templates are in `${CLAUDE_PLUGIN_ROOT}/templates/docker/`. Read them with the Read tool when generating configs.

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

## 8. Advanced Topics

For the following topics, read the reference files on demand using the Read tool:

| Topic | Reference File |
|-------|---------------|
| Performance tuning (workers, PostgreSQL, gzip) | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |
| Security hardening & SSL/TLS | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |
| CI/CD pipelines (GitHub Actions, multi-platform builds) | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |
| Centralized multi-project workspace layout | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |
| Database management in Docker | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |
| Debugging & remote debugger (debugpy) | `${CLAUDE_PLUGIN_ROOT}/reference/advanced-topics.md` |

Read `${CLAUDE_PLUGIN_ROOT}/reference/docker-patterns.md` for performance patterns and stress test data.

---

## 9. Troubleshooting

For the full troubleshooting reference with all known issue patterns and diagnostic commands, read `${CLAUDE_PLUGIN_ROOT}/reference/troubleshooting.md`.

For the production deployment checklist, read `${CLAUDE_PLUGIN_ROOT}/reference/production-checklist.md`.

---

## 10. Quick Command Reference

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

---

## Volume Safety Rules (CRITICAL - from real data-loss incidents)

These rules prevent filestore loss and data corruption.

### Never rename volume entries in compose files
When regenerating `docker-compose.{project}.yml`, detect and preserve existing volume names. Changing a volume name from `project_17_filestore` to `project_17_data` creates a brand-new empty volume. The database still references files in the old orphaned volume. Result: every image request returns HTTP 500.

### Never use `docker-compose down -v`
The `-v` flag deletes ALL named volumes -- including the filestore and database. Plain `down` (without `-v`) only removes containers and networks. Only use `-v` when you intentionally want to destroy all data.

### Switching compose files switches volumes
Running `docker-compose.yml` (default) vs `docker-compose.{project}.yml` (project-specific) mounts completely different volumes at the same path. The database doesn't change but the filestore disappears. Always use the project-specific compose file consistently.

### Filestore is NOT in the database
Odoo stores binary attachments as files in `{data_dir}/filestore/{db_name}/` on disk. The `ir_attachment` table only stores `store_fname` (a SHA1-based relative path). Restoring a database dump without restoring the corresponding filestore directory leaves all image fields pointing to nonexistent files. **Always backup and restore DB + filestore together.**

### Docker image VOLUME declarations create anonymous volumes
If the Odoo image declares `VOLUME [/var/lib/odoo /etc/odoo]` and the compose file only bind-mounts a single file like `./conf/odoo.conf:/etc/odoo/odoo.conf`, Docker creates an anonymous volume for `/etc/odoo`. Inspect container mounts with `docker inspect` to spot unexpected volumes.

### Diagnosis: use volume timestamps
`docker volume inspect <vol> --format '{{.CreatedAt}}'` reveals when each volume was created. Comparing timestamps across volumes reveals exactly when volume name drift occurred.

---

## Performance: DEV_MODE is the #1 Killer (CRITICAL)

`DEV_MODE=1` (or `--dev=all`) forces Odoo to re-read and re-parse ALL QWeb templates from XML files on EVERY page request. On Docker Desktop (Windows/Mac), the Odoo source is bind-mounted from the host, and bind mounts are 17-4000x slower than native volumes for filesystem operations.

**Combined effect: 6-8 seconds per page with DEV_MODE vs 25-100ms without.**

| Setting | Page Load | Use Case |
|---------|-----------|----------|
| `DEV_MODE=0` (default) | 25-100ms | Normal development, testing, production |
| `DEV_MODE=1` | 6-8 seconds | Only when actively editing Python/XML that needs auto-reload |

**Default: `DEV_MODE=0` in `.env`.** Only enable temporarily when you need auto-reload for the specific files you're editing. Disable immediately after.

---

## Windows Docker Issues

### MSYS_NO_PATHCONV=1 is required in Git Bash
Git Bash (MSYS2) auto-converts Unix paths like `/var/lib/odoo` to Windows paths like `C:/Program Files/Git/var/lib/odoo`. This breaks `docker exec`, `docker run -v`, and `docker run -w`.

Fix: prefix every Docker command with `MSYS_NO_PATHCONV=1`:

```bash
# Wrong (Git Bash will mangle the path):
docker exec container ls /var/lib/odoo

# Correct:
MSYS_NO_PATHCONV=1 docker exec container ls /var/lib/odoo

# Or use single-quoted bash -c:
docker exec container bash -c 'ls /var/lib/odoo'
```

---

## Backup and Restore (DB + Filestore Together)

**Always backup both database AND filestore.** A database restore without its filestore is broken -- all images return HTTP 500.

### Backup

```bash
# Database backup
MSYS_NO_PATHCONV=1 docker exec postgres pg_dump -U odoo -Fc DB_NAME > backup_DB_NAME.dump

# Filestore backup
MSYS_NO_PATHCONV=1 docker cp odoo-container:/var/lib/odoo/filestore/DB_NAME ./backup_filestore/
```

### Restore

```bash
# Restore database
MSYS_NO_PATHCONV=1 docker exec -i postgres pg_restore -U odoo -d DB_NAME --clean --if-exists < backup_DB_NAME.dump

# Restore filestore
MSYS_NO_PATHCONV=1 docker cp ./backup_filestore/DB_NAME odoo-container:/var/lib/odoo/filestore/
```

### Verify after restore
- Check image loading on key pages (products, website, categories)
- Run: `SELECT COUNT(*) FROM ir_attachment WHERE store_fname IS NOT NULL;` and verify files exist on disk
