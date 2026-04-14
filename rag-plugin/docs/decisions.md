# rag-plugin Decisions Log

Early decisions that bind every later phase. Each entry is a single binding rule with a one-paragraph rationale. Update only by appending — never rewrite history.

---

## D-001 — Plugin scope: ops-only, never search

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin is a **support, operations, and diagnostics layer** for ragtools. It will not implement `/rag-search` or any retrieval wrapper in MVP. The ragtools MCP server already exposes `search_knowledge_base`, `list_projects`, and `index_status` to Claude Code, and Claude already calls them directly via MCP. Adding a plugin-side wrapper would duplicate the existing tool surface, fight the Qdrant single-process lock, and split the token-efficiency story between the product's compact mode and a plugin formatter.

**Reverse only if:** a clear formatting need emerges that the MCP server can't address from inside the product. Even then, fix it upstream first.

---

## D-002 — Transport mix: HTTP for state, CLI for diagnostics, MCP for search

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When the service is up:
- **Status, projects, watcher, config, index stats** → HTTP API on `127.0.0.1:21420`.
- **`rag doctor`, `rag version`, `rag service start/stop/status`, `rag rebuild`** → shell out to the CLI; these commands are designed to handle both modes.
- **Search** → strictly via the MCP server already running inside Claude Code; the plugin does not call MCP tools itself.

CLI for things the HTTP API also covers (e.g. listing projects) is an anti-pattern — HTTP returns structured JSON; CLI returns pretty text. Prefer the structured side.

**Reverse only if:** the HTTP API drops a critical endpoint or starts returning unstructured responses.

---

## D-003 — References are bundled inline, not fetched

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Phase 1 splits `ragtools_doc.md` into ~12–15 topic files under `skills/ragtools-ops/references/`, bundled with the plugin. The plugin does **not** fetch them at runtime from a known path. Bundling means no install discovery is needed for the references themselves and the plugin is fully self-contained inside the marketplace package.

A maintainer-only doc-sync command (Phase 9) keeps the bundled references aligned with the upstream `ragtools_doc.md` checkout. `references/_meta.md` records the source-doc commit hash.

**Reverse only if:** references grow large enough that bundling them inflates plugin install size noticeably (unlikely — pure markdown).

---

## D-004 — Install discovery order

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When the plugin needs to find ragtools, it resolves in this order — mirroring `src/ragtools/config.py`'s own logic:

1. `RAG_DATA_DIR` env var (if set)
2. `RAG_CONFIG_PATH` env var (if set)
3. `where rag` (Windows) / `which rag` (macOS/Linux)
4. Platform default install paths:
   - Windows: `%LOCALAPPDATA%\Programs\RAGTools\rag.exe`
   - macOS: typical extract dirs (`~/Applications/rag/`, `/usr/local/bin/rag`)
5. Dev-mode detection: `pyproject.toml` + `.venv` in the current working tree
6. **Not installed** → suggest `/rag-setup` (Phase 3+)

This list is the source of truth for any path-resolution helper. Commands must not invent their own order.

**Reverse only if:** ragtools changes its own resolution order in a future major version.

---

## D-005 — Service-down behavior: read OK, write refuse

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

When `/health` is unreachable:
- **Read ops** (status, doctor, project list) — allowed, with a clear "service down → CLI direct mode → encoder will load (5–10s)" warning banner.
- **Write ops** (add/remove project, rebuild, watcher control) — **refused**, with a clear "service must be running for write operations — run `rag service start` first" message and an offer to start it.

The v2.4.1 data-loss bug is the justification: direct-mode writes are exactly where the data loss happened. Refusing them in service-down mode is the safest default.

**Reverse only if:** ragtools removes its dual-mode design and direct-mode writes become first-class.

---

## D-006 — Skill granularity: one skill, fat references

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin uses **exactly one skill** (`ragtools-ops`) with a fat `references/` library. Multiple skills (`ragtools-install`, `ragtools-diagnose`, `ragtools-search`) inflate the model's discovery surface for a tightly-scoped product, increase context cost on every turn, and risk routing collisions.

