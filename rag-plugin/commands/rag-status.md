---
description: Show ragtools service status, install mode, projects, and watcher state in a compact table
argument-hint: "[--verbose]"
allowed-tools: Bash(curl:*), Bash(rag service status:*), Bash(rag version:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Bash(printenv:*), Bash(echo:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-status

Compact one-screen status of the ragtools install and service. Use this **before** any other rag-plugin operation — most other commands depend on the mode it detects.

## Behavior

**Compact mode (default)** — ≤ 25 lines:
1. Mode banner (5–7 lines): install mode, service mode, binary path, config path, data path, log path.
2. State table (≤ 12 lines): version, projects count, files indexed, chunks, last index time, watcher state.
3. One-line "see also" pointing at the next likely command.

**`--verbose` mode** — adds full HTTP API responses, raw `rag service status` output, and platform detection details.

## Required steps (perform in order)

### Step 1 — Resolve install mode

Apply the **D-004 install discovery order** (mirrors `src/ragtools/config.py`):

1. Check env vars: `printenv RAG_DATA_DIR RAG_CONFIG_PATH 2>/dev/null` (or `echo %RAG_DATA_DIR% %RAG_CONFIG_PATH%` on Windows).
2. Find binary: `where rag` (Windows) or `which rag` (macOS/Linux).
3. If no binary on PATH, check platform default install paths:
   - Windows: `test -f "$LOCALAPPDATA/Programs/RAGTools/rag.exe"`
   - macOS: typical extract dirs like `~/Applications/rag/rag`
4. Detect dev-mode: presence of `pyproject.toml` + `.venv` in CWD with `ragtools` in `[project] name`.
5. If none of the above → install mode = `not-installed`. Stop here and tell the user to run `/rag-setup` (when Phase 3 ships) or follow `references/install.md`.

Compose the install-mode label: `packaged-windows`, `packaged-macos`, `dev-mode`, or `not-installed`.

### Step 2 — Probe service health

```bash
curl --max-time 1 -s -w "\n%{http_code}" http://127.0.0.1:21420/health
```

Branch on the HTTP code:

| Result | Service mode | Continue? |
|---|---|---|
| `200` + `{"status":"ready",...}` | **UP** | Yes — fetch full state via HTTP API in step 3 |
| `200` + `{"status":"starting",...}` | **STARTING** | Wait 2 s, retry once. If still starting, report "STARTING" and stop. |
| Connection refused / timeout / `000` | **DOWN** | Skip step 3, use CLI fallback in step 4 |
| `500` / hang | **BROKEN** | Skip step 3, recommend `/rag-doctor` and `references/repair-playbooks.md#service-will-not-start` |

### Step 3 — When service is UP: fetch state via HTTP API

Run these in parallel (single Bash call with `&` background plus `wait`, or sequential — your choice):

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/status
curl --max-time 2 -s http://127.0.0.1:21420/api/projects
curl --max-time 2 -s http://127.0.0.1:21420/api/watcher/status
```

Parse the JSON responses. Extract:
- `version` from `/api/status`
- `projects` count, total `files`, total `chunks`, `last_indexed` from `/api/status`
- `id`, `name`, `enabled`, `file_count`, `chunk_count` per project from `/api/projects`
- `running`, `watched_paths` count from `/api/watcher/status`

### Step 4 — When service is DOWN: CLI fallback

Print a warning line: `service down → using CLI direct mode (encoder will load, ~5–10 s)`.

Then:
```bash
rag version 2>&1
rag service status 2>&1
```

Do **NOT** run `rag index`, `rag rebuild`, `rag watch`, or anything that opens Qdrant in direct mode — that would fight the eventual service. Only read-only ops in this branch.

If even `rag version` fails, the binary is missing or broken — recommend `/rag-doctor`.

### Step 5 — Render compact output

**Mode banner** (always, ≤ 7 lines):

```
ragtools detected: <install-mode>
service mode: <UP (proxy) | DOWN (direct fallback) | STARTING | BROKEN>
binary: <resolved path or "not found">
config:  <resolved path or "not found">
data:    <resolved path or "not found">
logs:    <resolved path or "not found">
```

**State table** (when service is UP, ≤ 12 lines):

```
| Field         | Value                                  |
|---------------|----------------------------------------|
| Version       | ragtools v2.4.2                        |
| Projects      | 3 (3 enabled)                          |
| Files indexed | 1,247                                  |
| Chunks        | 8,912                                  |
| Last indexed  | 2 minutes ago                          |
| Watcher       | running, 3 paths                       |
```

If multiple projects, add a second small table:

```
| ID         | Name        | Files | Chunks |
|------------|-------------|-------|--------|
| docs       | Docs        | 412   | 2,103  |
| notes      | Notes       | 89    | 540    |
| references | References  | 746   | 6,269  |
```

Cap at 5 projects in compact mode; show "+N more — use --verbose" if there are more.

**Footer** (one line):

```
see also: /rag-doctor for a deeper health check
```

### Step 6 — `--verbose` extras (only if requested)

Append:
- Raw `/health`, `/api/status`, `/api/projects`, `/api/watcher/status` JSON (collapsed under headings)
- Output of `rag service status` (CLI version)
- All `RAG_*` env vars currently set
- Platform info (`uname -a` or `ver`)

## Failure handling

- **Binary not found** → mode banner only, with `not-installed` label, and one line: `run /rag-setup or see references/install.md`.
- **Service DOWN, binary present** → mode banner + CLI fallback output + one line: `start the service: rag service start`.
- **Service BROKEN (500/hang)** → mode banner + one line: `service is broken; run /rag-doctor or see references/repair-playbooks.md#service-will-not-start`.
- **Network error on a localhost curl** → that's a service-down, treat as DOWN.
- **Curl missing** (rare on Windows) → fall back to `Invoke-WebRequest -Uri http://127.0.0.1:21420/health -TimeoutSec 1` if PowerShell is available; otherwise tell the user to install curl or check `rag service status` directly.

## Boundary reminders

- Do **not** call any MCP tool from this command (D-001). The MCP server is for Claude's own use.
- Do **not** edit `config.toml` (D-002). This is a read-only command.
- Do **not** open Qdrant. CLI direct mode is fine for `rag version` / `rag service status` but **never** for `rag index` / `rag rebuild` / `rag watch`.
- Compact-by-default per D-008. Tables, not paragraphs.

## See also

- `/rag-doctor` — deeper structured health check via `rag doctor`
- `references/runtime-flow.md` — full HTTP API surface
- `references/paths-and-layout.md` — path resolution rules
- `references/quick-checklist.md` — 7-step triage flow when status is bad
