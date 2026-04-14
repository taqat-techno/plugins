---
description: Diagnose a ragtools symptom against the F-001..F-012 catalog and walk the matching repair playbook one step at a time with destructive-action gating
argument-hint: "[<free-text symptom>] | [--symptom F-NNN] | [--scan-logs]"
allowed-tools: Bash(curl:*), Bash(rag service:*), Bash(rag version:*), Bash(rag doctor:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Bash(tail:*), Bash(grep:*), Bash(netstat:*), Bash(lsof:*), Bash(tasklist:*), Bash(ps:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-repair

Diagnose a ragtools symptom against the F-001..F-012 failure catalog from `references/known-failures.md` and walk the matching playbook from `references/repair-playbooks.md` one step at a time. **Never auto-runs destructive steps** — every kill, delete, or unlock is a confirm-then-show-the-command moment.

## Behavior

**Three input modes:**
1. `/rag-repair <free text>` — classify free-text symptom against the catalog
2. `/rag-repair --symptom F-NNN` — skip classification, walk the named playbook directly
3. `/rag-repair --scan-logs` — invoke the `rag-log-scanner` agent on `service.log`, classify findings, then walk the most likely playbook

**Output discipline (D-008):**
- Mode banner first (same format as `/rag-status`)
- Classification result: one F-ID + confidence + matched evidence (≤ 4 lines)
- Playbook walkthrough: one step at a time, never the whole playbook in one dump
- Every destructive step is a confirm-then-show-command moment

## Required steps (perform in order)

### Step 0 — Mode detection

Reuse the Phase 2 mode-detection recipe from `/rag-status` Step 1–2. Print the mode banner. Service mode (`UP` / `DOWN` / `BROKEN`) matters because the F-010 special case depends on it.

### Step 1 — Classify the symptom

Pick exactly one of the three input modes:

#### Mode A — `--symptom F-NNN` (skip classification)

Validate that `F-NNN` is in the catalog (F-001 through F-012). If not, print `unknown failure ID — see references/known-failures.md for the full list` and stop.

Jump straight to **Step 2** with `failure_id = F-NNN, confidence = USER_SPECIFIED`.

#### Mode B — `--scan-logs` (use the log-scanner agent)

Resolve the log path from the mode banner. Then invoke the `rag-log-scanner` agent (Haiku-tier, defined in `agents/rag-log-scanner.md`) with the log path and the most recent 200 lines budget.

The agent returns JSON like:
```json
{"findings": [{"failure_id": "F-003", "line": 1421, "evidence": "Storage folder data/qdrant is already accessed by another instance of Qdrant client", "confidence": "high"}]}
```

If multiple findings, sort by confidence DESC then line number DESC (most recent first). Take the top finding. If no findings, fall back to **Mode C** with the user's free-text symptom (or ask them what they're seeing).

#### Mode C — Free-text symptom classification

Match the user's text against the rubric below. Each row has match patterns and a confidence level.

| F-ID | Match patterns (any) | Confidence |
|---|---|---|
| **F-001** | `permission denied.*ragtools.toml` / `projects disappear` / `Errno 13` + `ragtools.toml` | HIGH |
| **F-001** | `projects gone after restart` / `lost projects` (no other context) | MEDIUM |
| **F-002** | `MPS backend out of memory` / `MPS.*out of memory` | HIGH (note: pre-v2.4.2 only) |
| **F-002** | `apple metal` + `crash` / `oom` (no other context) | LOW |
| **F-003** | `is already accessed by another instance of Qdrant client` (exact substring) | **HIGH — strict matcher** |
| **F-003** | `qdrant.*locked` / `lock file` / `RuntimeError.*Qdrant` | HIGH |
| **F-004** | `watcher.*not running` / `watcher.*dead` / `watcher.*stopped` (and not `--scan-logs` finding F-005) | HIGH |
| **F-005** | `service.*won't start` / `service.*not starting` / `Application startup failed` | HIGH |
| **F-005** | `rag service start.*nothing happens` / `rag.exe.*exits` | MEDIUM |
| **F-006** | `Startup sync skipped: no projects configured` (exact) | HIGH |
| **F-006** | `projects empty after restart` (and service is UP) | HIGH |
| **F-006** | `add a project but it's gone after restart` | MEDIUM |
| **F-007** | `indexing.*slow` / `indexing.*stuck` / `index.*hangs` / `not finishing` | HIGH |
| **F-008** | `port.*21420` + `(in use|already bound|EADDRINUSE)` | HIGH |
| **F-008** | `admin panel.*won't load` + service is reachable on a different port | MEDIUM |
| **F-009** | `MCP.*not connecting` / `claude code.*MCP.*fail` / `rag-mcp.*broken` | HIGH |
| **F-010** | `Collection NOT FOUND` + `service is up` (BOTH MUST HOLD) | **HIGH — and this is NOT a bug** |
| **P-RULE** | `claude doesn't use the MCP` / `claude says no info but data is there` / `rag mcp not used` / `why didn't claude search` | HIGH — plugin behavior, not a ragtools F-ID |
| **P-RULE** | `CLAUDE.md rule missing` / `retrieval rule not installed` | HIGH — plugin behavior |
| **P-DEDUPE** | `duplicate MCP` / `two ragtools entries` / `mcp registered twice` | HIGH — plugin behavior |
| **P-DEDUPE** | `.claude.json has ragtools` + plugin installed | HIGH — plugin behavior |

**Plugin-behavior IDs (P-NNN)** are separate from ragtools product failures (F-NNN). They classify things the plugin itself needs to fix — not things wrong with the ragtools product. Currently two P-IDs exist:

- **P-RULE** — the CLAUDE.md retrieval rule is missing or outdated. Resolution: `/rag-config claude-md install`. Source: D-016. No playbook walk — single-command fix.
- **P-DEDUPE** — duplicate `ragtools` MCP registrations in user-level configs conflicting with the plugin-level `.mcp.json`. Resolution: `/rag-config mcp-dedupe clean`. Source: D-015. No playbook walk — single-command fix.

Both P-IDs are **confirm-then-delegate** — this command does not implement the fix itself; it points the user at `/rag-config` for the actual edit.

**Critical disambiguation rules:**

1. **F-010 vs F-003.** If the user says "Collection NOT FOUND" AND the mode banner from Step 0 shows `service mode: UP`, classify as **F-010 (NOT a bug)**, not F-003. F-010 is expected behavior when `rag doctor` runs against a service holding the Qdrant lock. **Do not** walk the F-003 playbook in this case — instead, explain the lock contention and recommend `/rag-status` (which talks to the running service via HTTP and won't see the lock issue).

2. **F-003 strict matcher.** Only classify as F-003 (HIGH) if the user pastes the exact substring `is already accessed by another instance of Qdrant client`, OR if the mode banner shows the service is DOWN and the user is trying to start it. Vague "qdrant lock" without service state context is MEDIUM at most.

3. **F-002 is fixed in v2.4.2.** If the user is on ≥ v2.4.2 and pastes an MPS error, this is unexpected — recommend re-checking `references/risks-and-constraints.md#macos-mps-must-stay-disabled` and filing an upstream issue.

4. **F-006 vs F-001.** Both involve "projects gone". F-006 is a config-load failure (config not found at expected path); F-001 is a config-write failure (the v2.4.1 bug). Use the version: pre-v2.4.1 → F-001; ≥ v2.4.1 → F-006.

5. **No match.** If nothing matches HIGH or MEDIUM, do NOT guess. Print `could not classify symptom against F-001..F-012 or P-RULE/P-DEDUPE`, list the closest 2 candidates with confidence LOW, and recommend `/rag-doctor --logs` to gather more evidence.

6. **P-RULE and P-DEDUPE are plugin-behavior IDs, not ragtools F-IDs.** They do NOT walk a playbook — they route to a single `/rag-config` subcommand. Do not try to classify a plugin-behavior symptom as an F-NNN, and do not try to walk an F-NNN playbook for a plugin-behavior symptom. The two namespaces are separate on purpose.

### Step 2 — Render classification result

Compact format for F-NNN:
```
mode banner (5–7 lines from Step 0)

classification: F-NNN (<HIGH|MEDIUM|LOW> confidence)
  evidence: <user phrase or log substring or --symptom flag>
  see: references/known-failures.md#f-NNN
  playbook: references/repair-playbooks.md#<anchor>
```

Compact format for P-NNN (plugin-behavior):
```
mode banner

classification: P-RULE (HIGH confidence — plugin behavior, not a ragtools F-ID)
  evidence: <user phrase>
  cause: the CLAUDE.md retrieval rule is not installed, so Claude doesn't know when to call the MCP
  fix:   /rag-config claude-md install
  see:   ../../docs/decisions.md#d-016
```

```
classification: P-DEDUPE (HIGH confidence — plugin behavior, not a ragtools F-ID)
  evidence: <user phrase>
  cause: duplicate ragtools MCP registrations in user-level configs conflicting with plugin-level .mcp.json
  fix:   /rag-config mcp-dedupe clean
  see:   ../../docs/decisions.md#d-015
```

If the user wants more context before walking (F-NNN) or running the fix (P-NNN), they can read the references directly. Otherwise:
- **F-NNN:** ask `walk the playbook? (yes/no)`.
- **P-NNN:** ask `run the fix? (yes/no)` — a yes invokes the corresponding `/rag-config` subcommand with the confirmation gates already built into that command. No playbook walk.

If they say no, stop. If yes:
- F-NNN → proceed to Step 3 (walk the playbook)
- P-NNN → tell the user to run the `/rag-config` subcommand themselves; do NOT auto-invoke another slash command from inside `/rag-repair`. The user retains control.

### Step 3 — Walk the playbook (one step at a time)

Each playbook from `references/repair-playbooks.md` has 4–7 numbered steps. Walk them **one step at a time**. Never dump all steps in one message. After each step, ask `done? (yes / failed / skip)` and act on the answer.

The 8 playbooks and their critical confirmation gates:

#### Playbook P-svc — `service-will-not-start` (F-005)

1. Read the log: `tail -n 50 <log-path>`. Look for `ERROR` / `Traceback`.
2. If `is already accessed by another instance` → re-classify as F-003 and switch to P-qdrant.
3. If model load error → recommend reinstall (`references/install.md`); bundle is corrupt.
4. Try foreground: `rag service run`.
5. Run `rag doctor` to check the layer below the service.

**No destructive steps.** All read-only diagnostics.

#### Playbook P-qdrant — `qdrant-already-accessed` (F-003)

1. **Confirmation gate 1:** `rag service stop` — no destructive flag, but ask "stop the service? (yes/no)".
2. **Confirmation gate 2:** Check for zombie processes:
   - Windows: `tasklist | findstr rag.exe` (read-only, just shows them)
   - macOS/Linux: `ps aux | grep rag` (read-only)
   - Show output, then ask: `kill PID <pid>? type the PID number to confirm` — user must type the actual PID, not just "yes". This is a destructive action.
3. **Confirmation gate 3:** Stale PID file removal:
   - Show: `%LOCALAPPDATA%\RAGTools\service.pid` (Windows) or platform equivalent
   - Ask: `delete stale PID file? type DELETE to confirm`
4. **Confirmation gate 4:** Qdrant lock file removal:
   - Show: `%LOCALAPPDATA%\RAGTools\data\qdrant\.lock`
   - **Critical safety check:** verify NO `rag.exe` processes are still running before suggesting this. Re-run `tasklist | findstr rag.exe`. If anything matches, refuse and tell the user to kill those first.
   - Ask: `delete the Qdrant lock file? type DELETE to confirm`
5. Restart: `rag service start`.

**Critical safety rule:** **never** suggest deleting the Qdrant **data directory** (`data/qdrant/`) in this playbook. Only the `.lock` file. Deleting the data directory wipes the index — that's `/rag-reset --data` territory, not repair.

#### Playbook P-perm — `add-project-permission-denied` (F-001)

1. Read `rag version`. If pre-v2.4.1 → strongly recommend `/rag-upgrade` first.
2. If on ≥ v2.4.1 → this should not happen; classify as UNCLASSIFIED and recommend `/rag-doctor --logs`.
3. Workaround for users who can't upgrade:
   - Stop the service: `rag service stop`
   - Manually create `%LOCALAPPDATA%\RAGTools\config.toml` with project entries (show the schema from `references/configuration.md`)
   - Restart: `rag service start`
4. Verify: `curl http://127.0.0.1:21420/api/projects`

**Confirmation gate:** the manual `config.toml` create step asks `proceed with manual config? (yes/no)`. Stopping the service is asked-before-acted.

#### Playbook P-empty — `projects-empty-after-restart` (F-006)

1. Confirm via API: `curl http://127.0.0.1:21420/api/projects` — should return `[]`.
2. Check log for `Startup sync skipped: no projects configured`.
3. Verify config exists at the resolved path (from mode banner).
4. Compare contents: does it have `[[projects]]` sections?
5. **Confirmation gate (F-006a stale-CWD check):** look for stray `ragtools.toml` in CWD-adjacent dirs (`C:\Windows\System32\`, user home, install dir). If found:
   - Show the path
   - Ask: `move <stray-path> to <canonical-path>? (yes/no)` — destructive on `<stray-path>` (it gets moved away)
   - **Always offer backup-first**: append `.bak` instead of overwriting.
6. Restart and verify: `curl /api/projects`.

**Syncthing/cloud-sync warning:** if the resolved config path is inside a known synced directory (Syncthing `.stfolder`, iCloud `Mobile Documents`, OneDrive, Dropbox), warn loudly per `references/risks-and-constraints.md#syncthing--cloud-synced-config-directory`. Recommend moving config out of the synced dir.

#### Playbook P-slow — `indexing-slow-or-stuck` (F-007)

1. Check the activity log via admin panel or `curl /api/activity`.
2. Check CPU usage of `rag.exe`. **Sustained high CPU = working, not stuck** (encoder is CPU-bound by design — `risks-and-constraints.md#macos-mps-must-stay-disabled`).
3. For very large projects, expect minutes for full index. Patience.
4. If watcher firing too often during edits: `rag watch . --debounce 5000`.
5. If truly hung (no CPU, no log progress for several minutes), **escalate to `/rag-reset --soft`** (rebuild). That's a separate command (Phase 7+).

**No confirmation gates here** — read-only diagnosis.

#### Playbook P-port — `admin-panel-port-collision` (F-008)

1. Identify conflicting process:
   - Windows: `netstat -ano | findstr 21420`
   - macOS/Linux: `lsof -i :21420`
2. Decide: kill the conflicting process, OR change the rag service port.
3. **Confirmation gate (kill path):** show the conflicting PID and ask `kill PID <pid>? type the PID number to confirm`. Same discipline as P-qdrant.
4. **Port change path:** set `RAG_SERVICE_PORT=21421` (or another free port) or edit `config.toml` → `service_port`. Restart required.

#### Playbook P-watcher — `watcher-not-running` (F-004)

1. `curl http://127.0.0.1:21420/api/watcher/status` — check `running` field.
2. If `false`, start it: `curl -X POST http://127.0.0.1:21420/api/watcher/start`.
3. Check log for watcher errors. Auto-restart with exponential backoff (5 retries, 5s–80s) is built in v2.4+.
4. Verify project paths exist (watcher skips nonexistent paths and logs a warning).

**No destructive steps.** All read or HTTP API ops.

#### Playbook P-mcp — `mcp-not-connecting` (F-009)

1. Service running? `rag service status`.
2. Check `.mcp.json` — is `command` correct? Compare against `curl /api/mcp-config` (canonical source).
3. Claude Code logs: see `~/.claude/logs/`.
4. Try direct launch: `rag-mcp` or `rag serve` in a terminal — should block on stdio. That confirms it launched.
5. Verify stdio is clean (no `print()` to stdout).

**Confirmation gate:** if `.mcp.json` needs to be rewritten (current command differs from `/api/mcp-config`), show the diff and ask `overwrite .mcp.json? (yes/no)`.

### Step 4 — Final state check

After the playbook walkthrough completes (or the user stops), re-run mode detection from Step 0. Print the new mode banner. Compare with the starting banner: did anything change? If the symptom is gone, congratulate briefly and stop. If the symptom persists, recommend `/rag-doctor --logs` for deeper investigation.

## Confirmation discipline (binding rules)

Every destructive step in this command **must** match one of these patterns:

| Action class | Confirmation requirement |
|---|---|
| Kill a process | User types the actual PID number |
| Delete a file (PID, lock, stray config) | User types `DELETE` verbatim |
| Move a file (stale config rescue) | User confirms `yes` AND the original is backed up to `.bak` |
| Stop the service | User confirms `yes` |
| Modify `config.toml` directly | **Refused unless the v2.4.1 workaround flow.** Always prefer HTTP API. |
| Delete the Qdrant data directory | **REFUSED in this command.** That's `/rag-reset --data` territory. |
| Delete the entire RAGTools dir | **REFUSED in this command.** That's `/rag-reset --nuclear` territory. |
| Modify `.mcp.json` | User confirms `yes` after seeing the diff |

**No silent destructive actions. Ever.**

## Failure handling

| Situation | Behavior |
|---|---|
| Free-text symptom matches no rules | Print "could not classify", list closest LOW candidates, recommend `--scan-logs` |
| `--symptom F-NNN` is invalid | Print "unknown failure ID — see references/known-failures.md" and stop |
| `--scan-logs` finds zero matches | Tell user "no known failure patterns in the last 200 lines"; ask for free-text symptom |
| User pastes a stack trace not matching any rule | Tag UNCLASSIFIED, recommend reading `references/known-failures.md` and the most recent `service.log` lines |
| User wants to skip a confirmation gate | **Refuse.** Confirmation gates are not optional. Print the rationale and stop. |
| User confirms but the action fails | Show the error, do NOT proceed to the next step automatically. Ask for guidance. |

## Boundary reminders

- **Do NOT call any MCP tool** (D-001). Repair never goes through the MCP layer.
- **Do NOT edit `config.toml`** except in the F-001 workaround flow, and even then only with explicit user confirmation. The v2.4.1 bug is the reason.
- **Do NOT delete the Qdrant data directory.** Only `.lock`. Data deletion is `/rag-reset` territory.
- **Do NOT confuse F-010 with F-003.** F-010 is expected behavior when `rag doctor` runs against a live service. Always check service mode before classifying.
- **Do NOT auto-run any destructive step.** Every kill/delete/move requires a confirmation typed verbatim.
- **Compact-by-default** per D-008. One playbook step per message.

## See also

- `/rag-status` — verify service state before and after repair
- `/rag-doctor` — structured health check; complements `/rag-repair`
- `/rag-reset` — destructive escalation when repair isn't enough (Phase 7)
- `references/known-failures.md` — F-001..F-012 catalog
- `references/repair-playbooks.md` — full playbook source
- `references/logs-and-diagnostics.md` — log substring catalog
- `references/risks-and-constraints.md` — Qdrant lock invariant, Syncthing risk
- `agents/rag-log-scanner.md` — Haiku log-scanner agent invoked by `--scan-logs`
