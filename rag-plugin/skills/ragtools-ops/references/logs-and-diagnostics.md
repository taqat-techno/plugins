---
title: Logs, Diagnostics, and Health Checks
topic: logs
relates-to: [runtime-flow, repair-playbooks, known-failures]
source-sections: [§13]
---

# Logs, Diagnostics, and Health Checks

## Log locations

| Environment | Location |
|-------------|----------|
| Windows installed | `%LOCALAPPDATA%\RAGTools\logs\service.log` |
| macOS installed | `~/Library/Application Support/RAGTools/logs/service.log` |
| Dev mode | `./data/logs/service.log` |

**Rotation:** `logging.handlers.RotatingFileHandler`, 10 MB per file, 3 backups retained. Max ~40 MB total.

**Format:** `%(asctime)s %(levelname)-8s %(name)s %(message)s`

Log level is configurable via `RAG_LOG_LEVEL` or the `log_level` field in `config.toml`. Defaults to `INFO`.

## In-memory activity log

A ring buffer of **500 recent events** held in memory (`src/ragtools/service/activity.py`). Exposed via:

- `GET /api/activity` — JSON response
- Admin panel bottom drawer — polls every 15 seconds
- Dashboard "Recent Activity" card

**Not persistent** — lost on service restart. For historical diagnostics, fall back to `service.log`. See `gaps.md` for the persistent-activity-log roadmap item.

## Health endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Lightweight ready check — `{"status":"ready","collection":"markdown_kb"}` |
| `GET /api/status` | Full index stats (files, chunks, projects, last_indexed) |
| `GET /api/projects` | Configured projects with file/chunk counts |
| `GET /api/watcher/status` | Watcher running state and watched paths |
| `GET /api/config` | Current settings |
| `GET /api/mcp-config` | Dynamically-generated MCP config snippet |
| `GET /api/activity` | In-memory activity log |

## Health check CLI

```bash
rag doctor
```

Returns a table with status of Python, all dependencies (qdrant-client, sentence-transformers, mcp, fastapi, etc.), service status, data directory, state DB, collection, and ignore rules.

**Note:** when the service is running, `rag doctor` will report **"Collection NOT FOUND"** because it opens its own Qdrant client which cannot read the locked directory. This is expected behavior — see `known-failures.md#collection-not-found-while-service-up`.

## Diagnostic hint substrings to look for in `service.log`

| Substring | What it means | Action |
|---|---|---|
| `Storage folder data/qdrant is already accessed by another instance of Qdrant client` | Lock contention | `repair-playbooks.md#qdrant-already-accessed` |
| `ERROR: Application startup failed. Exiting.` | Usually paired with the lock error or a missing model cache | `repair-playbooks.md#service-will-not-start` |
| `Failed to auto-register startup task (non-fatal)` | OK if user skipped startup, or on macOS where it's not implemented | Ignore |
| `Startup sync skipped: no projects configured (check config path)` | **Diagnostic hint.** Config didn't load. | `repair-playbooks.md#projects-empty-after-restart` |
| `MPS backend out of memory` | Pre-v2.4.2 macOS bug | Upgrade to ≥ v2.4.2; see `known-failures.md#mps-out-of-memory` |
| `HuggingFace unauthenticated warning` | Cosmetic | Ignore (set `HF_TOKEN` or `TRANSFORMERS_OFFLINE=1` to suppress) |

## See also

- `runtime-flow.md` — what gets logged during startup
- `known-failures.md` — full failure-mode catalog
- `repair-playbooks.md` — step-by-step recovery for each failure mode
- `gaps.md` — persistent activity log, structured request logging
