# Changelog

All notable changes to `rag-plugin` are documented here. Format is loosely based on [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.3.3] — 2026-04-14

Second retraction in the v0.3.x MCP-wiring saga. Drops the Python launcher (`scripts/rag_mcp_launcher.py`) introduced in v0.3.1 and calls `rag serve` directly from `.mcp.json`, matching the pattern every other working plugin in `~/.claude/plugins/cache/` uses (`chrome-devtools`/`context7`/`playwright`/`azure-devops` all call `npx` directly — no Python wrapper in the middle).

### The bug v0.3.2 left behind

v0.3.2 shipped the correct **flat shape** `.mcp.json` and kept the launcher. Symptom: `ListMcpResourcesTool` showed `plugin:rag:ragtools` registered, `/reload-plugins` counted the server, but `ToolSearch` found zero ragtools tools and the model could not call `search_knowledge_base`. The MCP handshake was failing.

Root cause: **Python's `os.execvp` on Windows does not preserve stdio pipe inheritance.** On POSIX, `execvp` atomically replaces the current process image, so the stdin/stdout/stderr pipes that Claude Code opened to the Python launcher transfer cleanly to the spawned `rag.exe`. On Windows, `os.execvp` is a thin wrapper over `_spawnv(_P_OVERLAY, ...)` — the Python parent exits and a new process is started, but the inherited pipe handles are not guaranteed to survive that transition. The spawned `rag.exe` never receives the `tools/list` RPC that Claude Code is already waiting on, the call silently times out, and no tool schemas reach the deferred-tool registry.

The launcher worked when probed directly via `python rag_mcp_launcher.py --dry-run` (that path doesn't exec), and the underlying `rag.exe serve` worked when invoked directly over stdio. Both parts were fine in isolation. The handoff between them was the bug.

### Fixed
- **`rag-plugin/.mcp.json`** — rewritten to spawn `rag` directly. Final canonical form:
  ```json
  {
    "ragtools": {
      "type": "stdio",
      "command": "rag",
      "args": ["serve"]
    }
  }
  ```
  Same shape as `devops-plugin/.mcp.json`, same pattern as every working plugin on disk. No Python middleman, no `os.execvp`, no launcher script.
- **`scripts/rag_mcp_launcher.py`** — **deleted**. No longer needed. The service-query → PATH-probe cleverness it provided was solving a problem that doesn't actually exist: every supported install mode already puts `rag` on PATH (packaged Windows installer adds `C:\Users\<you>\AppData\Local\Programs\RAGTools` by default — verified on the reporter's machine via `where rag`; packaged macOS requires the user to add the tarball directory per upstream docs; dev `pip install -e .` exposes `rag` as a pyproject console-script). The v0.3.0 bug was **hardcoding the wrong binary name** (`rag-mcp` instead of `rag`), not "no binary on PATH." Fixing the name removes the need for the runtime-resolution launcher entirely.

### Changed
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` schema assertions updated. Direct-spawn is now the rule: any `command` that is `python` / `python3` / `py` with an arg referencing `rag_mcp_launcher.py` is surfaced as a distinct `ERROR — plugin .mcp.json uses the legacy Python launcher which breaks stdio on Windows. Upgrade to v0.3.3+`. The PATH-resolution check remains; the launcher-file check is dropped.
- **`rag-plugin/commands/rag-doctor.md`** — MCP registrations row error documentation rewritten for direct-spawn. The launcher error state is kept as a diagnostic for users still on v0.3.1/v0.3.2, with the upgrade remediation.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.2` → `0.3.3`.
- **`rag-plugin/README.md`** — status badge and auto-wire bullet updated.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A simplified. No more launcher explanation — just the direct-spawn snippet and a Prerequisites bullet: `rag` must be on PATH. Legacy section retained with three version entries (v0.2.0/v0.3.0 wrong command, v0.3.1 wrong schema, v0.3.2 launcher stdio bug).
- **`rag-plugin/docs/decisions.md`** — new **D-020**: "plugin-level `.mcp.json` spawns the target binary directly; Python wrapper scripts are an anti-pattern because of `os.execvp` stdio-pipe semantics on Windows." Supersedes the launcher portion of D-018 (D-019 already superseded the schema portion). D-015's original flat-shape + direct-spawn posture is fully restored.

