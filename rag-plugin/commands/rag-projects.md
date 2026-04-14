---
description: Manage ragtools projects via the HTTP API — list, add, remove, enable, disable, rebuild. Refuses writes when the service is down. Never touches config.toml directly.
argument-hint: "list | add <path> [<name>] | remove <id> | enable <id> | disable <id> | rebuild [<id>]"
allowed-tools: Bash(curl:*), Bash(test:*), Bash(printenv:*), Bash(echo:*), Bash(rag service:*), Bash(rag version:*), Bash(where rag:*), Bash(which rag:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
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

The first positional argument is the subcommand. Validate against this whitelist:

| Subcommand | Args | Read or write |
|---|---|---|
| `list` | none | read |
| `add` | `<path> [<name>]` | write |
| `remove` | `<id>` | write |
| `enable` | `<id>` | write |
| `disable` | `<id>` | write |
| `rebuild` | `[<id>]` (optional, omit = rebuild all) | write |

If the subcommand is unknown, print the usage line and stop. If the subcommand is a write op AND `service_mode != UP`, refuse with:

```
write operations require a running service.
service mode: <DOWN|BROKEN>
start with: rag service start
then re-run: /rag-projects <subcommand>
```

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

#### `list`

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/projects
```

Parse the JSON response. Render as a markdown table with these columns: `ID`, `Name`, `Enabled`, `Files`, `Chunks`. Cap at 10 rows in compact mode; show `+N more — use --verbose` if exceeded.

If the response is `[]`, print: `no projects configured. add one with: /rag-projects add <path>`.

If the service is DOWN, print: `cannot list projects with service down. start with: rag service start`. **Do not** parse `config.toml` ourselves.

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

1. **If `<id>` is provided:** look up the project as in `remove`, then POST the rebuild trigger:
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects/<id>/rebuild
   ```

2. **If no `<id>`:** rebuild **all** projects. This is more destructive (re-encodes everything from scratch). **Confirmation gate:**
   ```
   about to rebuild ALL projects.
   this drops the index and re-embeds every chunk. takes minutes-to-hours depending on size.
   the service will remain responsive during the rebuild (split-lock indexing, v2.4+).
   
   type REBUILD to confirm: 
   ```

3. **POST the global rebuild:**
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/rebuild
   ```
   (Or whatever the product's global rebuild endpoint is — check `references/runtime-flow.md` for the canonical surface.)

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
