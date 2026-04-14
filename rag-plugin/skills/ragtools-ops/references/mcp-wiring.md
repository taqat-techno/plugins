---
title: MCP Configuration for Claude Code
topic: mcp
relates-to: [runtime-flow, configuration, repair-playbooks, risks-and-constraints]
source-sections: [§10]
---

# MCP Configuration for Claude Code

ragtools exposes **three MCP tools** to Claude Code:

| Tool | Purpose |
|------|---------|
| `search_knowledge_base(query, project?, top_k?)` | Semantic search with optional project filter |
| `list_projects()` | Return configured project IDs |
| `index_status()` | Check if the knowledge base is ready |

**Important boundary rule (from rag-plugin `ARCHITECTURE.md`):** the rag-plugin plugin **never** calls these tools itself. Claude Code calls them directly via the MCP server. The plugin's job is to wire the MCP correctly, not to wrap it.

## Registration: three options

### Option A — Plugin-level (automatic, recommended) — v0.3.3+

**The rag-plugin ships its own `.mcp.json` at the plugin root.** When you install the plugin via `/plugins`, Claude Code auto-discovers and registers it. No manual wiring required.

The bundled config (v0.3.3, D-015 + D-019 + D-020):

```json
{
  "ragtools": {
    "type": "stdio",
    "command": "rag",
    "args": ["serve"]
  }
}
```

Two things to notice:
- **Flat shape, no `mcpServers` wrapper.** Plugin-level `.mcp.json` files use the flat shape — verified empirically against every working plugin in `~/.claude/plugins/cache/` (`chrome-devtools-mcp`, `context7`, `playwright`, `azure-devops`). The wrapped shape (`{"mcpServers": {...}}`) is the schema for **user-level** (`~/.claude/.mcp.json`) and **project-level** (`<repo>/.mcp.json`) files, not plugin-level (see D-019).
- **`command: "rag"` — direct spawn of the ragtools binary.** No Python wrapper, no launcher script, no intermediate process. Same pattern every other working MCP plugin uses. v0.3.1/v0.3.2 briefly shipped a Python launcher that broke Windows stdio pipe inheritance via `os.execvp`; see D-020 for the full retraction.

**Prerequisites for Option A:**
- `rag` must be on `PATH`.
  - **Packaged Windows:** the installer at `C:\Users\<you>\AppData\Local\Programs\RAGTools\` adds itself to PATH by default (verified via `where rag` on the v0.3.3 reporter's machine).
  - **Packaged macOS:** user must manually add the tarball extract directory to `PATH`.
  - **Dev mode:** `pip install -e .` exposes `rag` as a pyproject console-script in the active venv.
- **Fallback** if `rag` is not on PATH: run `/rag-setup`. Branch C reads `GET /api/mcp-config` and writes a user-level `~/.claude/.mcp.json` with the wrapped shape and an absolute binary path — that file takes precedence over the plugin-level file and works without requiring PATH configuration.

#### Legacy versions

- **v0.2.0 / v0.3.0** shipped the flat shape with a hardcoded `rag-mcp` command. The schema was correct, but `rag-mcp` only exists on dev pip installs — on packaged Windows (no `rag-mcp.exe` shim) the server failed to start. Symptom: `/mcp` reports "Failed to reconnect to plugin:rag:ragtools". Upgrade to v0.3.3+.
- **v0.3.1** shipped a Python launcher (correct idea for cross-install-mode resolution) **and** switched `.mcp.json` to the wrapped shape (incorrect). Symptom: `/mcp` and `/reload-plugins` report the server as present, but `ToolSearch` cannot find any ragtools tool. Upgrade to v0.3.3+.
- **v0.3.2** reverted the schema to the flat shape (correct) but kept the Python launcher (incorrect on Windows). Symptom: `ListMcpResourcesTool` shows the server registered, but no tool schemas reach the model. Root cause: Python's `os.execvp` on Windows does not preserve stdio pipe inheritance across process replacement, so the spawned `rag.exe` never receives the `tools/list` RPC. Upgrade to v0.3.3+.
- **v0.3.3+** drops the launcher entirely and spawns `rag serve` directly from `.mcp.json`. This is the first configuration that works across all known install modes without a Windows stdio bug (see D-020).

### Option B — Project-level (manual, via `/rag-setup`)

For dev mode (source install with `pip install -e .`):

```json
{
  "mcpServers": {
    "ragtools": {
      "command": "rag-mcp",
      "args": []
    }
  }
}
```

Written to `<repo>/.mcp.json`. Uses the `mcpServers` wrapper per the standard Claude Code schema for project/user-level configs.

For packaged installs without PATH integration, the admin panel at **Settings → Connect to Claude** displays the exact config pointing to the installed `rag.exe`. This is computed dynamically in `routes.py` → `mcp_config()` using `sys.frozen` detection. The HTTP endpoint is:

```
GET http://127.0.0.1:21420/api/mcp-config
```

**Use this endpoint** to get the correct config — do not hand-construct paths. `/rag-setup` branch C.1 reads this endpoint and writes `.mcp.json` for you.

### Option C — User-level (manual)

`~/.claude/.mcp.json` (global across all projects) with the same `mcpServers` wrapper as Option B. Use when you want ragtools available in every Claude Code session without per-project config.

### Valid `.mcp.json` locations (summary)

- **Plugin-level:** `plugins/rag-plugin/.mcp.json` — auto-loaded when the plugin is enabled (Option A, **default with this plugin**)
- **Project-level:** `<repo>/.mcp.json` — per-project, team-shared
- **User-level:** `~/.claude/.mcp.json` — per-user, all projects

## Dual-mode MCP server

The MCP server (`src/ragtools/integration/mcp_server.py`) probes `http://127.0.0.1:{service_port}/health` at startup:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Proxy** | Service is running | MCP forwards all calls over HTTP. Instant startup, no model load. |
| **Direct** | Service is not running | MCP loads the encoder itself and opens Qdrant directly. Takes 5–10 seconds to load the model. Qdrant client is opened/closed per request to release the file lock. |

**Retry:** v2.4.2 added a 2-second retry before falling back to direct mode, in case the service is still starting up when Claude launches the MCP server.

### Preferred setup

**Always start the service first**, then let MCP run in proxy mode. This avoids:
- Cold-start encoder load (5–10s)
- Lock contention if you also use the CLI in another terminal
- Per-request Qdrant open/close overhead

```bash
rag service start
# then launch Claude Code; MCP will detect the service and use proxy mode
```

## Important MCP constraints

- **Never run `rag index` or `rag watch` (direct mode) while Claude Code is using the MCP server in direct mode.** Both take the Qdrant file lock — only one process can hold it at a time. This is the central failure mode the Phase 6 PreToolUse hook is built to prevent.
- **Stdio purity:** the MCP server uses stdio. Any stray `print()` to stdout breaks the protocol. Do not add print statements to the rag-mcp entry point.
- **Token efficiency:** the MCP output format is **compact by default** (sentence-boundary truncation, version-suffix deduplication) to reduce Claude's context consumption by ~60–70%. Compact mode is the default; full mode is only used for the admin panel search. Plugins that re-format MCP results in a verbose way undo this work.

## See also

- `runtime-flow.md` — service startup sequence and how proxy/direct gets decided
- `configuration.md` — `RAG_SERVICE_PORT`, `RAG_SERVICE_HOST`
- `repair-playbooks.md#mcp-not-connecting` — what to do when MCP fails to connect
- `risks-and-constraints.md#single-process-constraint-hard` — the Qdrant lock invariant