### Rationale
The v0.3.x series has now cycled through three wiring strategies: (1) flat shape + wrong command name (v0.3.0, broken on packaged Windows), (2) wrapped shape + Python launcher (v0.3.1, tool schemas never loaded), (3) flat shape + Python launcher (v0.3.2, stdio pipe handoff broken on Windows). v0.3.3 is strategy (4): flat shape + direct spawn of the correct binary. This matches the empirical ground truth of what every other MCP plugin on the reporter's machine actually does, and it eliminates the entire class of "Python wrapper middleman" failure modes at once.

The lesson that justifies D-020 is worth stating plainly: **when wiring a stdio MCP server, your `.mcp.json` command should be the real binary. Not a script that spawns it, not a launcher, not a shim. If no single literal command works, fix the command at install time or via a user-level `.mcp.json` fallback — do not wrap it in another process.** Wrappers add a pipe-handoff hazard on Windows for no practical benefit.

### Edge case: user-level fallback

For the rare install where `rag` is genuinely not on PATH (user skipped the installer's "Add to PATH" option on Windows, or did not set up PATH on macOS), `/rag-setup` branch C.1–C.2 still works: it reads `GET http://127.0.0.1:21420/api/mcp-config` to get the absolute binary path from the running service, then writes a user-level `~/.claude/.mcp.json` with the **wrapped** shape and that absolute path. Duplicate-registration cleanup via `/rag-config mcp-dedupe` handles the plugin-level-vs-user-level coexistence. This flow is unchanged from v0.1.0 and is the documented fallback.

### Verification
- `where rag` on the reporter's Windows machine returns `C:\Users\ahmed\AppData\Local\Programs\RAGTools\rag.exe` — confirming `rag` is on PATH by default after the installer runs (the reporter's screenshot also shows `C:\Users\ahmed\AppData\Local\Programs\RAGTools` in the user Path env var).
- `where rag-mcp` returns nothing on packaged Windows — this is why hardcoding `rag-mcp` in v0.2.0/v0.3.0 was broken, and also why `rag` is the correct choice (not `rag-mcp`).
- `python plugins/validate_plugin.py rag-plugin` passes.
- JSON sanity: `python -c "import json; d=json.load(open('plugins/rag-plugin/.mcp.json')); assert d['ragtools']['command']=='rag' and d['ragtools']['args']==['serve']"` exits 0.
- After Claude Code restart: `/mcp` shows `plugin:rag:ragtools` with tools enumerated; `ToolSearch query="+ragtools"` returns `mcp__plugin_rag-plugin_ragtools__search_knowledge_base` and siblings; the retrieval-reminder hook's recommended call is actually invocable.

## [0.3.2] — 2026-04-14

Hotfix retraction. v0.3.1 over-corrected the v0.3.0 bug and shipped a `.mcp.json` in the **wrapped** shape (`{"mcpServers": {"ragtools": {...}}}`). This turned out to be wrong for plugin-level `.mcp.json` files. Claude Code's plugin loader expects the **flat** shape (`{"ragtools": {...}}` with no wrapper) for plugin-level registrations. `/mcp` reported the server as "present" and `/reload-plugins` counted it among the loaded servers, but `ToolSearch` could not find any ragtools tool by name and the model could not call `search_knowledge_base`.

Empirical confirmation from `~/.claude/plugins/cache/`: every working plugin ships the flat shape. Checked: `chrome-devtools-mcp`, `context7`, `playwright`, `azure-devops` (from `devops-plugin`), and rag-plugin v0.2.0 / v0.3.0 itself. Only v0.3.1 shipped the wrapped shape, and only v0.3.1 was broken. The wrapped shape is for user-level (`~/.claude/.mcp.json`) and project-level (`<repo>/.mcp.json`) files, not plugin-level.

### Fixed
- **`rag-plugin/.mcp.json`** — reverted to the flat shape while **keeping the launcher**:
  ```json
  {
    "ragtools": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]
    }
  }
  ```
  The launcher (`scripts/rag_mcp_launcher.py`) was the right idea and stays — it still resolves the canonical ragtools binary at runtime via `GET /api/mcp-config` → `rag` on PATH → `rag-mcp` on PATH → fail loud, which is what makes the plugin work across dev and packaged installs without hardcoding a binary name that only exists in one of them.

