---
description: Smart ragtools diagnose. Detects install and service state, runs the right probe, classifies findings against F-001..F-012 + P-RULE/P-DEDUPE, and optionally walks the repair playbook inline. Absorbs the former /rag-status and /rag-repair commands (v0.4.0).
argument-hint: "[<free-text symptom>] [--full] [--symptom F-NNN] [--logs] [--fix] [--verbose]"
allowed-tools: Bash(curl:*), Bash(rag doctor:*), Bash(rag version:*), Bash(rag service:*), Bash(where rag:*), Bash(which rag:*), Bash(test:*), Bash(tail:*), Bash(grep:*), Bash(netstat:*), Bash(lsof:*), Bash(tasklist:*), Bash(ps:*), Bash(printenv:*), Bash(echo:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.4.0
---

# /rag-doctor

Smart, state-aware diagnose-and-repair entry point for ragtools. **One command** handles what used to be split across `/rag-status`, `/rag-doctor`, and `/rag-repair`. Branches on the detected state so it behaves correctly whether ragtools is missing, broken, half-configured, or perfectly healthy.

## Behavior by state (routing table)

| Detected state | What /rag-doctor does |
|---|---|
| **not-installed** | Print the mode banner with `not-installed` label and a single line: `ragtools is not installed. run /rag-setup to install.` Stop. No probes, no findings, no playbook walks. |
| **installed, service DOWN** | Mode banner + CLI-direct-mode read-only probes (`rag version`, `rag service status`). Classify any errors. Recommend `rag service start`. If `--full` was passed, also run `rag doctor` in CLI direct mode (it takes the Qdrant lock, which is safe because no other process holds it). |
| **installed, service STARTING** | Mode banner + "service is starting — encoder load ~5–10s" note. Re-probe once after 2s. If still STARTING, print the state and stop — do not run destructive probes against a loading service. |
| **installed, service BROKEN** (500/hang) | Mode banner + `[ERROR] service is broken` finding tagged against **F-005**. Offer to walk the P-svc playbook inline if `--fix` was passed. |
| **installed, service UP, all green** | Mode banner + compact state table (version / projects / files / chunks / watcher) + plugin-level assertions (CLAUDE.md rule, MCP registrations). One-line summary: `✓ all checks passed` if nothing is wrong. This is what the former `/rag-status` printed. |
| **installed, service UP, unhealthy** | Mode banner + state table + findings block with each finding tagged against F-001..F-012 or P-RULE/P-DEDUPE. Each finding has a remediation line. If `--fix` was passed and exactly one HIGH-confidence finding exists, walk its playbook inline. |
| **installed, service UP, old version** | Everything above + an `[INFO] upgrade available v<X> → v<Y>` row in the findings block (only if the command fetched `latest_version`). Recommend `/rag-setup` to walk the upgrade. Does NOT auto-walk upgrades from `/rag-doctor`. |
| **free-text symptom passed** | `/rag-doctor "projects disappeared after restart"` → classify the symptom against the F-001..F-012 + P-RULE/P-DEDUPE rubric, emit the top match, offer the playbook walk. This replaces the old `/rag-repair <text>` entry point. |
| **--symptom F-NNN passed** | Skip classification. Go straight to the named playbook. Same behavior as the old `/rag-repair --symptom F-NNN`. |
| **--logs passed** | Resolve the log path, invoke the `rag-log-scanner` Haiku agent on the last 200 lines, fold its findings into the findings block. If `--fix` is also set, walk the top-confidence finding's playbook inline. |

## Modes (command-line flags)

- `/rag-doctor` — **default mode.** Fast state probe (~400ms). Absorbs the former `/rag-status`. Best entry point for "what's going on with ragtools?"
- `/rag-doctor --full` — **deep diagnose.** Wraps `rag doctor` and classifies every row against F-001..F-012. Replaces the former standalone `/rag-doctor`. Takes several seconds because `rag doctor` walks the dependency tree.
- `/rag-doctor <free-text>` — **symptom classification.** Matches the user's text against the F-001..F-012 + P-RULE/P-DEDUPE rubric (20 rows with disambiguation rules). Replaces the former `/rag-repair <text>`.
- `/rag-doctor --symptom F-NNN` — **jump to a playbook.** Skip classification. Replaces the former `/rag-repair --symptom F-NNN`.
- `/rag-doctor --logs` — **log scan.** Invokes the `rag-log-scanner` Haiku agent. Replaces the former `/rag-repair --scan-logs` and `/rag-doctor --logs`.
- `/rag-doctor --fix` — **walk the playbook inline.** Combine with any of the above. After classification, if exactly one HIGH-confidence finding exists, walk its playbook one step at a time with typed confirmation gates. This was formerly a separate `/rag-repair` invocation.
- `/rag-doctor --verbose` — **expand output.** Adds full raw `rag doctor` output, the environment dump, and un-truncated log tails. Composes with the other flags.

Compact-by-default per D-008: ≤ 25 lines unless `--verbose` or a playbook walk is in progress.

## Step 0 — State detection

Follow the canonical recipe in `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Do NOT re-implement the probe. Produce the `state` object and print the 6-line mode banner verbatim. This is the first thing in the response.

If `state.install_mode == not-installed`, stop now with a single line:

```
ragtools is not installed. run /rag-setup to install.
```

No further steps. No probes. The user has nothing to diagnose.

## Step 1 — Dispatch on mode flags

Pick exactly one primary mode, in priority order:

1. `--symptom F-NNN` → go to **Mode A** (skip classification, walk named playbook).
2. `--logs` → go to **Mode B** (log scanner).
3. Positional free-text argument → go to **Mode C** (classify free-text symptom).
4. `--full` → go to **Mode D** (deep `rag doctor` wrap).
5. None of the above → **default fast probe** (Mode E).

`--fix` and `--verbose` are modifiers that compose with the primary mode.

---

## Mode E — Default fast probe (absorbs former /rag-status)

This is the most common entry point. A user types `/rag-doctor` with no args when they want "what state is ragtools in?"

### E.1 — When service is UP

Fetch state from the HTTP API in parallel:

```bash
curl --max-time 2 -s http://127.0.0.1:21420/api/status
curl --max-time 2 -s http://127.0.0.1:21420/api/projects
curl --max-time 2 -s http://127.0.0.1:21420/api/watcher/status
```

Extract `version`, `projects` count, total `files`, total `chunks`, `last_indexed`, watcher `running`, watched paths count, and per-project stats.

Render the state table (≤ 12 lines):

```
| Field         | Value                                  |
|---------------|----------------------------------------|
| Version       | ragtools v2.4.2                        |
| Projects      | 3 (3 enabled)                          |
| Files indexed | 1,247                                  |
| Chunks        | 8,912                                  |
| Last indexed  | 2 minutes ago                          |
| Watcher       | running, 3 paths                       |
```

If multiple projects, add a second small table capped at 5 rows with `+N more — use --verbose` if exceeded.

Run the **plugin-level assertions** — these are not from `rag doctor`, they are probed by this command directly (introduced in v0.2.0, v0.3.1, v0.3.3):

- `/rag-config claude-md status` → maps to `OK — INSTALLED v<N>` / `WARN — NOT INSTALLED` / `WARN — OUTDATED v<OLD>→v<NEW>` / `WARN — TARGET MISSING`
- `/rag-config mcp-dedupe status` → maps to `OK — 1 (plugin-level, canonical, schema OK)` / `WARN — <N+1> (plugin-level + <N> duplicates)` / `ERROR — plugin .mcp.json missing top-level 'ragtools' key` / `ERROR — plugin .mcp.json command '<cmd>' not on PATH` / `ERROR — plugin .mcp.json uses the legacy Python launcher`

An `ERROR` on the MCP registrations row is **always** more urgent than any WARN — it means ragtools MCP will not load at all.

Emit the findings block only if there are non-OK rows. If everything is green, print one line: `✓ all checks passed.` Stop.

### E.2 — When service is DOWN

Run CLI-direct-mode read-only probes:

```bash
rag version 2>&1
rag service status 2>&1
```

Do **NOT** run `rag index`, `rag rebuild`, `rag watch`, or anything that opens Qdrant for writing. The hook (`lock_conflict_check.py`) would block these anyway, but the command must not try them.

Print:
```
service down → started with: rag service start
```

If `rag version` itself fails, the binary is broken — classify as UNCLASSIFIED and recommend `--full --fix`.

### E.3 — When service is BROKEN

Print one line: `service returned 500 / hung. classified as F-005 (service will not start). run /rag-doctor --symptom F-005 --fix to walk the playbook.`

### E.4 — When service is STARTING

Print: `service is starting — encoder is loading (~5–10s). re-probe once in a moment or run /rag-doctor --full once it settles.`

---

## Mode D — Deep `rag doctor` wrap (absorbs former /rag-doctor --full)

### D.1 — Run `rag doctor`

```bash
rag doctor 2>&1
```

`rag doctor` prints a structured table: Python version, `qdrant-client`, `sentence-transformers`, `mcp`, `fastapi`, service status, data directory, state DB, collection, ignore rules.

### D.2 — Parse and classify

Walk the doctor output row by row. For each row, extract component / status / note. Classify non-OK rows against `references/known-failures.md`.

**Critical F-010 rule:** if `state.service_mode == UP` and `rag doctor` reports `Collection NOT FOUND`, tag this row as `[INFO] Collection NOT FOUND while service is up — expected (F-010)`. **Do not** route this to a playbook. F-010 is not a bug — it is lock contention between the doctor's own Qdrant client and the service that holds the lock.

Other non-OK rows:

| Doctor symptom | Failure ID | Playbook anchor |
|---|---|---|
| Python version too old | (no F-ID) | upgrade Python to ≥ 3.10 |
| `qdrant-client` not installed | (no F-ID) | reinstall ragtools |
| `sentence-transformers` not installed | (no F-ID) | reinstall ragtools |
| `mcp` not installed | (no F-ID) | reinstall ragtools |
| Data directory missing | (no F-ID) | reinstall, or check `RAG_DATA_DIR` |
| State DB corrupt | (no F-ID) | `references/recovery-and-reset.md#recovery-from-corrupted-qdrant-storage` |
| Service status `not running` (binary present) | F-005 | `repair-playbooks.md#service-will-not-start` |
| Service status `crashed` | F-005 | same |
| Collection error not matching F-010 | F-003 | `repair-playbooks.md#qdrant-already-accessed` |
| Ignore rules error | (no F-ID) | check `.ragignore` via `configuration.md` |

Unrecognized errors → `[UNCLASSIFIED]`, recommend `--logs`.

### D.3 — Render the doctor summary table

≤ 14 rows covering dependencies + service + data + plugin-level rows. Same format as the former `/rag-doctor` Step 5 rendering. See the classifier rubric above for what each status cell should say.

### D.4 — Emit findings block

One line per non-OK finding:
```
findings:
  [ERROR] Service status "not running" → /rag-doctor --symptom F-005 --fix
  [WARN]  CLAUDE.md rule missing → /rag-config claude-md install (D-016)
  [WARN]  MCP duplicate at ~/.claude.json → /rag-config mcp-dedupe clean (D-015)
```

Plugin-behavior findings (CLAUDE.md rule / MCP dedupe) are tagged with the D-NNN decision they trace to, not an F-NNN.

### D.5 — Footer

```
next: <recommended-action>
```

One of:
- `service is healthy — nothing to do`
- `start the service: rag service start`
- `walk the playbook: /rag-doctor --symptom F-NNN --fix`
- `scan the logs: /rag-doctor --logs`
- `install the CLAUDE.md rule: /rag-config claude-md install`
- `clean duplicate MCP registrations: /rag-config mcp-dedupe clean`
- `fix multiple issues: /rag-doctor --full --fix` (walks the top-confidence finding first)

---

## Mode C — Free-text symptom classification (absorbs former /rag-repair <text>)

Match the user's positional argument against the rubric below. Each row has a confidence level.

| F-ID | Match patterns (any) | Confidence |
|---|---|---|
| **F-001** | `permission denied.*ragtools.toml` / `projects disappear` / `Errno 13` + `ragtools.toml` | HIGH |
| **F-001** | `projects gone after restart` / `lost projects` (no other context) | MEDIUM |
| **F-002** | `MPS backend out of memory` / `MPS.*out of memory` | HIGH (note: pre-v2.4.2 only) |
| **F-002** | `apple metal` + `crash` / `oom` (no other context) | LOW |
| **F-003** | exact `is already accessed by another instance of Qdrant client` | **HIGH — strict matcher** |
| **F-003** | `qdrant.*locked` / `lock file` / `RuntimeError.*Qdrant` | HIGH |
| **F-004** | `watcher.*not running` / `watcher.*dead` / `watcher.*stopped` | HIGH |
| **F-005** | `service.*won't start` / `service.*not starting` / `Application startup failed` | HIGH |
| **F-005** | `rag service start.*nothing happens` / `rag.exe.*exits` | MEDIUM |
| **F-006** | exact `Startup sync skipped: no projects configured` | HIGH |
| **F-006** | `projects empty after restart` (and service is UP) | HIGH |
| **F-006** | `add a project but it's gone after restart` | MEDIUM |
| **F-007** | `indexing.*slow` / `indexing.*stuck` / `index.*hangs` / `not finishing` | HIGH |
| **F-008** | `port.*21420` + `(in use|already bound|EADDRINUSE)` | HIGH |
| **F-008** | `admin panel.*won't load` + service is reachable on a different port | MEDIUM |
| **F-009** | `MCP.*not connecting` / `claude code.*MCP.*fail` / `rag.*broken` | HIGH |
| **F-010** | `Collection NOT FOUND` + `service is up` (BOTH MUST HOLD) | **HIGH — and this is NOT a bug** |
| **P-RULE** | `claude doesn't use the MCP` / `claude says no info but data is there` / `why didn't claude search` | HIGH — plugin behavior |
| **P-RULE** | `CLAUDE.md rule missing` / `retrieval rule not installed` | HIGH — plugin behavior |
| **P-DEDUPE** | `duplicate MCP` / `two ragtools entries` / `mcp registered twice` | HIGH — plugin behavior |
| **P-DEDUPE** | `.claude.json has ragtools` + plugin installed | HIGH — plugin behavior |

### Disambiguation rules (binding)

1. **F-010 vs F-003.** If the user mentions "Collection NOT FOUND" AND `state.service_mode == UP`, classify as **F-010 (NOT a bug)**, not F-003. Explain the lock contention and recommend `/rag-doctor` (which hits the HTTP API and doesn't see the lock).
2. **F-003 strict matcher.** Only classify as F-003 (HIGH) if the user pastes the exact substring, OR if `service_mode == DOWN` and the user is trying to start it. Vague "qdrant lock" is MEDIUM at most.
3. **F-002 is fixed in v2.4.2.** If `state.version >= 2.4.2` and the user pastes an MPS error, recommend filing an upstream issue rather than walking the (obsolete) playbook.
4. **F-006 vs F-001.** Both involve "projects gone". Pre-v2.4.1 → F-001. ≥ v2.4.1 → F-006.
5. **No match.** Do not guess. Print `could not classify symptom against F-001..F-012 or P-RULE/P-DEDUPE`, list the closest 2 candidates with confidence LOW, and recommend `/rag-doctor --logs`.
6. **P-RULE and P-DEDUPE are plugin-behavior IDs, not ragtools F-IDs.** They do NOT walk a playbook — they route to a single `/rag-config` subcommand.

Render the classification result in compact form:
```
classification: F-NNN (<HIGH|MEDIUM|LOW> confidence)
  evidence: <user phrase>
  see: references/known-failures.md#f-NNN
  fix: /rag-doctor --symptom F-NNN --fix
```

If `--fix` was also passed, fall through to **Mode A** with the classified F-ID. Otherwise stop here — the user chooses whether to walk the playbook.

---

## Mode A — Walk a named playbook (absorbs former /rag-repair --symptom)

Validate that `F-NNN` is in F-001..F-012. If not, print `unknown failure ID — see references/known-failures.md` and stop.

Walk the matching playbook from `references/repair-playbooks.md` **one step at a time**. Never dump all steps in one message. After each step, ask `done? (yes / failed / skip)` and branch on the answer.

The 8 playbooks and their critical confirmation gates (unchanged from the former `/rag-repair`):

### P-svc — service will not start (F-005)

1. `tail -n 50 <log-path>` — look for `ERROR` / `Traceback`.
2. If `is already accessed by another instance` → re-classify as F-003 and switch to P-qdrant.
3. If model load error → reinstall recommended.
4. `rag service run` (foreground).
5. `rag doctor` to check the layer below.

No destructive steps.

### P-qdrant — qdrant already accessed (F-003)

1. **Gate 1 — stop service:** `rag service stop` — ask `stop the service? (yes/no)`.
2. **Gate 2 — show zombies:** `tasklist | findstr rag.exe` (Windows) / `ps aux | grep rag` (POSIX). Show output, ask `kill PID <pid>? type the PID number to confirm` — user must type the actual PID.
3. **Gate 3 — stale PID file:** show `%LOCALAPPDATA%\RAGTools\service.pid`. Ask `delete stale PID file? type DELETE to confirm`.
4. **Gate 4 — Qdrant lock file:** show `%LOCALAPPDATA%\RAGTools\data\qdrant\.lock`. **Safety check:** re-run the tasklist probe; refuse if anything matches. Ask `delete the Qdrant lock file? type DELETE to confirm`.
5. `rag service start`.

**Critical safety rule:** never suggest deleting the Qdrant **data directory** in this playbook. That is `/rag-reset --data` territory.

### P-perm — add-project permission denied (F-001)

1. `rag version`. If pre-v2.4.1 → strongly recommend `/rag-setup` (which walks the upgrade flow).
2. If ≥ v2.4.1 → unclassified; recommend `--logs`.
3. Workaround if user can't upgrade: stop service, manually create `%LOCALAPPDATA%\RAGTools\config.toml` with project entries. **Gate:** `proceed with manual config? (yes/no)`.
4. Verify: `curl /api/projects`.

### P-empty — projects empty after restart (F-006)

1. Confirm via API: `curl /api/projects` — should return `[]`.
2. Check log for `Startup sync skipped: no projects configured`.
3. Verify config exists at resolved path.
4. Compare contents — does it have `[[projects]]` sections?
5. **Gate — F-006a stale-CWD check:** look for stray `ragtools.toml` in `C:\Windows\System32\`, user home, install dir. If found: show path, ask `move <stray> to <canonical>? (yes/no)`. Always offer backup-first (`.bak` append).
6. Restart and verify.

**Syncthing/cloud-sync warning:** if the resolved config path is inside a synced dir, warn loudly per `references/risks-and-constraints.md`.

### P-slow — indexing slow or stuck (F-007)

1. Check activity log via admin panel or `curl /api/activity`.
2. CPU usage of `rag.exe`. Sustained high CPU = working, not stuck (encoder is CPU-bound by design).
3. Large projects expect minutes. Patience.
4. Watcher too eager during edits: `rag watch . --debounce 5000`.
5. Truly hung (no CPU, no log progress) → escalate to `/rag-reset --soft`.

Read-only. No gates.

### P-port — admin panel port collision (F-008)

1. Identify: `netstat -ano | findstr 21420` (Windows) / `lsof -i :21420` (POSIX).
2. Decide: kill conflicting process OR change rag port.
3. **Gate — kill path:** `kill PID <pid>? type the PID number to confirm`.
4. **Port change path:** set `RAG_SERVICE_PORT=21421` or edit `config.toml` → `service_port`. Restart required.

### P-watcher — watcher not running (F-004)

1. `curl /api/watcher/status`.
2. If `running: false`, `curl -X POST /api/watcher/start`.
3. Check log for watcher errors. Auto-restart with exponential backoff is built into v2.4+.
4. Verify project paths exist.

No destructive steps.

### P-mcp — MCP not connecting (F-009)

1. Service running? `rag service status`.
2. Check `.mcp.json` — is `command` correct? Compare against `curl /api/mcp-config` (canonical source).
3. Claude Code logs: `~/.claude/logs/`.
4. Try direct launch: `rag serve` in a terminal — should block on stdio.
5. Verify stdio purity (no stray `print()` to stdout).

**Gate:** if `.mcp.json` needs rewriting, show diff, ask `overwrite .mcp.json? (yes/no)`.

**Note (v0.4.0):** this playbook no longer applies to plugin-level MCP wiring on rag-plugin v0.3.3+ — the plugin spawns `rag serve` directly from a flat-shape `.mcp.json` (see D-020). The playbook remains relevant for project-level or user-level `.mcp.json` wired manually by the user.

## Final state check

After the playbook walk completes (or the user stops), re-run **Step 0 — state detection** and print the new mode banner. Compare with the starting banner — did anything change? If the symptom is gone, congratulate briefly. If it persists, recommend `--logs`.

---

## Mode B — Log scanner (absorbs former /rag-repair --scan-logs and /rag-doctor --logs)

Resolve the log path from the state object. Invoke the `rag-log-scanner` Haiku agent (defined in `agents/rag-log-scanner.md`) with the log path and a 200-line budget.

The agent returns JSON:
```json
{"findings": [{"failure_id": "F-003", "line": 1421, "evidence": "Storage folder data/qdrant is already accessed by another instance of Qdrant client", "confidence": "high"}]}
```

Sort findings by confidence DESC then line number DESC (most recent first). Fold them into the findings block:

```
findings (from service.log, last 200 lines):
  [F-003 HIGH] line 1421: Storage folder data/qdrant is already accessed by another instance of Qdrant client
```

Cap at 10 findings in compact mode.

If `--fix` was also passed and there is exactly one HIGH-confidence finding, fall through to **Mode A** with that F-ID. If there are multiple HIGH findings, list them and ask which to walk first. If there are zero HIGH findings, print the list and recommend free-text symptom mode.

---

## Confirmation discipline (binding)

Every destructive step in Mode A / playbook walks must match one of these patterns:

| Action class | Confirmation requirement |
|---|---|
| Kill a process | user types the actual PID number |
| Delete a file (PID, lock, stray config) | user types `DELETE` verbatim |
| Move a file (stale config rescue) | user confirms `yes` AND original is backed up to `.bak` |
| Stop the service | user confirms `yes` |
| Modify `config.toml` directly | **refused unless F-001 workaround flow.** Prefer HTTP API. |
| Delete Qdrant data directory | **refused.** That's `/rag-reset --data` territory. |
| Delete entire RAGTools dir | **refused.** That's `/rag-reset --nuclear` territory. |
| Modify `.mcp.json` | user confirms `yes` after seeing the diff |

**No silent destructive actions. Ever.**

## Failure handling

| Situation | Behavior |
|---|---|
| `state.install_mode == not-installed` | One-line refusal + pointer at `/rag-setup`. Stop. |
| `rag doctor` not found when `--full` was asked | Print `not-installed` banner, recommend `/rag-setup`. |
| `rag doctor` returns non-zero with no parseable output (`--full`) | Print raw output truncated to 30 lines, tag `[UNCLASSIFIED]`, recommend `--logs`. |
| Free-text symptom matches no rules (Mode C) | Print "could not classify", list closest LOW candidates, recommend `--logs`. |
| `--symptom F-NNN` invalid | Print "unknown failure ID", stop. |
| `--logs` finds zero matches | "no known failure patterns in last 200 lines"; ask for free-text. |
| `--fix` with zero HIGH-confidence findings | Refuse — recommend `--logs` or free-text. |
| `--fix` with multiple HIGH findings | List them, ask which to walk first. |
| User skips a confirmation gate | Refuse. Gates are not optional. |
| Service goes DOWN mid-walk | Re-run Step 0; if still down, offer `rag service start`. |

## Boundary reminders

- **Do NOT call any MCP tool** (D-001).
- **Do NOT edit `config.toml`** except in the F-001 workaround flow with explicit gate.
- **Do NOT delete the Qdrant data directory.** Only `.lock`.
- **Do NOT confuse F-010 with F-003.** Always check service mode.
- **Do NOT auto-run destructive steps.** Every kill/delete/move requires a typed confirmation.
- **Do NOT re-implement state detection.** Reference `rules/state-detection.md`.
- **Compact by default** per D-008.

## See also

- `/rag-setup` — install / upgrade / verify (absorbs the former `/rag-upgrade`)
- `/rag-projects` — project CRUD via HTTP API
- `/rag-reset` — destructive reset with three escalation levels
- `/rag-config` — plugin-layer config: telemetry, claude-md rule, mcp-dedupe, hook-observability
- `rules/state-detection.md` — canonical state-detection recipe
- `references/known-failures.md` — F-001..F-012 catalog
- `references/repair-playbooks.md` — full playbook source
- `references/logs-and-diagnostics.md` — log substring catalog
- `references/risks-and-constraints.md` — Qdrant lock invariant, Syncthing risk
- `agents/rag-log-scanner.md` — Haiku log-scanner agent invoked by `--logs`
