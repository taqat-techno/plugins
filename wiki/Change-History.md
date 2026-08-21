# Change History

Chronological milestones in the `taqat-techno-plugins` marketplace. Distilled from the git log (50+ commits) and the major reports at the repo root.

For plugin-specific changelogs, see each plugin's `CHANGELOG.md`:

- [`odoo-plugin/CHANGELOG.md`](../../odoo-plugin/CHANGELOG.md)
- [`notification-plugin/CHANGELOG.md`](../../notification-plugin/CHANGELOG.md) — v1.0.0
- [`devops-plugin/CHANGELOG.md`](../../devops-plugin/CHANGELOG.md) — v2.0 → v6.3 evolution
- [`rag-plugin/CHANGELOG.md`](../../rag-plugin/CHANGELOG.md) — v0.1.0 → v0.5.0 evolution
- [`remotion-plugin/CHANGELOG.md`](../../remotion-plugin/CHANGELOG.md) — v1.0 → v2.1

## Three eras

### Era 1 — Proliferation (Oct–Dec 2025)

Started as a single `odoo-upgrade` plugin in **Oct 2025**. Grew rapidly:

- `odoo-frontend` — website theme development with Bootstrap.
- `odoo-report` — email templates + QWeb reports.
- `odoo-test`, `odoo-security`, `odoo-i18n`, `odoo-service`, `odoo-docker` — each a narrow Odoo capability.
- `devops-plugin` — Azure DevOps integration.
- `ntfy-plugin` — mobile push notifications.
- `pandoc-plugin` — document conversion.
- `remotion-plugin` — video creation with narration.
- `ui-ux-mechanics-plugin` (shipped this era as `paper-plugin`) — UI/UX design.

Peak count: **13 plugins**. Every new Odoo capability got its own plugin directory. Every plugin had 5–10 narrow commands.

### Era 2 — Command consolidation wave (Dec 2025–Feb 2026)

A striking commit pattern: `feat(<plugin>): v2.0 — consolidate N commands into 1 unified /X command`:

- `pandoc`: **8 commands → 1** (`/pandoc setup|status|convert|formats|help`)
- `ui-ux-mechanics` (then named `paper`): **5 → 1** (single dispatcher command)
- `ntfy`: **8 → 2** (`/ntfy` + `/ntfy-mode`)
- `remotion`: **5 → 1** (`/remotion`)
- `devops`: **24 → 9** with user profiles & role-based state permissions (`feat(devops-plugin): v4.2`)
- `odoo-docker`: **8 → 1**
- `odoo-frontend`: **3 → 1** (v5.0)
- `odoo-i18n`: **5 → 1**
- `odoo-report`: **10 → 1**
- `odoo-security`: **5 → 1**
- `odoo-service`: **7 → 1**
- `odoo-test`: **6 → 1**

A refactor migrated all 13 plugins to a **skill-first architecture**, cutting **7,386 lines** of narrow-command boilerplate (commit `0636104`).

### Era 3 — Infrastructure hardening + Odoo unification (Feb–Apr 2026)

**Hook ecosystem stabilization** (multi-commit arc):

