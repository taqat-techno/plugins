---
title: macOS-Specific Behavior, Limitations, and Playbook Variations
topic: macos
relates-to: [install, paths-and-layout, gaps, risks-and-constraints, repair-playbooks, recovery-and-reset]
source-sections: [§4, §6.3, §8, §18.2, §18.3]
---

# macOS Specifics

ragtools macOS support is **Phase 1**: tarball-only, Apple Silicon only, no `.app`, no `.dmg`, no LaunchAgent auto-start, no signing. This file documents the deltas from the Windows experience and what the rag-plugin plugin must (and must not) do on macOS.

## The honest picture

| Aspect | Status | Reference |
|---|---|---|
| Build artifact | `RAGTools-{version}-macos-arm64.tar.gz` (~423 MB compressed) | `install.md` |
| Apple Silicon (arm64) | ✅ Supported via the macos-14 CI runner | `gaps.md#g-004` |
| Intel (x86_64) | ❌ Not built | `gaps.md#g-004` |
| `.app` bundle | ❌ Not produced | `gaps.md#g-002` |
| `.dmg` installer | ❌ Not produced | `gaps.md#g-002` |
| Code signing / notarization | ❌ Not implemented | `gaps.md#g-005` |
| Login auto-start (LaunchAgent) | ❌ Not implemented | `gaps.md#g-002` |
| MPS (Apple Metal) device | ❌ Disabled — `device="cpu"` forced | `risks-and-constraints.md#macos-mps-must-stay-disabled` |

The rag-plugin plugin reflects this honestly. It does not promise auto-start. It does not pretend `.app` exists. It refuses Intel Macs in `/rag-setup` (Phase 3 already implemented this).

## Paths

User state lives in macOS-conventional locations, **not** inside the tarball extract directory:

| Purpose | Path |
|---|---|
| Config file | `~/Library/Application Support/RAGTools/config.toml` |
| Data directory | `~/Library/Application Support/RAGTools/data/` |
| Qdrant storage | `~/Library/Application Support/RAGTools/data/qdrant/` |
| State DB | `~/Library/Application Support/RAGTools/data/index_state.db` |
| Service log | `~/Library/Application Support/RAGTools/logs/service.log` |
| PID file | `~/Library/Application Support/RAGTools/service.pid` |
| Binary | `<tarball-extract-dir>/rag` (e.g. `~/Applications/rag/rag`) |
| Bundled runtime | `<tarball-extract-dir>/_internal/` |
| Bundled model | `<tarball-extract-dir>/model_cache/` |

Resolution still uses the env-var-first order (`RAG_DATA_DIR`, `RAG_CONFIG_PATH`) and falls back to the macOS conventional paths via `_get_app_dir()` in `src/ragtools/config.py`.

## Install procedure (from install.md §6.3)

```bash
# 1. Verify Apple Silicon
uname -m   # must return arm64 — Intel is not supported

# 2. Download (manually — never auto-download)
#    https://github.com/taqat-techno/rag/releases

# 3. Extract
tar -xzf RAGTools-<version>-macos-arm64.tar.gz

# 4. Clear Gatekeeper quarantine (no signing yet, G-005)
xattr -cr rag/

# 5. Verify
cd rag
./rag version

# 6. Start
./rag service start

# 7. Verify
curl http://127.0.0.1:21420/health
```

**Service must be started manually each session.** There is no LaunchAgent.

## Gatekeeper friction

Because there is no code signing or notarization (G-005), macOS Gatekeeper quarantines the binary on first launch. Symptom: `"rag" cannot be opened because the developer cannot be verified` or `Operation not permitted`.

**Fix:** `xattr -cr rag/` clears the quarantine extended attribute on the entire extract directory. This is required:
- After every fresh extract
- After every upgrade (the new tarball is also unsigned)
- If the user moves the directory across volumes that strip xattrs

The plugin's `/rag-setup` and `/rag-upgrade` commands include this step in the macOS branch.

## What rag-plugin does differently on macOS

### `/rag-status` and `/rag-doctor`
- Mode banner shows `packaged-macos` and the macOS conventional paths
- Process discovery uses `ps aux | grep rag` instead of `tasklist | findstr rag.exe`
- Port collision diagnostic uses `lsof -i :21420` instead of `netstat -ano | findstr 21420`

### `/rag-setup`
- Detects arch via `uname -m`
- Refuses Intel (`x86_64`) with a hard-block message citing G-004
- Walks the tarball + Gatekeeper flow (Branch A.3 in `setup-walkthrough.md`)
- Warns that no LaunchAgent exists and the user must start the service manually each session

