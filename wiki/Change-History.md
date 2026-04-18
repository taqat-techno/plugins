# Change History

Chronological milestones in the `taqat-techno-plugins` marketplace. Distilled from the git log (50+ commits) and the major reports at the repo root.

For plugin-specific changelogs, see each plugin's `CHANGELOG.md`:

- [`odoo-plugin/`](../../odoo-plugin/) — no CHANGELOG (consolidated plugin, current version 1.0.0)
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
- `paper-plugin` — UI/UX design.

Peak count: **13 plugins**. Every new Odoo capability got its own plugin directory. Every plugin had 5–10 narrow commands.

### Era 2 — Command consolidation wave (Dec 2025–Feb 2026)

A striking commit pattern: `feat(<plugin>): v2.0 — consolidate N commands into 1 unified /X command`:

- `pandoc`: **8 commands → 1** (`/pandoc setup|status|convert|formats|help`)
- `paper`: **5 → 1** (`/paper` dispatcher)
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

## Current state (Apr 2026)

| Metric | Value |
|---|---|
| **Plugins in marketplace** | 7 |
| **Total commands** | 36 across all plugins |
| **Total agents** | 14 across all plugins |
| **Total skills** | 13 including sub-skills |
| **Plugins with MCP servers** | 2 (`devops`, `rag`) |
| **Plugins with hooks** | All 7 |
| **Marketplace maintainer** | Single (Ahmed Lakosha, 4 git identity variants, 132+ commits) |
| **Vendored references** | `claude-plugins-official-main/` (read-only) |

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
