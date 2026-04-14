# Changelog

All notable changes to `rag-plugin` are documented here. Format is loosely based on [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.2.0] — 2026-04-14

Post-roadmap amendment. Ships the CLAUDE.md retrieval rule as an auto-installed plugin asset, adds MCP-duplicate detection/cleanup, and wires both into `/rag-setup`, `/rag-doctor`, `/rag-repair`, and `/rag-config`.

### Added
- **`rules/claude-md-retrieval-rule.md`** — new top-level `rules/` directory. Contains the single source of truth for the Section-0 retrieval rule block delimited by machine-readable `<!-- rag-plugin:retrieval-rule:begin v=0.2.0 -->` / `<!-- rag-plugin:retrieval-rule:end -->` markers. Commands splice this block into target CLAUDE.md files idempotently.
- **`/rag-config claude-md status|install|remove [--yes] [--project]`** — new subcommand group. Installs, upgrades, removes, or reports on the retrieval rule in `~/.claude/CLAUDE.md` (or `<cwd>/CLAUDE.md` with `--project`). Idempotent. Backs up before writing. Atomic writes only.
- **`/rag-config mcp-dedupe status|clean [--yes]`** — new subcommand group. Scans `~/.claude.json` (top-level and per-project `mcpServers`) and `~/.claude/.mcp.json` for duplicate `ragtools` MCP registrations that conflict with the plugin-level `.mcp.json`. Removes duplicates atomically, leaving the plugin-level one as canonical.
- **`/rag-setup` Branch C Step C.2b** — detects and removes duplicate MCP registrations before wiring. Delegates to `/rag-config mcp-dedupe clean --yes`.
- **`/rag-setup` Branch C Step C.5** — installs the retrieval rule into `~/.claude/CLAUDE.md` as part of first-time setup. Delegates to `/rag-config claude-md install --yes`. Reminds user the rule takes effect in the next session.
- **`/rag-doctor` — two new rows** in the diagnostic summary table: `CLAUDE.md rule` (INSTALLED v<N> / MISSING / OUTDATED / TARGET MISSING) and `MCP registrations` (1 canonical / N duplicates found / plugin-level missing). Each maps to a remediation command.
- **`/rag-repair` — two new plugin-behavior classifier IDs**: **P-RULE** (retrieval rule missing → `/rag-config claude-md install`) and **P-DEDUPE** (duplicate MCP registrations → `/rag-config mcp-dedupe clean`). These are separate from the F-001..F-012 catalog, which is reserved for ragtools product failures.
- **D-016** in `docs/decisions.md` documenting the retrieval-rule decision with the incident context, safety rules for touching user CLAUDE.md files, and the non-violation of D-001 (installing a workflow instruction is not the same as wrapping a search tool).
- **Extended D-015** scope documentation — the D-015 entry now references `/rag-config mcp-dedupe` as the dedupe mechanism.

