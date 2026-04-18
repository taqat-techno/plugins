---
description: Manage ragtools projects. Standalone (no args) defaults to list. Subcommands list / status / summary / files / add / remove / enable / disable / rebuild. Prefers MCP project-ops tools (project_status, project_summary, list_project_files, reindex_project) when loaded; falls back to HTTP API. Refuses writes when the service is down. Never touches config.toml directly.
argument-hint: "[list | status <id> | summary <id> [<top_n>] | files <id> [<limit>] | add <path> [<name>] | remove <id> | enable <id> | disable <id> | rebuild [<id>]]"
allowed-tools: Bash(curl:*), Bash(test:*), Bash(printenv:*), Bash(echo:*), Bash(rag service:*), Bash(rag version:*), Bash(where rag:*), Bash(which rag:*), Read, mcp__plugin_rag_ragtools__list_projects, mcp__plugin_rag_ragtools__project_status, mcp__plugin_rag_ragtools__project_summary, mcp__plugin_rag_ragtools__list_project_files, mcp__plugin_rag_ragtools__run_index, mcp__plugin_rag_ragtools__reindex_project
disable-model-invocation: false
author: TaqaTechno
version: 0.5.0
---

# /rag-projects

CRUD on ragtools projects via the HTTP API at `127.0.0.1:21420`. **Never edits `config.toml` directly** — every write goes through `POST /api/projects`, `DELETE /api/projects/{id}`, or `POST /api/projects/{id}/rebuild`. The HTTP API funnels writes through `get_config_write_path()`, which is the only path that survived the v2.4.1 audit (F-001).

## Behavior

**Read ops** (`list`) — allowed in any service mode. If service is up, hits the HTTP API. If down, prints a one-line note that we cannot list projects without the service (we do not fall back to parsing `config.toml` ourselves — the schema is owned by the product).

**Write ops** (`add`, `remove`, `enable`, `disable`, `rebuild`) — **refused when the service is down** per D-005. Print a clear "service must be running for write operations" message and offer to start it via `rag service start`.

**Compact-by-default** (D-008): tabular output, ≤ 25 lines, drill-down only on user request.

## Required steps (perform in order)

### Step 0 — State detection (state-gate preamble)

Follow the canonical recipe in `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Produce the `state` object, print the 6-line mode banner. **Do not re-implement** — reference the rule file.

**State gate** — refuse early on bad states:

| Detected state | Action |
|---|---|
| `install_mode == not-installed` | Refuse: `ragtools is not installed. run /rag-setup first.` Stop. |
| `service_mode == BROKEN` | Refuse: `service is broken. run /rag-doctor --full --fix.` Stop. |
| `service_mode == STARTING` | Ask user to retry in 10s once the encoder finishes loading. Stop. |
| `service_mode == DOWN`, subcommand is a read op (`list`) | Print `cannot list projects with service down. start with: rag service start`. Stop. |
| `service_mode == DOWN`, subcommand is a write op | Refuse writes (per D-005) — see Step 1. |
| `service_mode == UP` | Continue. |

### Step 1 — Parse subcommand

The first positional argument is the subcommand. **No subcommand → default to `list`** (v0.5.0 — the command is generic and works standalone).

Whitelist:

| Subcommand | Args | Tier | Preferred MCP tool (v0.5.0+) |
|---|---|---|---|
| `list` (default) | none | read | `list_projects` (core) |
| `status` | `<id>` | read | `project_status` (project ops, default ON) |
| `summary` | `<id> [<top_n>]` | read | `project_summary` (project ops, default ON) |
| `files` | `<id> [<limit>]` | read | `list_project_files` (project ops, default ON) |
| `add` | `<path> [<name>]` | write | HTTP only — MCP excludes `add_project` by design (see `rules/mcp-envelope.md` §8) |
| `remove` | `<id>` | write | HTTP only — MCP excludes `remove_project` by design |
| `enable` | `<id>` | write | HTTP only (no equivalent MCP tool) |
| `disable` | `<id>` | write | HTTP only (no equivalent MCP tool) |
| `rebuild` | `[<id>]` | write | `reindex_project` (project ops, default ON, confirm_token + 30s cooldown + auto-backup) |

If the subcommand is unknown, print usage and stop.

If the subcommand is a **write op AND `service_mode != UP`**, refuse:
```
write operations require a running service.
service mode: <DOWN|BROKEN>
start with: rag service start
then re-run: /rag-projects <subcommand>
```

All MCP-using branches honor `${CLAUDE_PLUGIN_ROOT}/rules/mcp-envelope.md` — envelope → `error_code` → `mode` → fallback chain.

### Step 2 — Detect cloud-sync risk before any write

For write operations, resolve the config path from the mode banner. Check whether the parent directory is inside a known cloud-synced location:

| Sync provider | Path indicators (any match) |
|---|---|
| Syncthing | path contains `\Syncthing\` or `/Syncthing/` or sibling `.stfolder` exists |
| iCloud (macOS) | path contains `Mobile Documents/com~apple~CloudDocs/` |
| OneDrive | path contains `\OneDrive\` or `/OneDrive/` or `OneDrive - ` |
| Dropbox | path contains `\Dropbox\` or `/Dropbox/` |
| Google Drive | path contains `\Google Drive\` or `/Google Drive/` |

If any match, **print a warning before the write**:

```
⚠ config path appears to be inside a synced directory:
  <resolved config path>
  detected: <provider>

