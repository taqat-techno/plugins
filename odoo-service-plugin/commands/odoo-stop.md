---
title: 'Stop Odoo Server'
read_only: false
type: 'command'
description: 'Stop Odoo server by killing processes on port 8069/8072'
argument-hint: '[--port PORT] [--docker] [--all]'
---

# /odoo-stop — Stop Odoo Server

```
/odoo-stop [--port PORT] [--docker] [--all] [--force]
```

## Behavior

**Auto-detect**: If `docker-compose.yml` exists, run `docker-compose stop`. Otherwise kill local processes.

**Local — kill by port** (Windows):
```powershell
FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :8069') DO taskkill /PID %P /F
FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :8072') DO taskkill /PID %P /F
```

**Local — kill by port** (Linux/Mac):
```bash
lsof -ti:8069 | xargs kill -9
lsof -ti:8072 | xargs kill -9
```

**Docker**:
```bash
docker-compose stop
```

**`--all` flag**: Kill ALL Odoo Python processes on the system.

## Post-Stop Verification

Confirm port 8069 is no longer listening. If still in use after 3 seconds, suggest force kill.

## Script

Use `server_manager.py stop [--port PORT]` from the plugin scripts directory.
