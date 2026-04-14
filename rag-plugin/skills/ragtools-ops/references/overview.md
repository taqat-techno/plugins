---
title: ragtools — Overview and Components
topic: overview
relates-to: [install, paths-and-layout, runtime-flow]
source-sections: [§1, §2]
---

# ragtools — Overview

`ragtools` (current version **2.4.2**) is a **local-first Retrieval-Augmented Generation system** that indexes local Markdown files into an embedded Qdrant vector database and exposes them for:

- **CLI search** via the `rag` command
- **Claude Code** integration via a Model Context Protocol (MCP) server
- **Web admin panel** hosted locally on `http://127.0.0.1:21420`
- **File watcher** that auto-indexes on change

**Vendor:** TaqaTechno. **Repository:** `https://github.com/taqat-techno/rag`.

## Architectural principles

From `docs/decisions.md` in the upstream repo:

- **Single-process model** — one service process is the sole owner of the Qdrant data directory. Qdrant local mode takes an exclusive file lock; concurrent writers are not possible.
- **No cloud, no Docker, no API keys** — everything runs on the user's machine.
- **No external vector server** — Qdrant runs in embedded mode: `QdrantClient(path="...")`.
- **Single collection** called `markdown_kb` with per-project payload filtering (project isolation via `project_id` field).
- **Embedding model** `all-MiniLM-L6-v2` (384 dimensions, SentenceTransformers), forced to CPU device for cross-platform consistency.

## Repository components (upstream `C:/MY-WorkSpace/rag`)

| Area | Location | Purpose |
|------|----------|---------|
| CLI entry point | `src/ragtools/cli.py` | Typer `rag` command with subcommands |
| Config | `src/ragtools/config.py` | Pydantic Settings, path resolution, platform detection |
| Data models | `src/ragtools/models.py` | `Chunk`, `SearchResult`, etc. |
| Ignore rules | `src/ragtools/ignore.py` | Three-layer ignore (built-in + global + `.ragignore`) |
| Chunking | `src/ragtools/chunking/markdown.py` | Heading-based Markdown chunking with paragraph/sentence fallback |
| Embedding | `src/ragtools/embedding/encoder.py` | SentenceTransformer wrapper with LRU query cache |
| Indexing | `src/ragtools/indexing/{indexer,scanner,state}.py` | File scanning, SQLite state tracking, Qdrant upsert |
| Retrieval | `src/ragtools/retrieval/{searcher,formatter}.py` | Vector search + result formatting (full / compact / brief) |
| Service (FastAPI) | `src/ragtools/service/` | Admin panel, HTTP API, watcher host, owner pattern |
| MCP integration | `src/ragtools/integration/mcp_server.py` | Claude Code MCP server, proxy + direct modes |
| Watcher | `src/ragtools/watcher/observer.py` + `service/watcher_thread.py` | `watchfiles`-based auto-indexing |
| Templates | `src/ragtools/service/templates/` | Jinja2 admin panel (base, dashboard, projects, search, map, config) |
| Static assets | `src/ragtools/service/static/` | htmx, ECharts, CSS, logo, favicon |
| Tests | `tests/` | 253 pytest tests across all subsystems |
| Installer | `installer.iss`, `rag.spec`, `scripts/build.py`, `scripts/launch.vbs` | PyInstaller + Inno Setup Windows installer flow |
| CI/CD | `.github/workflows/release.yml`, `.github/workflows/test.yml` | Parallel Windows + macOS build pipeline |

## See also

- `install.md` — how to get ragtools onto a machine
- `paths-and-layout.md` — where files live after install
- `runtime-flow.md` — how the service starts and behaves
- `mcp-wiring.md` — how Claude Code talks to it
