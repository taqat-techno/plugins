---
title: Long-Form Setup Walkthrough
topic: setup
relates-to: [install, mcp-wiring, post-install-verify, configuration, gaps, risks-and-constraints]
source-sections: [§3, §6, §7, §10]
---

# Setup Walkthrough — long form

This is the long-form companion to `/rag-setup`. The slash command is interactive and asks one question at a time; this file is for users who would rather read the whole thing first. Both produce the same end state: service running, MCP wired, first project indexed.

## Time budget

| Step | Duration |
|---|---|
| Download installer | 2–5 min (488 MB Windows / 423 MB macOS) |
| Run installer / extract tarball | 1–2 min |
| First service start (encoder cold-load) | 5–10 sec |
| MCP wiring (read `/api/mcp-config`, write `.mcp.json`) | < 30 sec |
| Add first project | < 30 sec |
| Initial indexing (depends on project size) | seconds for tens of files, minutes for thousands |
| **Total time-to-first-search** | ~10 minutes typical |

## Pre-flight checks

Before running `/rag-setup`, you should know:

- **Your platform.** Windows 10/11 x64, macOS arm64 (Apple Silicon), or Linux dev-mode only.
- **Your project path.** A directory containing Markdown files you want searchable. ragtools indexes Markdown only — see `configuration.md` for chunking details.
- **Whether you want auto-start.** Windows: yes (login auto-start works). macOS: no (G-002 — LaunchAgent not implemented). Linux: no (no service infra).
- **Whether to write `.mcp.json` project-level or user-level.** Project-level is recommended for team-shared configs.

## Branch A — Install from scratch (Windows)

### A.1 — Download

Go to `https://github.com/taqat-techno/rag/releases`. Download `RAGTools-Setup-{latest}.exe`. ~488 MB. Expect a SmartScreen warning on first launch — there is no code signing (G-005). Click "More info" → "Run anyway".

### A.2 — Run the installer

The installer is **user-level** — no admin required.

| Option | Recommended |
|---|---|
| ☑ Add to PATH | Yes (so `rag` works from any terminal) |
| ☑ Add to Windows Startup folder | Yes (login auto-start via `RAGTools.vbs`) |
| ☑ Start service after install | Yes |
| ☑ Open admin panel after start | Optional |

The installer:
1. Copies files to `%LOCALAPPDATA%\Programs\RAGTools\` (default per-user install)
2. Adds the install directory to `HKCU\Environment\Path` if you checked the option
3. Creates the data directory under `%LOCALAPPDATA%\RAGTools\` (`data/`, `logs/`)
4. Drops `launch.vbs` for the smart launcher
5. Registers the Windows Startup folder task if you checked the option
6. Optionally starts the service and opens the admin panel

### A.3 — First-run cold load

The first time the service starts, the SentenceTransformer encoder loads from `model_cache/`. This takes **5–10 seconds**. After that, subsequent starts are instant.

The admin panel opens at `http://127.0.0.1:21420`. You should see "Add Your First Project" if no projects are configured.

## Branch A — Install from scratch (macOS arm64)

### A.1 — Check arch

```bash
uname -m
```

Must return `arm64`. If it returns `x86_64`, **stop** — there is no Intel macOS build (G-004). The `macos-14` CI runner only builds arm64.

### A.2 — Download and extract

```bash
curl -LO https://github.com/taqat-techno/rag/releases/download/v{version}/RAGTools-{version}-macos-arm64.tar.gz
tar -xzf RAGTools-{version}-macos-arm64.tar.gz
```

~423 MB compressed.

### A.3 — Bypass Gatekeeper

There is no code signing or notarization (G-005). Gatekeeper will quarantine the binary on first run. Clear the quarantine bit:

```bash
xattr -cr rag/
```

### A.4 — Verify and start

```bash
cd rag
./rag version
./rag service start
```

Open `http://127.0.0.1:21420` in your browser.

**Important macOS limitations** (from `risks-and-constraints.md` and `gaps.md`):

- ❌ No `.app` bundle — tarball only
- ❌ No `.dmg` — manual `tar -xzf`
- ❌ No LaunchAgent auto-start (G-002) — start manually each session
- ❌ No Intel build (G-004)
- ❌ No code signing (G-005)

If you want auto-start on macOS, you'll need to add it yourself (LaunchAgent plist) — the rag-plugin plugin will not pretend this works out of the box.

## Branch A — Linux (dev install only)

There is **no packaged Linux artifact** (G-001). The `.github/workflows/release.yml` does not produce a Linux binary. You must install from source:

```bash
git clone https://github.com/taqat-techno/rag.git
cd rag
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
rag version
rag doctor
rag service start
```

