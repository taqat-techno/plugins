# rag-plugin — Operational Console for ragtools

> Operations and support plugin for the **ragtools** local-first RAG product. Install, configure, diagnose, repair, upgrade, and run the local Markdown knowledge base from inside Claude Code.

**Status:** `v0.11.0` — All 10 phases shipped + 14 post-roadmap amendments. New in v0.11.0: retrieval-reminder hook gains an **operational-intent classifier** that silent-passes prompts asking about local machine state (closes the LESSONS.md TODO from 2026-04-28). Default probe threshold raised `0.5 → 0.65`. CLAUDE.md retrieval rule bumped to v0.3.0 with Section 0a (operational/inspection skip) baked into the managed block. Smoke-test harness `scripts/hook_classifier_smoke.py` ships 20 fixtures (12 operational + 8 knowledge), all passing. Per D-027. 9 generic state-aware commands + 9 skill-level MCP workflows + 3 skills + 4 hook files. Production-ready for ragtools 2.5.x including v2.5.1 Linux ARM64. New in v0.9.0: `/project-focus` — scope ragtools retrieval to the current project so Claude does not pull context from unrelated indexed projects. State persists at `~/.claude/rag-plugin/state/project-focus.json`; a UserPromptSubmit hook injects strict-mode reminders on every prompt while focus is active.

---