cloud sync can overwrite ragtools config from another device.
removed projects can reappear after a sync. see references/risks-and-constraints.md#syncthing--cloud-synced-config-directory.

continue with the write? (yes/no)
```

If the user says no, stop. If yes, proceed.

This is a **warning gate**, not a hard refusal — the user may have an intentional sync setup.

### Step 3 — Execute the subcommand

#### `list` (default when no args)

**Preferred (v0.5.0+):**
```
mcp__plugin_rag_ragtools__list_projects()
→ returns a formatted string listing projects with file + chunk counts
```

**Fallback:**
```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/projects
```

Parse the JSON response. Render as a markdown table with these columns: `ID`, `Name`, `Enabled`, `Files`, `Chunks`. Cap at 10 rows in compact mode; show `+N more — use --verbose` if exceeded.

If the response is `[]` or the MCP returns `"No projects found in the knowledge base."`, print: `no projects configured. add one with: /rag-projects add <path>`.

If the service is DOWN, print: `cannot list projects with service down. start with: rag service start`. **Do not** parse `config.toml` ourselves.

#### `status <id>` (new in v0.5.0)

Rich per-project health card. Requires `project_status` (MCP project-ops tool, default ON).

```
1. list_projects() → verify <id> exists; if not, offer closest matches.
2. mcp__plugin_rag_ragtools__project_status(project=<id>)
   → envelope; data shape:
     {
       "project_id": "alpha",
       "name":       "Alpha Notes",
       "path":       "C:\\...\\alpha",
       "path_exists": true,
       "enabled":     true,
       "files":       12,
       "chunks":      340,
       "last_indexed": "2026-04-18T01:14:43.763145",
       "ignore_patterns_count": 0
     }
3. Envelope handling:
   - error_code = SERVICE_DOWN | DEGRADED_MODE → "project_status requires proxy mode. start: rag service start"
   - error_code = STARTUP_FAILED → show verbatim, suggest /rag-doctor --full
4. Render a compact card:
     Project <id> — ENABLED — healthy
       Path:       <path>  (exists: true)
       Files:      <files>   Chunks: <chunks>
       Last index: <last_indexed>
       Ignore:     <ignore_patterns_count> patterns
     
   Highlight red if path_exists=false or enabled=false.
```

#### `summary <id> [<top_n>]` (new in v0.5.0)

Top-N files by chunk count. Useful to spot which files are dominating the index.

```
1. Default top_n = 10. Clamp to 1..50.
2. mcp__plugin_rag_ragtools__project_summary(project=<id>, top_files=<top_n>)
   → envelope; data shape:
     {
       "project_id": "alpha",
       "name":       "Alpha Notes",
       "path":       "...",
       "files":      12,
       "chunks":     340,
       "top_files":  [
         {"file_path": "alpha/big.md", "chunks": 143},
         {"file_path": "alpha/med.md", "chunks":  45},
         ...
       ]
     }
3. Render as a markdown table:
     Project <id> — <files> files, <chunks> chunks
     
     | Rank | File               | Chunks | % of total |
     |------|--------------------|--------|------------|
     | 1    | alpha/big.md       | 143    | 42.1%      |
     ...
```

#### `files <id> [<limit>]` (new in v0.5.0)

Complete file list for a project. Useful as the first step of the "why isn't X indexed?" workflow (also runnable directly via the skill).

```
1. Default limit = 200. Clamp to 1..1000.
2. mcp__plugin_rag_ragtools__list_project_files(project=<id>, limit=<limit>)
   → envelope; data shape:
     {
       "project_id": "alpha",
       "count":      12,
       "files": [
         {"path": "alpha/foo.md", "chunks": 23},
         ...
       ]
     }
