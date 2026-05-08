# Plugin Development Guide

Authoring conventions for plugins in the **taqat-techno-plugins** marketplace. The source-of-truth references are:

- **Anthropic's spec:** [`plugins/CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`](../../CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md) — 1500-line workspace-level guide.
- **Skills spec:** [`plugins/agent_skills_spec.md`](../../agent_skills_spec.md).
- **Reference patterns (read-only):** `claude-plugins-official-main/plugins/plugin-dev/skills/` — canonical examples of plugin-structure, command-development, agent-development, hook-development, skill-development, mcp-integration, plugin-settings.

This wiki page is the **house-style overview** — what we consistently do in this repo on top of Anthropic's spec.

## Step-by-step: create a new plugin

### 1. Scaffold the directory

```bash
mkdir -p plugins/<name>-plugin/.claude-plugin
mkdir -p plugins/<name>-plugin/commands
mkdir -p plugins/<name>-plugin/skills/<skill-name>
mkdir -p plugins/<name>-plugin/hooks
```

### 2. Write the manifest

`plugins/<name>-plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "<name>",
  "version": "0.1.0",
  "description": "Short, precise description. What problem does it solve?",
  "author": {
    "name": "TaqaTechno",
    "email": "info@taqatechno.com",
    "url": "https://github.com/taqat-techno"
  },
  "homepage": "https://github.com/taqat-techno/plugins/tree/main/<name>-plugin",
  "repository": "https://github.com/taqat-techno/plugins",
  "license": "MIT",
  "keywords": ["<keyword1>", "<keyword2>", "..."]
}
```

### 3. Register in the marketplace manifest

**Mandatory.** Without this step, Claude Code never loads the plugin. Edit `plugins/.claude-plugin/marketplace.json`:

```json
{
  "plugins": [
    ...,
    {
      "name": "<name>",
      "description": "...",
      "author": {"name": "TaqaTechno", "email": "info@taqatechno.com"},
      "source": "./<name>-plugin",
      "category": "<development | productivity | design>",
      "homepage": "https://github.com/taqat-techno/plugins/tree/main/<name>-plugin"
    }
  ]
}
```

### 4. Write the commands, skills, agents, hooks

See the sections below for house conventions on each component type.

### 5. Write the README

Mandatory sections (enforced by convention — see [[Contribution Guide|Contribution-Guide]]):

- H1 title
- Description paragraph
- Quick Start / Installation / Usage section
- Commands / Components / Features section

### 6. Validate

```bash
python plugins/validate_plugin.py <name>-plugin
```

Pass with 0 errors. Warnings like `Unknown hook event 'description'` or `Unknown hook event 'hooks'` are pre-existing validator false positives — document them in the CHANGELOG if they're new to your plugin; do not silence.

### 7. Update the marketplace README

Add a row to `plugins/README.md`'s **Available plugins** table and a section under **Plugin details** linking to your plugin's README. Stale marketplace READMEs have been a recurring regression — fix it in the same commit.

### 8. Update the wiki

Add a `plugins/wiki/<Name>-Plugin.md` page using the existing plugin pages as templates. Update `plugins/wiki/_Sidebar.md` to include it.

### 9. Commit and push

Permission-first. `taqat-techno/*` repos require `gh auth switch --user a-lakosha` before the push; switch back to `ahmed-lakosha` after. See [[Contribution Guide|Contribution-Guide]] §gh-auth.

## Component types (house conventions)

### Commands

Commands are markdown files in `commands/<name>.md` with YAML frontmatter. Each filename (minus `.md`) becomes a slash command.

**Frontmatter template:**
```yaml
---
description: One-sentence summary shown in the command catalog. Start with a verb.
argument-hint: "[<arg-descriptor>]"
allowed-tools: Bash(curl:*), Read, Write, mcp__plugin_<plugin>_<server>__<tool>
disable-model-invocation: false
author: TaqaTechno
version: <matches plugin.json>
---
```

**House conventions:**

1. **Generic / standalone** — every command should work with no required arguments, defaulting to the most common action. `/rag-projects` with no args defaults to `list`; `/rag-reset` with no flag enters an interactive picker.
2. **Thin dispatcher.** Behavior lives in skills, rules, agents, data files. Commands route and expose flags.
3. **State-aware preamble.** Mature plugins (`rag-plugin`) put a Step 0 that runs a shared state-detection probe (via `rules/state-detection.md`) before any dispatch. Commands refuse gracefully on `not-installed` / broken states.
4. **Consolidation first.** Before adding a new command, check if an existing command can take a new flag. The repo's "v2.0" commit wave consolidated many N→1 passes; sprawl is a regression.

