---
title: Directory Structure and File Locations
topic: paths
relates-to: [install, configuration, runtime-flow, repair-playbooks]
source-sections: [§8]
---

# Directory Structure and Important File Locations

## Installed layout

| Path (Windows) | Path (macOS) | Purpose |
|----------------|--------------|---------|
| `%LOCALAPPDATA%\Programs\RAGTools\rag.exe` | `{extract_dir}/rag` | Main executable (PyInstaller one-dir output) |
| `%LOCALAPPDATA%\Programs\RAGTools\_internal\` | `{extract_dir}/_internal/` | Bundled Python runtime + dependencies |
| `%LOCALAPPDATA%\Programs\RAGTools\model_cache\` | `{extract_dir}/model_cache/` | Pre-bundled embedding model (`all-MiniLM-L6-v2`) |
| `%LOCALAPPDATA%\Programs\RAGTools\launch.vbs` | — | Smart launcher (Windows only) |
| `%LOCALAPPDATA%\RAGTools\config.toml` | `~/Library/Application Support/RAGTools/config.toml` | User config file |
| `%LOCALAPPDATA%\RAGTools\data\qdrant\` | `~/Library/Application Support/RAGTools/data/qdrant/` | Qdrant local storage (vector DB) |
| `%LOCALAPPDATA%\RAGTools\data\index_state.db` | `~/Library/Application Support/RAGTools/data/index_state.db` | SQLite file-hash tracking |
| `%LOCALAPPDATA%\RAGTools\logs\service.log` | `~/Library/Application Support/RAGTools/logs/service.log` | Rotating service log (10 MB × 3 backups) |
| `%LOCALAPPDATA%\RAGTools\service.pid` | `~/Library/Application Support/RAGTools/service.pid` | Running service PID file |

## Resolution rules

### Data directory resolution (`src/ragtools/config.py` → `get_data_dir()`)

1. `RAG_DATA_DIR` env var (if set)
2. Platform-specific default via `_get_app_dir()`
3. Fallback: `./data/` resolved from CWD (dev mode)

### Config file resolution (`_find_config_path()`)

1. `RAG_CONFIG_PATH` env var (if set and file exists)
2. `<platform app dir>/config.toml`
3. `./ragtools.toml` (dev mode, CWD-relative)
4. `None` → falls back to code defaults

### Config WRITE path (`get_config_write_path()`) — **CRITICAL**

**Always uses the platform app dir in packaged mode. Never CWD-relative.**

This is the v2.4.1 fix. The launcher VBScript inherited CWD `C:\Windows\System32`, the config write landed in an unwritable directory, and the startup-sync deleted "orphaned" data on the next boot. See `known-failures.md#v241-config-permission-bug` and `repair-playbooks.md#add-project-permission-denied`.

**Any plugin or tool that writes config must use the same resolved path — never CWD-relative.**

## Source/dev tree (for reference)

```
src/ragtools/
  cli.py                 # CLI commands
  config.py              # Settings, path resolution
  models.py              # Data models
  ignore.py              # Three-layer ignore rules
  chunking/markdown.py   # Heading-based Markdown chunking
  embedding/encoder.py   # SentenceTransformer + LRU query cache
  indexing/
    indexer.py           # Full + incremental indexing
    scanner.py           # File discovery, nested-path scoping
    state.py             # SQLite hash tracking
  retrieval/
    searcher.py          # Semantic search + score thresholding
    formatter.py         # Full / compact / brief output
  integration/mcp_server.py   # Claude Code MCP server
  service/
    app.py               # FastAPI app setup, singleton accessors
    owner.py             # QdrantOwner (RLock) — sole Qdrant holder
    routes.py            # HTTP API routes
    pages.py             # Admin panel rendering + fragments
    run.py               # Service startup, lifespan, post-startup tasks
    startup.py           # Windows Startup folder VBScript registration
    process.py           # PID file, start/stop/kill cross-platform
    watcher_thread.py    # Watcher thread with auto-restart
    map_data.py          # Semantic map PCA projection
    activity.py          # In-memory activity log ring buffer
    templates/*.html     # Jinja2 templates
    static/              # CSS, JS, images
  watcher/observer.py    # Low-level watchfiles loop
tests/                   # 253 pytest tests
scripts/
  build.py               # Build orchestration
  launch.vbs             # Windows smart launcher
  verify_setup.py        # Environment check
  eval_retrieval.py      # Retrieval quality evaluation
docs/                    # Decision records
```

## See also

- `configuration.md` — what goes into `config.toml` and `RAG_*` env vars
- `install.md` — how files get to these locations in the first place
- `repair-playbooks.md` — when files are missing or in the wrong place