3. Render paged table; offer --verbose to bypass compact truncation.
4. If the user is looking for a specific file and it's missing, point at:
   "not found in this project — if you think it should be indexed,
    the ragtools-ops skill's why-not-indexed workflow (2.5.3) can trace it."
```

#### `add <path> [<name>]`

1. **Validate the path exists:**
   ```bash
   test -d "<path>" && echo OK || echo MISSING
   ```
   If missing, refuse and ask for a valid path.

2. **Derive a name** if not provided: use the basename of the path, normalized to ASCII letters/digits/underscores.

3. **Check for duplicates:** `GET /api/projects` first, see if a project with the same `path` (normalized) already exists. If yes, refuse with: `project already exists: <id>`. The product also validates this server-side (v2.4 fix), but client-side check gives a faster + clearer error.

4. **POST the new project:**
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects \
     -H "Content-Type: application/json" \
     -d '{"name": "<derived name>", "path": "<absolute path>"}'
   ```

5. **Verify by re-listing:** `GET /api/projects` and confirm the new entry is present.

6. **Note about indexing:** `indexing started in background. use /rag-doctor to monitor.` — do **not** poll for completion in this command (that's `/rag-status`'s job).

#### `remove <id>`

1. **Look up the project:** `GET /api/projects` and find the matching `id`. If not found: `no such project: <id>. see /rag-projects list`.

2. **Confirmation gate:** show the project details (id, name, path, files, chunks) and ask:
   ```
   about to remove project: <id> (<name>)
     path: <path>
     files: <files>, chunks: <chunks>
   
   this removes the project from the index but does NOT delete files on disk.
   type the project id verbatim to confirm: 
   ```
   The user must type the actual `id` value (not just "yes"). This is more deliberate than a blanket "yes" and matches the `/rag-doctor` confirmation discipline.

3. **DELETE via API:**
   ```bash
   curl --max-time 5 -s -X DELETE http://127.0.0.1:21420/api/projects/<id>
   ```

4. **Verify by re-listing.** Print the updated table.

#### `enable <id>` / `disable <id>`

1. **Look up the project** as in `remove`.
2. **POST the toggle:**
   ```bash
   curl --max-time 5 -s -X PATCH http://127.0.0.1:21420/api/projects/<id> \
     -H "Content-Type: application/json" \
     -d '{"enabled": <true|false>}'
   ```
   (If the product uses a different endpoint shape — e.g. `POST /api/projects/<id>/enable` — the command should fall back to that. The exact shape lives in `src/ragtools/service/routes.py`.)

3. **Verify by re-listing.** No confirmation gate — enable/disable is reversible and not destructive of data.

#### `rebuild [<id>]`

**Preferred for single-project (v0.5.0+):** MCP `reindex_project` — confirm-token guard + 30s cooldown + auto-backup of state DB before the drop.

1. **If `<id>` is provided:**
   a. `list_projects()` → verify `<id>` exists.
   b. **Typed gate:** show "about to reindex <id>. auto-backup of the state DB is taken before the drop. type DELETE to confirm."
   c. Call the MCP tool with **confirm_token = `<id>` programmatically** (never user-supplied; defeats blind injection):
      ```
      mcp__plugin_rag_ragtools__reindex_project(project=<id>, confirm_token=<id>)
      ```
   d. **Envelope handling per `rules/mcp-envelope.md`:**
      - `error_code = COOLDOWN` → read `retry_after_seconds`, inform user, sleep, retry once. On second COOLDOWN, surface — do not hammer.
      - `error_code = CONFIRM_TOKEN_MISMATCH` → **never retry.** This is a plugin bug (passed wrong token). Surface verbatim.
      - `error_code = SERVICE_DOWN | DEGRADED_MODE` → refuse: "rebuild requires the service to be running".
      - Success → data has `{status: "reindexed", project_id, stats: {deleted_files, files_indexed, chunks_indexed, projects}}`.
   e. Print stats. Do not poll for completion.

   **Fallback** (MCP not granted or in failed mode): HTTP POST
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects/<id>/rebuild
   ```
   Same typed-DELETE gate applies. HTTP path does NOT include the auto-backup discipline — warn the user of this difference in the info line.

2. **If no `<id>`:** rebuild **all** projects. No MCP equivalent — the MCP intentionally does not expose a global rebuild (blast radius). **Stronger confirmation gate:**
   ```
   about to rebuild ALL projects.
   this drops every collection and re-embeds every chunk. minutes-to-hours depending on size.
   service stays responsive during the rebuild (split-lock indexing, v2.4+).
   no auto-backup is taken on this path (unlike single-project via MCP).
   
   type REBUILD to confirm:
   ```
   Then HTTP:
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/rebuild
   ```

