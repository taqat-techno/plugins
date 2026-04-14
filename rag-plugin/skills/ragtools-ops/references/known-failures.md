---
title: Known Failure Modes
topic: failures
relates-to: [repair-playbooks, logs-and-diagnostics, versioning, recovery-and-reset]
source-sections: [§14]
---

# Known Failure Modes

Each failure has a stable ID for use by the symptom classifier. Format: `F-NNN`. The `INDEX.md` lists which playbook (if any) maps to each ID.

## Confirmed failures

### F-001 — v2.4.1 config-permission bug

**Symptoms:**
- Projects disappear after PC restart
- `[Errno 13] Permission denied: 'ragtools.toml'` when adding a project from the admin panel

**Root cause:** v2.4.1 fixed this. Pre-v2.4.1, the VBScript launcher inherited CWD `C:\Windows\System32`. The config write landed with a relative path in an unwritable directory, and the startup-sync deleted "orphaned" data on the next boot.

**Fix:** Upgrade to **≥ v2.4.1**. The fix has three parts:
1. VBScript now sets `shell.CurrentDirectory` explicitly.
2. `get_config_write_path()` always uses `%LOCALAPPDATA%`.
3. Startup-sync skips if the projects list is empty (data-loss guard).

**Playbook:** `repair-playbooks.md#add-project-permission-denied`

---

### F-002 — MPS out of memory (macOS)

**Symptom:** `MPS backend out of memory` error when loading the encoder on macOS.

**Root cause:** v2.4.2 fixed this. Pre-v2.4.2, PyTorch auto-detected the Apple Metal GPU and exhausted the MPS pool on small fixtures.

**Fix:** Encoder now forces `device="cpu"` in `SentenceTransformer(...)` (`src/ragtools/embedding/encoder.py`). **Do not revert this.** See `risks-and-constraints.md#macos-mps-must-stay-disabled`.

**Status:** Fixed. No playbook needed for v2.4.2+.

---

### F-003 — Qdrant lock contention

**Symptoms:**
- `RuntimeError: Storage folder data/qdrant is already accessed by another instance of Qdrant client`
- Service refuses to start
- CLI command hangs or errors when service is also running in direct mode

**Root cause:** Qdrant local mode takes an **exclusive file lock** on the data directory. Two processes cannot hold it. Common triggers:
- Running `rag service start` while another service instance is already running
- Running `rag index` / `rag rebuild` / `rag watch` while the service is up (CLI direct mode fights the service)
- Zombie Python process from a previous unclean shutdown still holding the lock
- Running `rag-mcp` directly while the service is up

**Status:** Not a bug — design constraint. Use the playbook to clean up.

**Playbook:** `repair-playbooks.md#qdrant-already-accessed`

---

### F-004 — Watcher silent death

**Symptom:** Watcher stops auto-indexing after a while; admin panel shows "watcher: stopped"; no error in the foreground.

**Root cause:** Pre-v2.4 the watcher thread could throw and die without recovery.

**Fix:** v2.4 added auto-restart with exponential backoff (5 retries, 5s–80s).

**Status:** Fixed in v2.4+. If still seen on v2.4+, the watcher exhausted its retry budget — see playbook.

**Playbook:** `repair-playbooks.md#watcher-not-running`

---

### F-005 — Service will not start

**Symptoms:**
- `rag service start` returns immediately but no service process appears
- `curl http://127.0.0.1:21420/health` → connection refused
- `service.log` contains `ERROR: Application startup failed. Exiting.`

**Root causes (most common first):**
1. Qdrant lock contention (see F-003)
2. Missing or corrupt `model_cache/` in the bundle (reinstall fixes this)
3. Port 21420 already in use (see F-008)
4. Permissions issue on the data directory

**Playbook:** `repair-playbooks.md#service-will-not-start`

---

### F-006 — Projects empty after restart

**Symptoms:**
- Service runs, admin panel loads, but no projects are listed
- `curl /api/projects` returns `[]`
- `service.log` contains `Startup sync skipped: no projects configured (check config path)`

