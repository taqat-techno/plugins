<!-- Last updated: 2026-03-26 for v2.1.0 -->
# Production Deployment Checklist

## Pre-Deployment

### Odoo Configuration (odoo.conf)
- [ ] `workers >= 2` (minimum); `workers = 4` for heavy load
- [ ] `data_dir = /var/lib/odoo` (filestore persistence)
- [ ] `proxy_mode = True` (required behind nginx)
- [ ] `list_db = False` (prevent database enumeration)
- [ ] `admin_passwd` = strong 32+ character password
- [ ] `db_maxconn = 16` per worker (connection pool safety)
- [ ] `max_cron_threads = 1` (prevent concurrent cron conflicts)
- [ ] `limit_time_cpu = 600` (prevent runaway processes)
- [ ] `limit_time_real = 1200` (prevent hung requests)
- [ ] `limit_memory_soft = 2147483648` (2 GB)
- [ ] `limit_memory_hard = 2684354560` (2.5 GB)
- [ ] Correct gevent key: `gevent_port` (v17+) or `longpolling_port` (v14-16)

### Docker Compose
- [ ] Health checks on ALL services (db, odoo, nginx)
- [ ] Resource limits: Odoo (memory: 2G, cpus: 2)
- [ ] Resource limits: PostgreSQL (memory: 1G, cpus: 1)
- [ ] Named volumes for DB data and filestore (NOT bind mounts)
- [ ] Source code mounted read-only (`:ro`)
- [ ] Config file mounted read-only (`:ro`)
- [ ] Isolated Docker network per project
- [ ] Warm-up service for asset pre-compilation
- [ ] `restart: unless-stopped` on all services

### Nginx
- [ ] Gzip compression enabled (level 6)
- [ ] WebSocket routing (`/websocket` → port 8072)
- [ ] Static asset caching (365d for `/web/assets/`)
- [ ] Rate limiting (10 req/s per IP, burst 20)
- [ ] Client max body size: 200m
- [ ] Proxy headers set (X-Real-IP, X-Forwarded-For, X-Forwarded-Proto)
- [ ] Proxy timeouts: 600s

### Security
- [ ] SSL/TLS with Let's Encrypt or other CA
- [ ] HTTP → HTTPS redirect
- [ ] TLS 1.2+ only
- [ ] Custom database credentials (not default odoo/odoo)
- [ ] Database container NOT exposed to host
- [ ] Firewall rules configured

### PostgreSQL
- [ ] `shared_buffers` tuned (25% of RAM)
- [ ] `work_mem` tuned (16-32 MB)
- [ ] `effective_cache_size` tuned (75% of RAM)
- [ ] `maintenance_work_mem` tuned (128-512 MB)
- [ ] `random_page_cost = 1.1` (SSD)
- [ ] `checkpoint_completion_target = 0.9`
- [ ] `shm_size: '256m'` in docker-compose

### Operations
- [ ] Backup strategy in place (pg_dump scheduled)
- [ ] Tested database restore procedure
- [ ] Log aggregation configured
- [ ] Monitoring/alerting in place
- [ ] Update/upgrade procedure documented

## Post-Deployment Verification

```bash
# 1. All containers healthy
docker-compose ps

# 2. Odoo web UI accessible
curl -sf -o /dev/null -w "%{http_code}" http://localhost:8069/web/login
# Expect: 200

# 3. Health check passes
curl -sf http://localhost:8069/web/health

# 4. No errors in logs
docker-compose logs odoo 2>&1 | grep -i "ERROR\|CRITICAL"
# Expect: empty

# 5. SSL working (if configured)
curl -sf -o /dev/null -w "%{http_code}" https://yourdomain.com/web/login

# 6. WebSocket working
# Check browser console for WebSocket connection

# 7. Assets loading (no 500 errors)
# Open browser DevTools → Network → check JS/CSS responses

# 8. Filestore exists and is populated
MSYS_NO_PATHCONV=1 docker exec odoo ls /var/lib/odoo/filestore/
# Should list database name directories

# 9. Product/category images load (not broken)
# Open a product page with images — no 500 errors
```

---

## Data Safety Checklist (from real incidents)

### Volume Naming
- [ ] Volume names in docker-compose are LOCKED — never rename existing volume entries
- [ ] Volume names match what containers actually use (check `docker inspect`)
- [ ] No anonymous volumes accumulating (check `docker volume ls`)

### Backup Strategy
- [ ] Database backup scheduled: `pg_dump -Fc` (not just SQL dump)
- [ ] **Filestore backup scheduled alongside DB** — filestore is on disk only, NOT in the database
- [ ] Backup includes both: `pg_dump` + `docker cp container:/var/lib/odoo/filestore/DB_NAME`
- [ ] Restore tested: DB + filestore restored together, images verified

### Performance
- [ ] `DEV_MODE=0` in `.env` (DEV_MODE=1 causes 6-8s page loads on Docker Desktop)
- [ ] Source bind mounts are read-only where possible (`:ro` flag)
- [ ] `--dev=all` is NOT in the Odoo command line for production

### Windows-Specific
- [ ] All Docker commands in scripts use `MSYS_NO_PATHCONV=1` prefix (Git Bash path conversion breaks container paths)
