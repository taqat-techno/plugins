<!-- Last updated: 2026-03-26 for v2.1.0 -->
# Docker Troubleshooting Quick Reference

## Issue → Solution Map

### Container Startup Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Container exits immediately | Source not mounted | Fix volume path in docker-compose |
| "Odoo source not found" | Missing volume mount | `ls sources/odoo-{v}/` and fix path |
| "No module named 'odoo'" | v19 PYTHONPATH issue | Add `PYTHONPATH=/opt/odoo/source` in entrypoint |
| Container in restart loop | Python crash on start | `docker logs {container} --tail 100` |
| "Permission denied" | Wrong file ownership | Files must be owned by uid 1000 (odoo) |

### Network Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Port already in use | Another process on 8069 | Kill: `netstat -ano \| findstr :8069` + `taskkill /PID {PID} /F` |
| Can't connect to DB | DB container not ready | Add `depends_on: db: condition: service_healthy` |
| "Connection refused" on port | Container not running | `docker ps` to check, `docker-compose up -d` |
| 502 Bad Gateway | Nginx can't reach Odoo | Check Odoo health, same network, upstream config |

### Application Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| JS/CSS returns HTTP 500 | Missing `data_dir` | Add `data_dir = /var/lib/odoo` in odoo.conf |
| Very slow (10s+ response) | `workers=0` | Set `workers=2` minimum for production |
| WebSocket not working | Wrong gevent key | v14-16: `longpolling_port`, v17+: `gevent_port` |
| Module not found | Wrong addons_path | Check `addons_path` in odoo.conf vs volume mounts |
| Changes not reflecting | Module not updated | `-u {module} --stop-after-init` inside container |
| Slow first load (25-120s) | Asset compilation | Add warm-up service or accept first-load delay |

### Resource Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Container OOM killed | Insufficient memory limit | Increase `deploy.resources.limits.memory` |
| "No space left on device" | Docker disk full | `docker system prune -af` |
| High CPU usage | Too many workers | Reduce workers, check cron threads |
| 51+ idle DB connections | No `db_maxconn` limit | Set `db_maxconn = 16` per worker |

### Database Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Role does not exist" | Missing PostgreSQL user | `CREATE USER odoo WITH PASSWORD 'odoo' CREATEDB;` |
| "Database does not exist" | DB not created | Create via API or `createdb -U odoo {name}` |
| Can't connect from host | Port not exposed | Add `ports: - "5433:5432"` to db service |

### Error Patterns & Auto-Diagnosis

These error patterns commonly appear in Docker logs or CLI output. When you see them, apply the fix:

| Error Pattern | Diagnosis | Fix |
|---------------|-----------|-----|
| `port is already allocated` / `address already in use` | Another container or host process on the same port | `docker compose down`, or kill process: `netstat -ano \| findstr :8069` |
| `no space left on device` / `ENOSPC` | Docker disk full | `docker system prune -af` (aggressive), or `docker system df` to investigate |
| `502 Bad Gateway` / `upstream connect refused` | Nginx can't reach Odoo | Check: Odoo running? Same network? Health check passing? |
| `OOMKilled` / `Out of memory` | Container memory limit too low | Increase `deploy.resources.limits.memory` and check `limit_memory_hard` in odoo.conf |
| `Odoo source not found` / `No such file.*odoo-bin` | Source not mounted into container | Fix volume path in docker-compose to point to your Odoo source |

## Diagnostic Commands

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs --tail=100 odoo
docker compose logs --tail=50 db

# Check health
docker exec {container} curl -sf http://localhost:8069/web/health
docker exec {db_container} pg_isready -U odoo

# Check volumes
docker exec {container} ls -la /opt/odoo/source/
docker exec {container} ls -la /opt/odoo/custom-addons/
docker exec {container} cat /etc/odoo/odoo.conf

# Check resources
docker stats --no-stream
docker system df

# Check network
docker network ls
docker exec {container} ping -c 1 db
```

---

## Volume and Filestore Issues (from real incidents)

### All images broken after changing docker-compose

**Symptom:** Every product image, website logo, and category image returns HTTP 500 or shows broken placeholder. Database queries work fine.

**Cause:** The docker-compose file was regenerated with a different volume name (e.g., `project_17_filestore` changed to `project_17_data`). Docker created a new empty volume. The database still references files via `ir_attachment.store_fname` but those files are in the old orphaned volume.

**Diagnosis:**
```bash
# Compare volume creation timestamps
docker volume inspect project_17_data --format '{{.CreatedAt}}'
docker volume inspect project_17_filestore --format '{{.CreatedAt}}'

# Check if the old volume has the files
MSYS_NO_PATHCONV=1 docker run --rm -v project_17_filestore:/data alpine ls /data/filestore/
```

**Fix:** Either rename the volume back in the compose file, or copy files from old volume to new:
```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v project_17_filestore:/old \
  -v project_17_data:/new \
  alpine sh -c 'cp -a /old/filestore /new/'
```

### Pages load in 6-8 seconds (extreme slowness)

**Symptom:** Every page takes 6-8 seconds. CPU usage spikes on each request.

**Cause:** `DEV_MODE=1` in `.env` file. This forces Odoo to re-read and re-parse ALL QWeb templates from bind-mounted XML files on every request. Bind mounts on Docker Desktop (Windows/Mac) are 17-4000x slower than native volumes.

**Fix:** Set `DEV_MODE=0` in the project's `.env` file and restart the container:
```bash
# Edit .env
sed -i 's/DEV_MODE=1/DEV_MODE=0/' .env
docker compose -f docker-compose.{project}.yml restart odoo
```

### Docker commands fail with mangled paths on Windows

**Symptom:** `docker exec container ls /var/lib/odoo` returns "No such file or directory" or permission errors. The path shows as `C:/Program Files/Git/var/lib/odoo`.

**Cause:** Git Bash (MSYS2) auto-converts Unix paths to Windows paths before passing them to Docker.

**Fix:** Prefix with `MSYS_NO_PATHCONV=1`:
```bash
MSYS_NO_PATHCONV=1 docker exec container ls /var/lib/odoo
```

### noupdate="1" records won't refresh after module update

**Symptom:** Category images or other XML-data records still show broken/old values after running `-u module_name`.

**Cause:** Records with `noupdate="1"` in XML data files are not overwritten by module updates. If the underlying attachment is broken, `-u` won't fix it.

**Fix:** Delete the broken attachment first, then re-create:
```python
# In Odoo shell
broken = env['ir.attachment'].search([('store_fname', '!=', False), ('res_model', '=', 'product.public.category')])
for att in broken:
    if not os.path.exists(att._full_path(att.store_fname)):
        att.unlink()
# Then re-import the image via ORM or copy the file to the filestore path
```