### Changed
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` schema assertion inverted. It now asserts the **flat shape** (top-level `ragtools` key) for plugin-level `.mcp.json`, not the wrapped shape. If a `mcpServers` wrapper is detected in a plugin-level file, surfaces a distinct `ERROR — plugin .mcp.json uses wrapped shape (mcpServers); plugin-level files require the flat shape — unwrap it`. User-level and project-level files continue to use the wrapped shape — the two scopes have different schemas.
- **`rag-plugin/commands/rag-doctor.md`** — the MCP registrations row's error documentation rewritten to describe the correct flat-shape rule and the wrapped-shape footgun.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.1` → `0.3.2`.
- **`rag-plugin/README.md`** — status badge updated.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A snippet reverted to the flat shape with the launcher. The D-018 wrapped-shape recommendation is explicitly retracted in the reference text.
- **`rag-plugin/docs/decisions.md`** — new **D-019** records the retraction: D-018's schema change was wrong, D-015's original flat-shape claim was correct all along. The launcher portion of D-018 stands (it fixes the real bug — the cross-install-mode command resolution). Only the schema portion is retracted.

### Rationale
The v0.3.0 bug was **one** bug (command `rag-mcp` not on PATH in packaged Windows installs), not two. My v0.3.1 changelog claimed it was also a schema bug and cited the workspace `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md` which documents the wrapped shape. That reference applies to user/project-level `.mcp.json` files, not plugin-level files. I missed the distinction and introduced a differently-broken schema on top of the fix for the command bug. The fix for v0.3.2 is simple: keep the launcher, revert the schema, document the scope rule so it does not happen again.

### Verification
- Before-and-after: `cat ~/.claude/plugins/cache/taqat-techno-plugins/rag/0.3.2/.mcp.json` shows flat shape with launcher.
- `python plugins/rag-plugin/scripts/rag_mcp_launcher.py --dry-run` resolves to `C:\Users\ahmed\AppData\Local\Programs\RAGTools\rag.exe serve` via the running service.
- Compared against `~/.claude/plugins/cache/claude-plugins-official/chrome-devtools-mcp/latest/.mcp.json` byte-for-byte structure — both use identical flat shape.
- `/mcp` after restart: `plugin:rag:ragtools` should now expose `search_knowledge_base`, `list_projects`, `index_status` to the model (requires Claude Code session restart so the deferred-tool registry re-indexes).

## [0.3.1] — 2026-04-14

Hotfix for a broken plugin-level MCP auto-wiring. Two compounding bugs in v0.3.0's `.mcp.json` prevented Claude Code from ever loading the `ragtools` MCP server on packaged Windows installs: the file shipped the flat shape without the `mcpServers` wrapper (which the plugin loader rejects for stdio servers), and it hardcoded `command: "rag-mcp"` which only exists on dev pip installs — packaged Windows ships `rag.exe` only. `/mcp` reported *"Failed to reconnect to plugin:rag:ragtools"* and the doctor `mcp-dedupe status` row did not catch either bug because it only counted duplicates. Closes the gap.

### Added
- **`scripts/rag_mcp_launcher.py`** — new cross-mode Python launcher (stdlib only, ~100 lines). Resolves the canonical ragtools binary at runtime and `os.execvp`-replaces itself with it so Claude Code's stdio pipe connects to the real MCP server directly. Resolution order: (1) `GET http://127.0.0.1:21420/api/mcp-config` with a 1-second timeout — the running service is the authoritative source for this install mode; (2) `rag` on PATH → exec `rag serve` (packaged Windows/macOS/Linux); (3) `rag-mcp` on PATH → exec `rag-mcp` (dev pip install); (4) fail loudly to stderr with exit code 127 so `/mcp` surfaces the failure. Supports `--dry-run` for smoke-testing (prints the resolved `{command, args}` as JSON and returns without exec).
- **D-018** in `docs/decisions.md` — binding decision. Plugin-level `.mcp.json` uses the wrapped shape (`{"mcpServers": {...}}`) and delegates command resolution to the cross-mode launcher. Overrides the flat-shape claim in D-015 for stdio servers, which was based on the `devops-plugin` pattern but empirically does not work for `rag-plugin` (confirmed by `/mcp` failure; corroborated by every stdio example in `claude-plugins-official-main/` using the wrapped shape). Does not touch SSE/HTTP plugins — flat shape remains acceptable there.

