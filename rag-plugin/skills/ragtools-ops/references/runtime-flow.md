---
title: Runtime, Launch, and Execution Flows
topic: runtime
relates-to: [mcp-wiring, logs-and-diagnostics, risks-and-constraints, repair-playbooks]
source-sections: [§11]
---

# Runtime, Launch, and Execution Flows

## Service startup sequence

Sources: `src/ragtools/service/run.py`, `app.py`, `startup.py`

1. `main()` sets up rotating file logging at `%LOCALAPPDATA%\RAGTools\logs\service.log` (10 MB × 3 backups).
2. PID file is written to `{data_dir}/service.pid`.
3. `uvicorn` starts FastAPI on `127.0.0.1:21420`.
4. FastAPI `lifespan` callback:
   - Creates `Settings()` (loads config file + env vars).
   - Validates configured project paths; logs warnings for missing paths.
   - Creates `QdrantOwner` — loads encoder (`SentenceTransformer("all-MiniLM-L6-v2", device="cpu")`) and opens Qdrant client.
   - Ensures the `markdown_kb` collection exists.
5. Post-startup thread (5-second `threading.Timer`):
   - Polls `/health` until ready (up to 30 seconds).
   - Starts the file watcher (auto-starts unconditionally if there are enabled projects).
   - Registers the Windows Startup folder task if not already installed (Windows only).
   - Runs startup sync: incremental index — **guarded**: skips if `settings.projects` is empty (prevents the v2.4.1 data-loss incident).
   - Opens browser if launched from scheduler and `startup_open_browser=true`.
6. Service is ready. All HTTP traffic is handled by `routes.py`; all UI fragments by `pages.py`.

## Search flow

```
User/Claude → rag search / MCP search_knowledge_base / Admin panel search
  → Searcher.search(query)
  → encoder.encode_query(query) [LRU cache]
  → client.query_points(collection="markdown_kb", query_vector,
                        filter={project_id}, top_k=10, score_threshold=0.3)
  → formatter.format_context(results)  # full / compact / brief
  → Return with HIGH/MODERATE/LOW confidence labels
```

**Confidence labels:**
- HIGH: score ≥ 0.7
- MODERATE: 0.5 ≤ score < 0.7
- LOW: score < 0.5

Score threshold is 0.3 (results below are discarded). Re-ranking is **not implemented** — pure bi-encoder retrieval. See `risks-and-constraints.md#re-ranking-not-implemented`.

## Incremental indexing flow (split-lock design from v2.4.0)

```
Phase 1 (OUTSIDE the RLock — pure file I/O):
  scanner.scan_configured_projects() → list of (project_id, file_path)
  For each file: hash_file(), check state.file_changed()
  If changed: chunk_markdown_file() → list of Chunk
  Accumulate pending: [(pid, rel_path, hash, chunks), ...]

Phase 2 (INSIDE the RLock, windowed batches of 30 files):
  For each batch:
    Acquire owner._lock
    Flatten all batch chunks → encoder.encode_batch(texts)
    For each file in batch:
      delete_file_points(old)
      chunks_to_points() + upsert_points()
      state.update()
    state.commit()  # one commit per batch
    Release lock
```

The lock release between batches lets queued search requests run, so search latency stays in the milliseconds even during a multi-minute full index.

## CLI dual-mode

Every CLI command first probes `http://127.0.0.1:21420/health` with a 1-second timeout:

- **Service up** → command forwards to it via HTTP. Fast.
- **Service down** → command opens Qdrant directly. Encoder loads (5–10s) for commands that need embeddings.

This means most commands work even when the service is stopped, **at the cost of taking the Qdrant lock in direct mode**. Running the CLI in direct mode while Claude Code's MCP is also in direct mode will fail with a Qdrant lock error — see `known-failures.md#qdrant-already-accessed`.

## HTTP API surface

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Lightweight ready check — `{"status":"ready","collection":"markdown_kb"}` |
| `GET /api/status` | Full index stats (files, chunks, projects, last_indexed) |
| `GET /api/projects` | Configured projects with file/chunk counts |
| `POST /api/projects` | Add project |
| `DELETE /api/projects/{id}` | Remove project |
| `GET /api/watcher/status` | Watcher running state and watched paths |
| `POST /api/watcher/start` | Start watcher |
| `POST /api/watcher/stop` | Stop watcher |
| `GET /api/config` | Current settings |
| `GET /api/mcp-config` | Dynamically-generated MCP config snippet |
| `GET /api/activity` | In-memory activity log (500-event ring buffer) |

## See also

- `mcp-wiring.md` — proxy vs direct mode decision
- `logs-and-diagnostics.md` — what gets logged during startup and runtime
- `risks-and-constraints.md` — single-process constraint, MPS rule, lock contention
- `repair-playbooks.md` — what to do when startup or runtime breaks
