# rag-plugin Architecture

## Layer ownership

`rag-plugin` is a **reference-heavy operations plugin** built in the style of the official `mcp-server-dev` and `claude-md-management` plugins. It is not a workflow-orchestrator plugin like `feature-dev` or `code-review`.

```
┌────────────────────────────────────────────────────────────────┐
│  COMMANDS (9)                                                  │
│  /rag-status, /rag-doctor, /rag-setup, /rag-repair,            │
│  /rag-projects, /rag-upgrade, /rag-reset,                      │
│  /rag-config, /rag-sync-docs (maintainer-only)                 │
│  Thin entry points. Print mode banner. Defer to the skill.     │
└──────────────────────┬─────────────────────────────────────────┘
                       │ invoke
┌──────────────────────▼─────────────────────────────────────────┐
│  SKILL (1)                                                     │
│  skills/ragtools-ops/SKILL.md                                  │
│  Owns: install/mode detection, path resolution recipe,         │
│         router for which reference to load, phased flow prose. │
│  References: references/*.md                                   │
└──────────────────────┬─────────────────────────────────────────┘
                       │ load on demand
┌──────────────────────▼─────────────────────────────────────────┐
│  REFERENCES (23)                                               │
│  skills/ragtools-ops/references/                               │
│  Topic-split slices of ragtools_doc.md + platform specifics.   │
│  Source of truth for install paths, config schema, MCP wiring, │
│  failure modes, repair playbooks, recovery, versioning, gaps.  │
└──────────────────────┬─────────────────────────────────────────┘
                       │ commands inject
┌──────────────────────▼─────────────────────────────────────────┐
│  RULES (1) — v0.2.0+                                           │
│  rules/claude-md-retrieval-rule.md                             │
│  Shipped plugin asset. Source of truth for the CLAUDE.md       │
│  rule block that teaches Claude to call search_knowledge_base  │
│  before saying "I don't have information". Installed by        │
│  /rag-config claude-md install into ~/.claude/CLAUDE.md,       │
│  delimited by machine-readable begin/end markers for           │
│  idempotent upgrade and clean removal.                         │
└──────────────────────┬─────────────────────────────────────────┘
                       │ describes
┌──────────────────────▼─────────────────────────────────────────┐
│  PRODUCT SURFACES (external — owned by ragtools)               │
│                                                                │
│  HTTP API     127.0.0.1:21420  /health, /api/status,           │
│                                /api/projects, /api/watcher,    │
│                                /api/config, /api/mcp-config    │
│  CLI          rag doctor, rag service start/stop/status,       │
│               rag version, rag rebuild, rag ignore check       │
│  MCP server   search_knowledge_base, list_projects,            │
│               index_status — auto-wired via plugin-level       │
│               .mcp.json (D-015), cleaned up by                 │
│               /rag-config mcp-dedupe (D-015 amendment)         │
│  Files        config.toml, service.log, qdrant/, state DB      │
└────────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────────────┐
│  USER CONFIG (external — owned by user, edited with care)     │
│                                                                │
│  ~/.claude/CLAUDE.md     ← rules/claude-md-retrieval-rule.md   │
│                            injected by /rag-config claude-md   │
│  ~/.claude.json          ← mcp-dedupe removes ragtools dups    │
│  ~/.claude/.mcp.json     ← mcp-dedupe removes ragtools dups    │
│  <plugin-root>/.mcp.json ← canonical ragtools registration     │
│                            (shipped by the plugin)             │
└────────────────────────────────────────────────────────────────┘
```

**The plugin reaches into product surfaces AND user config files. It never re-implements product features and only touches user config files through the command layer with explicit confirmation gates and atomic writes (backup → modify → tmp → rename).**

## What `rag-plugin` does

1. **Detect** install mode (packaged Windows / packaged macOS / dev-mode / not installed) and service mode (proxy-up / direct / down).
2. **Resolve** config, data, log, and binary paths using the same precedence order as `src/ragtools/config.py`: env vars → platform defaults → dev fallback.
3. **Probe** `http://127.0.0.1:21420/health` at the top of every command and print a one-line mode banner so the user always knows which mode they're in.
4. **Wrap** existing CLI and HTTP surfaces with compact-by-default outputs. Tables, not log dumps. `--verbose` for full output.
5. **Codify** the §15 repair playbooks as walkable interactive flows with explicit confirmation gates on destructive steps.
6. **Guard** against the Qdrant single-process lock by warning before any Bash command would fight a running service. PreToolUse hook in the `security-guidance` style.
7. **Walk** users through the documented upgrade, reset, and recovery flows from §16–17.

## What `rag-plugin` never does

