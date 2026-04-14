---
title: Safe Reset, Reinstall, and Recovery
topic: recovery
relates-to: [repair-playbooks, paths-and-layout, versioning]
source-sections: [§16]
---

# Safe Reset, Reinstall, and Recovery

**Destructive-action discipline:** every step that deletes files must be confirmed by the user. The plugin uses `--soft` / `--data` / `--nuclear` flag escalation — never a single "reset" button.

## Soft reset — `rag rebuild`

**What it does:** Drops all Qdrant data and the state DB, then re-indexes from configured projects.

**What it preserves:** Config file, project list, all settings.

```bash
rag rebuild
```

**When to use:** Index seems corrupted, search results are stale, or you want a clean re-index after a config change. This is the safest reset and the right starting point.

---

## Data reset — delete `data/`

**What it does:** Deletes the entire data directory: Qdrant storage, state DB, logs.

**What it preserves:** `config.toml` (if you delete only `data/`).

**⚠️ DESTRUCTIVE. Stop the service first.**

```bash
rag service stop
```

Then delete:

| Platform | Command | What it deletes |
|---|---|---|
| Windows | `rmdir /S /Q %LOCALAPPDATA%\RAGTools\data` | `data/` (preserves `config.toml`) |
| macOS | `rm -rf ~/Library/Application\ Support/RAGTools/data` | same |

Then restart: `rag service start`. A fresh data directory will be created.

---

## Nuclear reset — delete everything

**What it does:** Deletes config, data, logs — every user-state file.

**⚠️ MAXIMALLY DESTRUCTIVE. Stop the service first.**

```bash
rag service stop
```

Then:

| Platform | Command |
|---|---|
| Windows | `rmdir /S /Q %LOCALAPPDATA%\RAGTools` |
| macOS | `rm -rf ~/Library/Application\ Support/RAGTools` |

Restart: `rag service start`. Fresh empty state.

---

## Reinstall from scratch

1. **Uninstall** via Windows "Add or Remove Programs" (the installer has an uninstaller). During uninstall, it prompts whether to keep user data — say **YES** to keep, **NO** for a fresh start.
2. **Download** the latest `RAGTools-Setup-{version}.exe` from GitHub releases.
3. **Run the installer.** User data is preserved if you said "Yes".
4. **Verify** with the checklist in `post-install-verify.md`.

---

## Upgrade without losing data

The installer is designed for in-place upgrade. It:

1. Stops the running service.
2. Removes the startup task.
3. Overwrites files in the install directory.
4. Reinstalls the startup task.
5. Starts the service.

The data directory (`%LOCALAPPDATA%\RAGTools\data\`) and config are **untouched**.

---

## Recovery from corrupted Qdrant storage

If the `data/qdrant/` directory is corrupt (rare — usually from an ungraceful kill during upsert):

1. **Stop the service:** `rag service stop`.
2. **Backup** rather than delete:
   - Windows: `move %LOCALAPPDATA%\RAGTools\data\qdrant %LOCALAPPDATA%\RAGTools\data\qdrant.bak`
   - macOS: `mv ~/Library/Application\ Support/RAGTools/data/qdrant ~/Library/Application\ Support/RAGTools/data/qdrant.bak`
3. **Start the service:** a fresh empty collection will be created.
4. **Re-index:** `rag rebuild`.

State DB corruption is possible but uncommon — same recovery applies to `index_state.db`.

## Recovery decision tree

```
Symptom?
├─ Stale or wrong search results
│   └─ rag rebuild  (soft reset, safest)
├─ Index seems corrupt or service crashes during upsert
│   └─ Backup data/qdrant → restart → rag rebuild
├─ Config has gone wrong but data is fine
│   └─ Delete config.toml only, keep data/, restart
├─ Want a fresh start, keep config
│   └─ Stop service → delete data/ → restart
├─ Want a completely fresh start
│   └─ Stop service → delete %LOCALAPPDATA%\RAGTools → restart
└─ Suspect installer corruption
    └─ Reinstall (keep user data option)
```

## See also

- `repair-playbooks.md` — fix specific failures before resorting to reset
- `paths-and-layout.md` — exact paths for each platform
- `versioning.md` — what version was installed when, and whether to upgrade as part of recovery
- `known-failures.md` — verify the symptom matches a known failure before nuking