### Changed
- **`plugin.json` version bumped** `0.1.0` → `0.2.0` (minor bump — new functionality, no breaking changes).
- **`ARCHITECTURE.md` layer diagram updated** with the new `RULES (1)` layer between references and product surfaces, and a new `USER CONFIG (external)` layer showing the four files the plugin writes to with care (`~/.claude/CLAUDE.md`, `~/.claude.json`, `~/.claude/.mcp.json`, and the plugin's own `.mcp.json`).
- **`README.md`** updated with the v0.2.0 auto-install behavior under "What this plugin IS".

### Rationale
User incident — asked *"What is the process for emergency assistance requests?"*. The ragtools MCP was loaded and the answer was in `tq-workspace/planing/Alaqraboon/_Emergency_Assistance_Procedure_en.md` at confidence 0.80. Claude never called `search_knowledge_base` and said *"I don't have information about an 'emergency assistance request' process."* This was a retrieval failure: the tool existed, but nothing instructed Claude *when* to use it.

Fix: ship a workflow instruction block (`rules/claude-md-retrieval-rule.md`) that the plugin's setup and repair commands inject into the user's `~/.claude/CLAUDE.md`. The rule loads at session start and applies globally across all projects — no per-project configuration needed. Versioned with begin/end markers for idempotent upgrade and clean removal. Safety-gated like every other write operation in the plugin: backup, atomic write, confirmation, splice by marker.

Paired with MCP-duplicate cleanup (`/rag-config mcp-dedupe`) so users migrating from v0.1.0 (where they may have manually wired ragtools via `~/.claude.json`) get a clean single-registration state after upgrading.

## [0.1.0] — 2026-04-14

Initial release. All 10 phases (0–9) of the rag-plugin roadmap shipped.

### Phase 0 — Foundation, Boundaries, Scaffold

- Plugin manifest at `.claude-plugin/plugin.json`
- README, LICENSE (MIT), ARCHITECTURE.md (layer-ownership diagram + forbidden list + 5-question boundary self-test)
- `docs/decisions.md` with 13 binding decisions (D-001..D-013) covering scope, transport, references bundling, install discovery, service-down behavior, skill granularity, hook posture, output verbosity, macOS posture, plugin name, versioning, telemetry, helper genericity
- Marketplace registration as the 7th entry in `plugins/.claude-plugin/marketplace.json` under category `productivity`

### Phase 1 — Doc to References Library

- Split the 21-section `ragtools_doc.md` into 16 topic-focused reference files under `skills/ragtools-ops/references/` plus `INDEX.md` and `_meta.md`
- Stable failure IDs `F-001..F-012` defined in `known-failures.md`
- Stable gap IDs `G-001..G-010` defined in `gaps.md`
- Every file under the 400-line skill-loadable budget; full cross-link discipline

### Phase 2 — Core Skill and Status Surface

- `skills/ragtools-ops/SKILL.md` — keyword-rich router with 15+ trigger phrases including error-message substrings, 14-row routing table mirroring `INDEX.md`, 3-phase body (detect mode → route → answer/handoff)
- `commands/rag-status.md` — one-screen state probe (mode banner + state table + per-project table); HTTP API parallel fetch when service UP, CLI fallback when DOWN
- `commands/rag-doctor.md` — wraps `rag doctor`, classifies findings against F-001..F-012, special-cases F-010 (`Collection NOT FOUND` while service up = expected, NOT a bug), optional `--logs` mode
- Mode banner format established (6 lines, fixed) and reused across all later commands

### Phase 3 — Setup and Install Workflows

- `commands/rag-setup.md` — conversational 3-branch onboarding (Branch A install / Branch B start service / Branch C wire MCP + add project)
- Hard refusal for Intel macOS (G-004) and Linux packaged install (G-001)
- MCP wiring reads `/api/mcp-config` from the running service — never hand-constructed
- `references/setup-walkthrough.md` long-form companion with time budget table and per-platform install procedures

### Phase 4 — Diagnostics and Repair Playbooks

- `commands/rag-repair.md` — 3 input modes (free-text symptom / `--symptom F-NNN` / `--scan-logs`), 16-row classifier rubric with 4 disambiguation rules (most importantly, F-010 vs F-003 special case), all 8 walkable playbooks from `repair-playbooks.md`, typed-confirmation gates on every destructive step
- `agents/rag-log-scanner.md` — Haiku-tier scoped agent. 13 catalog patterns + 4 informational substrings. Returns single JSON object, never diagnoses, never invents F-IDs

### Phase 5 — Project Management Integration

- `commands/rag-projects.md` — single command with 6 subcommands (`list`, `add`, `remove`, `enable`, `disable`, `rebuild`)
- HTTP API only — never edits `config.toml` directly (D-002, F-001)
- Refuses write ops when service is down (D-005)
- 5-provider cloud-sync detection warning gate (Syncthing, iCloud, OneDrive, Dropbox, Google Drive)
- `remove` requires typing the project ID verbatim; all-projects `rebuild` requires typing `REBUILD`

### Phase 6 — Guardrail Hooks and Token-Efficient Outputs

- `hooks/hooks.json` — PreToolUse Bash guardrail in the official `security-guidance` plugin format
- `hooks/lock_conflict_check.py` — Python 3 stdlib-only script. 7-pattern matcher + 1-second urllib `/health` probe + two-condition gate (matcher AND service up). Returns `permissionDecision: ask` only when both hold; never `deny`. Live-tested with 8 echo-pipe payloads
- `references/output-conventions.md` — codifies D-008 as 8 binding rules with per-command line budgets

### Phase 7 — Upgrade and Recovery Tooling

- `commands/rag-upgrade.md` — version detection + GitHub releases lookup + 3 platform-specific upgrade walkthroughs (Windows installer / macOS tarball / dev source pull). Read-only — never auto-downloads
- `commands/rag-reset.md` — 3 escalation levels (`--soft` rebuild via HTTP API / `--data` delete data dir / `--nuclear` delete entire RAGTools dir) with 1×/2×/3× typed-`DELETE` gating
- Hard block on pre-v2.4.1 versions (F-001 is data-loss-tier)
- Service-state enforcement: `--soft` requires UP, `--data`/`--nuclear` require DOWN
- `references/upgrade-paths.md` — 4 upgrade modes with what-preserves and what-can-go-wrong tables

### Phase 8 — Cross-Platform Hardening

- `references/macos-specifics.md` — 8-aspect honest table, per-command behavior differences, MPS-must-stay-disabled rule, 6-row Windows-vs-macOS playbook variations table
- `references/linux-dev-mode.md` — dev-mode-only documentation with G-001 cited up front, CWD-relative path table, "wrong-CWD footgun" warning that ties to F-006 misclassification
- `references/INDEX.md` — added 3 new routing rows (macOS / Linux / upgrade-paths)
- Audit confirmed: existing commands already include macOS branches alongside Windows from Phases 4 and 7. No silent Windows-only assumptions

### Phase 9 — Polish, Distribution, Telemetry, Maintenance

- README finalized with full command catalog, troubleshooting table, limitations table (G-001..G-010), telemetry posture ("What we record"), architecture diagram
- This CHANGELOG file
- `commands/rag-sync-docs.md` — **maintainer-only** with `disable-model-invocation: true`. Reads upstream `ragtools_doc.md` and reports which references have drifted. Never auto-rewrites
- `commands/rag-config.md` — local-only opt-in usage-logging toggle. JSONL at `~/.claude/rag-plugin/usage.log`. Default off. No network egress, ever (D-012)
- `ARCHITECTURE.md` and `docs/decisions.md` finalized with Phase 9 closure note
- Final inventory documented in `<final_status>` of Phase 9 report

## Known issues

### Validator false positives (carried from Phase 6)

`validate_plugin_simple.py` (in `plugins/validate_plugin.py` sibling) line 267 has a stale `valid_events` list that predates the official Anthropic plugin hooks.json wrapper format. It treats the top-level `description` and `hooks` keys in `hooks/hooks.json` as unknown event names and emits 2 warnings. The same warnings would fire on the official `security-guidance` plugin run through this validator. The full `validate_plugin.py` validator has the correct event list. Fixing the simple validator is out of scope for this plugin.

These are **validator bugs**, not `rag-plugin` issues. Hook structure is verified to match the canonical Anthropic format byte-for-byte.

## Compatibility

- **ragtools versions:** 2.4.x (per D-011)
- **Claude Code:** any version that supports `.claude-plugin/plugin.json` manifest, slash commands, skills, agents, and PreToolUse hooks
- **Python:** the hook script uses Python 3 stdlib only (no third-party deps)
- **Operating systems:** Windows (primary), macOS arm64 (Phase 1), Linux dev mode only

## License

MIT — see `LICENSE`.
