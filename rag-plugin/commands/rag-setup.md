---
description: Smart ragtools install/upgrade/verify. Detects state and branches — install walkthrough when missing, start-service + verify when down, upgrade walkthrough when outdated, idempotent plugin-layer verify when healthy. Absorbs the former /rag-upgrade command (v0.4.0).
argument-hint: "[--project <path>] [--upgrade] [--verify]"
allowed-tools: Bash(curl:*), Bash(rag service:*), Bash(rag version:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Bash(printenv:*), Bash(echo:*), Bash(uname:*), Bash(ver:*), Bash(arch:*), Read, Write
disable-model-invocation: false
author: TaqaTechno
version: 0.4.0
---

# /rag-setup

Smart state-aware entry point for "get ragtools working." Replaces the former `/rag-setup + /rag-upgrade` split. One command handles install, start-service, upgrade, and idempotent post-install verification. Branches on the detected state — the user does not need to know which sub-flow they are in.

## Behavior by state (routing table)

| Detected state | What /rag-setup does |
|---|---|
| **not-installed** | **Branch A — Install walkthrough.** Detect platform, show installer URL, warn about friction, wait for install to complete, re-probe state, fall through to Branch D (verify). |
| **installed, service DOWN** | **Branch B — Start the service.** Offer `rag service start`, wait, re-probe, fall through to Branch D. |
| **installed, service STARTING** | Wait, re-probe once. If still starting, ask the user to re-run `/rag-setup` in 10 seconds. |
| **installed, service BROKEN** | Refuse. Print `service is broken. run /rag-doctor --full --fix first.` |
| **installed, service UP, old version** | **Branch C — Upgrade walkthrough.** Show version diff + changelog highlights, offer in-place upgrade, walk it. After upgrade, fall through to Branch D. This replaces the former `/rag-upgrade`. |
| **installed, service UP, current version** | **Branch D — Verify + summary.** Idempotent checks: MCP wiring, CLAUDE.md rule, dedupe. Fix any gaps inline. Print post-install summary. |
| **--upgrade flag** | Forces Branch C regardless of detected version (useful for testing or forced re-check against GitHub). |
| **--verify flag** | Forces Branch D regardless of state (idempotent re-check of plugin-layer wiring). |

## Step 0 — State detection

Follow `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Produce the `state` object, print the 6-line mode banner.

Then dispatch:

```
if state.install_mode == not-installed:
    → Branch A
elif state.service_mode == BROKEN:
    → refuse, point at /rag-doctor
elif state.service_mode in (DOWN, STARTING):
    → Branch B
elif --upgrade flag:
    → Branch C (forced)
else:
    → compare state.version to latest_version (fetch via Step C.0)
    → if installed < latest: Branch C
    → else: Branch D
```

---

## BRANCH A — Install walkthrough (not-installed)

### A.1 — Detect platform and arch

```bash
uname -sm 2>/dev/null || ver
```

| Platform / arch | Action |
|---|---|
| Windows x64 | → A.2 |
| macOS arm64 | → A.3 |
| macOS x86_64 (Intel) | **REFUSE.** No Intel build (G-004). Apple Silicon required. Stop. |
| Linux | **REFUSE packaged path.** No Linux artifact (G-001). Offer A.4 (dev install). |
| Unknown | Print platform + arch and ask user to confirm before proceeding. |

### A.2 — Windows installer flow

1. **Show URL** (do NOT auto-download): `https://github.com/taqat-techno/rag/releases`
2. **Warn about friction:** ~488 MB download, SmartScreen warning expected (G-005 — no signing), ~5–10s first-run encoder load.
3. **What to click:** download `RAGTools-Setup-{latest}.exe`, double-click. Recommended options: ☑ Add to PATH, ☑ Start service after install, ☑ Add to Windows Startup.
4. Wait for user to confirm install completed.
5. Re-run state detection (Step 0). Fall through to **Branch D** (verify).

### A.3 — macOS tarball flow

1. **Show URL:** `https://github.com/taqat-techno/rag/releases`
2. **Warn:** ~423 MB, Gatekeeper will block — must `xattr -cr rag/`, no `.app`/`.dmg`, no LaunchAgent (G-002 — manual start each session).
3. **Commands:**
   ```bash
   tar -xzf RAGTools-{version}-macos-arm64.tar.gz
   xattr -cr rag/
   cd rag
   ./rag version
   ./rag service start
   ```
4. Wait, re-run state detection, fall through to **Branch D**.

### A.4 — Linux dev install (from source)

Walk per `references/install.md` section 6.4:

```bash
git clone https://github.com/taqat-techno/rag.git
cd rag
python -m venv .venv
source .venv/bin/activate   # or .venv/Scripts/activate on Git Bash
pip install -e ".[dev]"
rag version
rag doctor
rag service start
```

Note: dev mode means config at `./ragtools.toml`, data at `./data/`. Fall through to **Branch D**.

---

## BRANCH B — Start the service (installed, service DOWN)

The simplest branch. Binary is present, service is not running.

1. Print: `ragtools is installed at <binary_path> but the service is not running.`
2. Offer: `rag service start` — ask user to confirm then run it themselves. Do NOT auto-invoke.
3. Wait 5–10s for encoder to load.
4. Re-probe `/health`. If DOWN → route to `/rag-doctor --symptom F-005 --fix` and stop.
5. If UP → fall through to **Branch D**.

---

## BRANCH C — Upgrade walkthrough (installed, service UP, version < latest — or --upgrade forced)

This branch absorbs the former `/rag-upgrade` command. Same in-place upgrade flow, same D-005 URL-only discipline, same D-008 compact output.

### C.0 — Fetch latest release from GitHub

```bash
curl --max-time 5 -s -L \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/taqat-techno/rag/releases/latest
```

Parse the response. Extract:
- `tag_name` (strip leading `v`)
- `name`
- `published_at`
- `body` (changelog)
- `assets[].name` and `assets[].browser_download_url`

Failure modes:
- API unreachable → print error, link to releases page, stop.
- No `tag_name` in response → print error, link to releases page, stop.
- Rate-limited (403) → suggest retrying later.

Record `state.latest_version`.

### C.1 — Compare versions

| Case | Action |
|---|---|
| `installed > latest` | Print `you are on a dev build (v<installed> > v<latest>). no upgrade needed.` Fall through to Branch D. |
| `installed == latest` | Print `up to date: ragtools v<installed>.` Fall through to Branch D. |
| `installed < latest` | Continue to C.2. |

### C.2 — Present the upgrade summary (compact, ≤ 12 lines)

```
ragtools v<installed> → v<latest>
released: <published_at> (<N> days ago)

highlights:
  • <line 1 from changelog>
  • <line 2 from changelog>
  • <line 3 from changelog>

[pre-v2.4.1 warning if applicable]

installer for your platform: <download URL from assets[]>
```

**Changelog highlights:** first 3 bullet points or first 3 non-empty lines after `## Changes` / `## What's Changed` / `### Highlights`. Cap each at ~80 chars. Empty body → `(no changelog provided — see GitHub release page)`.

**Installer asset selection:**

| Install mode | Match pattern |
|---|---|
| `packaged-windows` | `RAGTools-Setup-*.exe` |
| `packaged-macos` | `RAGTools-*-macos-arm64.tar.gz` |
| `dev-mode` | skip — recommend `git pull && pip install -e .` |

**Pre-v2.4.1 warning (strong):**
```
⚠ pre-v2.4.1 detected. config writes can land in the wrong path and cause
projects to disappear after restart (F-001). upgrade is strongly recommended.
```

### C.3 — Ask the user how to proceed

```
how would you like to upgrade?
  1. walk the in-place upgrade (recommended)
  2. just give me the URL — I'll handle it myself
  3. cancel — I'll upgrade later
```

Option 1 → C.4. Option 2 → print URL, fall through to Branch D for post-upgrade verify if/when the user returns. Option 3 → stop.

### C.4 — Walk the in-place upgrade

**Windows (packaged):**
1. Print: `the installer handles in-place upgrade automatically. it stops the service, replaces files, reinstalls the startup task, and restarts the service. data and config are preserved.`
2. Show URL — **never auto-download** (D-005).
3. Wait for user confirmation.
4. Re-run state detection. Confirm new version detected. Fall through to Branch D.

**macOS (packaged):**
1. Print platform caveats (G-005, G-002): no signing, manual `tar -xzf`, no LaunchAgent.
2. Show:
   ```bash
   ./rag service stop
   tar -xzf RAGTools-<latest>-macos-arm64.tar.gz
   xattr -cr rag/
   # move/replace the old install (preserves ~/Library/Application Support/RAGTools/data and config.toml)
   cd rag
   ./rag service start
   ```
3. Wait, re-run state detection, fall through to Branch D.

**Dev mode:**
1. Show:
   ```bash
   rag service stop
   git pull
   pip install -e ".[dev]"
   rag service start
   ```
2. Wait, re-run state detection, fall through to Branch D.

---

## BRANCH D — Verify and summary (installed, service UP, current version)

This branch is the **default end state** for all other branches. It is also what the user gets when they type `/rag-setup` on an already-healthy install. Branch D is **idempotent** — running it multiple times on a healthy install is a no-op that prints a green summary.

### D.1 — Read the canonical MCP config

**CRITICAL:** never hand-construct `.mcp.json`. Read it from the running service:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/mcp-config
```

This endpoint computes paths dynamically via `sys.frozen` detection. See `references/mcp-wiring.md` and D-020.

If the endpoint returns nothing parseable, route to `/rag-doctor` and stop.

### D.2 — Plugin-layer MCP wiring check

Run `/rag-config mcp-dedupe status` internally. Expected outcome on a healthy v0.3.3+ install:
- `OK — 1 (plugin-level, canonical, schema OK)` — nothing to do.
- `WARN — <N+1> (plugin-level + <N> duplicates)` → offer to clean: `/rag-config mcp-dedupe clean`. Ask for confirmation, do not auto-invoke.
- `ERROR` → surface the error and route to `/rag-doctor --full`.

If the user has a non-default wiring need (project-level or user-level `.mcp.json`), ask:

```
I can write a project/user-level .mcp.json:
  1. Project-level at <cwd>/.mcp.json (team-shared, wrapped shape)
  2. User-level at ~/.claude/.mcp.json (global, wrapped shape)
  3. Skip — the plugin-level .mcp.json is already in place (recommended)

Which? (1 / 2 / 3)
```

If 1 or 2, use the config from D.1 (wrapped shape at these scopes per D-019). If 3 (default), skip.

### D.3 — CLAUDE.md retrieval rule check

Run `/rag-config claude-md status` internally.
- `INSTALLED v<N>` matching bundled version → nothing to do.
- `NOT INSTALLED` → offer `/rag-config claude-md install`. Ask for confirmation.
- `OUTDATED v<OLD>` → offer upgrade to new version. Ask for confirmation.
- `TARGET MISSING` (`~/.claude/CLAUDE.md` does not exist) → print warning, recommend creating the target file.

Remind the user: the rule takes effect in the **next** Claude Code session (current session already loaded `~/.claude/CLAUDE.md` at startup).

### D.4 — Add first project (only if `--project <path>` was passed or projects list is empty on a fresh install)

Probe: `curl http://127.0.0.1:21420/api/projects`. If empty and the user is in the first-install flow (came from Branch A), ask for a project path.

Validate: `test -d "<path>"`. POST:

```bash
curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "<basename>", "path": "<path>"}'
```

**Never** edit `config.toml` directly (D-002, F-001). Poll `/api/status` for `chunks` to start increasing; cap wait at 30s and route longer indexing to `/rag-doctor`.

Skip this step entirely if the user is re-running `/rag-setup --verify` on an already-populated install — do not ask for a new project.

### D.5 — Smoke test hint

The plugin does not call `search_knowledge_base` itself (D-001). Instead, print:

> "Setup complete. Try a search from Claude Code in a new session by asking:
> > Search my knowledge base for [a topic from your project].
> Claude will call the `search_knowledge_base` MCP tool directly. If no results, run `/rag-doctor`."

### D.6 — Final summary banner

Re-run state detection and print:

```
setup complete.
  service: UP (v<installed>)
  mcp: wired (plugin-level, canonical)
  claude.md rule: INSTALLED v<N>
  projects: <count>
  next: try a search from Claude Code in a new session.
```

Reflect any skipped or warned sub-steps:

```
setup complete.
  service: UP (v<installed>)
  mcp: wired (plugin-level, canonical)
  claude.md rule: SKIPPED — run /rag-config claude-md install later
  projects: 1
  warning: Claude may not use the MCP for domain questions until the rule is installed.
```

---

## Failure handling

| Situation | Behavior |
|---|---|
| Binary not found and platform unknown | Stop after A.1 with "I can't tell what platform you're on" |
| Intel macOS detected | **Hard refuse.** Do not pretend arm64 will work. |
| Linux detected | Refuse packaged path; offer A.4 dev install. |
| GitHub API unreachable (C.0) | Print error, link to releases page manually, skip to Branch D if possible. |
| GitHub API rate-limited (403) | Print error with rate-limit note, suggest retrying later. |
| No installer asset for platform | Link to releases page manually. |
| Service goes DOWN mid-setup | Re-run Step 0; if still down, route to Branch B. |
| `/api/mcp-config` returns 500 or empty | Route to `/rag-doctor`. |
| `.mcp.json` exists with a different ragtools entry | Show diff, ask for confirmation before overwriting. |
| `POST /api/projects` returns 400 (duplicate path) | Tell user project is already added; show `/api/projects` output. |
| `POST /api/projects` returns 500 | Route to `/rag-doctor --logs`. |
| User wants to skip MCP wiring (D.2 option 3) | Skip to D.3. |
| User wants to skip project add | Skip to D.5 with a note that search returns nothing until a project is added. |

## Boundary reminders

- **Do NOT auto-download installer artifacts.** Produce URLs; user clicks. (D-005)
- **Do NOT hand-construct `.mcp.json`.** Always read from `/api/mcp-config`. (D-020, `references/mcp-wiring.md`)
- **Do NOT write `config.toml` directly.** Use `POST /api/projects`. (D-002, F-001)
- **Do NOT call `search_knowledge_base`** — explain how the user calls it from Claude Code instead. (D-001)
- **Do NOT promise** macOS LaunchAgent (G-002), WinGet install (G-003), Intel Macs (G-004), Linux installer (G-001), code signing (G-005).
- **Do NOT skip the pre-v2.4.1 warning.** F-001 is data-loss-tier.
- **Do NOT re-implement state detection.** Reference `rules/state-detection.md`.

## See also

- `/rag-doctor` — smart diagnose+status+repair (absorbs former `/rag-status` and `/rag-repair`)
- `/rag-projects` — project CRUD via HTTP API
- `/rag-reset` — destructive reset with three escalation levels
- `/rag-config` — plugin-layer config
- `rules/state-detection.md` — canonical state-detection recipe
- `references/setup-walkthrough.md` — long-form install companion
- `references/install.md` — install sources, prerequisites, dev install
- `references/mcp-wiring.md` — MCP architecture and registration scopes
- `references/upgrade-paths.md` — in-place vs portable vs source upgrade
- `references/known-failures.md#f-001` — the v2.4.1 data-loss bug behind the pre-v2.4.1 warning
- `references/gaps.md` — G-001..G-010 unverified/unimplemented items