> **Upstream product:** the ragtools application itself lives at **[`github.com/taqat-techno/rag`](https://github.com/taqat-techno/rag)**. This plugin is the operations console; the ragtools repo is where the application source, releases, installer artifacts, and product-level documentation live.
>
> Install artifacts per platform:
> - **Windows 10/11 (x64):** [`RAGTools-Setup-{version}.exe`](https://github.com/taqat-techno/rag/releases/latest) or portable zip
> - **macOS 14+ (Apple Silicon):** [`RAGTools-{version}-macos-arm64.tar.gz`](https://github.com/taqat-techno/rag/releases/latest)
> - **Linux ARM64:** [`RAGTools-{version}-linux-arm64.tar.gz`](https://github.com/taqat-techno/rag/releases/latest) (v2.5.1+)
> - **Any other platform** (macOS Intel, Linux x86_64, Windows ARM, etc.): clone [`github.com/taqat-techno/rag`](https://github.com/taqat-techno/rag) and install from source with `pip install -e ".[dev]"` — works on every platform Python supports.
>
> `/setup` walks all four paths automatically.

---

## What this plugin IS

`rag-plugin` is the **operations layer** for [ragtools](https://github.com/taqat-techno/rag), a local-first RAG product that indexes Markdown into an embedded Qdrant vector database and exposes it to Claude Code via its own MCP server. The plugin's job is to make the *operator's* life easier:

- **Auto-wire the ragtools MCP server.** The plugin ships its own flat-shape `.mcp.json` at the plugin root that spawns `rag serve` directly — the same pattern every other working MCP plugin uses (`chrome-devtools`, `context7`, `playwright`, `devops-plugin`). Installing the plugin registers `search_knowledge_base`, `list_projects`, and `index_status` automatically, assuming `rag` is on PATH (the RAGTools Windows installer adds it by default; dev `pip install -e .` exposes it as a pyproject console-script). For the edge case where `rag` is not on PATH, `/setup` branch C writes a user-level `~/.claude/.mcp.json` with an absolute binary path from `GET /api/mcp-config`. (D-015 / D-020)
- **Auto-install the CLAUDE.md retrieval rule.** The plugin ships `rules/claude-md-retrieval-rule.md`, a workflow instruction block that teaches Claude to call `search_knowledge_base` before saying "I don't have information" on any domain question. `/setup` installs it into `~/.claude/CLAUDE.md` automatically during first-time setup. `/doctor` surfaces its presence/version. `/rag-repair` classifies plugin-behavior symptoms as **P-RULE** and routes them here. (D-016)
- **Tier-2 UserPromptSubmit retrieval-reminder hook (v0.3.0).** A PreToolUse-style `UserPromptSubmit` hook ships inside the plugin. It fires on every user prompt, runs a shape heuristic (question-like, domain-possessive, not referencing current context), and if passed, probes `/api/search?top_k=1` for a likely match. When the top result scores ≥ 0.5 (MODERATE+), it injects a system reminder via `hookSpecificOutput.additionalContext` telling Claude to call `search_knowledge_base` before answering. **The hook is harness-enforced**, so Claude cannot "forget" the rule — the reminder is injected at the moment of answering, not loaded once at session start. Closes the advisory-only gap in the CLAUDE.md rule. (D-017)
- **Detect and clean up duplicate MCP registrations.** `/config mcp-dedupe` scans `~/.claude.json` and `~/.claude/.mcp.json` for stale ragtools entries that conflict with the plugin-level one and removes them atomically with backups.
- Detect install state (packaged Windows / packaged macOS / dev-mode / not installed)
- Resolve config / data / log paths the same way ragtools itself does
- Probe service health and report it as a one-screen banner
- Wrap `rag doctor`, `rag service status`, and the FastAPI admin endpoints
- Walk users through the documented repair playbooks for known failure modes
- Guard against the most common foot-gun: running a CLI command that fights the Qdrant single-process file lock while the service is up
- Codify safe upgrade and reset/recovery flows
- Manage projects through the HTTP API (never via direct `config.toml` edits)

## What this plugin is NOT

- ❌ **Not a search plugin.** The ragtools MCP server already exposes `search_knowledge_base` to Claude Code directly. Search lives in the product, not the plugin. The plugin **registers** the MCP server via its bundled `.mcp.json` (same pattern as `devops-plugin` registering the Azure DevOps MCP) but never wraps or re-implements any tool. (D-001, D-015)
- ❌ **Not a parallel admin panel.** ragtools ships its own Jinja2 admin UI on `http://127.0.0.1:21420`.
- ❌ **Not an installer.** The plugin produces installer URLs and walks setup; the user clicks. No multi-hundred-MB auto-downloads.
- ❌ **Not a config editor.** Every project write goes through `POST /api/projects` — never CWD-relative file writes. The v2.4.1 data-loss bug taught the project that the only safe write target is `get_config_write_path()`. (D-002, F-001)
- ❌ **Not a Qdrant client.** The service is the sole owner of the Qdrant file lock; the plugin never opens it directly.

If you want one of these things, you want the upstream ragtools product, not this plugin.

---

## Command catalog (v0.10.0 — 9 user + 1 maintainer)

Every command detects state and branches intelligently. See `rules/state-detection.md` for the shared contract and D-021 for the consolidation rationale.

| Command | Role | Smart behavior |
|---------|------|----------------|
| **`/doctor`** | Diagnose + status + repair. Absorbs the former `/rag-status` and `/rag-repair`. | Default: fast state probe. `--full`: deep `rag doctor` wrap with F-001..F-012 classification. Free-text positional: classify symptom. `--symptom F-NNN`: walk a named playbook. `--logs`: scan service.log via Haiku agent. `--fix`: walk the playbook inline after classification. `--verbose`: expand output. |
| **`/setup`** | Install + upgrade + verify. Absorbs the former `/rag-upgrade`. | Branches on state: install walkthrough (not-installed) / start-service (DOWN) / upgrade walkthrough (UP but old) / idempotent verify (UP and current). Checks MCP wiring, CLAUDE.md rule, dedupe on every run. |
| **`/projects`** | Project CRUD via HTTP API. | State-gate preamble refuses writes gracefully when the service is DOWN or BROKEN. Cloud-sync warning on write ops. Subcommands: `list` / `add` / `remove` / `enable` / `disable` / `rebuild`. |
| **`/reset`** | Destructive three-level reset. | State-gate preamble refuses on not-installed / BROKEN. Pre-v2.4.1 block remains. `--soft` (via HTTP API) / `--data` / `--nuclear` with typed-DELETE gates (1×/2×/3×). |
| **`/config`** | Plugin-layer config. | `telemetry {status\|on\|off}` / `claude-md {status\|install\|remove}` / `mcp-dedupe {status\|clean}` / `hook-observability {status\|on\|off\|analyze\|clear}`. Atomic writes, backup-first discipline. |
| **`/project-focus`** | Scope retrieval to the current project. | Auto-detects via CWD + git root, matches against `list_projects`, persists state at `~/.claude/rag-plugin/state/project-focus.json`. UserPromptSubmit hook injects scope-this-to-X reminders. Subcommands: `set` (default) / `<name>` (manual) / `status` / `clear`. |
| **`/report`** | Maintainer-feedback diagnostic report. | Generates two reports (application setup + plugin behavior) plus GitHub-ready issue bodies for `taqat-techno/rag` and `taqat-techno/plugins`. Captures install state, runtime, performance signals, configuration drift, missed retrievals, manual workarounds, improvement opportunities. Privacy-safe redaction, no auto-upload, no config mutation. `--no-sessions` / `--max-sessions N` / `--out <dir>`. |
| **`/sync-docs`** | Maintainer-only. `disable-model-invocation: true`. | Reports drift between bundled references and upstream `ragtools_doc.md`. Never auto-rewrites. |

Plus:
- **Skill** `ragtools-ops` — keyword-rich router that loads the right reference file on demand
- **Agent** `rag-log-scanner` — Haiku-tier `service.log` pattern matcher (returns JSON, never diagnoses)
- **Hook** `lock_conflict_check.py` — PreToolUse Bash guardrail; warns before commands that would fight the Qdrant lock

## Quick start

```
/plugins
→ Add Marketplace → https://github.com/taqat-techno/plugins.git
→ Install rag-plugin
```

Then in Claude Code:

```
/rag-status        # what state am I in?
/setup         # if not installed
/doctor        # if something is wrong
/rag-repair "..."  # walk a repair playbook for a specific symptom
```

For local development:
```bash
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

## Troubleshooting

| Problem | Where to look |
|---|---|
| "How do I install ragtools?" | `/setup` → `references/install.md` |
| "Is the service up?" | `/rag-status` |
| "Something is broken" | `/doctor` first, then `/rag-repair "<symptom>"` |
| "I see error X in logs" | `/rag-repair --scan-logs` invokes the `rag-log-scanner` agent |
| "Permission denied: 'ragtools.toml'" | F-001, the v2.4.1 bug. Run `/rag-upgrade` immediately. |
| "Qdrant already accessed by another instance" | F-003. Run `/rag-repair --symptom F-003`. |
| "Collection NOT FOUND in `rag doctor` while service is up" | F-010 — **NOT a bug**, expected lock contention. Use `/rag-status` instead. |
| "Projects disappeared after restart" | F-006. Run `/rag-repair --symptom F-006`. |
| "Want to nuke and start over" | `/reset` (3 escalation levels with typed-DELETE gating) |
| "How do I upgrade?" | `/rag-upgrade` |

Full failure catalog: `references/known-failures.md` (F-001..F-012)
Full repair playbooks: `references/repair-playbooks.md` (8 playbooks)
Full reference index: `references/INDEX.md`

## Limitations (honest)

These are **not bugs in rag-plugin** — they are limitations of the ragtools product itself, faithfully reflected here:

| ID | Limitation | Reference |
|---|---|---|
| **G-001** | No packaged Linux artifact. Dev install from source only. | `references/linux-dev-mode.md` |
| **G-002** | macOS LaunchAgent auto-start not implemented. Service must be started manually each session. | `references/macos-specifics.md` |
| **G-003** | WinGet manifests exist but are not yet submitted to the official repository. | `references/install.md` |
| **G-004** | Intel macOS (x86_64) not built. `/setup` hard-refuses. Apple Silicon required. | `references/macos-specifics.md` |
| **G-005** | No code signing or notarization. SmartScreen friction on Windows; Gatekeeper requires `xattr -cr rag/` on macOS. | `references/install.md` |
| **G-006** | Persistent activity log not implemented. In-memory 500-entry ring buffer only. | `references/logs-and-diagnostics.md` |
| **G-007** | No structured request logging in FastAPI. uvicorn access traces suppressed. | `references/gaps.md` |
| **G-008** | `scripts/verify_setup.py` semantics not fully verified for this doc cycle. | `references/gaps.md` |
| **G-009** | `rag ignore check` edge cases not fully verified. | `references/gaps.md` |
| **G-010** | Project disk-unmount runtime behavior not explicitly documented. | `references/gaps.md` |

The plugin **never** invents support for these. It refuses cleanly and points at the gap ID.

## What we record (telemetry)

`rag-plugin` is **local-first**. It records nothing by default. There is **no network telemetry — ever**.

If you opt in via `/config telemetry on`:

- A single JSONL file at `~/.claude/rag-plugin/usage.log`
- One JSON object per line: `{"ts": <iso8601>, "command": "<name>", "outcome": "<ok|error|user-cancel>", "failure_id": "<F-NNN or null>"}`
- **No paths, no project names, no search queries, no log contents — just command names and outcome tags**
- You can `cat ~/.claude/rag-plugin/usage.log` at any time
- `/config telemetry off` disables it (default)
- `/config status` shows current state and the file path

The default is **off**. The product is local-first, no-cloud, no-API-keys; the plugin matches that posture. If we ever can't meet all four bullets above, we ship without telemetry.

This is binding decision **D-012** in `docs/decisions.md`.

## Architecture

`rag-plugin` is a **reference-heavy operations plugin** in the style of the official `mcp-server-dev` and `claude-md-management` plugins. It is **not** a workflow-orchestrator plugin like `feature-dev` or `code-review`.

```
COMMANDS (9) ──invoke──> SKILL (1) ──load──> REFERENCES (23) ──describe──> PRODUCT SURFACES
                                                                          ├─ HTTP API on 127.0.0.1:21420
                                                                          ├─ rag CLI (rag service / rag doctor / rag version)
                                                                          ├─ MCP server (Claude calls directly, plugin never wraps)
                                                                          └─ files (config.toml, service.log, qdrant/, state DB)
```

Full architecture rules and the forbidden list are in `ARCHITECTURE.md`. Binding decisions D-001 through D-013 are in `docs/decisions.md`.

## Required reading

- `ARCHITECTURE.md` — what this plugin owns, what it never touches, the layer rules, and the 5-question boundary self-test
- `docs/decisions.md` — D-001..D-013 binding decisions
- `references/INDEX.md` — routing table from concern → reference file
- `CHANGELOG.md` — phase-by-phase deliverables (Phases 0–9)
- `../../../ragtools_doc.md` (workspace root) — operational source-of-truth for the ragtools product

## License

MIT — see `LICENSE`.