### `/rag-repair` playbooks
- **P-qdrant:** kill commands use `kill -9 <pid>` (after `ps aux | grep rag`) instead of `taskkill /F /PID <pid>`
- **P-qdrant:** lock-file path is `~/Library/Application Support/RAGTools/data/qdrant/.lock`
- **P-port:** `lsof -i :21420` to identify conflicting process
- **P-empty:** stale-CWD rescue is less common on macOS (no VBScript launcher) but still possible if the user runs `./rag` from an unusual working directory in dev mode

### `/rag-projects`
- Cloud-sync detection includes iCloud (`Mobile Documents/com~apple~CloudDocs/`) — see `risks-and-constraints.md#syncthing--cloud-synced-config-directory`
- HTTP API surface is identical to Windows

### `/rag-upgrade`
- Selects the macOS arm64 tarball asset
- Walks the tarball-replace flow from `upgrade-paths.md#tarball-replace-macos-arm64`
- Reminds about Gatekeeper for every upgrade (no signing → quarantine bit returns)
- Reminds that the service must be restarted manually post-upgrade (no LaunchAgent)

### `/rag-reset`
- `--data` shows `rm -rf "$HOME/Library/Application Support/RAGTools/data"`
- `--nuclear` shows `rm -rf "$HOME/Library/Application Support/RAGTools"`
- `--soft` is identical (HTTP API is platform-agnostic)
- Pre-v2.4.1 block applies regardless of platform

## MPS — must stay disabled

The encoder is forced to `device="cpu"` in `src/ragtools/embedding/encoder.py` to prevent MPS (Apple Metal) memory exhaustion. This is **not negotiable** per `risks-and-constraints.md#macos-mps-must-stay-disabled`. The rag-plugin plugin must:

- **Never** recommend setting `PYTORCH_ENABLE_MPS_FALLBACK`
- **Never** suggest editing the encoder to use MPS
- **Recognize** `MPS backend out of memory` errors as **F-002** (pre-v2.4.2 only) and recommend upgrade

If a user asks why ragtools is CPU-bound on their M-series Mac, the answer is: the MPS backend exhausted memory on small fixtures during testing, the fix is permanent, and the plugin will not help revert it.

## What's missing on macOS that exists on Windows

| Feature | Windows | macOS | Workaround |
|---|---|---|---|
| Login auto-start | Startup folder VBScript | ❌ Not implemented | Start manually each session, or write your own LaunchAgent plist |
| `.app` bundle | N/A | ❌ Not produced | Run `./rag` from the extract directory |
| `.dmg` installer | N/A | ❌ Not produced | `tar -xzf` manually |
| Code signing | Unsigned (SmartScreen friction) | Unsigned (Gatekeeper friction) | `xattr -cr rag/` on macOS; "Run anyway" on Windows |
| WinGet package | ❌ Not submitted (G-003) | N/A | Manual download from GitHub releases |

The plugin will not pretend any of these work. Each missing feature is a documented gap with a stable G-NNN ID in `gaps.md`.

## Repair-playbook variations summary

| Playbook | Windows command | macOS command |
|---|---|---|
| P-qdrant kill | `tasklist | findstr rag.exe`, `taskkill /F /PID <pid>` | `ps aux | grep rag`, `kill -9 <pid>` |
| P-qdrant lock file | `%LOCALAPPDATA%\RAGTools\data\qdrant\.lock` | `~/Library/Application Support/RAGTools/data/qdrant/.lock` |
| P-port collision | `netstat -ano | findstr 21420` | `lsof -i :21420` |
| P-empty config rescue | look for stray `ragtools.toml` in `C:\Windows\System32\` | look for stray `ragtools.toml` in dev-mode CWD |
| P-watcher restart | `curl -X POST http://127.0.0.1:21420/api/watcher/start` | identical |
| P-mcp `.mcp.json` | identical (HTTP API path) | identical |

## See also

- `install.md` — full install procedures including macOS §6.3
- `paths-and-layout.md` — per-platform path table
- `gaps.md` — G-001..G-010 unimplemented items (G-002, G-004, G-005 are macOS-relevant)
- `risks-and-constraints.md` — MPS rule, single-process lock
- `repair-playbooks.md` — playbooks already include macOS variants in their step lists
- `recovery-and-reset.md` — reset flows already include macOS commands
- `setup-walkthrough.md#branch-a--install-from-scratch-macos-arm64` — long-form setup walkthrough macOS branch
- `upgrade-paths.md#tarball-replace-macos-arm64` — upgrade flow
- `linux-dev-mode.md` — the other non-Windows reference (sibling to this one)