**Reverse only if:** references grow past ~25 files and routing inside the single skill becomes hard to follow.

---

## D-007 — Hook posture: ask, never silently deny

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The Phase 6 PreToolUse Bash hook fires **only when both conditions hold**:
1. The intended command matches a known Qdrant-lock-conflicting pattern (`rag index`, `rag rebuild`, `rag watch`, direct `rag-mcp` invocation, manual Qdrant access).
2. `GET /health` confirms the service is currently up.

When fired, it returns `hookSpecificOutput.permissionDecision: "ask"` with an explicit reason. It **never** returns `deny`. False positives on a hook that blocks would be worse than missed warnings — users would disable the hook and lose protection entirely.

**Reverse only if:** a class of operations emerges that is provably destructive and never-legitimate. Even then, prefer `ask` with strong language.

---

## D-008 — Output verbosity: compact by default, `--verbose` opt-in

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Every command outputs **at most one screen** (≤ 25 lines) by default. Tables, not paragraphs. Drill-down only on user request via `--verbose`. This mirrors the ragtools MCP server's own compact mode (§18.7) which already cuts context cost by 60–70%. Re-formatting MCP results in a verbose way undoes that work.

**Reverse only if:** a command genuinely needs more lines to be useful. Even then, the verbose case is opt-in.

---

## D-009 — macOS first-class by Phase 8, follower in MVP

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

ragtools itself calls macOS support "Phase 1" — tarball only, no `.app`, no `.dmg`, no LaunchAgent, no signing. The plugin will mirror that posture: Phases 0–7 are Windows-first; Phase 8 hardens macOS branches. The plugin will not invent macOS LaunchAgent support, will not pretend `.dmg` exists, and will explicitly fail Intel Macs early rather than letting users download an arm64 tarball that won't run.

**Reverse only if:** ragtools ships full macOS support in a future minor version.

---

## D-010 — Plugin name: `rag-plugin`

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

`rag-plugin` rather than `rag` (collides with the CLI binary), `ragtools` (collides with the package name), or `ragtools-ops` (longer with no benefit). Slash commands are namespaced: `/rag-status`, `/rag-doctor`, `/rag-setup`, `/rag-repair`, `/rag-projects`, `/rag-upgrade`, `/rag-reset`. The `rag-` prefix matches the user's mental model of "the rag tool" without colliding with the binary.

**Reverse only if:** a marketplace name conflict surfaces.

---

## D-011 — Versioning: major.minor compatibility band

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

The plugin declares "compatible with ragtools 2.4.x" and bumps on ragtools 2.5 / 3.0 / breaking changes to HTTP API or CLI surface. Exact-version pin is too brittle; "any ragtools" is too loose — references reflect a specific version's failure modes. The compatibility band is recorded in `references/_meta.md` (added in Phase 1).

**Reverse only if:** ragtools adopts strict per-patch breakage (unlikely).

---

## D-012 — Telemetry: none in MVP, opt-in local-only if added

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

No telemetry in MVP. If added in Phase 9, it must be:
- **Opt-in** via an explicit `/rag-config telemetry on` command. Default off.
- **Local-only** — single JSONL file at `~/.claude/rag-plugin/usage.log`. No network egress. Ever.
- **Inspectable** — the user can `cat` it.
- **Documented** in README under a "What we record" heading.

The product is local-first, no-cloud. Networked telemetry would betray the brand. If we can't meet all four bullets, we ship without telemetry.

**Reverse only if:** never. If you want telemetry that doesn't meet these bullets, build a different plugin.

---

## D-013 — Generic vs ragtools-specific helpers

**Date:** 2026-04-14
**Phase:** 0
**Status:** binding

Path resolution, mode banner, and compact-output formatter are **kept ragtools-specific** in MVP. We do not factor them into a "local-tool ops framework". Premature abstraction is worse than duplication for the next 12 months. If a second plugin emerges that needs the same helpers, factor them out then — not before.