| Forbidden | Why |
|-----------|-----|
| Re-implement `search_knowledge_base` or any retrieval logic | The MCP server already does this and applies the project's own token-efficient compact format. Duplicating it splits the token-efficiency story. |
| Open Qdrant directly | Qdrant local mode takes an exclusive file lock. Two openers = data loss. The service is the sole owner. |
| Load `SentenceTransformer` or any embedder | 5–10 second cost, no value the product doesn't already deliver. CPU pinning lives in the product for a reason — see `references/risks-and-constraints.md` once Phase 1 lands. |
| Build a parallel admin panel | `service/templates/*.html` already ships one. Re-doing it means maintaining two UIs forever. |
| Manage the file watcher | `watchfiles`-based watcher with auto-restart already lives in the product. |
| Write `ragtools.toml` from a CWD-relative path | This is the v2.4.1 data-loss bug. The only safe write target is `get_config_write_path()`'s resolved platform path. |
| Auto-download or auto-install installer artifacts | ~488 MB Windows installer / ~423 MB macOS tarball. Manual click is correct. The plugin produces URLs and instructions, not network calls. |
| Modify `device="cpu"` in the encoder, or recommend MPS | §18.3 of `ragtools_doc.md` is explicit: do not "optimize" this. MPS OOM is a real failure mode. |
| Promise unsupported platform features | No macOS LaunchAgent. No WinGet. No Linux installer. No signing. The plugin must fail clearly when asked, not pretend. |
| Networked telemetry | The product is local-first, no-cloud, no-API-keys. Anything telemetry-shaped must be opt-in, local-only, single-file, no egress. |

## Component conventions

When commands and skills land in Phases 1–9, they follow these rules:

- **plugin.json** stays minimal. `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`. No invented fields.
- **Slash commands** declare a tight `allowed-tools` list scoped to exactly the bash patterns the command needs (`Bash(rag doctor:*)`, `Bash(curl:*)`, etc.).
- **Skills** use keyword-rich descriptions packed with the user phrasings that should activate them ("ragtools", "rag tools", "Qdrant lock", "rag service", "rag doctor", "knowledge base setup", etc.).
- **References** are short, topic-focused, and end with cross-links. Every reference under ~400 lines.
- **Hooks** are guardrails, not features. PreToolUse Bash matcher only. `permissionDecision: ask`, never silently `deny`. Specific matcher list — false positives erode trust faster than missed warnings.
- **Agents** (if added) are scoped narrowly (one per analytical task) and explicitly model-tier-tagged: Haiku for log scanning, Sonnet for diagnosis. Mirrors `code-review` cost discipline.
- **Outputs** are compact-by-default. Status command: ≤ 25 lines without `--verbose`. Repair walkthroughs: one step at a time, never a wall.

## Transport rules

When the service is up:
- **Read ops** (status, projects list, watcher state, index stats): hit the HTTP API at `127.0.0.1:21420`.
- **Write ops** (add/remove project, rebuild): also hit the HTTP API. Never edit `config.toml` by hand.
- **Diagnostics** (`rag doctor`, `rag version`): shell out to the CLI — these are designed to work in both proxy and direct modes.
- **Search**: defer entirely to the MCP server already running in Claude Code. The plugin does not call `search_knowledge_base` itself.

When the service is down:
- **Read ops**: allowed in CLI direct mode with a clear "slow start, encoder will load" warning.
- **Write ops**: refuse with a clear "start the service first" message. The v2.4.1 bug history justifies the caution.

## The Qdrant invariant

Local-mode Qdrant takes an exclusive file lock on the data directory. The service is meant to be the sole owner of that lock. **Any time `rag-plugin` would suggest a CLI command that opens Qdrant in direct mode while the service is up, it is wrong.** The Phase 6 PreToolUse hook exists to enforce this at the Bash boundary.

## Boundary self-test

When adding a new feature, ask:
1. Does this re-implement something ragtools already exposes? → If yes, stop.
2. Does this write `config.toml` from CWD? → If yes, stop.
3. Does this open Qdrant directly? → If yes, stop.
4. Does this promise a platform behavior that ragtools itself doesn't support? → If yes, stop.
5. Does this auto-download a multi-hundred-MB artifact? → If yes, stop.

If all five answers are "no", the feature is in scope.

## Phase 9 closure — final inventory and state

All 10 phases (0–9) of the rag-plugin roadmap are shipped, plus three post-roadmap amendments (D-015, D-016, D-017). The plugin's surface as of **v0.3.0**:

- **Plugin manifest:** `.claude-plugin/plugin.json` (`v0.3.0`)
- **9 slash commands:**
  - User-facing (7): `/rag-status`, `/rag-doctor`, `/rag-setup`, `/rag-repair`, `/rag-projects`, `/rag-upgrade`, `/rag-reset`
  - User-facing config (1): `/rag-config` — four subcommand groups: telemetry (D-012), claude-md (D-016), mcp-dedupe (D-015), hook-observability (D-017)
  - Maintainer-only (1): `/rag-sync-docs` (`disable-model-invocation: true`, never auto-invoked)
