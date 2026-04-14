---
description: Reset ragtools state with three escalation levels — soft (rebuild), data (delete data dir), nuclear (delete everything). Each level requires typing DELETE verbatim. Blocks on pre-v2.4.1 versions.
argument-hint: "--soft | --data | --nuclear"
allowed-tools: Bash(curl:*), Bash(rag version:*), Bash(rag service:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-reset

Three levels of destructive reset for ragtools state, with strict confirmation gating. Every level requires the user to type `DELETE` verbatim. Pre-v2.4.1 versions are **blocked** because the v2.4.1 config-write-path bug (F-001) means a reset on those versions can lose more data than the user intended.

This command **shows** destructive shell commands but **never executes** them itself — the user runs the displayed commands manually. The command's job is gating, not execution.

## Behavior

Three escalation levels, ordered by destructive scope:

| Flag | What it does | What it preserves | Confirmation |
|---|---|---|---|
| `--soft` | Triggers `POST /api/rebuild` via the HTTP API — drops Qdrant data and the state DB, then re-indexes from configured projects | Config file, project list, all settings | type `DELETE` once |
| `--data` | User deletes the data directory (`%LOCALAPPDATA%\RAGTools\data\` or platform equivalent) | Config file (`config.toml`) | type `DELETE` twice (gate + confirm) |
| `--nuclear` | User deletes the entire `RAGTools` directory (data + config + logs + everything) | Nothing user-side. Bundled binary is not affected. | type `DELETE` three times (gate + confirm + final ack) |

Compact-by-default per D-008: ≤ 15 lines per branch.

## Required steps (perform in order)

### Step 0 — State detection (state-gate preamble)

Follow the canonical recipe in `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Produce the `state` object, print the 6-line mode banner. **Do not re-implement** — reference the rule file.

**State gate** — refuse early on bad states. This check runs **before** any typed-DELETE prompt, so the user never sees a destructive gate for an install that doesn't exist:

| Detected state | Action |
|---|---|
| `install_mode == not-installed` | Refuse: `ragtools is not installed. nothing to reset.` Stop. |
| `service_mode == BROKEN` | Refuse: `service is broken. run /rag-doctor --full --fix before resetting.` Stop. |
| `state.version` unparseable | Refuse: `could not parse rag version output. reinstall first via /rag-setup.` Stop. |
| Otherwise | Continue to Step 1. |

### Step 1 — Parse the flag

Exactly one flag is required:

| Input | Action |
|---|---|
| `--soft` | Continue to soft-reset branch |
| `--data` | Continue to data-reset branch |
| `--nuclear` | Continue to nuclear-reset branch |
| Multiple flags | Refuse: `pick exactly one of --soft / --data / --nuclear` |
| No flag | Print usage and stop |
| Unknown flag | Refuse with usage line |

### Step 2 — Pre-v2.4.1 version check (BLOCKING)

Run `rag version 2>&1` and parse the semver. If `installed_version < 2.4.1`:

```
⚠ BLOCKED: pre-v2.4.1 detected (you are on v<installed>).

the v2.4.1 fix changed how config writes are resolved. on pre-v2.4.1 versions,
the launcher VBScript inherited CWD = C:\Windows\System32, the config write
landed in an unwritable directory, and startup-sync deleted "orphaned" data
(F-001 in references/known-failures.md).

resetting on this version can lose MORE data than you intend, because the
post-reset startup-sync may not see your config and may treat your projects
as orphaned.

required action: upgrade first. run /rag-setup (which walks the upgrade flow for old versions).

if you are CERTAIN you understand the risk and want to proceed anyway, you
will need to bypass this check by running the destructive commands manually
(see references/recovery-and-reset.md). this command will not bypass it for you.
```

**Stop.** No reset on pre-v2.4.1.

If `rag version` is unparseable, print the parse error and refuse — do not assume a version. Recommend reinstall.

### Step 3 — Service-state check

`/rag-reset --soft` requires the service to be **up** (it goes through `POST /api/rebuild`).

`/rag-reset --data` and `--nuclear` require the service to be **down** (you cannot delete the data directory while the service holds the Qdrant lock).

| Flag | Required service mode | If wrong | Action |
|---|---|---|---|
| `--soft` | UP | DOWN/BROKEN | print: `--soft requires the service to be running. start with: rag service start` and stop |
| `--data` | DOWN | UP | print: `--data requires the service to be stopped. stop with: rag service stop` and stop |
| `--nuclear` | DOWN | UP | print: `--nuclear requires the service to be stopped. stop with: rag service stop` and stop |

This is enforced because:
- Soft-reset uses the HTTP API, which only exists when the service is up
- Data/nuclear delete files the service holds open — running them while the service is up corrupts the Qdrant lock and creates F-003 conditions next start

### Step 4 — Walk the chosen branch

#### --soft branch

1. **Print the gate:**
   ```
   /rag-reset --soft
   
   this drops all Qdrant data and the state DB, then re-indexes from your
   configured projects. it preserves config.toml and the project list.
   
   the rebuild runs through POST /api/rebuild on the service. it takes
   minutes-to-hours depending on project size. the service stays responsive
   during the rebuild (split-lock indexing, v2.4+).
   
   type DELETE to confirm:
   ```

2. **Wait for the user to type `DELETE` verbatim.** If they type anything else (including `yes`, `delete`, `Delete`, etc.), refuse and stop.

3. **Show the command** (do not auto-execute):
   ```bash
   curl --max-time 5 -s -X POST http://127.0.0.1:21420/api/rebuild
   ```

4. **Wait for the user to run it,** then poll `/api/status` for `chunks` to start increasing. Cap the wait at 30 seconds in compact mode and tell the user to monitor via `/rag-status`.

5. **Print:** `rebuild started. monitor via /rag-doctor. nothing else to do here.`

#### --data branch

1. **Print the gate:**
   ```
   /rag-reset --data
   
   this DELETES the entire data directory:
     <resolved data path from mode banner>
   
   it preserves config.toml (your project list survives).
   
   on next service start, ragtools creates a fresh data directory and re-indexes
   all configured projects from scratch.
   
   service mode: <DOWN — confirmed>
   
   type DELETE to confirm:
   ```

2. **Wait for `DELETE`.** Refuse anything else.

3. **Print the second gate:**
   ```
   final confirmation:
     about to delete: <resolved data path>
     this cannot be undone.
   
   type DELETE again to proceed:
   ```

4. **Wait for second `DELETE`.** Refuse anything else.

5. **Show the platform-correct delete command:**
   - Windows: `rmdir /S /Q "%LOCALAPPDATA%\RAGTools\data"`
   - macOS: `rm -rf "$HOME/Library/Application Support/RAGTools/data"`
   - Dev mode: `rm -rf ./data`

6. **Wait for the user to run it.** Then:
   ```bash
   rag service start
   ```
   Wait 5–10 seconds, then `curl /health` to confirm the service is up with a fresh data dir.

7. **Print:** `data reset complete. service: UP. projects: <count from /api/projects>. indexing will resume from the watcher. monitor via /rag-doctor.`

#### --nuclear branch

1. **Print the gate:**
   ```
   /rag-reset --nuclear
   
   ⚠ MAXIMALLY DESTRUCTIVE.
   
   this DELETES the entire RAGTools state directory:
     <resolved %LOCALAPPDATA%\RAGTools or platform equivalent>
   
   you will lose:
     • config.toml (your project list)
     • data/ (the Qdrant index)
     • logs/ (service logs)
     • all settings
   
   you will NOT lose:
     • the rag.exe binary itself (lives in %LOCALAPPDATA%\Programs\RAGTools)
     • your source files (the directories your projects pointed at)
   
   service mode: <DOWN — confirmed>
   
   type DELETE to confirm:
   ```

2. **Wait for first `DELETE`.**

3. **Print the second gate:**
   ```
   second confirmation:
     about to delete: <resolved RAGTools state dir>
     this is irreversible.
     after the reset, you will need to re-add your projects manually
     via /rag-projects add or /rag-setup.
   
   type DELETE again to proceed:
   ```

4. **Wait for second `DELETE`.**

5. **Print the final acknowledgment:**
   ```
   final acknowledgment:
     i understand i will lose my project list, my index, and my logs.
     i understand the rag binary itself will remain installed.
     i understand i will need to re-add projects after the reset.
   
   type DELETE one last time to proceed:
   ```

6. **Wait for third `DELETE`.**

7. **Show the platform-correct delete command:**
   - Windows: `rmdir /S /Q "%LOCALAPPDATA%\RAGTools"`
   - macOS: `rm -rf "$HOME/Library/Application Support/RAGTools"`
   - Dev mode: `rm -rf ./data ./ragtools.toml`

8. **Wait for the user to run it.** Then:
   ```bash
   rag service start
   ```

9. **Verify:** `rag version`, `curl /health`, `curl /api/projects` (should return `[]`).

10. **Print:** `nuclear reset complete. ragtools is in fresh-install state. run /rag-setup to add your first project.`

### Step 5 — Final mode banner

After any branch, re-run mode detection and print the updated banner. If anything is wrong, route to `/rag-doctor`.

## Failure handling

| Situation | Behavior |
|---|---|
| Pre-v2.4.1 detected | **BLOCK.** Print warning, recommend `/rag-setup` (which walks the upgrade flow), stop. |
| Multiple flags or no flag | Refuse with usage line |
| Service mode wrong for chosen flag | Refuse with "start/stop the service first" message |
| User types anything other than `DELETE` at a gate | Refuse and stop. **Do not retry automatically.** |
| `rag version` unparseable | Refuse — do not assume a version |
| User runs the displayed delete command but it fails | Show the error, route to `/rag-doctor` |
| Post-reset `curl /health` fails | Route to `/rag-doctor` |
| User has Syncthing/cloud-sync on the data dir | Print warning before the gate (sync may restore deleted files asynchronously, leading to confusion) |

## Boundary reminders

- **Do NOT execute destructive commands.** This command **shows** the commands; the user runs them. The command's value is the gating, not the execution.
- **Do NOT bypass the pre-v2.4.1 block.** F-001 is data-loss-tier. The block exists for a reason.
- **Do NOT use `rag rebuild` (CLI)** for `--soft`. Use the HTTP API endpoint `POST /api/rebuild`. The CLI form would fight the Qdrant lock and trip the Phase 6 hook.
- **Do NOT auto-run `rag service start`** after a reset. Show the command and wait.
- **Do NOT delete the binary itself.** Even nuclear reset preserves `%LOCALAPPDATA%\Programs\RAGTools\rag.exe` — only the user state goes.
- **Do NOT proceed past a gate without the exact `DELETE` token.** Case-sensitive. No leading or trailing whitespace. No alternative tokens like `yes`.
- Compact-by-default per D-008.

## See also

- `/rag-setup` — recommended path before any reset on a pre-v2.4.1 install (walks the upgrade flow). Also the entry point for re-adding the first project after `--nuclear`.
- `/rag-doctor` — verify post-reset state and diagnose any post-reset issues. Absorbs the former `/rag-status` and `/rag-repair`.
- `/rag-projects` — re-add additional projects after `--nuclear`
- `rules/state-detection.md` — canonical state-detection recipe used by the preamble
- `references/recovery-and-reset.md` — full reset/recovery source-of-truth
- `references/known-failures.md#f-001` — the v2.4.1 data-loss bug that drives the pre-v2.4.1 block
- `references/risks-and-constraints.md#syncthing--cloud-synced-config-directory` — sync risk on the data dir