### Skills

Skills are markdown files at `skills/<name>/SKILL.md` with YAML frontmatter. They auto-activate on keywords or user intent.

**Frontmatter template:**
```yaml
---
name: <skill-name>
description: Activation rule — list keywords, error messages, user intents. Specific and trigger-oriented. This description is what Claude uses to decide when to load the skill.
version: <matches plugin.json>
---
```

**House conventions:**

1. **Description is the trigger.** Be specific about what phrasing activates the skill. Include error messages and user intents, not just feature names. Example (from `rag-plugin`): "`why isn't this file in search?`, `why is my project missing results?`, `add an ignore rule`, ..."
2. **Phased body.** Break the skill into phases (1, 2, 3 or more). Phase 1 is usually state detection; later phases are workflow-specific. Each phase cites what references to load.
3. **References library.** Heavy reference material goes under `skills/<name>/references/`. Loaded on-demand by phase, not at session start.
4. **Increase skills, decrease commands.** Prefer workflow-level skills that chain tools automatically over new commands. This is a consistent maintainer direction.

### Agents

Agents are markdown files in `agents/<name>.md`. They're specialized sub-agents invoked by commands or other agents.

**Frontmatter template:**
```yaml
---
name: <agent-name>
description: What this agent is for. Mention specific user phrasing or command invocations.
model: haiku | sonnet | opus
---
```

**House conventions:**

1. **Model tiers matter.** `devops-plugin` assigns **haiku** to high-volume CRUD ops (`work-item-ops`) and **sonnet** to analytical work (`sprint-planner`, `pr-reviewer`). Pick the cheapest model that can do the job.
2. **Single responsibility.** One agent does one thing well. Complex workflows are chained at the skill level, not inside a monolithic agent.
3. **Scoped tools.** Use the `tools:` field in frontmatter to limit what the agent can call. Tight scopes make agent behavior predictable.

### Hooks

Hooks are JSON registrations in `hooks/hooks.json` + sibling scripts in `hooks/`.

**Hook conventions (from [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md)):**

1. **Never use prompt-type hooks.** They trigger Claude Code's prompt-injection detection. All 31 prompt-type hooks from earlier plugin versions have been removed.
2. **Output JSON, not plain text.** Use `hookSpecificOutput.additionalContext` for SessionStart / UserPromptSubmit.
3. **Fail fast.** Wrap logic in try/except; on error, silent-pass (exit 0 with no output). Never block the session over a hook bug.
4. **Respect timeouts.** Command hooks: 600s default (but target <1s). Prompt hooks: 30s default. Don't trust the defaults — set explicit timeouts in `hooks.json`.
5. **Ask, never silently deny.** Per `rag-plugin` D-007 — hooks that block should return `permissionDecision: "ask"` with a clear reason. `deny` is reserved for provably-destructive-never-legitimate cases.
6. **Don't spawn Python for simple checks.** A hook that fires on every `Write` / `Edit` costs interpreter startup time. Use bash for speed or pre-compiled tools. Python is fine for one-shot SessionStart hooks with real logic.
7. **Windows cross-platform.** `os.execvp` has different stdio-pipe semantics on Windows. Scripts must not assume POSIX behavior. Test on both platforms.

**Tiered SessionStart hook design (probe / background / full):**

A naïve "run the full sync pipeline on every session start" hook has multiple failure modes — latency (30s+), network dependency, accidental writes, concurrent-session conflicts on `git worktree add`. For any plugin whose SessionStart needs to do real work, design a three-tier mode:

| Mode         | Behavior                                                                  | Latency | Network  | Writes    | When to use         |
|--------------|---------------------------------------------------------------------------|---------|----------|-----------|---------------------|
| `disabled`   | Exit silently                                                             | 0 ms    | —        | —         | User opt-out        |
| `probe`      | Read manifest mtimes vs `.workspace_signature`. One-line note if stale.   | ~50 ms  | None     | None      | Daily driver default|
| `background` | Probe → if stale, fork via `nohup` / detached process                     | ~50 ms  | Yes (bg) | Yes (bg)  | Auto-sync, non-blocking |
| `full`       | Run the pipeline synchronously                                            | 30 s+   | Yes      | Yes       | CI / pipelines only |

**Hook timeout is a hard backstop.** Set `"timeout": 10` in `hooks.json` so even `probe` cannot stall the session. Probe should finish in ~50 ms; the timeout is for safety only.

