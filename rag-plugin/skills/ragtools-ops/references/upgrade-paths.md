---
title: Upgrade Paths — In-Place, Portable, Source
topic: upgrade
relates-to: [install, recovery-and-reset, versioning, known-failures, gaps]
source-sections: [§16, §17]
---

# Upgrade Paths

ragtools supports three upgrade modes, one per install mode. The right mode is determined by **how the user installed in the first place** — not a free choice at upgrade time.

## Decision table

| Install mode | Upgrade mode | Reference command |
|---|---|---|
| Packaged Windows (installer) | **In-place** | Re-run the new `RAGTools-Setup-<latest>.exe` |
| Packaged Windows (portable zip) | **Portable replace** | Manual unpack + carry config |
| Packaged macOS (tarball) | **Tarball replace** | Manual unpack + Gatekeeper |
| Dev mode (source install) | **Source pull** | `git pull && pip install -e ".[dev]"` |
| Linux dev install | **Source pull** | Same as above |

## In-place upgrade (Windows installer)

This is the **recommended path** for end users. The installer is designed for in-place upgrade and handles everything safely:

1. **Stops** the running service
2. **Removes** the Windows Startup folder task
3. **Overwrites** files in the install directory (`%LOCALAPPDATA%\Programs\RAGTools\`)
4. **Reinstalls** the Startup folder task
5. **Starts** the service

**What's preserved automatically:**
- `%LOCALAPPDATA%\RAGTools\config.toml` (project list and settings)
- `%LOCALAPPDATA%\RAGTools\data\` (Qdrant index, state DB)
- `%LOCALAPPDATA%\RAGTools\logs\` (service logs)

**What changes:**
- `%LOCALAPPDATA%\Programs\RAGTools\rag.exe` and bundled runtime
- `%LOCALAPPDATA%\Programs\RAGTools\model_cache\` (rare — only on model version bumps)
- `%LOCALAPPDATA%\Programs\RAGTools\launch.vbs`

**The user does:** download `RAGTools-Setup-<latest>.exe` from the GitHub releases page and double-click. That's it. The installer handles the rest.

**SmartScreen friction (G-005):** no code signing yet. Click "More info" → "Run anyway" on first launch.

**Verification after upgrade:**
```bash
rag version       # should show new version
curl http://127.0.0.1:21420/health
curl http://127.0.0.1:21420/api/projects
```

If anything is wrong, route to `/rag-doctor`.

## Portable replace (Windows zip)

The portable zip does not have an installer, so in-place upgrade is manual:

1. **Stop the service:**
   ```cmd
   rag.exe service stop
   ```

2. **Note the location** of the existing portable install (e.g., `C:\Tools\RAGTools\`).

3. **Note where config and data live** for the portable install. By default, portable mode still uses `%LOCALAPPDATA%\RAGTools\` for user state, **not** the install directory. If the user explicitly set `RAG_DATA_DIR` or `RAG_CONFIG_PATH` to point inside the portable install dir, those need to be backed up first.

4. **Download the new portable zip** from the GitHub releases page.

5. **Replace the install directory:**
   - Back up the old install dir if you want a rollback option
   - Extract the new zip to the same path

6. **Start the service:**
   ```cmd
   rag.exe service start
   ```

7. **Verify** with the post-install checklist.

**Note:** the portable zip does not register the Windows Startup folder auto-start. If you previously added it manually, you may need to update the path in your VBScript launcher.

## Tarball replace (macOS arm64)

Same shape as the portable zip, with two extra steps for Gatekeeper:

1. **Stop the existing service:**
   ```bash
   ./rag service stop
   ```

2. **Download the new tarball** from the GitHub releases page (do not auto-download).

3. **Extract:**
   ```bash
   tar -xzf RAGTools-<latest>-macos-arm64.tar.gz
   ```

4. **Clear Gatekeeper quarantine** (required every time, no signing per G-005):
   ```bash
   xattr -cr rag/
   ```

5. **Replace the old install directory.** User state lives at `~/Library/Application Support/RAGTools/`, **not** inside the install directory, so it survives the replace.

6. **Start the service:**
   ```bash
   cd rag
   ./rag service start
   ```

7. **Verify.**

**macOS-specific limitations during upgrade:**
- No `.app` bundle, so no double-click upgrade UX
- No `.dmg`, so no drag-and-drop replace
- No LaunchAgent (G-002), so the user must restart the service manually after upgrade — there's no auto-start to handle it

## Source pull (dev mode)

For users who installed via `pip install -e ".[dev]"`:

1. **Stop the service:**
   ```bash
   rag service stop
   ```

2. **Pull the latest source:**
   ```bash
   cd /path/to/rag
   git pull
   ```

3. **Reinstall (in case dependencies changed):**
   ```bash
   # Activate the venv first if not already active
   pip install -e ".[dev]"
   ```

4. **Start the service:**
   ```bash
   rag service start
   ```

5. **Verify.**

**Important:** dev mode uses CWD-relative paths (`./ragtools.toml` and `./data/`), so the upgrade must be run from the same directory as the original install. Running `git pull` from a different directory will break references.

## What can go wrong during upgrade

| Symptom | Likely cause | Fix |
|---|---|---|
| Service won't start after upgrade | Bundle corruption from incomplete download | Re-download installer; verify SHA if available |
| `rag version` shows old version | Old binary still on PATH | Restart shell or check PATH order |
| Projects empty after upgrade | Config landed in wrong place (pre-v2.4.1 bug, F-001) | This should not happen post-upgrade. If it does, route to `/rag-doctor` and `repair-playbooks.md#projects-empty-after-restart` |
| `rag doctor` reports `Collection NOT FOUND` | Expected if service is up (F-010) — not a bug | Ignore |
| Watcher not running after upgrade | Auto-restart budget exhausted from the upgrade interruption | `curl -X POST http://127.0.0.1:21420/api/watcher/start` |
| MCP server fails to connect from Claude Code | `.mcp.json` may need refresh if binary path changed | Re-run `/rag-setup` step C.1 to read fresh `/api/mcp-config` |

## Pre-v2.4.1 mandatory upgrade

If the user is on **any version below 2.4.1**, upgrading is **not optional**. The v2.4.1 fix addresses a data-loss-tier bug (F-001) in the config write path. Running on pre-v2.4.1:
- Adding a project from the admin panel can fail with `[Errno 13] Permission denied: 'ragtools.toml'`
- Even if the add appears to succeed, the next service restart can delete "orphaned" data
- `/rag-reset` is **blocked** by `/rag-reset` Step 2 on pre-v2.4.1 because a reset on a buggy version can lose more data than intended

The plugin's `/rag-upgrade` command surfaces a strong warning when pre-v2.4.1 is detected. The plugin's `/rag-reset` command refuses entirely. Both behaviors trace back to F-001 and the v2.4.1 incident history.

## What `/rag-upgrade` does for you

The `/rag-upgrade` slash command:
- Detects the installed version via `rag version`
- Fetches the latest release from `https://api.github.com/repos/taqat-techno/rag/releases/latest`
- Compares versions
- Picks the right upgrade mode based on the detected install mode
- Walks the user through the chosen mode
- Verifies post-upgrade state

The command **never auto-downloads** the installer artifact. URLs are produced for the user to click. This is intentional (D-005, scope rule) — auto-download of multi-hundred-MB installers from a slash command would create more risk than convenience.

## See also

- `install.md` — initial install procedures (the same artifacts are used for upgrade)
- `recovery-and-reset.md#upgrade-without-losing-data` — upstream description of the in-place upgrade flow
- `versioning.md` — semver scheme, breaking-change history
- `known-failures.md#f-001` — the v2.4.1 data-loss bug
- `gaps.md` — G-005 (no signing), G-002 (no macOS LaunchAgent), G-001 (no Linux installer)