- **1 skill:** `ragtools-ops` (`skills/ragtools-ops/SKILL.md`)
- **2 hooks** (both in `hooks/hooks.json`):
  - **PreToolUse Bash** → `hooks/lock_conflict_check.py` (Python 3 stdlib, 7-pattern matcher + 1-second `/health` probe, `permissionDecision: ask` only when both conditions hold). Lock-conflict guardrail.
  - **UserPromptSubmit** `matcher: "*"` → `hooks/prompt_retrieval_reminder.py` (Python 3 stdlib, Phase A shape gate + Phase B `/api/search` probe, injects `additionalContext` reminder when both phases pass). Retrieval-reminder (D-017, v0.3.0).
- **1 rules file:** `rules/claude-md-retrieval-rule.md` — the Section-0 canonical block installed into `~/.claude/CLAUDE.md` by `/rag-config claude-md install`.
- **1 Haiku agent:** `rag-log-scanner` (`agents/rag-log-scanner.md`)
- **1 maintainer script:** `scripts/analyze_hook_decisions.py` — reads the hook-decisions log and prints aggregate stats (v0.3.0, D-017).
- **23 reference files** under `skills/ragtools-ops/references/` (16 from Phase 1 + setup-walkthrough + output-conventions + upgrade-paths + macos-specifics + linux-dev-mode + INDEX + _meta)
- **1 plugin-level MCP config:** `.mcp.json` at the plugin root (D-015) — registers the ragtools MCP server automatically on plugin install.
- **Documentation:** `README.md`, `ARCHITECTURE.md` (this file), `CHANGELOG.md`, `LICENSE`, `docs/decisions.md` (D-001..D-017)

### v0.3.0 additions summary (D-017)

The new UserPromptSubmit hook is an **additional writable surface** for the plugin: it now injects `hookSpecificOutput.additionalContext` on matched prompts. This is a read+compute flow (read user prompt, compute shape/probe decision, write decision metadata to log, emit reminder JSON). It does NOT modify any user config file. It does NOT read any result content from the probe — only `results[0].score`. It does NOT call any MCP tool. It does NOT block, deny, or crash a turn.

The observability log at `~/.claude/rag-plugin/hook-decisions.log` is a new plugin-owned writable surface (distinct from the existing D-012 telemetry log at `~/.claude/rag-plugin/usage.log`). Same directory, different file, different purpose: the hook-decisions log captures **decision metadata** for the retrieval-reminder hook's own behavior; the telemetry log captures user command invocation counts. Neither contains user content.

### Validator state

The simple validator (`plugins/validate_plugin_simple.py`) reports the plugin structure as clean: 9 commands, 1 skill, 1 hooks file, README found, naming OK. Two false-positive warnings are emitted because of a stale `valid_events` list at line 267 of the simple validator that predates the official Anthropic plugin hooks.json wrapper format. The same warnings would fire on the official `security-guidance` plugin run through this validator. The full `validate_plugin.py` validator has the correct event list. Fixing the simple validator is out of scope for `rag-plugin` (it would touch a sibling tool used by other plugins).

### Boundary contract preserved through every phase

No phase introduced any of the 9 forbidden behaviors listed above. The boundary self-test (5 questions) was applied at every phase boundary. Every destructive action across the 7 user-facing commands is gated by a typed-confirmation pattern, never silently auto-executed. The Phase 6 PreToolUse hook adds a final safety net for the Bash surface outside the plugin's own commands.

### How to extend the plugin

When adding a new command, skill, agent, hook, or reference file:

1. **Read `docs/decisions.md`** first. D-001..D-013 are binding rules that constrain every later phase.
2. **Run the boundary self-test** (5 questions above). If any answer is "yes", stop.
3. **Match the official-plugin patterns** documented in `references/output-conventions.md` (compact-by-default, mode banner first, tables not paragraphs).
4. **Use tight `allowed-tools`** — no broad `Bash`, no `Edit`/`Write` unless absolutely necessary, no `rag index`/`rebuild`/`watch`/`mcp` direct invocation.
5. **Update `references/INDEX.md`** if you add a new reference file so the skill router can find it.
6. **Run `validate_plugin_simple.py`** and confirm no errors (warnings about hook events are the known false positives — ignore).
7. **Add a CHANGELOG entry.**
8. **If the change implies a new binding decision**, append a `D-NNN` entry to `docs/decisions.md` with the same `Date / Phase / Status / Reverse only if` format as D-001..D-013.

The plugin is **finished** in the sense that the original 10-phase roadmap is complete. It is **not finished** in the sense that ragtools itself will continue to evolve and Phase 9's `/rag-sync-docs` exists precisely so future maintainers can keep the references library aligned with the upstream product.
