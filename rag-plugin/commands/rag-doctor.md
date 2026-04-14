---
description: Run rag doctor, classify findings against known failure modes, summarize compactly with next-step playbook links
argument-hint: "[--verbose] [--logs]"
allowed-tools: Bash(rag doctor:*), Bash(rag version:*), Bash(rag service status:*), Bash(curl:*), Bash(where rag:*), Bash(which rag:*), Bash(tail:*), Bash(test:*), Read
disable-model-invocation: false
author: TaqaTechno
version: 0.1.0
---

# /rag-doctor

Wraps `rag doctor` with classification, failure-mode mapping, and compact output. Use when `/rag-status` reports a problem, or as a first deep diagnostic when something is wrong.

## Behavior

**Compact mode (default)** — ≤ 25 lines:
1. Mode banner (same format as `/rag-status`).
2. `rag doctor` summary table: dependency / status / note.
3. Findings block: 0–N lines, each formatted as `[<severity>] <issue> → see <playbook anchor>`.
4. One-line next-step recommendation.

**`--verbose` mode** — adds the full raw `rag doctor` output and the runtime environment dump.

**`--logs` mode** — additionally tails the last 50 lines of `service.log`, scans for known error substrings (from `references/logs-and-diagnostics.md`), and adds matched lines to the findings block.

## Required steps (perform in order)

### Step 1 — Mode detection

Run the same install-mode and service-mode detection as `/rag-status` (steps 1 and 2). Reuse the mode banner format. **Do not re-implement** — if `/rag-status` is the canonical detector, this command should produce identical banners.

### Step 2 — Run `rag doctor`

```bash
rag doctor 2>&1
```

`rag doctor` prints a structured table of: Python version, dependencies (qdrant-client, sentence-transformers, mcp, fastapi, etc.), service status, data directory, state DB, collection, ignore rules.

### Step 3 — Parse and classify

Walk the doctor output line by line. For each row, extract the component name, status (`OK` / `MISSING` / `ERROR` / `NOT FOUND` / `WARN`), and any note.

