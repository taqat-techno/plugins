---
title: 'Stop Odoo Server'
read_only: false
type: 'command'
description: 'Stop the Odoo server on port 8069/8072 (graceful first; --all lists every Odoo server and needs your confirmation)'
argument-hint: '[--port PORT] [--docker] [--all] [--force]'
---

# /stop — Stop Odoo Server

```
/stop [--port PORT] [--docker] [--all] [--force]
```

With no arguments: if a `docker-compose.yml` / `compose.yaml` with an Odoo service is in
the project, run `docker compose stop`; otherwise stop the local server on port 8069
(and its longpolling port 8072).

## Script

All local stops go through the plugin script, never through raw `kill -9` /
`taskkill /F` by port:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/service/server_manager.py" stop [--port PORT] [--force]
```

- It sends SIGTERM (`taskkill` without `/F` on Windows) and forces a kill only if the
  port is still busy 5 seconds later.
- It refuses to stop a port owner that is visibly not an Odoo server (nginx, another
  app). `--force` overrides that; use it only when the user asks.

**Docker**: `docker compose stop` (legacy: `docker-compose stop`).

## `--all`

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/service/server_manager.py" stop --all
```

lists every Odoo **server** process on the machine (`odoo-bin`, the `odoo` console
script, `python -m odoo`) and stops nothing. It never matches this plugin's MCP server,
editors or language servers. The list can include other projects' or other users'
servers, so:

1. Show the user the list.
2. Ask the user to confirm. Do not decide for them.
3. Only after an explicit yes, re-run with `--all --yes`.

The plugin's Bash guard asks the user before `stop --all --yes` runs.

## Post-Stop Verification

Run `server_manager.py status --port PORT`. If the port is still in use, report the
PID and command line and ask before using `--force`.