- Deduplicated 24 hooks, added timeouts + logging wrapper.
- Removed invalid `../` path traversals in hooks (hooks cannot reference files outside the plugin in the cache).
- Fixed invalid `matcher` types in `devops-plugin`.
- Removed `type: suggestion` (not a valid hook type — replaced with `prompt`, then removed prompt hooks entirely because they triggered Claude Code's prompt-injection detection).
- Fixed 8-plugin invalid hook-event registrations.
- Windows cross-platform reliability for 5 plugins.
- Removed `set -euo pipefail` from wrapper that crashed on minor hook errors.
- Stabilized the PostToolUse ecosystem.

Major audit reports produced in this era:

- [`HOOK_AUDIT_REPORT.md`](../../HOOK_AUDIT_REPORT.md)
- [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md)
- [`ENHANCEMENT_REPORT_JAN_2026.md`](../../ENHANCEMENT_REPORT_JAN_2026.md)
- [`PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`](../../PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md)

**Marketplace schema rewrite** — aligned `marketplace.json` to the official Anthropic schema (commit `81af8b6`).

**Odoo unification** — eight separate Odoo plugins merged into a single `odoo-plugin` with sub-skills per domain area (commit `ef9befe`).

**rag-plugin** built from scratch in a rapid arc:

- v0.1.0 — initial release (10 phases + 23 reference files).
- v0.2.0 — CLAUDE.md retrieval rule auto-install (D-016).
- v0.3.0 — Tier-2 UserPromptSubmit retrieval-reminder hook + observability (D-017).
- v0.3.1–v0.3.3 — MCP wiring saga: three retractions (D-018 schema, D-019 schema retraction, D-020 launcher retraction) — arrived at flat-shape `.mcp.json` + direct `rag serve` spawn.
- v0.4.0 — command consolidation: 9 → 6 smart state-aware commands; new shared `rules/state-detection.md` contract (D-021).
- v0.5.0 — integrated ragtools MCP v2.5.0's 22-tool surface via skill workflows; 6 new auto-activating workflows (why-not-indexed, ignore rules, reindex decision tree, tool-grant audit, etc.); new `rules/mcp-envelope.md` contract (D-022).

**devops-plugin** overhauls:

- v4.2 — consolidated 24 → 9 commands + user profiles + role-based state permissions.
- v6.0 → v6.3 — architecture overhaul (P0/P1/P2 refactor), persistent user profile, unified `/create`, `/workday` dashboard, time logging, `/init` setup with CLI + MCP, 100+ MCP tools, specialized subagents.

**Marketplace README** — rewritten Apr 2026 to reflect actual 7-plugin filesystem state (previously listed 13 plugins with many broken links to removed Odoo sub-plugins).

**Wiki** — `plugins/wiki/` directory created Apr 2026 with this documentation system.

### Era 4 — Rename + safety-plugin expansion (Jun 2026)

- **2026-06-13 — `paper` renamed to `ui-ux-mechanics`.** The design plugin was renamed: directory `paper-plugin/` → `ui-ux-mechanics-plugin/`, command `/paper` → `/ui-ux-mechanics`, package `paper` → `ui-ux-mechanics` (v3.0.0 → v3.1.0). The rename reflects the expanded scope: a new `figma-mcp-mechanics` skill adds safe Figma MCP write workflows (write-access probing, metadata-lossiness handling, auto-layout/variant mechanics, prototype-link-safe edits) alongside the existing `design` and `figma-workflow` skills. Wiki page renamed `Paper-Plugin` → `Ui-Ux-Mechanics-Plugin` with all inbound links updated.
- **2026-06-13 — two new safety plugins added this cycle:** `agent-safety-guards` and `release-safety`. Both focus on guardrails around agent actions and release operations.

### Era 5 — Framework toolkits, worktrees, and native notifications (Jul-Aug 2026)

- **2026-08 — framework toolkits landed:** `django` and `fastapi`, each shipping auto-activating skills, commands, analyzer agents, and advisory hooks. Both are adapter-driven: no project entities, roles, or URLs baked in.
- **2026-08 — `git-safety`** added the local git-workflow guardrails that commit helpers and PR plugins leave out, including shared-checkout safety for trees shared by more than one session or syncer. Advisory only; it never blocks.
- **2026-08-14 — `worktree`** made git worktrees a first-class workspace, with status-line integration and a deliberate **zero hooks** posture so installing it cannot disturb a session.
- **2026-08-18 — marketplace architecture audit.** `validate_marketplace.py` was added after an audit found **15 skills that had never loaded once** while every per-plugin validator reported green. A per-plugin structural check cannot see a runtime-discovery failure; both validators are now required.
- **2026-08-21 — `ntfy-notifications` retired, `notification` shipped (v1.0.0).** The old plugin pushed to the external [ntfy.sh](https://ntfy.sh) service, needed a topic and a phone app, and registered no hooks at all - it could never fire automatically. Its replacement uses each operating system's own notifier and requires no account, no network, and no third party.

  The rewrite is hooks-only and deliberately AI-free: five `async: true` command hooks (`PreToolUse`/`AskUserQuestion`, `Notification`/`permission_prompt`, `TaskCompleted`, `Stop`, `StopFailure`) route to one stdlib-only Python entry point. `async` is load-bearing rather than a performance tweak - three of those five are blocking events where exit code 2 would suppress a question, trap Claude in a non-terminating turn, or refuse a task completion, and an async hook cannot block Claude at all. Zero `SessionStart` hooks, nothing written to stdout, no shell anywhere.

  Two findings from the investigation are worth carrying forward. First, `TaskCompleted` cannot fire on Opus 4.8 / Sonnet 5 / Fable 5 / Mythos 5 unless Claude Code is started with `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, because v2.1.233+ does not give those models the Task tools and the task list is therefore never populated - and `TodoWrite` is behind the same gate, so it is not an escape hatch. Second, `validate_plugin.py` was iterating a hooks file's top-level keys instead of its `hooks` object, reporting `description` and `hooks` as unknown events on every plugin, and its event list knew 9 of the 31 events Claude Code now exposes. Both were fixed.

  Full investigation: `.claude/docs/2026-08-21_notification-plugin-investigation.md` in the workspace root.

## Current state (Aug 2026)

| Metric | Value |
|---|---|
| **Plugins in marketplace** | 17 |
| **Total commands** | 66 across all plugins |
| **Total agents** | 23 across all plugins |
| **Total skills** | 105 across all plugins |
| **Total hook handlers** | 27 across 11 plugins |
| **Plugins with MCP servers** | 3 (`odoo`, `devops`, `rag`) |
| **Plugins with no hooks at all** | 6 (`pandoc`, `remotion`, `ui-ux-mechanics`, `react-kit`, `docs-wiki`, `worktree`) |
| **Marketplace maintainer** | Single (Ahmed Lakosha, 4 git identity variants, 132+ commits) |
| **Vendored references** | `claude-plugins-official/` (read-only) |

## Milestones on the roadmap

Based on open follow-ups in the plugin CHANGELOGs and enhancement reports:

### Near-term

- Plugin-level E2E tests — the validator catches structural issues but not behavioral ones. A broken `.mcp.json` passes validation.
- CONTRIBUTING.md refresh — the current one predates the plugin taxonomy (commands / agents / skills / hooks / MCP).
- `/rag-setup` Branch D grants-check sub-step — audit which debug MCP tools are granted; offer toggle paths as a one-shot remediation list.
- Migrate `/rag-projects add` / `/rag-projects remove` from HTTP to CLI/admin-UI handoffs (the MCP intentionally excludes these; the plugin's HTTP paths are weaker).

### Medium-term

- Automated marketplace-README sync (a lightweight CI check that catches stale catalog vs filesystem).
- Per-plugin E2E smoke tests in CI.
- `rag-plugin` v0.6.0 — session-ID correlation in observability.
- `odoo-plugin` Odoo 19 controller type migration auto-fix (`type='json'` → `type='jsonrpc'`).
- `odoo-plugin` `attrs={}` removal full coverage.

### Deferred / out-of-scope

- Wrapping `search_knowledge_base` in `rag-plugin` — violates D-001 / D-022; stays deferred indefinitely.
- Adding a `/rag` super-command — user guidance is to decrease command count; `/rag-doctor` default mode already serves as the entry point.
- Stub-redirect commands for muscle memory after consolidation (e.g. keeping `/rag-status` → "use /rag-doctor" stub). Deliberate clean break; stubs create catalog noise.

## See also

- [[Plugin Catalog|Plugin-Catalog]] — what exists today
- Individual plugin CHANGELOGs (linked at the top)
- Workspace-level reports — [`HOOK_AUDIT_REPORT.md`](../../HOOK_AUDIT_REPORT.md), [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md), [`ENHANCEMENT_REPORT_JAN_2026.md`](../../ENHANCEMENT_REPORT_JAN_2026.md), [`PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md`](../../PLUGIN_ENHANCEMENT_REPORT_FEB_2026.md)