In dev mode:
- Config file is `./ragtools.toml` (CWD-relative)
- Data is stored in `./data/`
- Startup auto-registration is **not** implemented for Linux

See `paths-and-layout.md` for the full dev-mode layout.

## Branch B — Start an installed service that's down

Sometimes ragtools is installed but not running — service crashed, login auto-start was unchecked, machine just rebooted on macOS where there's no auto-start.

```bash
rag service start
```

Wait 5–10 seconds for the encoder to load, then verify:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/health
# Expected: {"status":"ready","collection":"markdown_kb"}
```

If the service still won't start, jump to `repair-playbooks.md#service-will-not-start`.

## Branch C — Wire MCP and add a first project

This is the same end state regardless of whether you started in Branch A or Branch B.

### C.1 — Read the canonical MCP config

**Never hand-construct `.mcp.json`.** Read it from the running service:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/mcp-config
```

This endpoint is computed by `src/ragtools/service/routes.py` → `mcp_config()` with `sys.frozen` detection, so it always points to the correct binary path for your install mode (packaged `rag.exe`, packaged `./rag`, or dev `rag-mcp`). See `mcp-wiring.md`.

The output looks like:

```json
{
  "mcpServers": {
    "ragtools": {
      "command": "C:\\Users\\you\\AppData\\Local\\Programs\\RAGTools\\rag.exe",
      "args": ["serve"]
    }
  }
}
```

### C.2 — Pick a location for `.mcp.json`

| Location | When to use |
|---|---|
| **Project-level**: `<repo>/.mcp.json` | Recommended for team-shared configs — the file lives next to your code |
| **User-level**: `~/.claude/.mcp.json` | Global — every Claude Code session for this user |

If `.mcp.json` already exists at your chosen location, **merge** the ragtools entry into the existing `mcpServers` object — do NOT overwrite. Other MCP servers may already be configured.

### C.3 — Add a project via the HTTP API

**Critical:** never edit `config.toml` directly. The v2.4.1 data-loss bug (F-001) was caused by a CWD-relative config write. The only safe write path is the HTTP API.

```bash
curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "path": "C:\\path\\to\\project"}'
```

Or use the admin panel at `http://127.0.0.1:21420` → "Add Project".

After adding, the watcher kicks in and incremental indexing starts. Watch progress in:

- The admin panel "Recent Activity" card
- `curl http://127.0.0.1:21420/api/status` (look at `chunks` and `last_indexed`)
- `/rag-status` (compact summary)

### C.4 — Smoke test from Claude Code

Now ask Claude Code something that should hit your knowledge base:

> Search my knowledge base for [a topic from your project].

Claude calls the `search_knowledge_base` MCP tool directly — neither rag-plugin nor any plugin wraps it. If results come back with HIGH or MODERATE confidence, you're done. If LOW or empty, check `/rag-status` for chunks count, then `/rag-doctor`.

## Verification checklist

After setup, run through `post-install-verify.md` or just:

- [ ] `rag version` returns expected version
- [ ] `curl http://127.0.0.1:21420/health` returns `{"status":"ready"}`
- [ ] `curl http://127.0.0.1:21420/api/projects` returns your project
- [ ] `curl http://127.0.0.1:21420/api/status` shows `chunks > 0`
- [ ] Admin panel opens at `http://127.0.0.1:21420`
- [ ] `.mcp.json` exists at the chosen location with a `ragtools` entry
- [ ] A search from Claude Code returns results

## What can go wrong

| Symptom | Where to look |
|---|---|
| SmartScreen blocks the installer | Click "More info" → "Run anyway" — no signing yet (G-005) |
| Gatekeeper blocks the macOS binary | `xattr -cr rag/` to clear the quarantine bit |
| Service won't start | `repair-playbooks.md#service-will-not-start` |
| Service starts but `/api/projects` is empty after restart | F-006 / `repair-playbooks.md#projects-empty-after-restart` |
| `Permission denied: 'ragtools.toml'` on add-project | F-001 / upgrade to ≥ v2.4.1 |
| MCP server doesn't connect from Claude Code | F-009 / `repair-playbooks.md#mcp-not-connecting` |
| Search returns no results | `/rag-status` to confirm chunks; `/rag-doctor` if chunks > 0 but search is empty |

## See also

- `install.md` — sources, prerequisites, full install procedures
- `mcp-wiring.md` — MCP architecture and dual-mode design
- `post-install-verify.md` — verification checklist
- `paths-and-layout.md` — where files live per platform
- `gaps.md` — what's not supported (Linux installer, macOS LaunchAgent, Intel Macs, signing, WinGet)
- `risks-and-constraints.md` — single-process lock, Syncthing risk, Gatekeeper friction
- `repair-playbooks.md` — what to do when something breaks