**Reverse only if:** a second consumer materializes.

---

## D-014 — Phase 9 closure

**Date:** 2026-04-14
**Phase:** 9
**Status:** binding (closure note)

All 10 phases of the rag-plugin roadmap are shipped. The plugin has reached its planned scope: 7 user-facing commands + 1 user-facing config command + 1 maintainer-only command + 1 skill + 1 PreToolUse hook + 1 Haiku agent + 23 reference files. The validator reports structure as clean except for 2 known false-positive warnings about hooks.json top-level keys (stale `valid_events` list in `validate_plugin_simple.py` line 267 — same warnings would fire on the official `security-guidance` plugin).

Phase 9 added:
- **README.md finalization** — full command catalog, troubleshooting table, limitations table (G-001..G-010), telemetry posture, architecture diagram
- **CHANGELOG.md** — phase-by-phase deliverables for Phases 0–9
- **`/rag-config`** — local-only opt-in usage-log toggle. Default off. JSONL at `~/.claude/rag-plugin/usage.log`. No paths, no project names, no search queries, no log contents recorded. Zero network egress. Honors D-012 strictly.
- **`/rag-sync-docs`** — maintainer-only with `disable-model-invocation: true`. Reads upstream `ragtools_doc.md` and reports drift. Never auto-rewrites. Out of the user surface.
- **ARCHITECTURE.md** — appended a Phase 9 closure section with the final inventory and the "how to extend the plugin" steps for future contributors

The plugin is **roadmap-complete**. Future work is maintenance:
- Apply `/rag-sync-docs` when ragtools releases a new version
- Update the compatibility band in `_meta.md` and `plugin.json` when ragtools 2.5.x or 3.x ships
- Extend the failure catalog and gap register as the upstream product evolves
- Add new commands only after a new binding decision is recorded here

**Reverse only if:** never. This is a closure entry. Any future scope expansion appends new D-NNN entries.

---

## D-015 — Plugin-level `.mcp.json` ships ragtools MCP automatically

**Date:** 2026-04-14 (post-roadmap amendment)
**Phase:** Post-9
**Status:** binding

The plugin ships its own `.mcp.json` at the plugin root (`plugins/rag-plugin/.mcp.json`), following the `devops-plugin` pattern. When the user installs `rag-plugin` via `/plugins`, Claude Code auto-registers the ragtools MCP server — no manual wiring required, assuming `rag-mcp` is on `PATH`.

**The wired command** is `rag-mcp` with empty args. This is the pip console-script entry from ragtools' `pyproject.toml` and works in both:
- **Dev mode** via `pip install -e .` (active venv = `rag-mcp` on PATH)
- **Packaged Windows** if the installer was run with "Add to PATH" checked (default)

Packaged macOS users must manually add the extract directory to PATH (no installer PATH-registration step yet — macOS is Phase 1 in the upstream product).

**This does NOT violate D-001** (ops-only, never search). The plugin is not implementing search — it is *registering* the pre-existing ragtools MCP server so Claude can call `search_knowledge_base` / `list_projects` / `index_status` directly. Exactly the same pattern as `devops-plugin` registering the Azure DevOps MCP server without re-implementing work items. The plugin is the convenient delivery mechanism for the registration, not the tool implementation.

**Fallback paths remain unchanged:**
- `/rag-setup` branch C.1 still reads `GET /api/mcp-config` and writes a project-level or user-level `.mcp.json` with the exact binary path. Required for packaged installs without PATH integration.
- `references/mcp-wiring.md` documents all three registration options (Option A plugin-level auto, Option B project-level manual, Option C user-level manual) so users on any install mode can get MCP working.

**Placement:** `.mcp.json` lives at the **plugin root**, NOT under `.claude-plugin/`. Matches `devops-plugin/.mcp.json` exactly. Claude Code auto-discovers plugin-level `.mcp.json` files at the root when the plugin is enabled.