### MCP servers

Plugin-level MCP registration is a `.mcp.json` file at the plugin root. **Flat shape** (no `mcpServers` wrapper) — verified empirically against every working plugin in the cache.

```json
{
  "<server-name>": {
    "type": "stdio",
    "command": "<binary>",
    "args": ["<arg1>", "<arg2>"]
  }
}
```

**House conventions:**

1. **Flat shape at plugin level.** Wrapped shape (`mcpServers: {...}`) is for user-level (`~/.claude/.mcp.json`) and project-level (`<repo>/.mcp.json`) files, not plugin-level. The `rag-plugin` v0.3.1→v0.3.2 retraction (D-019) is the cautionary tale.
2. **Spawn the binary directly.** Do not wrap in a Python launcher script — Python's `os.execvp` on Windows doesn't preserve stdio pipe inheritance, and the spawned process never gets the handshake. D-020 codifies this.
3. **Register, don't wrap.** The plugin registers the MCP server so Claude can call its tools directly. The plugin itself never wraps content-retrieval tools (e.g., `search_knowledge_base` in `rag-plugin`). Ops tools are fair game (D-022).
4. **Empirical-pattern check before changing manifest shape.** Before "fixing" a plugin's `.mcp.json` because it looks wrong, grep every working `~/.claude/plugins/cache/*/.mcp.json` for the same shape. The "right" shape is whatever the working examples on disk are using, not what the documentation claims. If 4-of-4 working plugins use shape A and your broken one uses shape B, A is the answer regardless of what the spec says.
5. **Never allowlist execution-shaped MCP tools too broadly.** When defining `allowed-tools` on a command or building a `.claude/settings.json` permissions allowlist, treat the following as arbitrary code execution and require explicit user approval: `mcp__*__evaluate_script`, `mcp__*__browser_evaluate`, `mcp__*__browser_run_code_unsafe`, and any tool that takes a free-form script string. Wildcarded interpreters (`wsl *`, `curl *`, `python3 *`, `node *`, `npx *`) are equivalent.
6. **Mode is locked at MCP startup; never switch mid-session.** When an MCP server can operate in two modes (proxy vs direct, online vs offline, dev vs production), the server must pick the mode at init and lock it. If the dependency later goes down, return a clean `[ERROR] Service unavailable` and require a restart — do NOT auto-switch mode mid-session. Mid-session mode switching multiplies edge cases (half-loaded resources, stale clients, dangling state) and rarely solves a real user problem. The `rag-plugin` MCP encodes this in `rules/mcp-envelope.md` §3.

**Restart discipline after MCP changes:** any time you edit a plugin's `.mcp.json`, install or upgrade a plugin, or toggle an MCP tool grant in the server's admin panel, **fully restart Claude Code** — not `/reload-plugins`. The agent-visible deferred-tool registry is populated at session start; `/reload-plugins` reports updated server counts but does not re-index the tool catalog reaching the agent. After restart, verify with `ToolSearch query="+<server-name>"`.

### Rules

Behavioral contracts referenced by skills, agents, and commands. Single-owner layering — each rule lives in one file; everyone else references it.

**Examples from `rag-plugin`:**

- `rules/state-detection.md` — canonical state probe recipe.
- `rules/mcp-envelope.md` — MCP envelope / error-code / cooldown discipline.
- `rules/claude-md-retrieval-rule.md` — shipped asset installed into the user's CLAUDE.md.

**Convention:** referenced at `${CLAUDE_PLUGIN_ROOT}/rules/<name>.md` from commands/skills. Don't duplicate.

## Cross-cutting plugin design patterns

These patterns recur in multi-component plugins. Read once, apply where the plugin actually needs them.

### Layered config: frozen plugin tree vs user-owned workspace

For plugins that need user-specific configuration (project paths, custom rules, persona overrides, classifier weights), split config into two layers so a forced plugin update doesn't clobber user customizations:

| Layer | Lives at | Owned by | Survives plugin update? |
|---|---|---|---|
| Defaults + detection logic | `<plugin>/skills/<skill>/config.env`, `refs/example/*.json` | Plugin maintainer | N/A — refreshed on every update |
| User overrides (resolved paths, custom rules) | `<workspace>/.claude/<skill-name>/config.env`, `<workspace>/.claude/<skill-name>/refs/*.json` | User | ✅ Always — outside the plugin tree |

Skill loads them in order; second wins:

