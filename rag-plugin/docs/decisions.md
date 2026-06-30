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
6. **Not installed** → suggest `/setup` (Phase 3+)

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

`rag-plugin` rather than `rag` (collides with the CLI binary), `ragtools` (collides with the package name), or `ragtools-ops` (longer with no benefit). Slash commands are namespaced: `/rag-status`, `/doctor`, `/setup`, `/rag-repair`, `/projects`, `/rag-upgrade`, `/reset`. The `rag-` prefix matches the user's mental model of "the rag tool" without colliding with the binary.

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
- **Opt-in** via an explicit `/config telemetry on` command. Default off.
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
- **`/config`** — local-only opt-in usage-log toggle. Default off. JSONL at `~/.claude/rag-plugin/usage.log`. No paths, no project names, no search queries, no log contents recorded. Zero network egress. Honors D-012 strictly.
- **`/sync-docs`** — maintainer-only with `disable-model-invocation: true`. Reads upstream `ragtools_doc.md` and reports drift. Never auto-rewrites. Out of the user surface.
- **ARCHITECTURE.md** — appended a Phase 9 closure section with the final inventory and the "how to extend the plugin" steps for future contributors

The plugin is **roadmap-complete**. Future work is maintenance:
- Apply `/sync-docs` when ragtools releases a new version
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
- `/setup` branch C.1 still reads `GET /api/mcp-config` and writes a project-level or user-level `.mcp.json` with the exact binary path. Required for packaged installs without PATH integration.
- `references/mcp-wiring.md` documents all three registration options (Option A plugin-level auto, Option B project-level manual, Option C user-level manual) so users on any install mode can get MCP working.

**Placement:** `.mcp.json` lives at the **plugin root**, NOT under `.claude-plugin/`. Matches `devops-plugin/.mcp.json` exactly. Claude Code auto-discovers plugin-level `.mcp.json` files at the root when the plugin is enabled.

**Format:** the plugin-level `.mcp.json` uses the **flat shape** `{"serverName": {...}}` without a `mcpServers` wrapper — matches `devops-plugin/.mcp.json` exactly. Project-level and user-level `.mcp.json` files still use the `mcpServers` wrapper per the standard Claude Code schema. This format difference is plugin-level-specific and documented in `references/mcp-wiring.md` Option A vs Option B/C.

**Reverse only if:** the upstream ragtools product changes the `rag-mcp` entry-point name or removes the pip console script. In that case, update `.mcp.json` to use whatever the new canonical command is.

---

## D-016 — CLAUDE.md retrieval rule is a shipped plugin asset, installed by /config

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

The `/config claude-md` subcommand group owns install / upgrade / remove / status operations. The `/setup` command invokes `claude-md install` as part of its Branch C Step C.5 so first-time users get the rule automatically. `/doctor` surfaces the rule's presence/version in the diagnostic table. `/rag-repair` classifies plugin-behavior symptoms ("Claude doesn't use the MCP") as **P-RULE** and routes them to `/config claude-md install`.

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
- **Confirm by default.** Show a diff summary before writing. `--yes` opt-out only for scripted use or when called from `/setup`'s first-install branch.
- **Idempotent.** Running `claude-md install` twice on an already-installed rule produces no diff.
- **Never edit inside the markers by hand.** Always use the bundled rule as the source of truth.
- **Never touch content outside the markers.** Other CLAUDE.md sections are untouched.

### Scope of the /config mcp-dedupe amendment (same release)

D-015 shipped plugin-level `.mcp.json` auto-wiring. After the plugin is installed, users who had previously wired ragtools manually via `~/.claude.json` or `~/.claude/.mcp.json` end up with duplicate registrations. `/config mcp-dedupe status|clean` detects and removes those duplicates, leaving the plugin-level `.mcp.json` as the sole canonical registration. Same safety rules as the `claude-md` subcommand group: backup, atomic writes, confirmation, splice by key (never touch non-ragtools entries).

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

### `/config hook-observability` subcommand group

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

## D-018 — Plugin-level `.mcp.json` uses wrapped shape + cross-mode launcher (supersedes D-015 format claim)

**Date:** 2026-04-14 (hotfix amendment)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.3.1
**Triggered by:** User bug report. On packaged Windows (RAGTools 2.4.1 installed at `%LOCALAPPDATA%\Programs\RAGTools\`), `/mcp` reported *"Failed to reconnect to plugin:rag:ragtools"* and `search_knowledge_base` was never callable. Two compounding bugs in the v0.3.0 plugin-level `.mcp.json`:

1. **Schema bug.** The file shipped the flat shape `{"ragtools": {...}}` without the `mcpServers` wrapper. Claude Code's plugin loader expects the wrapped form for stdio servers and silently registered nothing. D-015 had claimed the flat shape was plugin-level convention, citing `devops-plugin`, but this turned out to be wrong for stdio. A cross-repo audit of `claude-plugins-official-main/` showed that **every stdio `.mcp.json` in the Anthropic reference marketplace uses the wrapped shape** (`discord`, `fakechat`, `imessage`, `telegram`). The flat shape appears only in SSE/HTTP plugins (`asana`, `github`, `example-plugin`). The `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md` at the workspace root (lines 362–375) documents the wrapped shape as canonical.
2. **Command-resolution bug.** The file hardcoded `command: "rag-mcp"`, which only exists as a pip console-script in dev installs. The packaged Windows installer ships `rag.exe` only — no `rag-mcp.exe` shim. The canonical command per the service's own `GET /api/mcp-config` endpoint is `rag.exe serve` on packaged Windows and `rag-mcp` on dev installs. No single literal command is correct for both.

The `/doctor` `mcp-dedupe status` row failed to catch either bug because it only counted duplicate registrations across `~/.claude.json` / `~/.claude/.mcp.json` / plugin-level — it never parsed the plugin-level file's contents or verified that the wired command resolved on PATH.

### The decision

1. **Use the wrapped shape.** The plugin-level `.mcp.json` now uses `{"mcpServers": {"ragtools": {...}}}` matching the documented Claude Code plugin MCP schema. This supersedes D-015's flat-shape claim **for stdio servers only**. SSE/HTTP plugins may continue to use the flat shape — D-018 does not touch them.

2. **Delegate command resolution to a launcher.** Rather than hardcoding any single binary name, `.mcp.json` wires `command: "python"` with `args: ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]`. The launcher resolves the canonical ragtools binary at runtime and `os.execvp`-replaces itself with it, so Claude Code's stdio pipe connects directly to the real MCP server with no subprocess wrapping overhead.

   Launcher resolution order (stdlib only, ~100 lines, zero deps):
   - **(1) Service query.** `GET http://127.0.0.1:21420/api/mcp-config` with a 1-second timeout. The running ragtools service is the authoritative source of truth for this install mode — it knows whether this is packaged or dev, where the binary lives, and what args it expects. If the service responds with a valid `config.mcpServers.ragtools` entry, use that and return.
   - **(2) Packaged-binary probe.** `shutil.which("rag")` → if found, `exec rag serve`. Works on packaged Windows, packaged macOS (with `rag` on PATH), and Linux dev mode.
   - **(3) Dev-binary probe.** `shutil.which("rag-mcp")` → if found, `exec rag-mcp`. Works on `pip install -e .` dev installs.
   - **(4) Fail loud.** Write a clear error to stderr naming all three attempts and exit 127. Claude Code surfaces the stderr in `/mcp`.

3. **Harden `/config mcp-dedupe status`.** The doctor check no longer just counts duplicates. It parses the plugin-level `.mcp.json` and asserts four invariants: (a) file exists and is valid JSON; (b) `mcpServers.ragtools` key is present (catches the schema bug); (c) wired `command` resolves via `shutil.which` (catches the wrong-command bug); (d) when the launcher pattern is detected, the launcher script file is readable. Any failed assertion is surfaced as a distinct `ERROR` row in `/doctor` **before** duplicate-count issues, because a broken plugin-level registration means ragtools will not load at all regardless of user-level state.

### Why Python on PATH is an acceptable assumption

- Every ragtools install mode already requires or bundles Python. Dev installs run on a Python venv. Packaged installs bundle Python as a PyInstaller runtime. Users of this plugin are operators of a Python-based RAG tool — `python` on PATH is the minimum bar.
- If a future regression surfaces where `python` is not resolvable (e.g., a minimal Windows user without Python), we ship platform-specific `.cmd` / `.sh` shims in a later patch. Out of scope for this hotfix.

### Why not regenerate `.mcp.json` at install time instead

Considered: have `/setup` fetch `GET /api/mcp-config` on first run and rewrite the plugin-level `.mcp.json` with the exact binary path for the current install. Rejected because:
- The plugin directory is cache-managed (`~/.claude/plugins/cache/...`). Rewriting versioned assets at runtime is fragile and survives plugin updates unpredictably.
- The launcher achieves the same outcome (correct binary selected per install) without persisting mutable state inside the plugin cache.
- The launcher re-queries `/api/mcp-config` **every time Claude Code spawns the MCP server**, so it adapts automatically when the user reinstalls ragtools, upgrades it, or switches between dev and packaged modes — no setup step required.

### Non-violation of D-001 (ops-only, never search)

The launcher `exec`s into the real ragtools MCP server. It does not implement search, wrap search, parse search results, or proxy MCP traffic. It is a thin process-replacement shim — the same pattern as any Unix shebang wrapper. `rag-plugin` continues to own only the ops layer.

### Relationship to D-015

