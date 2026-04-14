---
description: Guided ragtools setup — detect install state, walk install/start, wire MCP, add a first project, smoke-test the search loop
argument-hint: "[--project <path>]"
allowed-tools: Bash(curl:*), Bash(rag service:*), Bash(rag version:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Bash(printenv:*), Bash(echo:*), Bash(uname:*), Bash(ver:*), Bash(arch:*), Read, Write
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-setup

Interactive first-run setup for ragtools. Walks the user from "I don't have it" or "I have it but it's broken" all the way to "service running, MCP wired, first project indexed, first MCP search returns a result". This is the **highest-friction** command in the plugin — every flow has to be honest about what it can and cannot automate.

## Behavior

This command is **conversational, not single-shot.** It gathers a small number of branching answers from the user (`mcp-server-dev/build-mcp-server` interrogation pattern), commits to a path, then walks one phase at a time. **Do not** dump the entire plan up front. Print the mode banner, decide the branch, ask the next question, act.

## Required steps (perform in order)

### Step 0 — Mode detection (reuse Phase 2 recipe)

Run the same install-mode + service-mode detection as `/rag-status` (steps 1 and 2). Print the mode banner. **Do not re-implement** — the format is fixed:

```
ragtools detected: <packaged-windows | packaged-macos | dev-mode | not-installed>
service mode: <UP (proxy) | DOWN | STARTING | BROKEN | N/A>
binary: <path or "not found">
config:  <path or "not found">
data:    <path or "not found">
logs:    <path or "not found">
```

### Step 1 — Branch on detected state

Pick exactly one of the three branches below.

| Detected | Branch |
|---|---|
| `not-installed` | **A — Install** |
| Installed, `service mode: DOWN` or `BROKEN` | **B — Start the service** |
| Installed, `service mode: UP` or `STARTING` | **C — Wire MCP and add first project** |

---

### BRANCH A — Install (not-installed)

#### A.1 — Detect platform and arch

```bash
uname -sm 2>/dev/null || ver
```

Map to one of:

| Platform / arch | Action |
|---|---|
| Windows x64 | Show installer URL, walk install (A.2) |
| macOS arm64 | Show tarball URL, walk extract + Gatekeeper (A.3) |
| **macOS x86_64 (Intel)** | **REFUSE.** Print: `ragtools does not ship an Intel macOS build (G-004 in references/gaps.md). The macos-14 CI runner only builds arm64. Apple Silicon is required.` Stop. |
| **Linux** | **REFUSE the packaged path.** Print: `ragtools does not ship a packaged Linux artifact (G-001 in references/gaps.md). Use the dev install from source — see references/install.md section "Development install from source".` Offer to walk the dev install. |
| Unknown | Print platform + arch and ask the user to confirm before proceeding. |

#### A.2 — Windows installer flow

1. **Show the URL** (do NOT auto-download): `https://github.com/taqat-techno/rag/releases`
2. **Warn about friction** up front:
   - `~488 MB download` (per `references/install.md`)
   - `SmartScreen warning is expected — no code signing yet (G-005)`
   - `~5–10 second first-run delay while encoder loads`
3. **Tell the user what to click:**
   - Download `RAGTools-Setup-{latest version}.exe`
   - Double-click. User-level install — no admin required.
   - Recommended options: ☑ Add to PATH, ☑ Start service after install, ☑ Add to Windows Startup
4. **Wait for confirmation:** "Tell me when the installer says it's done."
5. **Re-run mode detection** (back to Step 0) to confirm the install landed and the service is up.
6. Move to **Branch C**.

#### A.3 — macOS tarball flow

1. **Show the URL** (do NOT auto-download): `https://github.com/taqat-techno/rag/releases`
2. **Warn about friction** up front:
   - `~423 MB download`
   - `Gatekeeper will block on first launch — must run xattr -cr to clear quarantine (no signing, G-005)`
   - `No .app bundle, no .dmg — manual tar extract only`
   - `No login auto-start (G-002) — service must be started manually each session`
3. **Tell the user what to do:**
   ```bash
   tar -xzf RAGTools-{version}-macos-arm64.tar.gz
   xattr -cr rag/
   cd rag
   ./rag version
   ./rag service start
   ```
4. **Wait for confirmation,** then re-run mode detection. Move to **Branch C**.

#### A.4 — Linux dev install (if user accepted the offer)

Walk the source install from `references/install.md` section 6.4:

```bash
git clone https://github.com/taqat-techno/rag.git
cd rag
python -m venv .venv
source .venv/bin/activate     # or .venv/Scripts/activate on Git Bash
pip install -e ".[dev]"
rag version
rag doctor
rag service start
```

Note loudly: `dev mode means config lives at ./ragtools.toml and data at ./data/ — see references/paths-and-layout.md`.

---

### BRANCH B — Start the service (installed, service down)

This is the simplest branch. The user already has ragtools; they just need it running.

1. **Print:** `ragtools is installed at <binary path> but the service is not running.`
2. **Offer to start it:** Show the command and ask the user to confirm.
   ```bash
   rag service start
   ```
3. **After they run it,** wait 5–10 seconds for the encoder to load, then re-probe `/health`:
   ```bash
   curl --max-time 2 -s http://127.0.0.1:21420/health
   ```
4. **If still down,** route to `/rag-doctor` and `references/repair-playbooks.md#service-will-not-start`. Stop.
5. **If up,** congratulate briefly and move to **Branch C**.

---

### BRANCH C — Wire MCP and add first project (installed, service up)

The service is healthy. Now we wire Claude Code and seed the first project.

#### C.1 — Read the canonical MCP config

**CRITICAL:** never hand-construct the `.mcp.json`. Always read it from the running service:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/mcp-config
```

This endpoint is computed dynamically in `src/ragtools/service/routes.py` → `mcp_config()` using `sys.frozen` detection, so it always points to the correct binary for the current install mode (packaged vs dev). See `references/mcp-wiring.md`.

If the endpoint returns nothing parseable, print: `could not read /api/mcp-config — service may be misconfigured. Run /rag-doctor.` Stop.

#### C.2 — Decide where to write `.mcp.json`

Ask the user one question:

> "I can write `.mcp.json` to:
>   1. **Project-level** at `<current cwd>/.mcp.json` (recommended for team-shared configs)
>   2. **User-level** at `~/.claude/.mcp.json` (global, all your projects)
>
> Which? (1 or 2)"

If `.mcp.json` already exists at the chosen location, **read it first**, merge the `ragtools` entry from `/api/mcp-config` into the existing `mcpServers` object, and write the merged result. Never overwrite blindly — other MCP servers may already be configured.

If the merge would replace an existing `ragtools` entry with different command/args, **show the diff and ask the user to confirm** before writing.

#### C.3 — Add the first project

Ask the user for a project path (or use `--project <path>` if passed as an argument). Validate that the path exists:

```bash
test -d "<path>" && echo OK || echo MISSING
```

If missing, ask again. If OK, POST to the projects API:

```bash
curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "<derived from basename>", "path": "<path>"}'
```

**Never** edit `config.toml` directly — the v2.4.1 bug is the reason. The HTTP API goes through `get_config_write_path()`, which is the only safe write path.

After the POST returns success, poll `/api/status` for `index_status` to flip to `ready` (or for `chunks` to start increasing). Cap the wait at 30 seconds in compact mode — for larger projects, tell the user "indexing is in progress; check `/rag-status` to monitor".

#### C.4 — Smoke test

The plugin **does not** call `search_knowledge_base` itself (D-001). Instead, tell the user:

> "Setup complete. Try a search from Claude Code by asking something like:
>
> > Search my knowledge base for [a topic from your project].
>
> Claude will call the `search_knowledge_base` MCP tool directly. If you don't see results, run `/rag-status` to verify projects and chunks, then `/rag-doctor` if needed."

#### C.5 — Final mode banner

Re-run mode detection one more time and print the banner. Append a one-line summary:

```
setup complete. service: UP. mcp: wired. projects: 1. next: try a search from Claude Code.
```

---

## Failure handling

| Situation | Behavior |
|---|---|
| Binary not found and platform unknown | Stop after the platform/arch check with a clear "I can't tell what platform you're on" message |
| Intel macOS detected | **Hard refuse.** Do not pretend an arm64 build will work |
| Linux detected | Refuse packaged path; offer dev install |
| `/api/mcp-config` returns 500 or empty | Route to `/rag-doctor` with a hint that service is misconfigured |
| `.mcp.json` exists with a different ragtools entry | Show diff, ask user to confirm before overwriting |
| `POST /api/projects` returns 400 (duplicate path) | Tell the user the project is already added; show `/api/projects` output |
| `POST /api/projects` returns 500 | Route to `/rag-doctor --logs` |
| User wants to skip MCP wiring | Skip C.1–C.2, go straight to C.3 |
| User wants to skip project add | Skip C.3, go straight to C.4 with a note that they must add a project before search returns anything |
| Service goes DOWN mid-setup (e.g. user kills it) | Re-run mode detection; if still down, offer to restart |

## Boundary reminders

- **Do NOT auto-download** the installer. Produce URLs and instructions; the user clicks. (D-005, scope rule)
- **Do NOT hand-construct `.mcp.json`.** Always read from `/api/mcp-config`. (`references/mcp-wiring.md`)
- **Do NOT write `config.toml` directly.** Use `POST /api/projects`. (D-002, F-001)
- **Do NOT call `search_knowledge_base`** — explain to the user how to call it from Claude Code instead. (D-001)
- **Do NOT promise** macOS LaunchAgent (G-002), WinGet install (G-003), Intel Macs (G-004), Linux installer (G-001), code signing (G-005). Be honest in every branch.

## See also

- `/rag-status` — verify install mode and service state
- `/rag-doctor` — deep diagnostic when setup fails
- `references/setup-walkthrough.md` — long-form companion document with full command examples
- `references/install.md` — install sources, prerequisites, dev install from source
- `references/mcp-wiring.md` — MCP architecture, proxy vs direct mode, registration locations
- `references/gaps.md` — G-001..G-010 unverified/unimplemented items
- `references/risks-and-constraints.md` — Gatekeeper, Syncthing, single-process lock