**Root causes:**
- Config file loaded from the wrong path (a CWD-relative `ragtools.toml` instead of `%LOCALAPPDATA%\RAGTools\config.toml`)
- v2.4.1 bug (see F-001) on pre-v2.4.1
- Stale `ragtools.toml` in `C:\Windows\System32\` from the v2.4.1 era
- Syncthing or similar overwriting the config file (see `risks-and-constraints.md#syncthing--cloud-synced-config-directory`)

**Playbook:** `repair-playbooks.md#projects-empty-after-restart`

---

### F-007 — Indexing slow or stuck

**Symptoms:**
- "Indexing X files..." in admin panel sits at the same number for minutes
- CPU usage is sustained on `rag.exe`
- Activity log shows long gaps between events

**Root causes:**
- **Expected for full index of large projects** — encoder is CPU-bound by design (see `risks-and-constraints.md#macos-mps-must-stay-disabled`)
- Watcher debounce too low (firing constantly during edits)
- Hash check skipping correctly; full re-encode in progress

**Playbook:** `repair-playbooks.md#indexing-slow-or-stuck`

---

### F-008 — Admin panel won't load / port collision

**Symptoms:**
- Browser shows "connection refused" on `http://127.0.0.1:21420`
- `netstat -ano | findstr 21420` shows another process on the port

**Root cause:** Another service is bound to port 21420.

**Fix:** Change the port via `RAG_SERVICE_PORT` or `config.toml` → `service_port`. Restart the service.

**Note:** "Restart required" badge appears in Settings — `service_port` and `log_level` changes need a service restart.

**Playbook:** `repair-playbooks.md#admin-panel-port-collision`

---

### F-009 — MCP server not connecting from Claude Code

**Symptoms:**
- Claude Code shows MCP server errored out at startup
- `~/.claude/logs/` contains MCP startup failures
- `rag-mcp` works in a terminal but fails when launched by Claude Code

**Root causes:**
- `.mcp.json` has wrong path to `rag.exe` (rebuild from `/api/mcp-config`)
- Stray `print()` to stdout in the MCP server breaking the protocol
- Service is down and direct-mode startup is taking longer than Claude Code's launch timeout

**Playbook:** `repair-playbooks.md#mcp-not-connecting`

---

### F-010 — `Collection NOT FOUND` from `rag doctor` while service is up

**Symptom:** `rag doctor` reports `Collection: NOT FOUND` even though the service is healthy.

**Root cause:** `rag doctor` opens its own Qdrant client to inspect the collection, which cannot read the locked directory while the service holds the lock.

**Status:** **Not a bug.** Confirm the service is healthy via `curl /health` instead.

**Anchor:** `#collection-not-found-while-service-up`

---

### F-011 — Add project fails silently (pre-v2.4)

**Status:** Fixed in v2.4 — duplicate path validation in `project_create()`.

---

### F-012 — `NameError: _get_ignore_rules` in `cli.py` (pre-v2.4)

**Status:** Fixed in v2.4. If a user sees this, they are on a broken dev branch.

## UI-visible errors

- **"Failed to add project: [Errno 13] Permission denied: 'ragtools.toml'"** → F-001. Upgrade.
- **"Project not found"** flash when removing a project → project deleted in another window/tab, or config reloaded externally.
- **"Rebuilding knowledge base... this may take several minutes"** → not an error; full-page banner during a `Rebuild` action.

## Cosmetic warnings (ignore)

- **`HuggingFace unauthenticated warning`** at startup — model is bundled locally. Set `HF_TOKEN` or `TRANSFORMERS_OFFLINE=1` to suppress.

## See also

- `repair-playbooks.md` — step-by-step fixes for the failures with playbooks
- `logs-and-diagnostics.md` — log substrings that map to failure IDs
- `versioning.md` — which version fixed what
- `recovery-and-reset.md` — when no playbook works