**Critical classification rule (F-010):** if the service is UP (per step 1's `/health` probe) and `rag doctor` reports `Collection NOT FOUND`, this is **NOT a bug**. It's expected lock contention — the doctor opens its own Qdrant client which can't read the locked directory while the service holds the lock. Tag this row as `[INFO] Collection NOT FOUND while service is up — expected (F-010)`. **Do not** route this to a repair playbook.

For all other non-OK rows, classify against `references/known-failures.md`:

| Doctor symptom | Failure ID | Playbook anchor |
|---|---|---|
| Python version too old | (no F-ID) | suggest upgrade to ≥ 3.10 |
| `qdrant-client` not installed | (no F-ID) | reinstall ragtools (`references/install.md`) |
| `sentence-transformers` not installed | (no F-ID) | reinstall ragtools |
| `mcp` not installed | (no F-ID) | reinstall ragtools |
| Data directory missing | (no F-ID) | reinstall, or check `RAG_DATA_DIR` env var |
| State DB corrupt | (no F-ID) | `references/recovery-and-reset.md#recovery-from-corrupted-qdrant-storage` |
| Service status `not running` (and binary present) | F-005 | `references/repair-playbooks.md#service-will-not-start` |
| Service status `crashed` | F-005 | `references/repair-playbooks.md#service-will-not-start` |
| Collection error not matching F-010 | F-003 | `references/repair-playbooks.md#qdrant-already-accessed` |
| Ignore rules error | (no F-ID) | check `.ragignore` syntax via `references/configuration.md` |

For **unrecognized errors**, do NOT guess a failure ID. Tag as `[UNCLASSIFIED]` and recommend reading `references/known-failures.md` and the most recent `service.log` lines.

### Step 4 — When `--logs` is set: scan `service.log`

Resolve the log path from the mode banner:
- Windows packaged: `%LOCALAPPDATA%\RAGTools\logs\service.log`
- macOS packaged: `~/Library/Application Support/RAGTools/logs/service.log`
- Dev mode: `./data/logs/service.log`

```bash
tail -n 50 "<resolved-log-path>" 2>/dev/null
```

Scan for the substrings from `references/logs-and-diagnostics.md`:

| Substring | Tag |
|---|---|
| `Storage folder data/qdrant is already accessed by another instance of Qdrant client` | F-003 — Qdrant lock |
| `ERROR: Application startup failed. Exiting.` | F-005 — startup failure |
| `Failed to auto-register startup task (non-fatal)` | INFO — ignore |
| `Startup sync skipped: no projects configured` | F-006 — config didn't load |
| `MPS backend out of memory` | F-002 — pre-v2.4.2 only; recommend upgrade |
| `HuggingFace unauthenticated warning` | INFO — cosmetic, ignore |

Append matched lines (with line numbers) to the findings block. **Cap at 10 matched lines** in compact mode to honor D-008.

### Step 5 — Render compact output

**Mode banner** (same as `/rag-status`).

**Doctor summary table** (≤ 12 lines):

```
| Component             | Status      | Note                          |
|-----------------------|-------------|-------------------------------|
| Python                | OK          | 3.12.4                        |
| qdrant-client         | OK          | 1.12.2                        |
| sentence-transformers | OK          | 3.0.1                         |
| mcp                   | OK          | 1.26.0                        |
| fastapi               | OK          | 0.115.0                       |
| Service               | OK          | running on 127.0.0.1:21420    |
| Data directory        | OK          | %LOCALAPPDATA%\RAGTools\data  |
| State DB              | OK          | 1247 files tracked            |
| Collection            | INFO        | NOT FOUND (expected, F-010)   |
| Ignore rules          | OK          | 3 layers active               |
```

If everything is OK and the only `INFO` row is F-010, print a single-line summary: `✓ All checks passed. Collection NOT FOUND is expected when the service is running.` (Plus the mode banner above.)

**Findings block** (only if there are non-OK, non-F-010 issues):

```
findings:
  [ERROR] Service status "not running" → see references/repair-playbooks.md#service-will-not-start (F-005)
  [WARN]  State DB has 0 files tracked → run `rag rebuild` or check projects via /rag-status
```

**Footer** (one line):

```
next: <recommended-action>
```

Where `<recommended-action>` is one of:
- `service is healthy — nothing to do` (all green, F-010 only INFO)
- `start the service: rag service start` (service down)
- `walk the playbook: see references/repair-playbooks.md#<anchor>` (specific failure ID matched)
- `read recent logs: /rag-doctor --logs` (unclassified errors)
- `run /rag-status for a fuller state picture` (no findings, but user wanted more)

### Step 6 — `--verbose` extras (only if requested)

Append:
- Full raw `rag doctor` output (collapsed under heading)
- Resolved environment: all `RAG_*` env vars
- Platform info (`uname -a` / `ver`)
- If `--logs` was also set, the full 50-line tail (not just matched lines)

## Failure handling

- **`rag doctor` not found** → binary is missing or not on PATH. Print mode banner with `not-installed` label and recommend `/rag-setup`.
- **`rag doctor` returns non-zero with no parseable output** → print the raw output (truncated to 30 lines), tag `[UNCLASSIFIED]`, recommend reading `references/known-failures.md`.
- **Service is DOWN** during step 1 → `rag doctor` will run in CLI direct mode, take the Qdrant lock, and report a clean collection. **This is fine** because no other process holds the lock. Note this in the banner: `service mode: DOWN (rag doctor running in direct mode)`.
- **Log file missing in `--logs` mode** → skip the log-scan step with a note: `log file not found at <path> — service may have never run`.

## Boundary reminders

- Do **not** call any MCP tool (D-001). This command is for diagnostics, not search.
- Do **not** edit `config.toml` (D-002).
- Do **not** auto-run `rag rebuild` or any destructive remediation. This command **diagnoses**; the user runs the fix manually or via `/rag-repair` (Phase 4+).
- Do **not** dump full log files in compact mode. Tail and grep only.
- F-010 (`Collection NOT FOUND` while service is up) is **expected behavior**, not a bug. Do not route to a repair playbook.

## See also

- `/rag-status` — quick state probe; run this first
- `references/known-failures.md` — F-001..F-012 classification source
- `references/repair-playbooks.md` — playbooks linked from findings
- `references/logs-and-diagnostics.md` — log substring catalog
- `references/post-install-verify.md` — what `rag doctor` is supposed to look like on a healthy install