3. **Incremental alternative (v0.5.0+):** if the user just wants to pick up new files (not re-encode existing ones), suggest:
   ```
   tip: for incremental indexing (idempotent, 2s cooldown, keeps existing chunks), use:
        "reindex project <id>" (the skill's reindex workflow calls run_index first, only escalates to destructive on drift detection)
   ```

4. **Print:** `rebuild started. monitor progress via /rag-doctor or the admin panel.` Do not poll for completion.

### Step 4 — Final mode banner

After any write op, re-probe `/health` and print the updated mode banner. If the service crashed mid-operation (rare but possible), route to `/rag-doctor`.

## Output examples

**`list` happy path (≤ 25 lines):**

```
ragtools detected: packaged-windows
service mode: UP (proxy)
binary: %LOCALAPPDATA%\Programs\RAGTools\rag.exe
config:  %LOCALAPPDATA%\RAGTools\config.toml
data:    %LOCALAPPDATA%\RAGTools\data
logs:    %LOCALAPPDATA%\RAGTools\logs

| ID         | Name        | Enabled | Files | Chunks |
|------------|-------------|---------|-------|--------|
| docs       | Docs        | ✓       | 412   | 2,103  |
| notes      | Notes       | ✓       | 89    | 540    |
| references | References  | ✓       | 746   | 6,269  |

3 projects, 1,247 files, 8,912 chunks.
```

**`list` empty:**

```
ragtools detected: packaged-windows
service mode: UP (proxy)
[paths...]

no projects configured. add one with: /rag-projects add <path>
```

**Write op with service down:**

```
ragtools detected: packaged-windows
service mode: DOWN
[paths...]

write operations require a running service.
service mode: DOWN
start with: rag service start
then re-run: /rag-projects add <path>
```

## Failure handling

| Situation | Behavior |
|---|---|
| Unknown subcommand | Print usage line and stop |
| Write op + service down | Refuse with "start the service first" message |
| Write op + service BROKEN | Refuse with "service is broken — run /rag-doctor" |
| `add` path doesn't exist | Refuse and ask for valid path |
| `add` path already configured | Refuse with "project already exists: <id>" |
| `remove` id doesn't exist | "no such project: <id>" — show available via `/rag-projects list` |
| User confirmation token wrong (e.g. typed `yes` instead of project id) | Refuse, do not retry automatically |
| Cloud-sync warning declined | Stop without writing |
| HTTP API returns 4xx | Print the response body, do not retry |
| HTTP API returns 5xx | Route to `/rag-doctor --logs` |
| HTTP API times out | Route to `/rag-doctor` |

## Boundary reminders

- **Do NOT edit `config.toml`** under any circumstances. Always go through the HTTP API. The v2.4.1 incident is the reason. (D-002, F-001)
- **Do NOT call any MCP tool.** Project management is a plugin concern; search lives in the running MCP server. (D-001)
- **Do NOT delete files on disk** when a project is removed. Removal is a config-only operation that drops the project from the index. The user's source files are untouched.
- **Do NOT retry failed writes automatically.** A failed write is information; silent retry hides it.
- **Do NOT poll for indexing completion** here. That's `/rag-doctor`'s job.
- **Do NOT bypass the cloud-sync warning** silently. Always show it before any write if the config path is inside a known synced dir.
- **Compact-by-default** per D-008.

## See also

- `/rag-doctor` — monitor indexing progress, diagnose write failures, classify known failures (e.g. F-006 "projects empty after restart"), walk repair playbooks. Absorbs the former `/rag-status` and `/rag-repair`.
- `/rag-setup` — first-time setup including the first project add. Also handles upgrades.
- `rules/state-detection.md` — canonical state-detection recipe used by the preamble
- `references/runtime-flow.md` — canonical HTTP API surface (`/api/projects`, etc.)
- `references/configuration.md` — `config.toml` schema (read-only — never write directly)
- `references/risks-and-constraints.md` — Syncthing / cloud-sync risk
- `references/known-failures.md#f-001` — the v2.4.1 config-write bug that drives D-002 and the HTTP-API-only rule
