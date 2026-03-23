---
title: 'Start Odoo Server'
read_only: false
type: 'command'
description: 'Start Odoo server with config detection and environment awareness'
argument-hint: '[CONFIG] [--dev] [--workers N] [--docker]'
---

# /odoo-start — Start Odoo Server

```
/odoo-start [CONFIG] [--dev] [--workers N] [--db DATABASE] [--port PORT] [--detach] [--docker]
```

## Behavior

1. **Detect environment**: venv, Docker, or bare Python
2. **Find config**: If no CONFIG given, scan `conf/` and prompt user to select
3. **Check port**: If 8069 is already in use, warn and suggest `/odoo-stop`
4. **Start server**:

**Local venv**:
```bash
python -m odoo -c conf/PROJECT.conf              # basic
python -m odoo -c conf/PROJECT.conf --dev=all     # with --dev
python -m odoo -c conf/PROJECT.conf --workers=4   # production
```

**Docker**:
```bash
docker-compose up -d
docker-compose up -d --build   # if --build flag
```

## Post-Start Verification

1. Check port 8069 is listening within 10 seconds
2. HTTP GET to `/web/login` returns 200
3. Print: `Odoo is running at http://localhost:PORT`

## Script

Use `server_manager.py start --config <path> [--dev] [--workers N]` from the plugin scripts directory.
