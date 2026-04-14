---
title: Configuration Files and Environment Variables
topic: config
relates-to: [paths-and-layout, mcp-wiring, runtime-flow]
source-sections: [§9]
---

# Configuration

## `config.toml` / `ragtools.toml`

TOML file with optional sections. Example structure:

```toml
version = 2

[[projects]]
id = "my_project"
name = "My Project"
path = "C:\\path\\to\\project\\folder"
enabled = true
ignore_patterns = []

[[projects]]
id = "another_project"
name = "Another Project"
path = "C:\\other\\path"
enabled = true
ignore_patterns = ["*.tmp", "scratch/"]

[startup]
open_browser = true
delay = 30

[ignore]
patterns = ["*.bak", "_private/"]
```

### Schema versioning

- `version = 2` is current.
- `version = 1` was the legacy single-`content_root` format and is auto-migrated on load (`migrate_v1_to_v2()` in `src/ragtools/config.py`).

### Where the config file lives

- Packaged Windows: `%LOCALAPPDATA%\RAGTools\config.toml`
- Packaged macOS: `~/Library/Application Support/RAGTools/config.toml`
- Dev mode: `./ragtools.toml` (CWD-relative)

See `paths-and-layout.md` for the full resolution order. Writes always go to `get_config_write_path()` — never CWD-relative in packaged mode.

## Environment variables (`RAG_*` prefix)

All settings can be overridden via env vars. Full list from `src/ragtools/config.py`:

| Variable | Default | Purpose |
|----------|---------|---------|
| `RAG_CONFIG_PATH` | auto | Override config file location |
| `RAG_DATA_DIR` | auto | Override data directory |
| `RAG_QDRANT_PATH` | `data/qdrant` | Qdrant local storage path |
| `RAG_COLLECTION_NAME` | `markdown_kb` | Collection name (single, don't change) |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Model name (don't change without rebuild) |
| `RAG_CHUNK_SIZE` | `400` | Target tokens per chunk |
| `RAG_CHUNK_OVERLAP` | `100` | Overlap tokens |
| `RAG_TOP_K` | `10` | Default search result count |
| `RAG_SCORE_THRESHOLD` | `0.3` | Minimum similarity score |
| `RAG_STATE_DB` | `data/index_state.db` | SQLite state path |
| `RAG_CONTENT_ROOT` | `.` | Legacy v1 content root |
| `RAG_SERVICE_HOST` | `127.0.0.1` | Bind address |
| `RAG_SERVICE_PORT` | `21420` | Bind port |
| `RAG_LOG_LEVEL` | `INFO` | Logger level |
| `RAG_STARTUP_DELAY` | `30` | Seconds before auto-start fires |
| `RAG_STARTUP_OPEN_BROWSER` | `true` | Open browser after startup |

## `.ragignore` files

Per-directory files with **gitignore syntax**. Supports `!` negation. Parsed by `src/ragtools/ignore.py` via `pathspec`.

## Built-in ignore rules (always active)

From `src/ragtools/ignore.py`:

```
.git/, .hg/, .svn/
__pycache__/, .venv/, venv/, site-packages/, .mypy_cache/, .pytest_cache/
*.pyc, *.pyo
dist/, build/, *.egg-info/
.cache/, .claude/, CLAUDE.md
node_modules/
```

## Configuration write rules

- **Never write `ragtools.toml` from a CWD-relative path** in packaged mode. Always go through `get_config_write_path()` semantics: resolve to `%LOCALAPPDATA%\RAGTools\config.toml` (Windows) or `~/Library/Application Support/RAGTools/config.toml` (macOS).
- **Prefer the HTTP API** for project management when the service is running. The plugin will use `POST /api/projects` etc. — see `mcp-wiring.md` and `runtime-flow.md` for endpoints.
- **Refuse direct file edits** when the service is up: it would race the `QdrantOwner` config reload.

## See also

- `paths-and-layout.md` — resolution and write-path rules
- `mcp-wiring.md` — how MCP discovers config
- `runtime-flow.md` — how the service loads config at startup
- `known-failures.md#v241-config-permission-bug` — the v2.4.1 data-loss bug
