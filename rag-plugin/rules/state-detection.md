# State detection — shared contract

Every user-facing command in `rag-plugin` begins with the same state probe. The probe produces a **state object** and a **mode banner**. Commands branch on the state object; the mode banner is printed verbatim at the top of the response.

This file is the single source of truth. Commands reference it as `see rules/state-detection.md` in their Step 0 instead of re-documenting the recipe — that is how we enforce single-owner layering (see `ARCHITECTURE.md`).

## The state object

```
state.install_mode   ∈ { not-installed, packaged-windows, packaged-macos, dev-mode, unknown }
state.service_mode   ∈ { UP, STARTING, DOWN, BROKEN, N/A }
state.mcp_available  : bool                     # true if MCP tools are in the session registry
state.mcp_mode       ∈ { proxy, direct, degraded, failed, N/A }   # from the MCP envelope
state.binary_path    : str | None
state.version        : semver | None            # from `rag version` or MCP metadata
state.config_path    : str | None
state.data_path      : str | None
state.log_path       : str | None
state.latest_version : semver | None            # only when a command explicitly fetched it
```

Cases a command can distinguish from the state object alone:

| Case | install_mode | service_mode | version |
|---|---|---|---|
| **not-installed** | `not-installed` | `N/A` | `None` |
| **installed, service down** | packaged-* / dev-mode | `DOWN` | parsed |
| **installed, service starting** | packaged-* / dev-mode | `STARTING` | parsed |
| **installed, service broken** | packaged-* / dev-mode | `BROKEN` | parsed (may be None if binary hangs) |
| **installed, healthy, old version** | packaged-* / dev-mode | `UP` | `< latest_version` |
| **installed, healthy, current version** | packaged-* / dev-mode | `UP` | `== latest_version` |
| **installed, healthy, dev/newer** | packaged-* / dev-mode | `UP` | `> latest_version` |

## The detection recipe (perform in order)

**Preferred path (v0.5.0+): MCP-first when the ragtools MCP is loaded in the session.** The MCP's `index_status` core tool works in both proxy and direct mode, returns a stable 8-key output, and subsumes parts of the HTTP/CLI probe. Fall back to HTTP and CLI when the MCP is not loaded or returns `STARTUP_FAILED`.

### Step 1 — MCP probe (preferred when tools are available)

If the ragtools MCP is loaded (`mcp__plugin_rag_ragtools__*` tools are in the session's deferred tool registry), call:

```
mcp__plugin_rag_ragtools__index_status()
```

This returns a string like:
```
[RAG STATUS] Knowledge base is ready (proxy mode).
  Collection:       markdown_kb
  Total files:      12
  Total chunks:     340
  Points:           340
  Projects:         alpha, beta
  Embedding model:  all-MiniLM-L6-v2
  Score threshold:  0.3
  Mode:             proxy (forwarding to service)
```

Parse:
- **`Mode:`** line → `service_mode = UP` if `proxy`; `DOWN` if `direct`; `BROKEN` if the call returns a string starting with `[RAG ERROR]` or `[RAG STATUS] ... failed`.
- **`Projects:`** line → project list.
- **`Total files:` / `Total chunks:`** → stats for the state table.

If the MCP call returns an envelope with `error_code: STARTUP_FAILED`, the MCP itself is broken — fall through to Step 2 (HTTP probe) and mark `mcp_available = False` in the state object for the command to surface.

### Step 2 — HTTP probe fallback (when MCP is not loaded or failed)

```bash
curl --max-time 1 -s -w "\n%{http_code}" http://127.0.0.1:21420/health
```

| HTTP result | service_mode |
|---|---|
| `200` + `{"status":"ready",...}` | `UP` |
| `200` + `{"status":"starting",...}` | `STARTING` (re-probe once after 2s; if still starting, keep STARTING) |
| Connection refused / timeout / `000` | `DOWN` |
| `500` / hang past timeout | `BROKEN` |

### Step 3 — Resolve install mode (mirrors D-004)

1. **Env var check:** `printenv RAG_DATA_DIR RAG_CONFIG_PATH` (POSIX) / `echo %RAG_DATA_DIR% %RAG_CONFIG_PATH%` (Windows). If set, record them.
2. **Binary on PATH:** `where rag` (Windows) / `which rag` (macOS/Linux). If found, record `binary_path`.
3. **Platform default install paths:**
   - Windows: `test -f "$LOCALAPPDATA/Programs/RAGTools/rag.exe"`
   - macOS: common extract dirs like `~/Applications/rag/rag`
4. **Dev-mode detection:** `pyproject.toml` + `.venv` in CWD, with `ragtools` as the package name.
5. **None of the above →** `install_mode = not-installed`. Set every other path field to `None`. Stop detection here and return the state object — there is nothing else to probe.

Compose `install_mode`: `packaged-windows`, `packaged-macos`, `dev-mode`, or `not-installed`.

### Step 4 — Parse version (only if `binary_path` resolved)

Preferred: extract from the MCP `index_status` output if Step 1 succeeded (ragtools reports it as part of `as_of` metadata in structured mode).

Fallback:
```bash
rag version 2>&1
```

Parse with a `(\d+\.\d+\.\d+)` regex. If the parse fails, set `state.version = None` and mark the install as suspect. Commands must treat unparseable versions as an error condition — do not assume a version.

### Step 5 — Resolve paths

**Preferred (when debug tool `get_paths` is granted):**
```
mcp__plugin_rag_ragtools__get_paths()
```
Returns all absolute paths (`data_dir`, `qdrant_path`, `state_db`, `logs_dir`, `backups_dir`, `service_pid`, `supervisor_pid`, `tray_pid`). Works in degraded mode (filesystem fallback).

**Fallback when service is UP:**
```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/status
```
Parse `config_path`, `data_path`, `log_path` from the response.

**Fallback when service is DOWN:** resolve paths from the platform defaults in `references/paths-and-layout.md`. Never hand-construct from scratch.

## The mode banner — verbatim format

Every command prints this at the top of its response. It is **exactly 6 lines**. Do not reformat, do not re-order, do not add decorations:

```
ragtools detected: <install_mode>
service mode: <UP (proxy) | DOWN (direct fallback) | STARTING | BROKEN | N/A>
binary: <binary_path or "not found">
config:  <config_path or "not found">
data:    <data_path or "not found">
logs:    <log_path or "not found">
```

When `install_mode == not-installed`, all five non-first lines are `N/A` or `not found`.

## Rules for commands consuming this contract

1. **Do not re-implement the recipe.** Reference this file. If the probe needs to change, update this file once; every command picks it up.
2. **Do not assume any state.** Every command must handle `not-installed` — the minimum behavior is a one-line refusal with a pointer at `/rag-setup`.
3. **Do not skip the probe to save time.** The probe is ~150–400ms total (one `where rag`, one `curl /health`, optionally one `curl /api/status`). That is cheap compared to the cost of a command acting on a false assumption.
4. **Do not let the banner be optional.** Users rely on it for at-a-glance orientation. Compact-by-default (D-008) does not allow dropping the banner — it allows dropping prose around the banner.

## See also

- `ARCHITECTURE.md` — single-owner layering rule
- `docs/decisions.md` — D-004 (install discovery order), D-005 (service-down behavior), D-008 (compact output)
- `references/paths-and-layout.md` — platform default paths when the service is down
- `references/runtime-flow.md` — HTTP API surface used by the UP-state path resolution
