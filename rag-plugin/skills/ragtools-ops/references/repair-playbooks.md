---
title: Repair Playbooks
topic: repair
relates-to: [known-failures, logs-and-diagnostics, recovery-and-reset, paths-and-layout]
source-sections: [§15]
---

# Repair Playbooks

**Confirmation discipline:** any playbook step that deletes files, kills processes, or removes the Qdrant directory **must be confirmed by the user** before running. The plugin walks the playbook one step at a time and never auto-executes destructive steps.

## service-will-not-start

**Maps to:** F-005

1. Check the log: `%LOCALAPPDATA%\RAGTools\logs\service.log` (Windows) or `~/Library/Application Support/RAGTools/logs/service.log` (macOS).
2. Grep for `ERROR` or `Traceback`.
3. If you see `is already accessed by another instance` → jump to `#qdrant-already-accessed`.
4. If you see model load error (missing `model_cache/`) → reinstall; the bundle is corrupt.
5. Try running in the foreground: `rag service run`. This shows startup output directly in the terminal.
6. Try `rag doctor` — if Python or dependencies are broken, the issue is below the service layer.

---

## qdrant-already-accessed

**Maps to:** F-003

1. **Stop any running RAG service:** `rag service stop`.
2. **Check for zombie processes** (confirm before killing):
   - Windows: `tasklist | findstr rag.exe` then `taskkill /F /PID <pid>` (DESTRUCTIVE — confirm pid first)
   - macOS/Linux: `ps aux | grep rag`, then `kill -9 <pid>` (DESTRUCTIVE — confirm pid first)
3. **Remove stale PID file** if present: `%LOCALAPPDATA%\RAGTools\service.pid` (DESTRUCTIVE — confirm)
4. **Remove the Qdrant lock file:** `%LOCALAPPDATA%\RAGTools\data\qdrant\.lock` (DESTRUCTIVE — confirm; only do this if no rag.exe processes remain)
5. **Start the service again:** `rag service start`.

**Critical safety rule:** Never delete the Qdrant **data directory** while the service is running. Only the lock file. Deleting the data directory wipes the index. See `recovery-and-reset.md` for the full nuclear reset flow if needed.

---

## add-project-permission-denied

**Maps to:** F-001 (v2.4.1 config-permission bug)

**Best fix:** **Upgrade to ≥ v2.4.1 immediately.**

**Workaround on older versions:**
1. Stop the service: `rag service stop`.
2. Manually create `%LOCALAPPDATA%\RAGTools\config.toml` with the project entries (see `configuration.md` for schema).
3. Restart the service: `rag service start`.
4. Verify: `curl http://127.0.0.1:21420/api/projects`.

---

## projects-empty-after-restart

**Maps to:** F-006

1. **Confirm the API also reports zero:** `curl http://127.0.0.1:21420/api/projects`.
2. **Check the log** for `Startup sync skipped: no projects configured` — confirms the config didn't load.
3. **Verify the config file exists** at the platform-specific path (see `paths-and-layout.md`).
4. **Compare contents:** does it have `[[projects]]` sections?
5. **Check for stale CWD-relative files:** look for a `ragtools.toml` in `C:\Windows\System32\`, the user home, or the install directory. If found, **back it up first**, then move it to `%LOCALAPPDATA%\RAGTools\config.toml`.
6. **Restart the service:** `rag service stop && rag service start`.
7. **Verify:** `curl http://127.0.0.1:21420/api/projects`.

If the config is in a Syncthing / iCloud / OneDrive folder, see `risks-and-constraints.md#syncthing--cloud-synced-config-directory`.

---

## indexing-slow-or-stuck

**Maps to:** F-007

1. **Check the activity log** in the admin panel (bottom drawer). Watch for "Incremental: X indexed, Y skipped, Z deleted" or "Full index started/completed" messages.
2. **Check CPU usage.** The encoder is CPU-bound by design — see `risks-and-constraints.md#macos-mps-must-stay-disabled`. Sustained high CPU on `rag.exe` usually means it's working, not stuck.
3. **For very large projects:** incremental index is fast (SHA256 hash check skips unchanged files). Full index is proportional to total chunks — be patient.
4. **If the watcher is firing too often during edits**, increase debounce: `rag watch . --debounce 5000`.
5. **Before launching an index by hand, check whether the service is already doing it.** A service that auto-syncs on startup turns a manual `rag index` into a lock-contention generator. If the CLI exits 1 with `index job for all projects never acquired the index lock; another indexing run is stuck. Nothing was indexed.`, read the two clauses separately — "nothing was indexed" is true only of *your* invocation. The service's own startup sync can hold the lock and be indexing normally the whole time, in which case the "stuck" run is the healthy one and the CLI call was the redundant duplicate. The message asserts a broken system; it is not evidence of one.
6. **Decide hung-vs-working from a CPU *delta over an interval* plus fresh timestamped log writes** — never from a snapshot counter and never from a lock-timeout message. Sample the service process twice a fixed interval apart (roughly 150 s of CPU consumed per 20 s of wall clock is unambiguous work) and look for live encoder batch progress in the log. `points_count` / `total_files` sit **completely flat for tens of minutes** between project commits, so two identical status samples are not evidence of a hang either.

