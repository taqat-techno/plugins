# Changelog

All notable changes to `rag-plugin` are documented here. Format is loosely based on [Keep a Changelog](https://keepachangelog.com/). Versioning follows [SemVer](https://semver.org/).

## [0.5.0] — 2026-04-18

MCP v2.5.0 integration. The plugin now uses the full 22-tool MCP surface — 3 core + 9 project ops (default ON) + 9 debug (default OFF, user-granted) — for diagnostics, project introspection, ignore-rule management, and guarded writes. **Command count stays at 6 user-facing commands + 1 maintainer-only**; every new capability is delivered as a skill workflow that auto-activates on user intent, rather than as a new slash command. Every existing command is now **generic** (works standalone without required arguments, accepts optional parameters).

### Added
- **`rules/mcp-envelope.md`** — new shared rule codifying the MCP envelope contract: error-code-first branching, mode-based dispatch, three-tier fallback chain (MCP → HTTP → CLI), tool-grant awareness, cooldown discipline, confirm-token guard for `reindex_project`. Referenced by every MCP-using command and by the `ragtools-ops` skill. Single source of truth for envelope handling; commands do not inline the discipline.
- **Skill workflows 2.5.1–2.5.9** in `skills/ragtools-ops/SKILL.md` — auto-activating MCP workflows, each triggered by user-intent phrasing:
  - **2.5.2 Project health** — `list_projects` → `project_status` for a rich per-project card on "is project X healthy?".
  - **2.5.3 Why-not-indexed workflow** — `list_project_files` → `get_project_ignore_rules` → `preview_ignore_effect` → offer `remove_project_ignore_rule` + `run_index`. Activates on "why isn't file F in search?", "file F is missing", etc. Entirely new capability.
  - **2.5.4 Add-ignore-rule workflow** — preview → typed `ADD` gate → `add_project_ignore_rule` → offer `run_index`. Activates on "exclude X", "ignore tmp/", "don't index node_modules".
  - **2.5.5 Remove-ignore-rule workflow** — refuses to remove `built_in` rules (explains why); typed `REMOVE` gate for `config_project` rules.
  - **2.5.6 Reindex decision tree** — `run_index` incremental first (2s cooldown), drift detection (deleted > 5 AND indexed < 2), escalation to `reindex_project` with typed `DELETE` and 30s cooldown only on drift.
  - **2.5.7 Tool-grant audit** — shows which MCP tools are enabled vs disabled, names the toggle path for each. Activates on "what tools are enabled?".
  - **2.5.8 Multi-project search preparation** — constructs the `projects=[...]` spec but does NOT call `search_knowledge_base` (D-001 preserved).
  - **2.5.9 MCP failure handling** — uniform fallback-chain discipline across all workflows.
- **D-022** in `docs/decisions.md` — binding decision refining D-001. Plugin uses MCP **ops tools** freely (all 18 non-search tools across core, project-ops, debug tiers); plugin still never wraps `search_knowledge_base`. Explicit table of what's allowed vs forbidden. Non-violation notes against D-001, D-005, D-007, D-008, D-012, D-015, D-017, D-020, D-021.
- **New `/rag-projects` subcommands (v0.5.0)** — `status <id>` (uses `project_status`), `summary <id> [<top_n>]` (uses `project_summary`), `files <id> [<limit>]` (uses `list_project_files`). All read-only; envelope handling per `rules/mcp-envelope.md`.

### Changed
- **`commands/rag-doctor.md`** — Mode E (default fast probe) now prefers `mcp__plugin_rag_ragtools__index_status` + `list_projects` (+ optional `service_status`), with HTTP `/api/status` + `/api/projects` + `/api/watcher/status` as fallback when the MCP is in failed mode or not loaded. Mode D (`--full`) prefers `system_health` + `crash_history` for structured diagnostic output, falls back to wrapping `rag doctor` CLI when the debug tools aren't granted (with an admin-UI toggle hint). Mode B (`--logs`) prefers `tail_logs` (has filesystem fallback — works even in degraded mode) and supplements with `recent_activity` when granted. The `rag-log-scanner` Haiku agent contract is unchanged — still classifies findings — but now receives log content from the MCP tool rather than a direct disk read.
- **`commands/rag-projects.md`** — now **generic and standalone**: running `/rag-projects` with no arguments defaults to `list`. Subcommand whitelist updated to document which MCP tool each subcommand uses (`list` → core, `status`/`summary`/`files` → project-ops, `rebuild` → `reindex_project` with confirm_token + 30s cooldown + auto-backup). `add` / `remove` documented as MCP-excluded-for-safety; plugin keeps HTTP paths for them but flags them as weaker than MCP-guarded alternatives. `rebuild <id>` now routes through MCP `reindex_project` (typed `DELETE` gate + confirm_token = project_id programmatic); global rebuild (no id) stays on HTTP because the MCP has no global equivalent.
- **`commands/rag-reset.md`** — now **generic and standalone**: running `/rag-reset` with no flag enters an **interactive picker** showing the 3 escalation levels with their auto-backup / service-state / gate requirements. `--soft` routes single-project rebuilds through MCP `reindex_project` for the auto-backup + cooldown benefits; global `--soft` stays on HTTP with an explicit warning that auto-backup is not taken on that path. `--data` and `--nuclear` branches unchanged.
- **`rules/state-detection.md`** — now describes an MCP-first probe (`index_status` core tool, works in both proxy and direct mode) as the preferred Step 1, with HTTP `/health` and CLI `rag version` as Steps 2–3 fallbacks. State object gains `mcp_available: bool` and `mcp_mode: proxy|direct|degraded|failed|N/A` fields. Path resolution (Step 5) prefers MCP `get_paths` when the debug tool is granted; falls back to HTTP `/api/status` parsing.
- **`skills/ragtools-ops/SKILL.md`** — frontmatter `description` expanded with operational intent phrases ("why isn't this file in search", "add an ignore rule", etc.) so the skill auto-activates when users describe intents rather than ragtools keywords. Phase 1 (mode detection) now defers to `rules/state-detection.md` + `rules/mcp-envelope.md`. Phase 2.5 is new — MCP tool dispatch with 9 workflow sections. Phase 3 routing rewritten: operational questions default to **skill-chained MCP tool calls** (no slash command needed); only deep diagnosis, setup/install/upgrade, destructive reset, and plugin-layer config still route to slash commands.
- **`.claude-plugin/plugin.json`** — version `0.4.0` → `0.5.0`.

### Rationale
ragtools v2.5.0 expanded the MCP from 3 content tools to 22 total (3 core + 9 project ops + 9 debug). The v0.4.0 plugin used only the 3 core content tools via Claude's direct calls (D-001); everything operational was done via HTTP API or CLI. D-022 refines D-001 to keep the content-tool boundary (plugin never wraps `search_knowledge_base`) while unlocking the 18 non-search tools for plugin use. The MCP's own safety model — envelope contract, error-code enum, mode detection, cooldowns, confirm-token guard, auto-backup, intentionally-excluded tools (`add_project`, `remove_project`, `shutdown`, `backup_restore`, `set_active_project`) — is stronger than the ad-hoc HTTP paths the plugin previously used. Routing through the MCP means the plugin inherits those guarantees instead of duplicating (and drifting from) the logic.

Every net-new capability ships as a **skill workflow**, not a new command. The skill auto-activates on user intent (e.g. "why isn't file X indexed?") and chains the MCP tools without requiring a slash-command interface. This matches the user's directional guidance ("decrease commands, increase skills"), preserves D-021's "fewer, stronger, smarter commands" posture, and fills the 22-tool surface without growing the command count.

Every surviving command is now **generic / standalone** — `/rag-projects` defaults to `list` with no args, `/rag-reset` defaults to an interactive picker. Previously they printed usage and stopped; now they do the most common thing automatically.

### Verification
- Validator passes: `python validate_plugin.py rag-plugin` (pre-existing SKILL.md YAML and hooks.json false positives unchanged).
- Schema sanity: no change to `.mcp.json`, `.claude-plugin/plugin.json` manifest still valid.
- Command count: exactly 6 files under `commands/` (`rag-config.md`, `rag-doctor.md`, `rag-projects.md`, `rag-reset.md`, `rag-setup.md`, `rag-sync-docs.md`) — no growth.
- Rules: 3 files under `rules/` (`claude-md-retrieval-rule.md`, `state-detection.md`, `mcp-envelope.md`).
- Decisions: D-001 through D-022 — D-022 is the one new binding entry.
- All four envelope assertions in `rules/mcp-envelope.md` are testable against live MCP output once a session has the tools loaded: envelope shape, `error_code` enum, `mode` enum, fallback chain.

### Known follow-ups (later phases)
- **v0.6.0:** `/rag-setup` Branch D adds a grant-check sub-step that audits which debug tools are granted vs which plugin workflows need them; offers the toggle path as a one-shot remediation list.
- **v0.7.0:** session-ID correlation in `/rag-config hook-observability` — log the MCP session ID (`mcp:<sid>`) alongside hook decisions so multi-window users can diff.
- **Deferred:** migrate `/rag-projects add` and `/rag-projects remove` off HTTP toward CLI/admin-UI-only handoffs, matching the MCP's intentional-exclusion posture (D-022 §8).

## [0.4.0] — 2026-04-14

Command surface consolidation. Collapses 9 commands (8 user-facing + 1 maintainer) into 7 (6 user-facing + 1 maintainer) by folding `/rag-status` and `/rag-repair` into a smart `/rag-doctor` and folding `/rag-upgrade` into a smart `/rag-setup`. Every surviving command is now **state-aware at the top** — it runs a shared state-detection preamble, branches on the detected state, and refuses gracefully when the state is wrong instead of failing with a generic error.

The user complaint that drove this: commands assumed an already-installed, already-healthy state and fragmented the "get ragtools working" mental model across too many entry points.

### Added
- **`rules/state-detection.md`** — new shared contract file. Documents the canonical state-detection recipe (install mode + service mode + version + paths) and the exact 6-line mode banner format. Every command references it via `${CLAUDE_PLUGIN_ROOT}/rules/state-detection.md` in its Step 0 instead of re-documenting the probe. Single-owner layering per `ARCHITECTURE.md`.
- **D-021** in `docs/decisions.md` — binding decision. "Each command is a smart entry point that detects state and branches; commands do not assume an ideal state. State detection lives in `rules/state-detection.md` and is referenced, not re-implemented."

### Changed
- **`commands/rag-doctor.md`** — rewritten as the unified diagnose+status+repair command. Default mode is the fast state probe the former `/rag-status` did. `--full` is the deep `rag doctor` wrap the former standalone `/rag-doctor` did. A free-text positional argument runs the F-001..F-012 + P-RULE/P-DEDUPE classification rubric the former `/rag-repair` did. `--symptom F-NNN` walks the named playbook. `--logs` runs the `rag-log-scanner` Haiku agent. `--fix` composes with any of the above to walk the repair playbook inline after classification. All 8 repair playbooks (P-svc, P-qdrant, P-perm, P-empty, P-slow, P-port, P-watcher, P-mcp) are preserved verbatim with their existing confirmation-gate discipline.
- **`commands/rag-setup.md`** — rewritten as the unified install+upgrade+verify command. Branches: A install (not-installed), B start-service (DOWN), C upgrade (UP but old, absorbs the former `/rag-upgrade`), D verify (UP and current — idempotent plugin-layer checks for MCP wiring, CLAUDE.md rule, dedupe). All other branches fall through to D on completion so the user always ends in a known-good state.
- **`commands/rag-projects.md`** — added an explicit state-gate preamble at Step 0. Refuses writes when the service is DOWN or BROKEN with a clear pointer at `/rag-doctor` and `rag service start`. Refuses all ops when `install_mode == not-installed`. Cross-references updated (`/rag-status` → `/rag-doctor`, `/rag-repair` → `/rag-doctor --symptom`).
- **`commands/rag-reset.md`** — added an explicit state-gate preamble. Now checks `install_mode == not-installed` and `service_mode == BROKEN` **before** showing any typed-DELETE prompt, so destructive gates are never surfaced for an install that cannot be reset. Pre-v2.4.1 warning now routes users to `/rag-setup` (which walks the upgrade flow) instead of the removed `/rag-upgrade`.
- **`commands/rag-config.md`** — cross-reference fixes only. No behavior change. Pointers to `/rag-status` / `/rag-repair` remapped to `/rag-doctor` and to `/rag-upgrade` remapped to `/rag-setup`.
- **`skills/ragtools-ops/SKILL.md`** — Phase 1 (mode detection) now references `rules/state-detection.md` instead of inlining the probe. Phase 3 (command routing) rewritten for the new 6-command surface with the consolidation note explaining where `/rag-status`, `/rag-repair`, and `/rag-upgrade` went.
- **`.claude-plugin/plugin.json`** — version `0.3.3` → `0.4.0`.

### Removed
- **`commands/rag-status.md`** — absorbed into `/rag-doctor` default mode.
- **`commands/rag-repair.md`** — absorbed into `/rag-doctor` via free-text symptom classification, `--symptom F-NNN`, `--logs`, and `--fix` flags.
- **`commands/rag-upgrade.md`** — absorbed into `/rag-setup` Branch C.

Deletion rather than stub-redirects because stubs would create dead entries in the slash-command catalog and confuse users about what is still supported.

### Rationale
The current 3-file split `/rag-status + /rag-doctor + /rag-repair` forced users to pick a hammer before they knew what was wrong. Every one of those files started with the same mode-detection block and ended with a footer pointing at the other two. The new `/rag-doctor` lets the user just ask "what's wrong?" and branches based on state: default is a fast probe, `--full` goes deep, `--symptom` jumps to a playbook, `--fix` walks it. Same reasoning for `/rag-setup + /rag-upgrade`: the user's mental model is "get ragtools working" regardless of whether that means "install it" or "upgrade it," and a single smart command handles both based on the detected version.

The destructive commands `/rag-reset` and `/rag-projects` **stay separate** because destructive/write operations benefit from their own namespace — they should not be hidden behind an innocuous command name. Instead, they get the state-gate preamble so they fail fast and safely on bad states.

`/rag-config` stays because it operates on a genuinely different scope (plugin-layer config: telemetry, claude-md rule, mcp-dedupe, hook-observability) rather than the ragtools product layer.

`/rag-sync-docs` stays because it is maintainer-only with `disable-model-invocation: true` and is invisible to the user surface.

### Verification
- `python validate_plugin.py rag-plugin` passes (commands: 6, skill: 1, agent: 1, hooks: 1; only the pre-existing SKILL.md YAML false-positive remains).
- Shape: `ls commands/` shows exactly 6 files — `rag-config.md`, `rag-doctor.md`, `rag-projects.md`, `rag-reset.md`, `rag-setup.md`, `rag-sync-docs.md`.
- `rules/state-detection.md` exists and is referenced by both rewritten command files.
- Grep confirms no live operational references to the deleted commands remain — all remaining mentions of `/rag-status`, `/rag-repair`, `/rag-upgrade` are in historical "absorbs the former X" documentation strings.
- CHANGELOG, decisions.md D-021, README catalog, ARCHITECTURE inventory, and SKILL routing all updated to the new surface.

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
