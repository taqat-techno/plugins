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

### Option A — Plugin-level (automatic, recommended) — v0.3.1+

**The rag-plugin ships its own `.mcp.json` at the plugin root.** When you install the plugin via `/plugins`, Claude Code auto-discovers and registers it. No manual wiring required.

The bundled config (v0.3.1, D-018):

```json
{
  "mcpServers": {
    "ragtools": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]
    }
  }
}
```

Two things to notice:
- **Wrapped shape with `mcpServers`.** This is the canonical Claude Code plugin MCP schema for stdio servers (see `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md:362` and every stdio example in `claude-plugins-official-main/`). The v0.3.0 flat shape turned out to be invalid for stdio plugins — the loader silently registered nothing.
- **`command: "python"` + launcher path**, not a hardcoded `rag-mcp` or `rag`. No single binary name is correct across every supported install mode, so the plugin ships a tiny Python launcher (`scripts/rag_mcp_launcher.py`, ~100 lines, stdlib only) that resolves the canonical ragtools binary at runtime and `os.execvp`-replaces itself with it. Stdio connects directly to the real MCP server — no subprocess wrapping.

The launcher resolution order:
1. `GET http://127.0.0.1:21420/api/mcp-config` with a 1s timeout — the running service knows the authoritative command for this install mode.
2. `rag` on PATH → `exec rag serve` (packaged Windows/macOS/Linux).
3. `rag-mcp` on PATH → `exec rag-mcp` (dev pip install).
4. Fail to stderr with exit 127 — Claude Code surfaces the failure in `/mcp`.

**Prerequisites for Option A (v0.3.1+):**
- `python` (or `python3` / `py`) must be on `PATH`. Every supported ragtools install mode already requires or bundles Python, so this is the minimum bar for plugin users.
- **At least one** of: ragtools service running on `127.0.0.1:21420`, `rag` on PATH, or `rag-mcp` on PATH. If none are available, the launcher fails loudly and the plugin cannot auto-wire until ragtools is installed.
- **Fallback:** if the launcher cannot resolve any binary, use Option B or Option C to manually wire a project-level or user-level `.mcp.json`.

#### Legacy (v0.3.0 and earlier)

Earlier versions shipped the flat shape with a hardcoded `rag-mcp` command:

```json
{
  "ragtools": {
    "type": "stdio",
    "command": "rag-mcp",
    "args": []
  }
}
```

This configuration is **broken on packaged Windows installs** (no `rag-mcp.exe` shim) and rejected by Claude Code's plugin loader for stdio servers regardless of the command (missing `mcpServers` wrapper). If you are on v0.3.0 and seeing `Failed to reconnect to plugin:rag:ragtools` in `/mcp`, upgrade to v0.3.1+.

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