If the indexer truly hangs (no CPU delta across an interval, no fresh log lines for several minutes), use `recovery-and-reset.md#soft-reset-rag-rebuild` to start over. If instead the guard reports busy while the progress tick is frozen at its start value and the age climbs, that is a deadlocked job rather than a slow one — see `known-failures.md` F-015.

---

## admin-panel-port-collision

**Maps to:** F-008

1. **Identify the conflicting process:**
   - Windows: `netstat -ano | findstr 21420`
   - macOS/Linux: `lsof -i :21420`
2. **Decide whether to kill the conflicting process or change the rag service port.**
3. **To change the port:** set `RAG_SERVICE_PORT=21421` (or another free port) or edit `config.toml` → `service_port`.
4. **Restart the service.** Note: "Restart required" badge appears in Settings — `service_port` and `log_level` changes need a service restart.

---

## watcher-not-running

**Maps to:** F-004

1. `curl http://127.0.0.1:21420/api/watcher/status` — check `running` field.
2. If `false`, start it: `curl -X POST http://127.0.0.1:21420/api/watcher/start`.
3. Check log for watcher errors. The auto-restart kicks in with exponential backoff (5 retries, 5s–80s).
4. **Verify project paths exist** (the watcher skips nonexistent paths and logs a warning).

---

## mcp-not-connecting

**Maps to:** F-009

1. **Is the service running?** `rag service status`.
2. **Check `.mcp.json`** — is the `command` correct? For installed mode it should be the full path to `rag.exe` with `serve` argument. The Settings page in the admin panel and `GET /api/mcp-config` show the exact correct config — use those rather than hand-writing.
3. **Claude Code logs:** see `~/.claude/logs/` for MCP server startup failures.
4. **Try direct launch:** run `rag-mcp` or `rag serve` in a terminal. It should block waiting for stdio input — that confirms it launched correctly.
5. **Verify stdio is clean** (no `print()` statements to stdout). The MCP protocol uses stdio and any stray output breaks it.

---

## fresh-project-reindex-is-noop

**Symptom:** the user just registered a project (`/rag:projects add ...`), then ran `/api/projects/<id>/reindex` and the chunk count is still zero.

**Why:** `POST /api/projects/<id>/reindex` for a project that was just registered with `files=0` runs as a no-op — the log line `Project data deleted: <id> (0 files)` followed by a full-index pass that finds nothing because the project has no indexed file rows yet.

**Fix:**
1. Trigger a **global** full index instead — `POST /api/index {"full": true}` (synchronous; slow on large repos).
2. Or **restart the service** — startup sync triggers a global index pass that picks up newly-added projects.

**Rule:** after bulk-adding ragtools projects, never rely on per-project reindex for first-time indexing. Use the global path. Document this when walking the user through `add` → `index` flows.

---

## bulk-destructive-operation-confirmation

**When the user asks for a bulk refactor** (delete N projects, add M new ones, prune all node_modules across all projects), do not execute immediately:

1. **Enumerate** the proposed remove and add lists with IDs and paths.
2. **Flag concerns** — chunk-count overflow against the 20k hard limit, suspicious paths (system dirs, dotfiles), ID collisions with existing projects.
3. **Wait for explicit `go`** before executing anything destructive.
4. **Do not** pre-prefix project names (`my-`, `tq-`) unless asked. The convention is leaf-folder kebab-case IDs.

This applies to `/rag:projects remove`, `/rag:reset` (any level), `/rag:projects rebuild`, and any combined "remove + add" bulk flow. The confirmation discipline at the top of this file is the general rule; this section is the bulk-operation specialization.

---

## Quick playbook lookup

| Failure ID | Symptom keyword | Playbook anchor |
|---|---|---|
| F-001 | permission denied / projects disappear | `#add-project-permission-denied` |
| F-003 | qdrant locked / already accessed | `#qdrant-already-accessed` |
| F-004 | watcher dead / not auto-indexing | `#watcher-not-running` |
| F-005 | service won't start | `#service-will-not-start` |
| F-006 | projects empty after restart | `#projects-empty-after-restart` |
| F-007 | indexing stuck or slow | `#indexing-slow-or-stuck` |
| F-008 | port already in use / panel won't load | `#admin-panel-port-collision` |
| F-009 | MCP not connecting from Claude Code | `#mcp-not-connecting` |
| —    | reindex no-op on fresh project          | `#fresh-project-reindex-is-noop` |
| —    | bulk destructive op (remove/add many)   | `#bulk-destructive-operation-confirmation` |

## See also

- `known-failures.md` — full failure-mode catalog with root causes
- `logs-and-diagnostics.md` — log substrings to identify failures
- `recovery-and-reset.md` — when no playbook works
- `paths-and-layout.md` — file locations referenced in the playbooks