### Changed
- **`rag-plugin/.mcp.json`** — rewritten. Now uses `{"mcpServers": {"ragtools": {"type": "stdio", "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/rag_mcp_launcher.py"]}}}`. The `${CLAUDE_PLUGIN_ROOT}` variable is expanded by Claude Code's plugin loader at registration time.
- **`rag-plugin/commands/rag-config.md`** — `mcp-dedupe status` hardened. No longer just counts duplicates. Now parses the plugin-level `.mcp.json` and asserts four invariants: file exists and is valid JSON; top-level `mcpServers.ragtools` key is present (catches the v0.3.0 schema bug); `command` resolves on PATH via `shutil.which` (catches the wrong-command bug); and when the launcher pattern is detected, the launcher script file is readable. Plugin-level failures are surfaced before duplicate-count issues because a broken plugin-level registration means ragtools will not load at all.
- **`rag-plugin/commands/rag-doctor.md`** — MCP registrations row documents the five new error states produced by the hardened `mcp-dedupe status`: schema bug, missing wrapper, command-not-on-PATH, launcher-missing, and the original missing-file case. Each maps to a clear remediation.
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.3.0` → `0.3.1`.
- **`rag-plugin/README.md`** — the "Auto-wire" bullet now reflects the cross-mode launcher pattern and no longer assumes `rag-mcp` is on PATH.
- **`rag-plugin/skills/ragtools-ops/references/mcp-wiring.md`** — Option A rewritten to document the wrapped shape + launcher. The old flat-shape snippet is retained as "legacy (v0.3.0 and earlier)" with a note explaining why it stopped working.

### Rationale
This is a shipped bug, not a feature. The v0.3.0 plugin was demonstrably broken for the primary install target (packaged Windows) and the doctor check that was supposed to catch MCP-wiring regressions did not parse the file it was checking. The fix has to be generic (no single command name works across every supported install mode), so command resolution is delegated to a launcher script that asks the running service first and falls through to PATH probing. The schema fix is the canonical Claude Code plugin shape documented in `CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`. The doctor hardening is the regression-prevention layer the original bug report explicitly called out as missing.

### Verification
- Static validation: `python plugins/validate_plugin.py rag-plugin` passes.
- Schema sanity: `python -c "import json; d=json.load(open('plugins/rag-plugin/.mcp.json')); assert 'ragtools' in d['mcpServers']"` exits 0.
- Launcher dry-run: `python plugins/rag-plugin/scripts/rag_mcp_launcher.py --dry-run` prints `{"command": "<resolved path>", "args": ["serve"]}` on packaged Windows install where `rag.exe` is on PATH.
- Live MCP: after a Claude Code restart, `/mcp` reports `plugin:rag:ragtools connected` and `mcp__plugin_rag-plugin_ragtools__search_knowledge_base(query=...)` returns results instead of `Failed to reconnect`.

## [0.3.0] — 2026-04-14

Post-roadmap amendment #3. Ships the **Tier-2 guided-enforcement UserPromptSubmit retrieval-reminder hook** with lightweight observability. Closes the advisory-only gap in the D-016 CLAUDE.md rule by adding a harness-enforced layer that injects a system reminder at the moment of answering, not just at session start. Also includes the canonical marker-wrapped upgrade to `~/.claude/CLAUDE.md` on the development machine.

### Added
- **`rag-plugin/hooks/prompt_retrieval_reminder.py`** — new `UserPromptSubmit` hook script, ~230 lines. Python 3 stdlib only (`json`, `os`, `re`, `sys`, `time`, `urllib.*`). Two-phase decision: Phase A shape gate (question-like OR possessive-domain, NOT current-context), Phase B domain probe via `GET /api/search?top_k=1&compact=true` with a 1-second timeout. Injects a ~10-line reminder via `hookSpecificOutput.additionalContext` when both phases pass. Silent-passes in every other case. Honors D-007 (never deny, never block), D-008 (compact reminder ~200 tokens), and D-012 (observability log contains zero user content).
- **`rag-plugin/scripts/analyze_hook_decisions.py`** — new maintainer tool, ~150 lines. Reads `~/.claude/rag-plugin/hook-decisions.log` and prints aggregate stats: decisions by action tag, probe-score histogram, shape-gate pass rate, reminder-injection rate, hook version distribution, tuning hints. Read-only, stdlib only, takes no arguments.
- **`/rag-config hook-observability {status|on|off|analyze|clear}`** — new subcommand group. Controls the hook-decisions log. Default **enabled** (opt-out via `~/.claude/rag-plugin/.hook-observability-disabled` marker file). `analyze` invokes the analyzer script; `clear` deletes the log with typed `CLEAR` confirmation.
- **Observability log at `~/.claude/rag-plugin/hook-decisions.log`** — JSONL, append-only. Schema: `{ts, shape_match, probe_match, probe_top_score, action, prompt_length, hook_version}`. Zero user content. D-012 aligned.
- **D-017** in `docs/decisions.md` — the binding decision, terminology correction ("Tier 2 = guided, Tier 3 = strong"), observability-first escalation rationale, D-001/D-012 non-violation argument.

### Changed
- **`rag-plugin/hooks/hooks.json`** — now registers two hooks: the existing `PreToolUse` Bash lock-conflict guardrail AND the new `UserPromptSubmit` retrieval-reminder. Both use the plugin-level format with `matcher` field (`"Bash"` and `"*"` respectively).
- **`rag-plugin/.claude-plugin/plugin.json`** — version `0.2.0` → `0.3.0`.
- **`rag-plugin/commands/rag-config.md`** — four feature groups now (was three). New `hook-observability` subcommand group documented with per-subcommand steps. Unified `status` dashboard now reports four rows.
- **`rag-plugin/ARCHITECTURE.md`** — layer diagram updated with the new `UserPromptSubmit` hook, the new `scripts/` directory, and the plugin's right to inject `hookSpecificOutput.additionalContext`. Forbidden list unchanged (the hook never wraps or calls `search_knowledge_base` — the `/api/search` probe reads only `results[0].score`, never result content).
- **`rag-plugin/README.md`** — status badge `v0.2.0` → `v0.3.0`. Added "Tier-2 UserPromptSubmit retrieval-reminder hook" as a new capability bullet under "What this plugin IS". Updated "What we record" section to document the hook-decisions log schema alongside the existing telemetry description.
- **`~/.claude/CLAUDE.md`** (on the development machine) — canonical marker-wrapped upgrade applied via direct splice. Manually-written Section 0 (29 lines, no markers) replaced with the marker-wrapped v0.2.0 canonical block (33 lines). Backup at `~/.claude/CLAUDE.md.bak-pre-claude-md-install`. This is outside the plugin repo and does not ship with the release, but the operation is documented here for completeness.

### Rationale
The D-016 CLAUDE.md rule was correct as a first step but insufficient on its own. User incident: *"What is the process for emergency assistance requests?"* — rule loaded, still skipped. Two root causes:

1. **CLAUDE.md is advisory.** The harness doesn't enforce it; Claude reads it and chooses whether to follow it per-turn.
2. **Model judgment gap.** Even when the rule is read, classifying a question as "domain" vs "general" is fuzzy without explicit `my notes` signals.

Fix: add a **harness-enforced** layer via `UserPromptSubmit`. The hook always runs. When the shape heuristic + domain probe both pass, a reminder is injected into the model's context **at the moment of answering** (not at session start). Claude can still choose to ignore the reminder, but failure mode #1 (forgot the rule) is closed, and failure mode #2 (misjudged the domain) is sharply reduced by surfacing the reminder right when the decision is being made.

Observability is paired with the hook so the Tier-2-vs-Tier-3 decision can be data-driven. If the reminder alone is sufficient, we never ship Tier 3 (pre-fetch) and save the context cost. If not, we have the data to justify the escalation.

**Key safety properties preserved:**
- Hook never blocks, denies, or throws. Silent-pass on any error.
- Probe is a confidence check (`results[0].score` only), not a retrieval — never reads content.
- Observability log contains zero user content (metadata only).
- Default-enabled observability is consistent with diagnostic syslogs; opt-out is one command.
- `D-001` (ops-only, never search) non-violation: registering a reminder ≠ wrapping the MCP.

### Verification
- 9 unit tests via echo-pipe (current-context, trivia, low-probe, high-probe, service-down, malformed JSON, no user_prompt, possessive domain, question+current-context). All pass.
- Emergency-assistance regression test: probe returned score 0.813, reminder injected correctly.
- Analyzer script run against 9 real log entries: stats render correctly, tuning hints fire appropriately.
- Validator: 9 commands, 1 skill, 1 hooks file, 0 errors (same 2 documented stale-validator false positives on hooks.json from Phase 6).

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
