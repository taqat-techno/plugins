<!-- Last updated: 2026-03-26 for v3.0.0 -->
# Odoo Service — Version Matrix

Single source of truth for version-specific requirements used by `env_initializer.py` and `docker_manager.py`.

## Core Matrix

| Version | Python | Docker Base Image | PostgreSQL | Node.js | Gevent Key | Entry Point |
|---------|--------|-------------------|------------|---------|------------|-------------|
| 14 | 3.7-3.10 | python:3.8-slim-buster | 12 | No | `longpolling_port` | `odoo-bin` |
| 15 | 3.8-3.11 | python:3.9-slim-bullseye | 12 | No | `longpolling_port` | `odoo-bin` |
| 16 | 3.9-3.12 | python:3.10-slim-bullseye | 12 | No | `longpolling_port` | `odoo-bin` |
| 17 | 3.10-3.13 | python:3.10-slim-bookworm | 15 | 20 LTS | `gevent_port` | `odoo-bin` |
| 18 | 3.10-3.13 | python:3.11-slim-bookworm | 15 | 20 LTS | `gevent_port` | `odoo-bin` |
| 19 | 3.10-3.13 | python:3.12-slim-bookworm | 15 | 20 LTS | `gevent_port` | `setup/odoo` |

## Breaking Changes by Version

| Version | Change |
|---------|--------|
| 17+ | `gevent_port` replaces `longpolling_port` in odoo.conf |
| 18 | `cbor2` added to requirements |
| 19 | `libmagic1` required; `<list>` replaces `<tree>`; `type='jsonrpc'` replaces `type='json'`; inline `invisible` replaces `attrs` dict |

## How to Add a New Odoo Version

Update these files when a new major version is released:

| File | What to update |
|------|---------------|
| `scripts/env_initializer.py` | `PYTHON_VERSION_REQUIREMENTS` dict + config template |
| `scripts/docker_manager.py` | `DOCKERFILES` dict — add new Dockerfile template |
| `odoo-service/SKILL.md` | Version table + `odoo-versions` in frontmatter |
| `reference/version-matrix.md` | This file — add row to Core Matrix |
| `scripts/tests/test_env_initializer.py` | Add version-specific test case |
| `scripts/tests/test_docker_manager.py` | Add Dockerfile generation test |