```bash
source "$SKILL_DIR/config.env"                                                  # plugin defaults
[ -f "$WS/.claude/<skill>/config.env" ] && source "$WS/.claude/<skill>/config.env"  # user overrides
```

**Rule:** the plugin tree is frozen on every install. User data **never** lives there. A plugin force-update replaces every plugin file but never touches the workspace directory — so the user can `force-update` and zero of their resolved paths / classifier rules / persona overrides are touched.

### Service-owner architecture (single-process resource lock)

For plugins that wrap a tool with a single-owner resource (Qdrant local mode, exclusive port, OS-level lock, SQLite-on-network-share, etc.), the right architecture is:

1. **One service process owns the resource.** Lock-protected accessors only; never raw exports.
2. **CLI commands probe `/health` first** — route through HTTP if up, fall back to direct access if down.
3. **MCP server probes once at startup** and locks itself into proxy mode (httpx forwarder, ~15ms cold start, no encoder load) or direct mode for the session.
4. **Watcher / background work runs as a daemon thread inside the service process** using the owner's shared client; never opens its own.
5. **Mid-session mode-switching is forbidden.** See the MCP servers §6 rule above — fail clean and require a restart.

The `rag-plugin` is the canonical implementation; see `rag-plugin/skills/ragtools-ops/references/risks-and-constraints.md` § "Single-process constraint" for the concrete invariants.

### Three-strategy auto-discovery (zero-config → signature scan → interactive)

For plugins that need to find user repos / projects / configurations in arbitrary workspace layouts:

1. **Standard layout (zero config).** Workspace root contains direct children matching canonical names. If everything is found, run with no further questions.
2. **Signature scan (handles renames + nesting).** Walk the workspace tree up to depth 3. For each `.git/` dir, read `git remote get-url origin` and content fingerprints. Match by **git remote URL + content fingerprint**, never by folder name. Handles bundled / renamed / vendored layouts.
3. **Interactive prompt (only for what survived 1+2).** Tell the user once: "I couldn't locate the **<name>** repo automatically. Tell me a path, or say *skip* to disable it for this run." Persist the answer to the workspace config so step 2 never re-asks.

Hardcoding paths makes the plugin unusable for anyone with a different layout. Pure interactive prompting on every run is annoying. Three-strategy ladder asks the minimum.

## Binding decisions (D-NNN)

Load-bearing choices — "which schema shape?", "ops tools are fair game?" — go in `docs/decisions.md` as append-only entries:

```markdown
## D-NNN — Short decision title

**Date:** YYYY-MM-DD
**Phase:** Post-<N>
**Status:** binding
**Ships in:** v<X.Y.Z>
**Triggered by:** (the incident or request)

### The decision

(one or two paragraphs)

### Non-violation of prior decisions

(explicit check against D-{N-k} where relevant)

### Reverse only if

(exit criteria — when would this decision get superseded?)
```

**Rules:**

- Append-only. Never rewrite or delete an earlier entry.
- Supersede with a new dated entry that names its predecessor.
- Every decision has a "Reverse only if:" exit clause.
- Non-violation notes against prior decisions — explicit, not implied.

## Testing and validation

- **Structural:** `python plugins/validate_plugin.py <plugin-dir>` — checks manifest, command/agent/skill frontmatter, hook wiring, README presence, naming.
- **Fast check:** `python plugins/validate_plugin_simple.py <plugin-dir>` — same check without PyYAML.
- **Behavioral:** plugin-specific — e.g., `/rag-doctor` on a test ragtools install, `/pandoc convert` on sample documents. No universal E2E harness yet.

## Versioning

- **Semver.** Major.Minor.Patch.
- **Minor bumps** for new commands, new skills, new MCP tools, user-visible surface changes.
- **Patch bumps** for bug fixes and non-breaking refinements.
- **Major bumps** for breaking changes (removed commands, incompatible schema, etc.).
- **Changelog every bump.** At least for mature plugins (`rag-plugin`, `devops-plugin`, `remotion-plugin`). Minimum-viable CHANGELOG entry: what changed and why.

## See also

- [[Architecture]] — shared layering patterns across plugins
- [[Contribution Guide|Contribution-Guide]] — PR workflow, account switching, commit discipline
- [`CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`](../../CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md) — workspace-level spec
- [`agent_skills_spec.md`](../../agent_skills_spec.md) — skills spec
- `claude-plugins-official-main/plugins/plugin-dev/skills/` — Anthropic's canonical examples (read-only, do not modify)