D-015 remains binding in its intent: the plugin ships its own `.mcp.json` at the plugin root and auto-wires the ragtools MCP server so users do not have to manually edit config files. D-018 supersedes **only** D-015's specific claim that the flat shape is correct for stdio plugin-level registrations. The "Format" paragraph of D-015 is obsolete as of v0.3.1; read D-018 for the current schema rule.

### Reverse only if

- The `${CLAUDE_PLUGIN_ROOT}` variable stops being expanded by the Claude Code plugin loader (would break the launcher path). Unlikely — the variable is documented and used by multiple official plugins.
- A future Claude Code release accepts the flat shape for stdio plugin-level `.mcp.json` files AND we want to drop the launcher. Even then, keeping the launcher is defensible because it handles the cross-install-mode command problem independently of the schema question.

---

## D-019 — Retraction of D-018 schema change; flat shape is correct for plugin-level `.mcp.json`

**Date:** 2026-04-14 (retraction amendment)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.3.2
**Supersedes:** D-018 schema portion (the launcher portion of D-018 stands)
**Triggered by:** Empirical failure of v0.3.1. With the wrapped-shape `.mcp.json` deployed, `/mcp` reported the ragtools server as present and `/reload-plugins` counted it among the loaded servers, but `ToolSearch` could not find any ragtools tool and the model could not call `search_knowledge_base`. The server initialized cleanly when probed directly over stdio — confirming the launcher worked — but the tool schemas never reached the deferred-tool registry.

### What went wrong in D-018

D-018 claimed that plugin-level `.mcp.json` must use the wrapped shape (`{"mcpServers": {"ragtools": {...}}}`). The evidence cited was:
1. `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md:362–375` documents the wrapped shape.
2. Every stdio example in `claude-plugins-official-main/` uses the wrapped shape.

Both statements are true. The error was applying them to the wrong scope. **Those docs and examples describe user-level and project-level `.mcp.json` files, not plugin-level files shipped inside a plugin directory.** The plugin-level format is a separate, flat schema, and the two scopes are not interchangeable.

### Empirical evidence for the flat shape at plugin-level

Direct inspection of `~/.claude/plugins/cache/` on the reporter's machine found:

| Plugin | Path | Shape | Tools reach model |
|---|---|---|---|
| `chrome-devtools-mcp` | `claude-plugins-official/.../latest/.mcp.json` | **flat** `{"chrome-devtools": {...}}` | ✅ yes |
| `context7` | `claude-plugins-official/.../.mcp.json` | **flat** `{"context7": {...}}` | ✅ yes |
| `playwright` | `claude-plugins-official/.../.mcp.json` | **flat** `{"playwright": {...}}` | ✅ yes |
| `devops-plugin` | `taqat-techno-plugins/devops/6.3.0/.mcp.json` | **flat** `{"azure-devops": {...}}` | ✅ yes |
| `rag-plugin v0.2.0` | `.../rag/0.2.0/.mcp.json` | **flat** `{"ragtools": {...}}` | (v0.2.0 had the command-resolution bug in some environments but its schema was correct) |
| `rag-plugin v0.3.0` | `.../rag/0.3.0/.mcp.json` | **flat** `{"ragtools": {...}}` | (same — correct schema, broken command) |
| `rag-plugin v0.3.1` | `.../rag/0.3.1/.mcp.json` | **wrapped** `{"mcpServers": {"ragtools": {...}}}` | ❌ **no** — tool schemas never reached the model despite the launcher working |

Every plugin whose tools actually reach the model uses the flat shape. The single plugin that adopted the wrapped shape is the single plugin whose tools could not be found. This is sufficient evidence to revert the v0.3.1 schema change.

### The scope rule, recorded explicitly

| File location | Shape | Owner |
|---|---|---|
| `<plugin-root>/.mcp.json` (plugin-level) | **flat** `{"<server>": {...}}` | Plugin author, ships with plugin |
| `~/.claude/.mcp.json` (user-level) | **wrapped** `{"mcpServers": {"<server>": {...}}}` | User, global config |
| `<repo>/.mcp.json` (project-level) | **wrapped** `{"mcpServers": {"<server>": {...}}}` | Project author, checked into repo |

The wrapped shape is for files that need to coexist with other non-MCP sections of the same JSON document (user-level `~/.claude.json` uses the same `mcpServers` key alongside other top-level keys, and project-level `.mcp.json` files have historically been a subset of the user-level schema for copy-pasting convenience). The flat shape is for plugin-level because the file has nothing else in it — the entire file is the MCP registration for that plugin.

### What of D-018 survives

The **launcher** portion of D-018 — `scripts/rag_mcp_launcher.py` that resolves the canonical ragtools binary via the running service → `rag` on PATH → `rag-mcp` on PATH → fail loud — is **retained and correct**. That fix addresses the real v0.3.0 bug (no single hardcoded command works across every install mode) and is not affected by the schema question. The v0.3.2 `.mcp.json` still delegates to the launcher; it just does so using the flat shape instead of the wrapped shape:

```json
{
  "ragtools": {
    "type": "stdio",
    "command": "python",
    "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]
  }
}
```

### Also retracted: the `mcp-dedupe status` schema assertion

v0.3.1 added a doctor assertion that the plugin-level file has `mcpServers.ragtools`. That assertion was inverted in v0.3.2 to assert the top-level `ragtools` key directly (flat shape). The detection of a wrapped-shape plugin-level file is now treated as a distinct `ERROR`, because it is the specific regression that v0.3.2 exists to prevent from recurring.

### Why the mistake was made and how to prevent it

The development guide and the reference marketplace both heavily feature the wrapped shape, which is the correct shape for ~90% of `.mcp.json` files a developer encounters (because most `.mcp.json` files are user/project-level, not plugin-level). A bug report claimed plugin-level needed the wrapped shape; the cross-reference check looked at the most prominent examples (which happened to match the claim); the empirical check against actually-working plugins on disk was skipped. Rule going forward: **when validating `.mcp.json` shape for plugin-level registrations, always cross-reference against working plugins in `~/.claude/plugins/cache/`, not just documentation examples.** The cache contains ground truth for what the plugin loader actually accepts.

### Reverse only if

- A future Claude Code release formally standardizes the plugin-level `.mcp.json` schema to require the wrapped shape. If that happens, update `.mcp.json` and document the version boundary. Until such a release exists and is verified empirically against installed plugins, the flat shape is the only known-working format.

---

## D-020 — Plugin-level `.mcp.json` spawns `rag serve` directly; no Python wrapper (retracts D-018 launcher portion)

