---
description: Generate two evidence-based diagnostic reports for the maintainers — (1) RAC/RAG application setup report (target repo...
argument-hint: "[--no-sessions] [--max-sessions N] [--out <dir>] [--quiet]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(where rag:*), Bash(which rag:*), Bash(rag version:*), Bash(curl:*), Read
disable-model-invocation: false
---

# /report

Generates **two diagnostic reports** plus a summary and two GitHub-ready issue bodies, in a single timestamped directory. Captures install/runtime/performance/configuration/session-behavior evidence for the maintainers. Reports surface findings whether the system is healthy, degraded, or broken — not just bugs but also performance issues, config drift, missed retrievals, manual workarounds, and improvement opportunities.

## What it produces

A timestamped directory at `~/.claude/rag-plugin/reports/YYYY-MM-DD-HHMMSS/` containing:

| File | Purpose |
|---|---|
| `rag-application-setup-report.md` | Local ragtools install / runtime / config / data / logs health. Targets **github.com/taqat-techno/rag**. |
| `rag-plugin-behavior-report.md` | Plugin install state, Claude configuration, hooks, MCP wiring, session-behavior analysis. Targets **github.com/taqat-techno/plugins**. |
| `summary.md` | Top-level findings table, recommended actions, paths to the full reports. |
| `github-rag-issue.md` | Copy-pasteable issue body for the **rag** repo. |
| `github-plugins-issue.md` | Copy-pasteable issue body for the **plugins** repo. |
| `redacted-diagnostics.json` | Machine-readable structured findings. |

## What it inspects

- **ragtools install state** via `where rag` / `which rag`, version parse, platform-default paths, `RAG_*` env vars.
- **ragtools runtime** via `GET /health`, `GET /api/status`, `GET /api/projects`, `GET /api/watcher/status`.
- **Logs** — tails the most recent service log files, matches against error patterns, redacts secrets before inclusion.
- **Plugin layout** — `.claude-plugin/plugin.json`, commands/skills/agents/hooks/rules/scripts inventories, expected-file presence.
- **Claude configuration** — `~/.claude/CLAUDE.md` (retrieval-rule marker), `~/.claude/settings.json`, user-level `.mcp.json` and `.claude.json`, plugin-level `.mcp.json`.
- **MCP duplicates** — flags ragtools entries in user-level configs that conflict with the plugin-level registration.
- **Hook observability log** — reads `~/.claude/rag-plugin/hook-decisions.log` (no prompt content, only action tags + scores) and computes injection rates.
- **Recent session JSONL files** — newest-first, scans for RAC/RAG-related signals only:
  - mentions of ragtools / rag-plugin / search_knowledge_base / 127.0.0.1:21420
  - "I don't have information"-shaped responses
  - User corrections like "why didn't you search" / "use the knowledge base"
  - MCP error phrases / connection-refused / port-in-use
  - Skipped-retrieval patterns (rag context present + canned-refusal response)

## What it does NOT do

- Does **NOT** upload anything to GitHub or anywhere else.
- Does **NOT** create GitHub issues automatically.
- Does **NOT** mutate any user configuration.
- Does **NOT** include full conversations — only short, secret-redacted, single-line snippets.
- Does **NOT** call any MCP tool that would touch the knowledge base — pure filesystem + HTTP probes.
- Does **NOT** include unrelated user activity — only ragtools/plugin-relevant signals.

## Privacy and redaction

The script redacts before any text reaches a report:

- Bearer / Authorization headers, cookies
- API keys, secrets, passwords, tokens (key=value, JSON, and bare-token shapes)
- GitHub PATs (`ghp_*`, `github_pat_*`), AWS access keys (`AKIA*`), Slack tokens (`xox[bpoa]-*`)
- PEM private keys
- Long base64-shaped trailing tokens after `=`

Home directory paths are normalized to `~/...`. Hostname is partially masked. Snippets are clipped to ~220 chars and stripped of newlines.

## Step 0 — State detection

Follow `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md`. Print the 6-line mode banner verbatim. The script handles its own probing internally — Step 0 is to give the user the same orientation as `/doctor`. If `state.install_mode == not-installed`, the script will still produce both reports; the application report will simply note "ragtools is not installed on this device" as the top finding (this is the expected case for users who run the report before installing).

## Step 1 — Run the script

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/rag_report.py"
```

Pass `--max-sessions N` to limit the JSONL scan (default 60, newest-first). Pass `--no-sessions` to skip session scanning entirely if the user is privacy-cautious or in a shared environment. Pass `--out <dir>` to override the output location. Pass `--quiet` to suppress progress lines.

The script:

1. Probes ragtools install + service state.
2. Inspects plugin layout + Claude configuration + MCP wiring.
3. Reads the hook-decisions log (no user prompts).
4. Tails recent service logs.
5. Scans recent session JSONL files for RAC/RAG-only signals.
6. Synthesizes severity-ranked findings (`A-NNN` for application, `P-NNN` for plugin).
7. Writes the six files atomically to the timestamped directory.

Exit code 0 on success even if findings exist (non-zero only on hard errors — unwritable output dir, etc.).

## Step 2 — Show the user the result

After the script returns, show:

1. The output directory path.
2. The summary table from `summary.md` — top application-side issues + top plugin-side issues, severity-sorted.
3. The recommended next actions (only critical + high).
4. The exact paths of the two GitHub-ready issue files.
5. A reminder: **the command does not upload anything; copy the GitHub-ready files into a new issue manually.**

Compact-by-default per D-008. If the user passes `--verbose` to the slash command (we accept it as a marker — the script doesn't consume it), additionally print the per-finding detail block from each report.

## When to use

- **Before opening a maintainer issue.** The two GitHub-ready files capture environment, severity, evidence, and reproduction notes — saves 30 minutes of back-and-forth in the issue thread.
- **After hitting unexpected behavior.** Captures the local state at the moment of failure.
- **Periodically as a health-check.** The summary tells you in 10 seconds whether anything changed.
- **Before upgrading.** Lets you compare "before" and "after" diagnostics to confirm the upgrade fixed (or didn't fix) the symptom.

## Severity model

| Severity | Meaning |
|---|---|
| `critical` | Cannot proceed — install missing, service broken, plugin broken, MCP completely down. |
| `high` | Frequent failure or systemic issue — retrieval skipped, hook missing, version mismatch, install incomplete. |
| `medium` | Repeated warnings, partial feature failure, manual workaround detected, drift. |
| `low` | Improvement opportunity, minor cleanup, confusing output. |
| `info` | Healthy state, useful environment detail. |

## Manual validation checklist

After implementation:

1. `python scripts/rag_report.py --self-test` → all checks pass.
2. `python scripts/rag_report.py --max-sessions 5` → produces 6 files in `~/.claude/rag-plugin/reports/<ts>/`.
3. The application report prints the install mode + service mode banner correctly.
4. The plugin report shows command/skill/agent/hook/rule/script inventories.
5. The session scanner finds at least one RAC/RAG mention in recent sessions (or notes "no Claude session directory found").
6. The redaction layer scrubs synthetic secrets injected as test data.
7. No file outside the output directory is created or modified.

## See also

- `/doctor` — interactive state probe + repair (live, not a report)
- `/config status` — current plugin config (no report file)
- `scripts/rag_report.py` — the analyzer
- `scripts/analyze_hook_decisions.py` — hook-decisions histogram
- `rules/state-detection.md` — shared state probe contract
- `docs/decisions.md` — D-024 (rag-report design contract)
