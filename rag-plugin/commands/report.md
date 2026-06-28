---
description: Generate local diagnostic reports, route findings to the right repo, and — after one yes/no confirmation — file GitHub issues automatically. Application/runtime findings go to taqat-techno/rag; plugin/Claude/behavior findings go to taqat-techno/plugins. Redacts secrets, dedups by fingerprint, writes artifacts under ~/.claude/rag-plugin/reports/. Use --dry-run for local-only (no creation); falls back to local-only if the GitHub CLI is unavailable.
argument-hint: "[--dry-run] [--no-sessions] [--max-sessions N] [--out <dir>] [--quiet]"
allowed-tools: Bash(python:*), Bash(python3:*), Bash(where rag:*), Bash(which rag:*), Bash(rag version:*), Bash(curl:*), Bash(gh:*), Read
disable-model-invocation: false
---

# /report

Generates **two diagnostic reports** plus a summary and two GitHub-ready issue bodies in a single timestamped directory, then — by default, after one explicit yes/no confirmation — **files the issues automatically** to the correct repo via the GitHub CLI. Captures install/runtime/performance/configuration/session-behavior evidence for the maintainers. Reports surface findings whether the system is healthy, degraded, or broken — not just bugs but also performance issues, config drift, missed retrievals, manual workarounds, and improvement opportunities.

**Creation is never silent:** the command always shows which repo each issue targets and the issue title(s), then asks `Create GitHub issue(s) now? [yes/no]`. `--dry-run` skips the question and stays local-only (the legacy behavior). If the GitHub CLI is missing or unauthenticated, it falls back to local-only and says so. Duplicate filing is prevented by a fingerprint marker (see **Duplicate prevention** below).

## What it produces

A timestamped directory at `~/.claude/rag-plugin/reports/YYYY-MM-DD-HHMMSS/` containing:

| File | Purpose |
|---|---|
| `rag-application-setup-report.md` | Local ragtools install / runtime / config / data / logs health. Targets **github.com/taqat-techno/rag**. |
| `rag-plugin-behavior-report.md` | Plugin install state, Claude configuration, hooks, MCP wiring, session-behavior analysis. Targets **github.com/taqat-techno/plugins**. |
| `summary.md` | Top-level findings table, recommended actions, paths to the full reports. |
| `github-rag-issue.md` | Human-facing copy-paste issue body for the **rag** repo (includes the title/labels preamble). |
| `github-plugins-issue.md` | Human-facing copy-paste issue body for the **plugins** repo. |
| `redacted-diagnostics.json` | Machine-readable structured findings. |
| `issue-plan.json` | Machine-readable creation plan: per repo — target, title, labels, fingerprint, body file, and whether the finding set is actionable. Drives `--create`. |
| `_issue-body-rag.md` / `_issue-body-plugins.md` | The clean bodies actually posted on creation (copy-paste preamble stripped, fingerprint marker retained). |

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

- Does **NOT** create or upload any issue **without your explicit `yes`** to the one confirmation prompt — and never at all under `--dry-run`.
- Does **NOT** create a **duplicate**: before filing, it searches the target repo for an open issue carrying the same fingerprint marker and, if found, prints that issue's URL instead of opening a new one.
- Does **NOT** mutate any user configuration, ragtools data, or the knowledge base — generation is pure filesystem + HTTP probes (no MCP write tools, D-001).
- Does **NOT** include full conversations — only short, secret-redacted, single-line snippets; redaction (secrets, tokens, cookies, PEM keys, home-path normalization, hostname masking) is **unchanged** from the local-only era.
- Does **NOT** attach raw session logs or unrelated logs to the issue body.
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

## Step 2 — Show the result and the issue plan

After the generation run returns, show compactly:

1. The output directory path.
2. The summary table from `summary.md` — top application-side + plugin-side findings, severity-sorted.
3. The **GitHub issue plan** the script printed (also saved as `issue-plan.json`): for each actionable repo, the **target repo** and the **issue title**. Healthy (info-only) reports have **no** actionable issues — say so and stop (nothing to file).

Compact-by-default per D-008.

## Step 3 — Ask the one confirmation, then file (unless `--dry-run`)

**If `--dry-run` was passed:** skip this step entirely. Print `dry-run: local report written, no GitHub issue created.` and stop. (Legacy local-only behavior.)

**Otherwise, ask exactly one simple question**, showing the target repo + title per issue so the user knows precisely what will be filed:

```
Create GitHub issue(s) now? [yes/no]
  • taqat-techno/rag     — [ragtools] <title>
  • taqat-techno/plugins — [rag-plugin] <title>
```

- **If the user answers no** (or anything not affirmative): print `No issue created. Local report + issue bodies are at <dir>.` and stop. Nothing is filed.
- **If the user answers yes:**
  1. **Ensure GitHub auth + account.** These are `taqat-techno/*` repos, so per the workspace rule switch first (only if not already active): `gh auth switch --user a-lakosha`. If `gh` is missing or unauthenticated, do **not** fail — the script detects this and falls back to local-only.
  2. **File the issues** against the directory just generated — **no re-scan, no re-redaction**:
     ```bash
     python "${CLAUDE_PLUGIN_ROOT}/scripts/rag_report.py" --create --from "<dir>"
     ```
  3. **Relay the script's result verbatim:** `CREATED <repo>: <url>` per issue; `DUPLICATE <repo>: <existing url>` when an open issue with the same fingerprint already exists (nothing re-filed); or the local-only fallback line if `gh` was unavailable.
  4. **Switch the account back:** `gh auth switch --user ahmed-lakosha`.

**Never** create issues without the explicit `yes`. **Never** hand-build the issue body — the script posts the clean, redacted, fingerprint-marked `_issue-body-*.md` automatically via `gh issue create --body-file`.

## Duplicate prevention

Each issue body carries a stable hidden marker `<!-- rag-plugin-report:fingerprint:<hash> -->`, where the hash is a SHA-256 over the sorted non-info finding IDs for that repo (so the same diagnostic state always yields the same fingerprint). Before creating, `--create` runs `gh issue list --repo <repo> --state open --search <hash>` and confirms the marker is present in a candidate body. If an open match exists, it is **not** re-filed — the existing URL is reported instead. (Commenting/updating an existing issue is intentionally out of scope; we skip rather than risk a noisy or wrong update.)

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
2. `python scripts/rag_report.py --max-sessions 5` → produces **9** files in `~/.claude/rag-plugin/reports/<ts>/` (the 6 reports + `issue-plan.json` + `_issue-body-rag.md` + `_issue-body-plugins.md`), and **creates no GitHub issue**.
2a. `python scripts/rag_report.py --dry-run --no-sessions` → local-only, creates no issue. `--create --from <dir>` on a generated dir files (or dedups) via `gh`, and prints a clear local-only fallback when `gh` is unavailable.
2b. `python scripts/test_rag_report.py` → all unit tests pass (routing, cause-based re-route, fingerprint, dedup, create, never-create-during-generation).
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