**Date:** 2026-04-14 (retraction amendment #2)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.3.3
**Supersedes:** D-018 launcher portion. D-019 already retracted D-018's schema claim. D-020 retracts the launcher claim. D-015's original posture — plugin-level `.mcp.json` registers the ragtools MCP server directly via the canonical binary — is fully restored.
**Triggered by:** v0.3.2's empirical failure on Windows. With the flat-shape `.mcp.json` delegating to `scripts/rag_mcp_launcher.py`, `ListMcpResourcesTool` showed `plugin:rag:ragtools` as registered and `/reload-plugins` counted the server among loaded servers, but `ToolSearch` found zero ragtools tools and `search_knowledge_base` was never callable. The MCP handshake was failing silently at the `tools/list` step.

### Root cause

Python's `os.execvp` on Windows does not preserve stdio pipe inheritance the way POSIX `execvp` does. On POSIX, `execvp` replaces the current process image atomically — the stdin/stdout/stderr pipes that Claude Code opened to the Python launcher transfer to the spawned `rag.exe` with no handoff. On Windows, `os.execvp` is implemented via `_spawnv(_P_OVERLAY, ...)`: the Python parent exits and a new process is started, and the pipe handles Claude Code inherited are not guaranteed to survive that transition. The spawned `rag.exe` never receives the `tools/list` RPC that Claude Code is already waiting on, the call silently times out, and no tool schemas reach the deferred-tool registry.

Two corroborating observations:
1. The launcher worked when probed via `python rag_mcp_launcher.py --dry-run` — that code path prints and exits without `exec`, so the `os.execvp` path was never exercised during static testing.
2. `rag serve` worked correctly when invoked directly as an MCP server over stdio — confirming the ragtools product side was fine.

Both halves of the plugin were fine in isolation. The Python-to-native-binary handoff was the failure point.

### The decision

**Plugin-level `.mcp.json` calls the ragtools binary directly, with no Python wrapper in the middle.** Final canonical form:

```json
{
  "ragtools": {
    "type": "stdio",
    "command": "rag",
    "args": ["serve"]
  }
}
```

This matches the pattern used by every working MCP plugin on the reporter's machine (verified in `~/.claude/plugins/cache/`): `chrome-devtools-mcp`, `context7`, `playwright`, and `azure-devops` all invoke their target binary directly via `npx`. None of them use a Python or shell wrapper. The direct-spawn pattern is the ground truth for what Claude Code's plugin loader can reliably handle on Windows.

### Why `rag` (not `rag-mcp`)

`where rag` returns `C:\Users\ahmed\AppData\Local\Programs\RAGTools\rag.exe` on the reporter's packaged Windows install. `where rag-mcp` returns nothing. This was the original v0.3.0 bug — the plugin hardcoded `rag-mcp` which only exists as a pip console-script on dev installs. Fixing the binary name (`rag`) was the single change v0.3.0 actually needed. Everything after that (wrapped schema, launcher script) was over-correction.

`rag` is a pyproject console-script in the ragtools package, so it is also available on dev installs via `pip install -e .`. Both supported install modes cover it.

### Why dropping the launcher is not a loss of functionality

The launcher's stated value-add was "ask the running service for the canonical command via `GET /api/mcp-config`" — adapting to the current install mode dynamically. In practice:
- If `rag` is on PATH (the common case for both install modes), the service query is redundant — the binary is already resolvable.
- If `rag` is genuinely not on PATH (user skipped the installer's "Add to PATH" option, or did not set up PATH on macOS), `/setup` branch C.1 already reads `/api/mcp-config` and writes a **user-level** `~/.claude/.mcp.json` with the absolute binary path, which then takes precedence over the plugin-level file. This fallback is unchanged from v0.1.0 and is the documented recovery path.

So the launcher was duplicating logic that already existed in `/setup` — but doing it with a Python middleman that had a Windows stdio bug.

### The general rule (binding)

**When wiring a stdio MCP server in a plugin-level `.mcp.json`, `command` must be the ragtools binary (or the real target binary for any other plugin), not a Python or shell script that spawns it.** Wrappers add a pipe-handoff hazard on Windows via `os.execvp` process replacement, and they add latency and failure surface for no practical benefit — the target binary is already resolvable on PATH in the common case, and the "target not on PATH" edge case is handled by a user-level `.mcp.json` fallback, not by shipping a runtime resolver.

This applies to every future MCP plugin in this marketplace. If a contributor proposes a Python or shell wrapper inside a plugin `.mcp.json`, point them at D-020 and require them to either fix the command name directly or use the user-level fallback.

### Non-violation of D-001

The plugin still does not implement, wrap, or proxy search. It registers the pre-existing ragtools MCP server with Claude Code so the model can call `search_knowledge_base` directly. Same posture as D-015. The only change is removing the Python shim that v0.3.1/v0.3.2 put between Claude Code and that server.

### Reverse only if

- A future Claude Code release introduces a `.mcp.json` feature that actually requires a wrapper script (e.g., per-invocation environment injection that cannot be done via static `env` fields). In that case, design the wrapper as a native binary or a compiled helper, not a Python script — or use a `.cmd` / `.sh` shim and accept the extra install-mode handling. Never re-introduce a Python `os.execvp` middleman.

---

## D-021 — Command surface is a small set of smart, state-aware entry points; state detection is centralized

**Date:** 2026-04-14 (consolidation amendment)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.4.0
**Triggered by:** User feedback that commands assumed an ideal state (ragtools already installed, already healthy, already configured) and fragmented the "get ragtools working" and "something is wrong" mental models across too many narrow entry points. User explicitly asked for "fewer, stronger, more context-aware commands."

### The decision — two rules, one binding consequence

**Rule 1: Each user-facing command is a smart entry point that detects state and branches.** Commands do not assume an ideal state. Every command's Step 0 is a state-detection preamble that produces a structured `state` object (`install_mode`, `service_mode`, `binary_path`, `version`, `config_path`, `data_path`, `log_path`). Every command's subsequent steps are gated on that state. A command that is asked to operate in an impossible state (e.g. `/projects add` when the service is down, `/reset` when ragtools is not installed) refuses gracefully with a clear remediation pointer rather than failing with a generic HTTP or CLI error.

**Rule 2: State detection lives in one file and is referenced by every command.** The canonical recipe is at `rules/state-detection.md`. Commands do not re-implement the probe — they reference the rule file. Single-owner layering per `ARCHITECTURE.md`. If the probe ever needs to change (new install mode, new service state, new path category), the change happens in one file and every command picks it up automatically.

### The binding consequence — command consolidation

v0.4.0 collapses the former 8-user-command surface into **6 user-facing commands + 1 maintainer-only**:

| Command | Role |
|---|---|
| `/doctor` | Smart diagnose. Default: fast state probe. `--full`: deep `rag doctor` wrap. `--symptom F-NNN`: walk a playbook. Free-text positional: classify symptom. `--logs`: scan service.log. `--fix`: walk the playbook inline after classification. **Absorbs the former `/rag-status` and `/rag-repair`.** |
| `/setup` | Smart install/upgrade/verify. Branches: install (not-installed) / start-service (DOWN) / upgrade (UP but old) / verify (UP and current). **Absorbs the former `/rag-upgrade`.** |
| `/projects` | Project CRUD via HTTP API with state-gate preamble. |
| `/reset` | Destructive reset with typed-DELETE gates and state-gate preamble. |
| `/config` | Plugin-layer config (telemetry, claude-md rule, mcp-dedupe, hook-observability). |
| `/sync-docs` | Maintainer-only with `disable-model-invocation: true`. |

Deleted files: `commands/rag-status.md`, `commands/rag-repair.md`, `commands/rag-upgrade.md`. Their logic moved verbatim into the surviving commands — all 8 repair playbooks, the F-001..F-012 classification rubric, the GitHub releases fetch, the in-place upgrade walkthroughs, the state-probe recipe, the MCP-wiring verify flow are all still present. What changed is **how the user enters them**, not **what they get once inside**.

### Why these consolidations and not others

- **`/rag-status + /doctor + /rag-repair → /doctor`.** All three began with the identical mode-detection block and all three ended with a footer pointing at the other two. The user's mental model is "what's wrong with ragtools?" not "should I run status or doctor or repair?" — the single command handles all three phases and walks the playbook inline via `--fix`.
- **`/setup + /rag-upgrade → /setup`.** The user's mental model is "get ragtools working" regardless of whether that means installing, starting, or upgrading. `/rag-upgrade` previously refused outright when ragtools was missing — a classic case of a narrow command assuming an ideal state. The unified `/setup` detects state and picks the right sub-flow.
- **`/projects` stays separate.** Project CRUD is a distinct operational scope. Merging it into `/setup` or `/doctor` would hide destructive write operations behind an innocuous command name, and the user's mental model of "manage my projects" is clearly distinct from "diagnose my install."
- **`/reset` stays separate.** Destructive reset is a distinct scope and destructive operations benefit from their own namespace — users searching for "reset" should find `/reset` directly, not a flag on a setup command. Merging reset into setup would violate the rule that destructive paths should never be hidden behind innocuous names.
- **`/config` stays separate.** Plugin-layer config (telemetry, claude-md rule, mcp-dedupe, hook-observability) operates on a fundamentally different layer than the ragtools product. Merging it into a product-layer command would blur the ops-layer/product-layer boundary the plugin works hard to maintain (see D-001).
- **`/sync-docs` stays separate.** Maintainer-only with `disable-model-invocation: true`, invisible to the user surface.

### Why deletion, not stub redirects

Considered: keep `rag-status.md` / `rag-repair.md` / `rag-upgrade.md` as thin stubs that print "this command is now part of /rag-X" and redirect. Rejected because:
1. Stubs create dead entries in the slash-command catalog that compete with the real commands for user attention.
2. Stubs give a false signal that the old commands are "still supported but deprecated," when in fact their logic has moved entirely and the old names are obsolete.
3. Deletion forces users to learn the new surface once; stubs force them to learn the new surface AND remember the mapping from old to new.

### Non-violation of existing decisions

- **D-001 (ops-only, never search):** every consolidated command continues to refuse MCP tool calls. Search is still delegated to the running ragtools MCP server and the model calls it directly.
- **D-002 (no direct config.toml writes):** preserved in both rewritten commands. All project writes continue to go through `POST /api/projects`. The F-001 workaround flow in the P-perm playbook retains its explicit user-confirmation gate.
- **D-005 (service-down behavior):** preserved. Read ops still work in CLI direct mode with the "encoder will load" warning; write ops still refuse gracefully.
- **D-007 (hook posture — ask never deny):** unaffected. Commands do not change hook behavior.
- **D-008 (compact by default):** preserved. Both rewritten commands are compact-by-default with `--verbose` for opt-in drill-down. The state banner + state table + findings block + footer pattern is unchanged.
- **D-015, D-016, D-017, D-018, D-019, D-020:** all preserved. The plugin-layer MCP wiring, CLAUDE.md retrieval rule, UserPromptSubmit hook, and launcher-to-direct-spawn history are untouched by the command consolidation — only the entry point names changed, not the underlying plugin architecture.

### Reverse only if

- A future Claude Code release introduces a formal command-deprecation mechanism that makes stub redirects low-cost. Even then, consider whether deprecation is actually worth the slash-command-catalog pollution before reintroducing any removed command.
- A user-flow emerges where state-aware branching is genuinely worse than a narrow command (unlikely — the primary criticism of v0.3.x was the opposite).

### What this decision does NOT do

- Does not add a top-level `/rag` super-command that dispatches to sub-commands. The user asked for fewer commands, not a new meta-command, and `/doctor` as the default diagnose-and-status command already fills that role.
- Does not refactor the hook scripts (`lock_conflict_check.py`, `prompt_retrieval_reminder.py`) to consume `rules/state-detection.md`. Those have their own stdlib-only minimal detectors; converging them is not worth the risk in this release.
- Does not change the `references/` library or the `F-001..F-012` catalog. The ragtools product surface is unchanged; only the plugin entry points are.

---

## D-022 — Plugin uses MCP ops tools freely; refines D-001 scope for the v2.5.0+ MCP surface

**Date:** 2026-04-18 (MCP v2.5.0 integration amendment)
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.5.0
**Refines:** D-001 (ops-only, never search). Does not supersede it. D-001 remains in force for content-retrieval tools.
**Triggered by:** ragtools MCP v2.5.0 (handoff doc at `C:\MY-WorkSpace\claude_plugins\ragtools_mcp_doc.md`) expanded the MCP surface from 3 content-retrieval tools to **22 tools**: 3 core (content), 9 optional project ops (default ON), 9 optional debug (default OFF). D-001 was written when the MCP only had the 3 core content tools, and its "never call MCP tools" posture would now forbid the plugin from using 19 explicitly-designed operational tools — which is backwards.

### The clarification

D-001's binding rule — **"plugin never wraps or re-implements `search_knowledge_base`"** — is preserved without change. Content retrieval stays with Claude calling the MCP directly; the plugin never intercepts, reformats, or proxies search results.

D-022 adds: **the plugin freely chains the 18 non-search MCP tools (`list_projects`, `index_status`, 9 project ops, 9 debug) to drive diagnostic, operational, and guided-write workflows in its commands and skill.** These are ops tools, not content tools. Using them is exactly what the MCP was expanded for.

### The line between "wrap" and "use"

| Action | D-001 says | D-022 says |
|---|---|---|
| Plugin calls `search_knowledge_base` to retrieve content for the user | ❌ **forbidden** (wrapping search) | Unchanged — still forbidden |
| Plugin reformats `search_knowledge_base` results before showing them | ❌ forbidden | Unchanged — still forbidden |
| Plugin calls `index_status` to probe health | (not mentioned — pre-v2.5.0 the plugin hit HTTP instead) | ✅ allowed — ops tool |
| Plugin calls `system_health` / `crash_history` / `service_status` for diagnostics | (not mentioned) | ✅ allowed — ops tools |
| Plugin calls `project_status` / `list_project_files` for `/projects status` | (not mentioned) | ✅ allowed — ops tools |
| Plugin calls `reindex_project` with user-confirmation gate | (not mentioned) | ✅ allowed — guarded write |
| Plugin calls `add_project_ignore_rule` after `preview_ignore_effect` | (not mentioned) | ✅ allowed — guarded write |
| Plugin calls `search_knowledge_base(top_k=1)` as a "has this content?" probe | ⚠ ambiguous pre-v2.5.0 | ✅ allowed only in the UserPromptSubmit hook (pre-loading context), forbidden elsewhere |
| Plugin pre-fetches search results and injects them into a skill response | ❌ forbidden (Tier 3 retrieval — not shipped; see D-017 "Reverse only if") | Unchanged — still forbidden unless D-017's escalation criteria are met |

### Why the distinction is load-bearing

Three safety and design properties fall out of this split:

1. **Content tools are the user's domain; ops tools are the plugin's domain.** `search_knowledge_base` answers user questions; the user must see Claude's unmediated call to that tool. Ops tools answer "is the service up?" or "why isn't this indexed?" — those are plugin-operational questions, not user-content questions.
2. **Ops tools carry their own safety model.** The MCP's `reindex_project` has a confirm-token guard; `run_index` has a 2s cooldown; `add_project_ignore_rule` auto-surfaces the "run reindex" reminder. If the plugin *doesn't* use these tools and hits the HTTP API instead (as pre-v0.5.0 did), it loses the envelope contract's benefits and duplicates logic that drifts.
3. **The MCP explicitly excludes high-blast-radius writes** (`add_project`, `remove_project`, `shutdown`, `backup_restore`, `set_active_project`). The plugin's existing HTTP paths that call those endpoints (e.g. `POST /api/projects`) now stand out as **weaker than what the MCP would accept** — D-022 flags them for future migration to CLI-only or admin-UI-only paths. The plugin should not add new HTTP paths that bypass the MCP's intentional exclusions.

### How the plugin enforces the distinction

- **`rules/mcp-envelope.md`** (new in v0.5.0) codifies the envelope contract, error-code branching, mode handling, fallback chain (MCP → HTTP → CLI), and tool-grant awareness. Every MCP-using command references this rule rather than inlining the discipline.
- **Commands that need debug tools** (`system_health`, `crash_history`, `tail_logs`, `service_status`) must degrade gracefully when the user hasn't granted them — print the specific toggle path in the admin UI, fall back to CLI/HTTP, never fail cryptically.
- **Skills route to MCP tools automatically.** The `ragtools-ops` skill now includes a Phase 2.5 "MCP tool dispatch" section that lists which MCP tool to call for each user-intent pattern (ignore rules, project diagnostics, why-not-indexed, etc.). When the user asks "why isn't file X in the search?", the skill chains `list_project_files` → `get_project_ignore_rules` → `preview_ignore_effect` without the user typing a single command.

### Non-violation of other decisions

- **D-005 (service-down behavior):** preserved. Writes still refuse gracefully when the service is down — now the refusal comes from the MCP envelope (`SERVICE_DOWN` / `DEGRADED_MODE`) instead of a raw curl error, which is a UX improvement. Read tools with filesystem fallbacks (`tail_logs`, `get_paths`, etc.) continue to work.
- **D-007 (hook posture — ask never deny):** unaffected. Hooks do not call MCP tools; they still use minimal HTTP/stdlib probes.
- **D-008 (compact by default):** preserved. MCP envelopes are structured data; the plugin still renders compact tables and emits `--verbose` only on request.
- **D-012 (local-first telemetry):** preserved. All MCP traffic is loopback. Session-ID stamping is metadata only — no content logged.
- **D-015 (plugin ships `.mcp.json`):** preserved. D-022 just expands what the plugin can do *with* the MCP the plugin already auto-wires.
- **D-017 (retrieval-reminder hook):** preserved. The hook's domain probe via `/api/search` is a non-MCP HTTP call that still happens pre-hook — it does not call `search_knowledge_base`.
- **D-020 (`.mcp.json` direct spawn):** preserved. D-022 is about *using* the MCP's tools; D-020 is about *wiring* the MCP server. Orthogonal.
- **D-021 (state-aware smart commands):** preserved. `rules/state-detection.md` was updated to prefer MCP probes; the state-aware dispatch pattern is unchanged.

### Reverse only if

- The MCP contract ever removes the envelope discipline or breaks the error-code enum. Then the plugin must fall back entirely to HTTP/CLI until a new stable contract lands.
- The MCP exposes `search_knowledge_base` in a way the plugin is forced to mediate (e.g. if the user asks for a search scope the MCP can't express). Even then, prefer adding the missing capability to the MCP itself and cite an upstream issue — do not wrap around it.

### What D-022 does NOT change

- Plugin still does not call `search_knowledge_base` from any command. Content retrieval is Claude's direct call, period.
- Plugin still does not re-implement search or index logic. The MCP owns that.
- Plugin still does not auto-execute destructive operations. Every write is gated by typed confirmation (`DELETE`, `ADD`, `REMOVE`, or the project ID verbatim).
- Plugin still honors the MCP's intentional exclusions (`add_project`, `remove_project`, `shutdown`, `backup_restore`, `set_active_project`) — does not wrap them even where HTTP fallbacks exist. Future plugin releases should migrate the existing HTTP paths for `add_project` / `remove_project` toward CLI-only or admin-UI-only handoffs.

---

## D-023 — Markdown authoring standard + always-safe improvement boundary

**Date:** 2026-04-19
**Phase:** Post-9
**Status:** binding
**Ships in:** v0.7.0
**Triggered by:** user-provided Markdown authoring standard at `C:\MY-WorkSpace\claude_plugins\rag_md_guidelines.md`, reverse-engineered from `src/ragtools/chunking/markdown.py` + `src/ragtools/retrieval/formatter.py` + `src/ragtools/embedding/encoder.py` (MiniLM-L6-v2, 256-token max). The guideline documents exactly which Markdown patterns the chunker rewards and which it punishes. Ships alongside the rag-plugin's shift from "any Markdown" to "Markdown that chunks well for this specific RAG pipeline."

### The decision

1. **Markdown creation in the rag-plugin defers to the `markdown-authoring` skill.** The skill lives at `skills/markdown-authoring/SKILL.md` with three reference files: `references/rag-md-guidelines.md` (the 359-line canonical standard, copied verbatim from the source-of-truth), `references/page-templates.md` (5 copy-paste scaffolds — concept, SOP, reference, runbook, architecture), and `references/anti-patterns.md` (the 9 anti-patterns with per-item chunker-mechanism rationale). The skill activates on Markdown creation intent — "write a README", "document component X", "create a runbook", "draft an SOP" — and emits content that satisfies the §8 pre-commit checklist: opens with `#` heading, sections ≤ 300 words, leaf headings unique, no knowledge in YAML frontmatter, code blocks ≤ 60 lines, tables ≤ 15 rows, prose before code.

2. **The `/md-rag-enhance` command is ALWAYS-SAFE by design.** No `--analyze` toggle, no `--fix-safe` flag, no `--fix-aggressive` flag. Safe enhancement is the single mode. Every invocation applies exactly two mechanical fix categories that cannot change semantic meaning by construction:
   - **GL-05 pseudo-heading → real heading conversion.** Bold-text lines used as section titles (`**Text**` on its own line, blank-line-surrounded, outside code fences) get converted to `## Text`. The ragtools heading regex doesn't match bold-as-heading — this is pure structural improvement.
   - **Blank-line normalization around headings and code fences.** Adds a blank line before/after every `##`/`###`/`####` heading and every fenced code block if missing. Typographical only, never touches code-fence interiors or flowing text.

3. **Every other finding is REPORT-ONLY.** Content-before-first-heading (GL-01), oversized sections (GL-02), vague headings (GL-03), duplicate leaf headings (GL-04), oversized code blocks (GL-06), oversized tables (GL-07), YAML frontmatter carrying knowledge (GL-08), code block without prose intro (GL-09), skipped heading levels (GL-10) — all surfaced in the command's output for manual review, never auto-applied. Structural rewrites require semantic judgment; the tool reports, the human decides.

4. **Every enhancement writes atomic + backup-first.** Never in-place edit. Never touch code-fence interiors. Never change commands, URLs, file paths, config keys, version numbers, or numeric values — the safe-fix categories do not write into flowing text. `<file>.bak-pre-md-rag-enhance` sibling is written before every modification; `--no-backup` opts out for git-managed users.

5. **Parameter surface is minimal and binding:**
   ```
   /md-rag-enhance                 enhance every .md under CWD
   /md-rag-enhance <file>          enhance only that file
   /md-rag-enhance --verbose       full per-file report
   /md-rag-enhance --no-backup     skip the backup sibling files
   ```
   No other flags ship. No `--path`, no `--max-files`, no `--report`, no `--fix-*`, no `--analyze`, no `--dry-run` (the `--dry-run` / `--json` / `--self-test` flags exist in the underlying analyzer script for development and testing, but are **not exposed** through the command). **Simplicity is the safety property.** A command with one mode is always-safe; a command with modes can be invoked in the wrong mode.

6. **Hardcoded 500-file safety cap** for whole-project runs. Exceeded → clear error message telling the user to pass a specific file path. Defensive, not user-configurable.

### Non-violation of prior decisions

- **D-001 / D-022:** the skill and command do not call `search_knowledge_base` or any MCP content-retrieval tool. They operate purely on the filesystem. The Markdown they affect will be chunked by ragtools later if the user indexes the project, but the plugin does no indexing and no search. Boundary unchanged.
- **D-005:** the command does not require ragtools to be running. It's a filesystem tool, not a service client. Install-mode `not-installed` is not a blocker — the command prints an info line and continues. The state-detection preamble still runs for UX consistency.
- **D-007:** the command does not block tool calls or deny actions. It produces reports and applies safe fixes.
- **D-008:** compact-by-default output discipline preserved. `--verbose` for drill-down.
- **D-012:** no network egress. The analyzer is stdlib-only Python; no external endpoints.
- **D-015 / D-020:** MCP wiring untouched. The skill and command are new; they do not change `.mcp.json`.
- **D-021:** command is generic (works standalone with no args; defaults to enhance-all in CWD; optional positional arg for a single file). New capability ships 80% as a skill and 20% as a command — matches the "decrease commands, increase skills" directional guidance.

### Reverse only if

- **The upstream ragtools chunker changes meaningfully** (new section-boundary rules, different token budget, different embedder model). Then both the skill reference content and the analyzer heuristics need updating together. Update `references/rag-md-guidelines.md` first; bump the plugin minor version; document which chunker-version range the heuristics now target.
- **Structural auto-fixes prove safe enough in practice** that the REPORT-ONLY list can shrink. Requires empirical evidence from field use, not theory. The first candidate for promotion from report-only to safe-fix would be YAML-frontmatter-to-`## Tags` migration (GL-08) — mechanical, but the risk tail with non-semantic frontmatter keys is why v0.7.0 keeps it report-only.
- **The always-safe posture becomes a usability bottleneck** (user explicitly asks for a riskier mode to save time on large projects). Even then, prefer a new companion command with a scary name (e.g. `/md-rag-rewrite`) over adding a `--fix-aggressive` flag to the always-safe one. Flag-based safety regressions are how safety erodes.

### What D-023 does NOT change

- Does not change how ragtools itself chunks or embeds. That's upstream.
- Does not require any plugin user to run `/md-rag-enhance` — it's a tool, not a mandate. The plugin still works without it.
- Does not touch files other than `.md` files. No YAML, JSON, Python, shell — those are not in scope.
- Does not index, search, or read any chunks from the knowledge base. Purely a Markdown-authoring hygiene tool.

---

## D-024 — Maintainer-feedback diagnostic reports (`/report`)

Date: 2026-05-01
Phase: Post-9
Status: binding
Ships in: v0.8.0

Decision:

1. The plugin ships a single command — `/report` — that produces **two** reports (application-setup + plugin-behavior) plus a summary, two GitHub-ready issue bodies, and a structured JSON diagnostics blob, in a single timestamped directory at `~/.claude/rag-plugin/reports/YYYY-MM-DD-HHMMSS/`.
2. The command **never uploads** anything. It never creates a GitHub issue. It never mutates user configuration. It only reads filesystem + HTTP. The user copies the GitHub-ready files into an issue manually.
3. Findings are severity-ranked (`critical / high / medium / low / info`) and namespaced by target repo: `A-NNN` for findings filed against `taqat-techno/rag`, `P-NNN` for findings filed against `taqat-techno/plugins`. The two reports never share findings.
4. Privacy invariants (binding):
   - Secrets, tokens, bearer headers, cookies, PEM keys, GitHub PATs, AWS access keys, and Slack tokens are redacted via a single redaction layer applied before any text reaches a report.
   - Home directory paths are normalized to `~/...`.
   - Hostname is partially masked.
   - Session snippets are clipped to 220 chars and stripped of newlines.
   - Only RAC/RAG-related signals are extracted from sessions — no unrelated user activity is summarized.
5. Session JSONL scanning is opt-out via `--no-sessions` and budget-capped via `--max-sessions N` (default 60, newest-first). The signal taxonomy covers: `rag-mention`, `rag-port`, `mcp-error`, `retrieval-skipped`, `user-correct-search`, `rag-error-line`, `connect-refused`, `port-in-use`. New signals are added by extending `_SIGNAL_PATTERNS` in `scripts/rag_report.py`.
6. The command degrades gracefully when ragtools is not installed (top finding becomes "ragtools not installed on this device"), the service is down (skips API probes, falls back to platform-default paths), the hook log is missing (notes "no hook-decisions log"), and the session directory is missing (notes "no Claude session directory found"). No path through the script crashes when the environment is incomplete.

Non-violation of prior decisions:

- **D-001 / D-022 / D-007:** the report does not call `search_knowledge_base` or any MCP retrieval tool. It reads filesystem + HTTP only. No tool-call blocking.
- **D-008 (compact by default):** the slash command's output to the user is compact (banner + summary table + paths). Verbose detail is in the report files, not in the chat response.
- **D-012 (telemetry opt-in):** the report writes only to its own timestamped output directory. No usage events are recorded outside that directory unless `/config telemetry on` is independently set.
- **D-021 (decrease commands, increase skills):** this is a +1 command because the maintainer-feedback flow needs a single explicit user-triggered entry point — running it as a side-effect of another command (skill-driven activation) would be wrong. The script behind it is a pure analyzer with no MCP coupling, so it does not belong in a skill body.

Reverse only if:

- A future Claude Code platform feature lets the plugin produce structured diagnostic output through a sanctioned channel (e.g. an issue-creation API) that supersedes the copy-paste workflow. At that point, the command would gain an opt-in `--submit` flag with explicit confirmation rather than producing markdown files.
- The privacy invariants prove insufficient (a maintainer reports a leaked secret through a report). Then the redaction layer expands and the snippet length cap shrinks; the architecture stays.

---

## D-025 — Project-focus mode (`/project-focus`)

Date: 2026-05-01
Phase: Post-9
Status: binding
Ships in: v0.9.0

Decision:

1. Focus state lives in a single local JSON file at `~/.claude/rag-plugin/state/project-focus.json`. Atomic writes (tmp + `os.replace`). The file is the single source of truth — no env vars, no second config location, no per-project overrides.
2. The injector hook (`hooks/project_focus_inject.py`) reads only that file, never the user's prompt. On missing/malformed state, it silent-passes. The hook composes alongside the existing retrieval-reminder hook — both fire independently per Claude Code's multi-hook support for `UserPromptSubmit`.
3. Filter-fallback policy when `search_knowledge_base` does not accept a `project` parameter:
   - Try the parameter first; if accepted, use it.
   - Otherwise post-filter results by metadata (`source` / `path` / `project` / `name`) and keep only entries matching the focused project.
   - If neither path can guarantee strict focus for a given query, **warn the user** that strict focus is not technically enforceable for that response. Do not silently fall back.
4. Cross-project retrieval is gated on an explicit user phrase ("across all projects", "compare projects", "global knowledge", "all of them"). A weaker phrasing keeps focus.
5. The command **never auto-mutates ragtools project config**. No auto `add_project`, no auto `reindex_project`, no auto `add_project_ignore_rule`. If the focused project is missing from `list_projects` or has zero chunks, the command tells the user which `/projects` invocation to run; it does not run it.
6. Match scoring is deterministic: exact-path > ancestor-path (longer prefix wins) > descendant-path > name. Ambiguity (top two scores within 10 points and same method, with similar path lengths) returns `{ok: false, reason: "ambiguous"}` — the user must rerun with an explicit name.

Non-violation of prior decisions:

- **D-001 / D-022 / D-007:** the command does not call `search_knowledge_base` or any retrieval tool. The hook does not call any MCP. The script reads the local HTTP API only to enumerate `list_projects`. No tool-call blocking.
- **D-008 (compact by default):** the chat output is compact (4-6 lines on success). The detailed JSON from the script is parsed by the command renderer, not dumped raw.
- **D-012 (telemetry opt-in):** the focus state file is the only artifact written outside the user's CWD. No usage events, no prompts, no result content persisted.
- **D-017 (Tier 2 retrieval reminder):** the project-focus reminder composes additively with the retrieval reminder. They do not interfere — Claude can receive both injections in one turn.
- **D-021 (decrease commands, increase skills):** this is a +1 command because the focus toggle needs an explicit user-triggered entry point with persistent state. Skill-driven activation would be wrong (no clear "off" semantic).

Reverse only if:

- A future ragtools release exposes a stable `project=` parameter on `search_knowledge_base`. At that point the post-filter fallback can be removed and the hook reminder simplifies to "always pass project=<name>".
- The ambiguity-detection thresholds prove too conservative or too loose in practice. Adjust the score-gap and same-method criteria; do not remove the ambiguity gate.
- Multi-project focus is requested as a feature. Implement as `mode: "set"` with an array of project names rather than promoting a second config location.

---

## D-026 — Drop the `rag-` prefix from command file names

Date: 2026-05-01
Phase: Post-9
Status: binding (BREAKING)
Ships in: v0.10.0

Decision:

1. The seven plugin commands `rag-bug-report`, `rag-config`, `rag-doctor`, `rag-projects`, `rag-reset`, `rag-setup`, `rag-sync-docs` are renamed by dropping the `rag-` prefix. Files become `report.md`, `config.md`, `doctor.md`, `projects.md`, `reset.md`, `setup.md`, `sync-docs.md`. Plugin-namespaced invocations become `/rag:report`, `/rag:config`, `/rag:doctor`, `/rag:projects`, `/rag:reset`, `/rag:setup`, `/rag:sync-docs`. Note: `rag-bug-report` becomes `report` (not `bug-report`) — the command captures performance / drift / behavior evidence across the full health spectrum, not just defects.
2. Two commands are NOT renamed: `md-rag-enhance` (the `rag` here is "RAG pipeline", not "rag-plugin") and `project-focus` (already prefix-free).
3. The plugin name `rag-plugin` is unchanged. The agent `rag-log-scanner` is unchanged. The plugin namespace `/rag:` is unchanged.

Rationale:

- Claude Code surfaces plugin commands as `/<plugin-name>:<command-name>`. With `<plugin-name>` already being `rag`, every `rag-*` command file produced an invocation like `/rag:rag-doctor` — the `rag-` was duplicated. The team announcement for v0.7.0 made that awkwardness visible.
- Renaming is mechanical: same file content, new name. No behavior change. Only the entry-point string changes.

Non-violation of prior decisions:

- D-021 (decrease commands): no command count change. 9 user-facing commands, same as v0.9.0.
- D-008 (compact by default): unchanged.
- D-007 / D-001 / D-022: no behavior change in tool-call discipline.

Reverse only if:

- Claude Code platform changes how plugin namespacing works such that the bare slash form becomes canonical. As of v0.10.0, the namespaced form is canonical and shorter without the prefix.

---

## D-027 — Operational-intent classifier in the retrieval-reminder hook

Date: 2026-05-01
Phase: Post-9
Status: binding
Ships in: v0.11.0
Closes: LESSONS.md TODO "rag-plugin enhancement (future work)" items #1, #2, #3

Decision:

1. The `UserPromptSubmit` retrieval-reminder hook (`hooks/prompt_retrieval_reminder.py`) gains a Phase A.5 **operational-intent classifier** that runs after the shape gate and before the probe. When a prompt matches the operational-intent regex — imperative action verbs near the start of the prompt (`start|stop|run|fix|install|configure|where is|what's running|why is X failing|...`), optionally preceded by polite lead-ins or "how do I X" — the hook silent-passes with action tag `silent-pass:operational-intent`. The reminder is suppressed.
2. The default probe threshold (`RAG_PLUGIN_HOOK_PROBE_THRESHOLD`) is raised from `0.5` to `0.65`. The CLAUDE.md rule (Section 0) still describes the MODERATE band (0.5–0.7) as legitimate retrieval context; the hook just stops nagging until the score is convincingly HIGH.
3. The CLAUDE.md retrieval rule v0.3.0 ships **Section 0a** ("Override: Operational / Inspection Questions Skip the MCP") inside the managed marker block. Every install of rag-plugin now writes Section 0a as part of the canonical rule. The user no longer needs to hand-roll Section 0a outside the markers.
4. The classifier regex lives in **one place** — the hook module — and is imported by the smoke-test harness (`scripts/hook_classifier_smoke.py`) and surfaced by `/doctor --classify`. Single source of truth: changing the regex changes all consumers.

Rationale:

The hook's probe-score similarity gate cannot distinguish "how do I start my bot in WSL" (operational; answer on disk) from "what's our process for token rotation" (knowledge; answer in notes). LESSONS.md "Inspect the machine before asking clarifying questions" (2026-04-28) documents the resulting bias: the hook fires on operational prompts, the assistant searches the KB, gets nothing relevant, and asks clarifying questions instead of running `ls` / `wsl -- ls` / `which`. The classifier closes the gap mechanically — operational-intent matches silent-pass, knowledge-shape matches probe normally.

Non-violation of prior decisions:

- D-001 / D-007: the hook still does not block any tool call. It only suppresses an advisory reminder. Claude can still call `search_knowledge_base` whenever it wants.
- D-008 (compact by default): no output change. Silent-pass is silent.
- D-012 (telemetry opt-in): the new `silent-pass:operational-intent` action tag appears in the hook-decisions log, alongside the existing tags. No user content logged.
- D-016 (CLAUDE.md rule): Section 0a is additive within the managed block. Section 0 (the original rule) is untouched.
- D-017 (Tier 2 guided enforcement): unchanged. The classifier is a finer-grained shape filter, not a tier escalation.

Reverse only if:

- The classifier's false-negative rate on operational prompts proves >5% in observability data (legitimate operational prompts that still trigger reminders). Then expand the regex; do not remove the gate.
- The classifier's false-positive rate on knowledge prompts proves >10% (knowledge prompts incorrectly silent-passed as operational). Then narrow the regex anchors; do not remove the gate.
- A future ragtools release exposes a richer probe API that returns intent classification server-side. At that point the client-side classifier becomes redundant.

---

*Append new decisions below. Never rewrite or delete an entry — supersede with a new dated entry that references the old one.*

---

## D-028 — Per-workspace project-focus + explicit global (supersedes D-025 §1)

Date: 2026-05-08
Phase: Post-12
Status: binding (BREAKING — auto-migrated)
Ships in: v0.13.0
Supersedes: D-025 §1 (single-record global state). Other clauses of D-025 (filter-fallback policy, no-auto-mutation, ambiguity gating, cross-project gate phrases) remain binding and unchanged.

### The decision

1. The state file at `~/.claude/rag-plugin/state/project-focus.json` becomes a v2 schema: a map of focus records keyed by **normalized workspace root** (`workspaces`) plus an optional explicit global record (`global`). The single-record v1 shape is auto-migrated on first read; the original v1 file is backed up exactly once to `project-focus.v1.bak.json`.
2. The workspace key is computed from the current cwd as `_norm(detect_git_root(cwd) or cwd)` — git root preferred, cwd fallback. Normalization resolves symlinks, posix-slashes, and lowercases on Windows so the same workspace produces the same key across runs on one machine.
3. `set` (auto or manual) writes to `workspaces[<current_workspace_key>]`. `set --global <name>` writes to `global` (manual name required; auto-detect is meaningless for global).
4. Effective focus precedence is **workspace > global > none**. The hook honors precedence on every prompt by reading the same engine code that powers `set`/`status` — no duplicate logic.
5. **Strict mismatch behavior.** When the state has focus records for OTHER workspaces but neither this workspace nor a global applies, the hook injects a neutral notice that does NOT include the foreign project's name. The phrase `not applied here` is literal, so Claude cannot accidentally use the foreign project name as a `project=` filter.
6. **Explicit-global labeling.** When global focus is the effective source, the injected reminder begins with `EXPLICIT GLOBAL FOCUS` and explains that the focus applies because the user used `--global`, not because it matches the current cwd. Workspace-source reminders carry no such label.
7. `clear` clears only the current workspace's record. `clear --global` clears only the global. `clear --all` clears both. Bare `clear` no longer wipes everything.
8. v1 → v2 migration is **strictly into `workspaces[<key>]` only**. v1 records are NEVER auto-promoted to `global` — global focus is opt-in and explicit; auto-elevating an old single-record state would re-create the leak this decision exists to fix.
9. The state file is **machine-local**. Workspace keys are absolute paths on the local disk. The plugin documents that `~/.claude/rag-plugin/state/` should be excluded from Syncthing / iCloud / OneDrive / Dropbox; cross-machine sync produces ghost entries.

### Non-violation of prior decisions

- **D-001 / D-022:** the plugin still does not call `search_knowledge_base`. The hook injects context; Claude does the call. Backend untouched.
- **D-002 (transport mix):** unchanged. The script enumerates projects via HTTP `GET /api/projects`; nothing else changed.
- **D-007 (hook posture):** the hook still never blocks or denies. Strict mismatch is a non-injection or a neutral-notice injection, not a deny.
- **D-008 (compact by default):** the workspace-source reminder shape is unchanged. The new global-source reminder is bounded; the new neutral notice is one paragraph.
- **D-012 (telemetry):** no telemetry added. The state file remains the only artifact.
- **D-016 / D-017 / D-027 (CLAUDE.md retrieval rule + classifier hook):** independent and unaffected. The two UserPromptSubmit hooks compose additively.
- **D-021 (decrease commands):** no command count change.
- **D-025 (project-focus contract):** §1 superseded; all other clauses preserved.

### Rollback path

If v0.13.0 misbehaves on real state files, users can revert by:

```bash
cp ~/.claude/rag-plugin/state/project-focus.v1.bak.json \
   ~/.claude/rag-plugin/state/project-focus.json
```

then downgrade to v0.12.x. The `.bak` is never overwritten on subsequent migrations, so this command is safe even if the user has already used v0.13 for a while (they only lose v0.13-era focus state, not their original v0.9.x state).

### Reverse only if

- A future ragtools release exposes a richer focus API that supersedes plugin-side state entirely.
- Workspace-key normalization proves unreliable across user environments (test plan §9 covers Windows + WSL specifically; widen the normalization rule, do not abandon the per-workspace model).
- Multi-project union focus per workspace is requested. Implement as a list value inside a workspace record (`{... "project_names": [...]}`); do not promote a second top-level key.

---

## RFC-001 — MCP-level enforcement of project focus (deferred from Phase 1)

Date: 2026-05-08
Status: deferred / RFC

D-028 closes the cross-workspace leak by making the plugin's hook cwd-aware, but the actual filtering of `search_knowledge_base` calls remains an honor-system contract: Claude must read the injected reminder and pass `project=<name>`. A future change could move enforcement into the ragtools MCP server itself by having it read the same state file (or a shared lookup) at startup and apply the focus as a default `project=` when the caller does not specify one.

This crosses the D-001 boundary (the plugin currently never wraps `search_knowledge_base`) and likely needs an upstream ragtools change. Out of scope for v0.13.0. Filed here so the option is recorded; revisit if honor-system bypass becomes a real complaint after v0.13 ships.

---

## D-029 — RAG is reference, not sole truth: route by source of truth

Date: 2026-06-28
Phase: Post-13 amendment
Status: binding
Ships in: v0.14.0
Relates to: D-016 (CLAUDE.md retrieval rule), D-017 / D-027 (retrieval-reminder hook + operational-intent classifier)

### Context

D-016 / D-017 / D-027 all addressed a single failure mode — **under-retrieval** (Claude saying "I don't have information" when the answer was in the knowledge base). The installed rule that fixed that leaned the other way: it treated a HIGH-confidence (≥0.7) KB hit as terminal truth, folded indexed *code* into the retrieval lane, and routed current vendor/API/pricing/security questions to "answer directly" from training memory with no verification path. The knowledge base — explicitly "my own docs, notes, code, and past decisions" — is a point-in-time snapshot that can lag the live code, the current product, and the current web. Presenting a stale snapshot as authoritative is the symmetric failure: **over-trust** of retrieval.

### The decision

1. The ragtools knowledge base is **project memory/reference, not the sole source of truth.** A KB hit is evidence of what was *written*, not proof of what is *true now*. It is authoritative only for **internal history / intent** (decisions, conventions, SOPs, requirements, prior research).
2. The injected CLAUDE.md block (`rules/claude-md-retrieval-rule.md`, bumped `v=0.3.0` → `v=0.4.0`) **routes by who owns the truth**, not by "is it in my workspace?":
   - Internal SOPs / decisions / conventions / requirements / project history → **knowledge base** (search first).
   - How the code or app actually behaves → **live code / runtime / tests** (inspect; don't trust an indexed snapshot).
   - Current vendor / product / API / SDK / pricing / limits / security → **official docs / web** (context7, WebFetch); training memory AND the KB can both be stale.
   - Local machine state → **filesystem / processes / `--help`** (the existing Section 0a override, preserved byte-for-byte).
3. **Answering discipline is source-type-aware.** A ≥0.7 hit is authoritative only for internal history; for implementation or external/vendor facts it is a *lead to verify* against the owning source before committing.
4. **Conflicts are surfaced, not silently resolved.** When the KB disagrees with the live code or current docs, state both sources explicitly and prefer the owning source (code/runtime for behavior; docs/web for external truth; KB for internal history).
5. **Answers report their source type** when it isn't obvious: `[from KB]` / `[from code]` / `[from official docs]` / `[assumption]`.
6. The **internal RAG-first guarantee is preserved**: the hard search-first rule still fires for internal-knowledge questions before any "I don't have information" answer.

### Why the always-loaded block, not a skill (re-affirms D-016)

The policy must govern zero-keyword prompts ("what is the process for X?"), and skills only load on keyword triggers. So the contract stays self-contained in the marker-delimited block injected into `~/.claude/CLAUDE.md` and delivered by `/config claude-md install`. No new hook is added — source routing is a reasoning judgment, and hooks "enforce, they don't reason" (ARCHITECTURE.md); the existing retrieval-reminder hook already "cannot tell knowledge questions from operational ones," so adding hook logic would amplify the over-retrieval pressure this decision corrects.

### Non-violation of prior decisions

- **D-001 / D-022:** the plugin still does not call `search_knowledge_base`; the block is instruction, Claude makes the call.
- **D-007:** no new blocking; the change is instruction text, not a deny.
- **D-016:** extends the retrieval rule; does not retract the always-loaded-block delivery mechanism.
- **D-017 / D-027:** the hook is untouched; its narrowed internal-only nudge stays compatible. Aligning the hook's reminder text + namespace is deferred as a separate hook-scoped change.

### Reverse only if

- A future ragtools release makes the KB authoritative for live code (e.g. a real-time index of HEAD with currency guarantees), which would retire the implementation-verify lane.
- Per-claim source tagging proves too verbose in practice — narrow it further (it is already scoped to "load-bearing claims, when the source isn't obvious"), do not drop the source-routing matrix.

---

## D-030 — `/report` files GitHub issues automatically after one confirmation

Date: 2026-06-29
Phase: Post-14 amendment
Status: binding
Ships in: v0.15.0
Relates to: D-024 (maintainer-feedback reports), D-001/D-022 (plugin never wraps search), D-007 (hooks ask, never deny)

### Context

D-024 deliberately stopped `/report` at local files + copy-paste issue bodies ("never uploads, never creates an issue"). In practice the copy-paste step was friction and produced no de-duplication, and the deterministic A-NNN/P-NNN routing already knew the correct target repo. The product decision is to close the loop: file the issues automatically, but only behind a single explicit confirmation and with safety rails.

### The decision

1. **Default flow:** `/report` generates local artifacts (unchanged), shows the routed plan (repo + title), then asks exactly one question — `Create GitHub issue(s) now? [yes/no]`. On `yes` it files via the GitHub CLI; on `no` it leaves local files only. This **supersedes the D-024 "never creates" clause**; all D-024 redaction/no-raw-logs/local-artifact guarantees remain binding.
2. **`--dry-run`** preserves the legacy local-only behavior (never asks, never creates) and always wins over `--create`. **Creation is never silent** — no `yes`, no issue.
3. **Mechanism:** the deterministic, unit-tested logic (routing, fingerprint, plan, dedup, create) lives in `scripts/rag_report.py`; the single human confirmation lives in `commands/report.md`. All GitHub access funnels through one `_run_gh` chokepoint (mockable; tests never touch real GitHub). `gh` is the only transport; if it is missing/unauthenticated the command **falls back to local-only** and says so. `Bash(gh:*)` is added to `report.md` allowed-tools (the single capability that enables creation). `taqat-techno/*` account-switch is performed around the create step.
4. **Routing:** application/runtime → `taqat-techno/rag`; plugin/Claude/behavior → `taqat-techno/plugins`. Routing now merges both finding lists **by `target`** (so a re-targeted finding is never silently dropped) and the previously-silent drop is surfaced. Transport faults route by **actual cause**: MCP-error and skipped-retrieval signals re-target to the app repo when the service was DOWN/BROKEN/not-UP.
5. **Duplicate prevention:** each body carries `<!-- rag-plugin-report:fingerprint:<hash> -->` (SHA-256 over sorted non-info finding IDs). Before creating, an open-issue search for the hash prevents re-filing; an existing match's URL is reported instead. Comment/update of an existing issue is intentionally out of scope (skip, don't risk a wrong update).
6. **Privacy:** redaction is unchanged from D-024; no raw/unrelated session logs are attached; only sanitized findings + clipped, secret-redacted signal snippets.

### Non-violation of prior decisions

- **D-001 / D-022:** generation still never calls `search_knowledge_base`; `/report` touches no knowledge-base data. Issue creation is a `gh` call, not an MCP write.
- **D-007:** no new hook; nothing blocks/denies. The confirmation is a normal command prompt.
- **No destructive command changed; `/doctor` does not create issues.**

### Reverse only if

- Auto-creation produces misfiled or noisy issues in practice — tighten the confirmation (e.g. per-repo yes/no) or revert `/report` to D-024 local-only, rather than removing routing.
- A future change wants comment/update of existing issues — design an explicit, idempotent update path first (the current skip-on-duplicate is the safe default).

---

## D-031 — Advisory hooks must be fail-open by construction (not just script-level)

Date: 2026-06-29
Phase: Post-15 amendment
Status: binding
Ships in: v0.15.1
Relates to: D-007 (hooks ask, never deny), D-017 / D-027 (retrieval-reminder hook), D-025 / D-028 (project-focus hook); see `RAG_PLUGIN_HOOK_INVESTIGATION_REPORT.md`

### Context

The two `UserPromptSubmit` advisory hooks were invoked as the raw
`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py` (unchanged since v0.3.0). When
the host does not expand `${CLAUDE_PLUGIN_ROOT}` (reported on Cowork / headless
Windows), the variable is unset, or the script is missing, **Python exits 2**
because it cannot open the file. Per the Claude Code hook spec, **exit 2 on
`UserPromptSubmit` is a *blocking* error** — the prompt is cancelled before the
model request ("spinner / no response / no model call"). The scripts already
`sys.exit(0)` on every internal error, but **that fail-safe cannot run if the
script file never loads** — the failure is one layer *above* the script, at the
command-invocation layer, which was unguarded.

Four of the five causal links are proven by repo code + the official hook spec +
empirical tests; only the Cowork-specific non-expansion *trigger* needs runtime
Cowork logs. The fix is applied regardless, because an advisory/injection hook
must never be *able* to cancel a prompt.

### The rule (binding)

1. **Advisory / injection / reminder hooks MUST be fail-open by construction.**
   Any failure to resolve, load, or run them must yield exit `0`, never the
   blocking exit `2` (and preferably never any non-zero).
2. **Script-level `sys.exit(0)` is necessary but NOT sufficient.** The fail-open
   guarantee must exist *above* the script — in the command-invocation layer —
   so a path-resolution failure (the script never loading) still cannot block.
3. **Any hook that can block a user prompt must be *intentionally* blocking and
   documented as such.** Do not make an intentionally-blocking hook fail-open.

### The mechanism

- `hooks/hooks.json` no longer names a script file on the interpreter command
  line for **any** hook. Each command runs a tiny inline `-c` bootstrap. Because
  `-c` takes **no script-file argument**, the "can't open file → exit 2" branch
  is *structurally impossible*. The bootstrap resolves the plugin root from the
  `CLAUDE_PLUGIN_ROOT` **runtime environment variable** (with the host-expanded
  `${CLAUDE_PLUGIN_ROOT}` path as a secondary fallback) and runs
  `hooks/hook_launcher.py` only if it actually exists; otherwise it exits 0.
- **Interpreter fallback (v0.15.1):** each command chains
  `python3 -c … || python -c … || py -3 -c …` so the hook still runs where
  `python3` is not the interpreter name (e.g. python.org Windows). Safe by spec:
  the only blocking code is `2`, so a missing interpreter (127) or a stray shell
  parse error is non-blocking; and because the bootstrap exits 0 on every
  fail-open path, the chain only advances when an interpreter is genuinely absent
  (no double execution of the real hook logic).
- `hooks/hook_launcher.py` resolves the real target script *beside its own*
  `__file__`, runs it in-process via `runpy` (stdin/stdout pass through, so
  `additionalContext` / `permissionDecision` injection is preserved). It has two
  per-target modes: **advisory** (the `UserPromptSubmit` injectors) normalizes
  **every** exit — even a target `sys.exit(2)` — to `0`; **guarded** (the lock
  hook) **passes the target's own exit code through** so a deliberate decision
  survives. Both modes fail open (exit 0) on a path-resolution failure or an
  unexpected exception.
- **The PreToolUse lock-conflict hook IS routed through the launcher in GUARDED
  mode (v0.15.1 enhancement).** Its `ask` (and any future deliberate block via
  exit 2) passes through unchanged — D-007 preserved — but a path-resolution
  failure or an internal crash now fails open instead of exiting 2. This fixes a
  worse-than-advisory false-block: an unresolved `${CLAUDE_PLUGIN_ROOT}`
  previously made the PreToolUse Bash hook exit 2 and block **every Bash tool
  call**. Guarded mode removes the false block without weakening the `ask`.
- **Report-engine detector `P-013`:** `scripts/rag_report.py` flags any advisory
  `UserPromptSubmit` command in `hooks.json` that can return a blocking exit code
  (raw `python ${VAR}/...py` without a fail-open wrapper) — **High** when the
  risky command is present, **Critical** when runtime log signatures
  (`can't open file …hooks…py` / `[Errno 2]` / literal `${CLAUDE_PLUGIN_ROOT}`)
  confirm the path actually fired. P-013 emits only on **static** evidence
  (current `hooks.json` is actually risky); runtime signatures only *escalate*,
  because the same stderr text appears in transcripts that merely *discuss* the
  failure. P-013 **supersedes** the old generic `P-012` ("MCP error phrases") as
  the lead plugin issue — P-012 could never have detected this hook-fatal failure.

### Non-violation of prior decisions

- **D-007:** advisory hooks still never deny; this *strengthens* "never block" by
  making blocking impossible. The lock hook's `ask` is preserved via guarded
  mode (exit code passes through) — only its path-resolution *false-block* is
  removed.
- **D-017 / D-027 / D-025 / D-028:** the target scripts' logic, thresholds, and
  injection behavior are unchanged — only the invocation layer moved.
- **No new hook is added** (the launcher is a helper invoked by the existing
  hooks, not a new hook registration).

### Reverse only if

- Claude Code guarantees host-side `${CLAUDE_PLUGIN_ROOT}` expansion *and* an
  always-blocking-free invocation on every surface (incl. Cowork) — even then,
  keep the launcher; it is pure upside and risk-free.
- A future advisory hook genuinely needs to block — then it is by definition not
  advisory; document it as intentionally blocking and route it outside the
  launcher.

---

## D-032 — Plugin awareness of the Code Knowledge Index MCP tools; `set_project_mode` stays write-gated until the app-side redaction fix ships

Date: 2026-07-01
Phase: Post-16 amendment
Status: binding
Ships in: v0.17.0
Relates to: D-001 (plugin never wraps `search_knowledge_base`), D-022 (plugin uses MCP ops tools freely), D-021 (skill workflow over new command), D-029 (RAG is reference, not sole truth)

### Context

ragtools grew a Code Knowledge Index surface beyond the ~22-tool inventory D-022 fixed: `search_project_context` (layered code/docs/config retrieval), `find_definition` (code-graph symbol lookup), `secret_audit` (scans indexed content for embedded secrets), and `set_project_mode` (sets a project's indexing mode: `docs` / `code` / `general`, default `docs`). None of these tools existed when D-022 was written, and the plugin had zero references to any of them anywhere — no hook, rule, skill, or command.

Independent verification against the live ragtools source (not just app-side release notes) found that the production indexing write path does not invoke the app's content-level secret-redaction step. This affects **every** project's routine indexing — the watcher, manual reindex, project-add auto-index — regardless of mode, not only `code`/`general` ones. Until that is fixed and confirmed app-side, the plugin must not give a user any reason to believe enabling a richer indexing mode is risk-free, and should not stay silent about the fact that this also applies to projects already indexed today.

A separate observation, not resolved by this decision: the MCP's live tool registry was also found to include `add_project`, which `rules/mcp-envelope.md` §8 still lists as a deliberately excluded tool (blast-radius reasoning: arbitrary filesystem path from an agent is an injection vector). That contradiction needs its own review and is explicitly out of scope here.

### The decision

1. **`search_project_context` and `find_definition` are content/discovery tools and fall under D-001's existing boundary**, the same as `search_knowledge_base`: Claude calls them directly; the plugin documents *when* to use them (routing guidance in the CLAUDE.md retrieval rule and the skill) but never wraps, mediates, or calls them on Claude's behalf.
2. **`secret_audit` is an ops/audit tool and falls under D-022's carve-out**: the plugin may build a skill workflow and a thin command subcommand around it, the same as `project_status` or `list_project_files`. It needs no destructive-write gate (§6.3 of `mcp-envelope.md`) because it never mutates anything — but its *output* must always carry the redaction-bypass caveat (point 4 below) until that caveat is retired by a future decision.
3. **`set_project_mode` is a write tool, held to write-tool discipline (§6 of `mcp-envelope.md`) plus an additional gate this decision adds.** It may be *documented* (so Claude can explain it correctly when asked) but **no plugin command, skill workflow, or hook may call it to actually change a project's mode** until both:
   a. A plugin maintainer has confirmed, from the live ragtools release notes, that the production indexing write path applies content-level secret redaction; and
   b. `rules/state-detection.md`'s `KNOWN_SAFE_FLOOR` constant has been updated to reflect that confirmation.
   Until then, any code path that would reach `set_project_mode` for an actual mode change must refuse with a clear, specific reason — not a generic error.
4. **The redaction-bypass risk is not scoped to Dev Mode.** Because the affected write path is the *general* indexing pipeline, used by every project regardless of mode, `/doctor --full` recommends running `secret_audit` against existing projects independent of any interest in Dev Mode. This is a one-time, read-only recommendation, not an automatic scan: `/doctor` names the action; the user (or Claude, asked once) runs `/projects audit <id>`.
5. **`add_project`'s reappearance in the live tool registry is explicitly NOT addressed by this decision.** `rules/mcp-envelope.md` §8's exclusion of it stands until a separate decision revisits it.
6. **No new hook.** This decision is implemented entirely in rules, skills, and existing-command extensions (`/doctor`, `/projects`). The plugin's hook surface (`lock_conflict_check.py`, `prompt_retrieval_reminder.py`, `project_focus_inject.py`) is unchanged — hooks fire on every matching event and are reserved for the narrow guardrails they already cover. A slow-moving, judgment-dependent safety gate like this one belongs in skill-level reasoning plus an explicit, user-invoked one-time command action, not automatic per-prompt interception.

### Non-violation of prior decisions

- **D-001 / D-022:** the content-vs-ops boundary is extended consistently, not redrawn. `search_knowledge_base` remains the only tool the plugin can never call; `search_project_context` and `find_definition` join it under the same "Claude calls directly" principle by analogy, not by exception.
- **D-021:** no new top-level command. `secret_audit` and project-mode status land as a subcommand and a field of the existing `/projects` command; the routing/awareness logic lives in the skill, not a new command.
- **D-007:** nothing here introduces a hook that could block or deny — there is no new hook at all.
- **D-029:** the "RAG is reference, not sole truth" framing is the model for how the plugin treats the app's own redaction guarantee — it is not assumed safe by default, and the conflict between what the app claims and what the code does is surfaced explicitly rather than picked silently.

### Reverse only if

- The app-side redaction-bypass fix ships and is confirmed — then a follow-up decision raises `KNOWN_SAFE_FLOOR` in `rules/state-detection.md` and `set_project_mode` gets wired into a real, gated `/projects mode <id> <mode>` subcommand. This decision's restriction in point 3 is what gets reversed; points 1, 2, 4, and 6 are not contingent on the app fix and stay as-is.
- A future ragtools release exposes a clean boolean capability flag (rather than requiring version-string comparison) for the redaction guarantee — adopt it in `rules/state-detection.md` in place of the version-floor comparison.