**Format:** the plugin-level `.mcp.json` uses the **flat shape** `{"serverName": {...}}` without a `mcpServers` wrapper — matches `devops-plugin/.mcp.json` exactly. Project-level and user-level `.mcp.json` files still use the `mcpServers` wrapper per the standard Claude Code schema. This format difference is plugin-level-specific and documented in `references/mcp-wiring.md` Option A vs Option B/C.

**Reverse only if:** the upstream ragtools product changes the `rag-mcp` entry-point name or removes the pip console script. In that case, update `.mcp.json` to use whatever the new canonical command is.

---

## D-016 — CLAUDE.md retrieval rule is a shipped plugin asset, installed by /rag-config

**Date:** 2026-04-14 (post-roadmap amendment #2)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.2.0
**Triggered by:** User incident — a user asked *"What is the process for emergency assistance requests?"*. The ragtools MCP was loaded and the answer was in `tq-workspace/planing/Alaqraboon/_Emergency_Assistance_Procedure_en.md` at confidence 0.80. Claude never called `search_knowledge_base` and said *"I don't have information about an 'emergency assistance request' process."* This was a retrieval failure: the tool existed, but nothing instructed Claude *when* to use it.

### The decision

The plugin ships a **rules/claude-md-retrieval-rule.md** file that contains the verbatim instruction block to be injected into the user's `~/.claude/CLAUDE.md`. The block is delimited by machine-readable begin/end markers:

```
<!-- rag-plugin:retrieval-rule:begin v=0.2.0 -->
### 0. Knowledge Base Retrieval (ragtools MCP)
...
<!-- rag-plugin:retrieval-rule:end -->
```

The `/rag-config claude-md` subcommand group owns install / upgrade / remove / status operations. The `/rag-setup` command invokes `claude-md install` as part of its Branch C Step C.5 so first-time users get the rule automatically. `/rag-doctor` surfaces the rule's presence/version in the diagnostic table. `/rag-repair` classifies plugin-behavior symptoms ("Claude doesn't use the MCP") as **P-RULE** and routes them to `/rag-config claude-md install`.

### Why the plugin installs into ~/.claude/CLAUDE.md instead of shipping a skill

The `ragtools-ops` skill only loads on keyword triggers (`ragtools`, `Qdrant`, `rag service`, etc.). A user asking "what is the process for X?" with zero ragtools-related keywords would never trigger the skill. The retrieval rule must apply to **all** user questions across **all** projects, so it has to live in a place Claude reads before its first response: `~/.claude/CLAUDE.md`.

A PreToolUse or UserPromptSubmit hook could also enforce this, but hooks that inject instructions on every turn pollute context and are too aggressive. The CLAUDE.md rule is the right layer: loaded once at session start, applies globally, costs nothing on a per-turn basis, and the user can read / edit / remove it like any other instruction.

### Why the rule is bundled, not hardcoded into the command

- **Single source of truth.** If the rule text needs to change, it changes in one file and every command picks up the new version automatically.
- **Version tracking.** The `v=X.Y.Z` marker in the begin line lets the install command detect outdated installations and upgrade them cleanly.
- **Clean removal.** The end marker lets the remove command splice out the block without affecting surrounding CLAUDE.md content.
- **Auditable by the user.** Users can read `rules/claude-md-retrieval-rule.md` directly before trusting the command to write to their CLAUDE.md.

### Does this violate D-001 (ops-only, never search)?

**No.** The plugin is not implementing search — it is installing a *workflow instruction* that teaches Claude to call the pre-existing `search_knowledge_base` MCP tool. The search tool lives in the ragtools MCP server; the plugin never wraps it. The CLAUDE.md rule is an **instructional layer**, not a search implementation. Same pattern as how a company style guide tells engineers when to run `make test` without re-implementing the test runner.

### Safety rules for touching user CLAUDE.md files

- **Backup first.** Before any write, copy the target to `<target>.bak-pre-claude-md-<operation>`.
- **Atomic writes only.** Load → modify in memory → write `.tmp` → rename. Never in-place edit.
- **Splice by markers, not by string-replace.** Always locate the begin→end range and replace it as a whole.
- **Confirm by default.** Show a diff summary before writing. `--yes` opt-out only for scripted use or when called from `/rag-setup`'s first-install branch.
- **Idempotent.** Running `claude-md install` twice on an already-installed rule produces no diff.
- **Never edit inside the markers by hand.** Always use the bundled rule as the source of truth.
- **Never touch content outside the markers.** Other CLAUDE.md sections are untouched.

### Scope of the /rag-config mcp-dedupe amendment (same release)

D-015 shipped plugin-level `.mcp.json` auto-wiring. After the plugin is installed, users who had previously wired ragtools manually via `~/.claude.json` or `~/.claude/.mcp.json` end up with duplicate registrations. `/rag-config mcp-dedupe status|clean` detects and removes those duplicates, leaving the plugin-level `.mcp.json` as the sole canonical registration. Same safety rules as the `claude-md` subcommand group: backup, atomic writes, confirmation, splice by key (never touch non-ragtools entries).

### Reverse only if

Never. The rule closes a genuine retrieval failure and the install mechanism is idempotent, reversible, and auditable. If the rule content itself ever needs to change substantially (e.g., a new MCP tool is added and the trigger table needs expansion), bump the version marker, update `rules/claude-md-retrieval-rule.md`, and the next `claude-md install` will upgrade existing installations cleanly.

---

## D-017 — Tier-2 UserPromptSubmit retrieval-reminder hook + observability-first escalation

**Date:** 2026-04-14 (post-roadmap amendment #3)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.3.0
**Triggered by:** The D-016 CLAUDE.md rule is advisory. A follow-up incident confirmed the gap: with the rule loaded, Claude still misclassified *"What is the process for emergency assistance requests?"* as general knowledge and refused to call `search_knowledge_base`, even though the answer was in `tq-workspace/planing/Alaqraboon/_Emergency_Assistance_Procedure_en.md` at confidence 0.80. The user correctly identified this as a failure of instruction-layer enforcement: CLAUDE.md is text Claude reads, not a hook Claude must execute.

### The decision

Ship a **Tier-2 guided-enforcement `UserPromptSubmit` hook** inside the plugin at `hooks/prompt_retrieval_reminder.py`, registered via `hooks/hooks.json`. The hook:

1. **Runs on every user prompt** (harness-enforced by Claude Code — this part is not advisory).
2. **Phase A — shape gate** (cheap regex, no network): excludes current-context references ("this file", "above", etc.), passes on question shape (`?`, wh-words, imperative retrieval verbs), passes on possessive domain statements (`our deployment pipeline`, `the runbook`, etc.).
3. **Phase B — domain probe** (one local HTTP call, ~30–50ms): probes `/health` with 500ms timeout, then `GET /api/search?query=<prompt>&top_k=1&compact=true` with 1s timeout. Checks `results[0].score ≥ 0.5` (the ragtools MODERATE confidence boundary).
4. **Injects a reminder** via `hookSpecificOutput.additionalContext` when both phases pass. Silent-passes in every other case.
5. **Never blocks, denies, or crashes a turn** — any error at any phase is swallowed as a silent-pass (D-007 spirit).

### Terminology correction (explicit, binding)

- **Tier 1 / Tier 2 = stronger guided enforcement.** The hook is harness-enforced (it definitely runs on every user prompt), but after reading the injected reminder, Claude can still choose not to call `search_knowledge_base`. Enforcement is on the *reminder delivery*, not the *tool call*.
- **Tier 3 = strongest practical enforcement.** Retrieval is prefetched by the hook before Claude composes its response. By the time Claude answers, the data is already in `additionalContext` — no "decide to search" step for the model to skip. **Tier 3 is NOT shipped in v0.3.0.** Escalation is deferred until observability data shows Tier 2 is insufficient.

### Why Tier 2 first, not Tier 3 immediately

- **Cost.** Tier 3 burns ~500–1500 tokens per matched prompt (pre-fetched results). Tier 2 burns ~200 tokens per matched prompt (reminder text only). For a session with many non-domain prompts, Tier 2's `silent-pass` discipline means most prompts cost **zero** tokens.
- **Reversibility.** If Tier 2 turns out to have too many false positives (reminder injected on prompts that don't need search), we can tune the threshold or heuristic without breaking anything. If Tier 3 is too aggressive, it's harder to dial back because the results are already in context.
- **Measurability.** With observability (below), we can tell within days whether the judgment gap is closed by Tier 2's reminder, or whether it persists even when Claude is reminded. That data determines whether to ship Tier 3 at all.

### Lightweight observability log

Every hook invocation appends one JSON line to `~/.claude/rag-plugin/hook-decisions.log`. Schema:

```json
{
  "ts": "2026-04-14T15:11:35Z",
  "shape_match": true,
  "probe_match": true,
  "probe_top_score": 0.813,
  "action": "reminder-injected",
  "prompt_length": 53,
  "hook_version": "0.3.0"
}
```

**Fields are decision metadata only.** The log NEVER contains:
- ❌ Prompt text (not even hashed)
- ❌ Search query text
- ❌ Result content (file paths, chunks, headings)
- ❌ Project IDs
- ❌ User, machine, or network identifiers
- ❌ Environment variables

This is D-012 aligned: local-only, no network egress, user-inspectable, zero content persistence. The only things stored are booleans, a float score, an action tag, and a prompt-length integer — enough for aggregate FP/FN analysis, insufficient to reconstruct what the user asked.

**Default: enabled.** Consistent with diagnostic syslogs in server software (on by default, user can turn off). Rationale: user explicitly asked for observability to drive the Tier-2-vs-Tier-3 decision, and the data must actually accumulate to be useful. Opt-out via a marker file at `~/.claude/rag-plugin/.hook-observability-disabled`.

### `/rag-config hook-observability` subcommand group

Added in v0.3.0 to manage the log lifecycle: `status`, `on`, `off`, `analyze` (invokes `scripts/analyze_hook_decisions.py` for aggregate stats), `clear` (delete log with typed `CLEAR` confirmation). Same discipline as the existing telemetry subcommand group.

### `scripts/analyze_hook_decisions.py`

New maintainer/power-user tool. Reads the log, prints aggregate stats: decisions by action tag, probe-score histogram, shape-gate pass rate, reminder-injection rate overall and within shape-passed prompts, hook version distribution, and tuning hints (e.g., "injection rate > 25%, consider raising the threshold"). Read-only, no arguments, defaults to the canonical log path. Python 3 stdlib only.

### Non-violation of D-001 (ops-only, never search)

The hook **REGISTERS A REMINDER** that mentions `search_knowledge_base`. It does NOT call the MCP tool. It does NOT wrap or reformat the MCP tool's results. It does NOT implement search of its own. The closest it gets to search is a lightweight HTTP probe to `/api/search?top_k=1&compact=true` to check *whether* a domain match exists — but it only reads `results[0].score`, not the result content. The probe is a **confidence check**, not a retrieval. Compact mode is used specifically to minimize the response payload the hook has to parse.

This is the same non-violation as D-015 (registering an MCP server ≠ wrapping it) and D-016 (installing a workflow rule ≠ implementing a search tool).

### Reverse only if

- The upstream ragtools product removes the `/api/search` endpoint (the probe would fail → hook would silent-pass every prompt → reverts to CLAUDE.md-only guidance).
- The observability data shows Tier 2 is insufficient over a meaningful window (weeks, not hours) — in which case **escalate to Tier 3** (new D-018), don't remove Tier 2.
- Never remove the hook because of context-cost concerns without first measuring the actual cost per turn via the observability log. The silent-pass path is ~zero tokens; cost only accumulates on matched prompts.

---

*Append new decisions below. Never rewrite or delete an entry — supersede with a new dated entry that references the old one.*
