# Plugin Catalog

All 7 plugins in the **taqat-techno-plugins** marketplace, with current version, category, component inventory, and a link to each plugin's own wiki page.

## Catalog

| # | Plugin | Version | Category | Components | Wiki page | Source README |
|---|---|---|---|---|---|---|
| 1 | **odoo** | `1.0.0` | development | 17 commands, 4 agents, 8 sub-skills, hooks | [[Odoo Plugin\|Odoo-Plugin]] | [`odoo-plugin/README.md`](../../odoo-plugin/README.md) |
| 2 | **devops** | `6.3.0` | productivity | 9 commands, 3 agents, MCP server, rules, data, hooks | [[DevOps Plugin\|DevOps-Plugin]] | [`devops-plugin/README.md`](../../devops-plugin/README.md) |
| 3 | **rag** | `0.5.0` | productivity | 6 commands, 1 agent, 1 skill, MCP server, 3 rules, hooks | [[Rag Plugin\|Rag-Plugin]] | [`rag-plugin/README.md`](../../rag-plugin/README.md) |
| 4 | **paper** | `3.0.0` | design | 1 command, 2 agents, 2 skills, hooks | [[Paper Plugin\|Paper-Plugin]] | [`paper-plugin/README.md`](../../paper-plugin/README.md) |
| 5 | **pandoc** | `2.1.0` | productivity | 1 command, hooks | [[Pandoc Plugin\|Pandoc-Plugin]] | [`pandoc-plugin/README.md`](../../pandoc-plugin/README.md) |
| 6 | **remotion** | `2.1.0` | development | 1 command, templates, hooks | [[Remotion Plugin\|Remotion-Plugin]] | [`remotion-plugin/README.md`](../../remotion-plugin/README.md) |
| 7 | **ntfy-notifications** | `3.0.0` | productivity | 2 commands, hooks | [[Ntfy Plugin\|Ntfy-Plugin]] | [`ntfy-plugin/README.md`](../../ntfy-plugin/README.md) |

## One-line purpose

- **odoo** — "Do anything an Odoo developer needs, across Odoo 14–19, from upgrade to theme scaffolding to security audit."
- **devops** — "Azure DevOps from inside Claude Code, with persistent identity, role-based permissions, and business-rule enforcement."
- **rag** — "Make the local `ragtools` RAG product install, run, repair, and stay healthy. Never re-implement search."
- **paper** — "Turn Claude into a professional UI/UX designer with Figma MCP sync and WCAG accessibility rigor."
- **pandoc** — "Convert between 50+ document formats with one command that understands what you mean."
- **remotion** — "Create narrated videos with a continuous audio pipeline that doesn't cut between slides."
- **ntfy** — "Get a push notification on your phone when Claude finishes a task or needs you. Free. No account."

## Category breakdown

| Category | Plugins |
|---|---|
| **development** | `odoo`, `remotion` |
| **productivity** | `devops`, `rag`, `pandoc`, `ntfy-notifications` |
| **design** | `paper` |

## Components at a glance

### Commands per plugin

- **odoo**: 17 — `/odoo-upgrade`, `/odoo-precheck`, `/odoo-quickfix`, `/odoo-frontend`, `/create-theme`, `/odoo-docker`, `/odoo-service`, `/odoo-start`, `/odoo-stop`, `/odoo-init`, `/odoo-db`, `/odoo-ide`, `/odoo-scaffold`, `/odoo-test`, `/odoo-security`, `/odoo-i18n`, `/odoo-report`
- **devops**: 9 — `/init`, `/create`, `/workday`, `/standup`, `/sprint`, `/log-time`, `/timesheet`, `/cli-run`, `/task-monitor`
- **rag**: 6 — `/rag-doctor`, `/rag-setup`, `/rag-projects`, `/rag-reset`, `/rag-config`, `/rag-sync-docs` (maintainer-only)
- **paper**: 1 — `/paper` (dispatcher to skills)
- **pandoc**: 1 — `/pandoc` (dispatcher with subcommands: `setup`, `status`, `convert`, `formats`, `help`)
- **remotion**: 1 — `/remotion` (project init + status)
- **ntfy-notifications**: 2 — `/ntfy`, `/ntfy-mode`

### Agents per plugin

- **odoo**: `security-auditor`, `test-analyzer`, `theme-generator`, `upgrade-analyzer`
- **devops**: `work-item-ops`, `sprint-planner`, `pr-reviewer`
- **rag**: `rag-log-scanner`
- **paper**: `design-reviewer`, `wireframe-builder`

### MCP servers (plugin-level auto-wiring)

- **devops** — Azure DevOps MCP (npx `@azure-devops/mcp`, wrapped in flat-shape `.mcp.json`)
- **rag** — ragtools MCP v2.5.0 (spawns `rag serve` directly — 22 tools: 3 core + 9 project ops + 9 debug)

Paper's Figma integration uses an external Figma MCP that the user configures separately — it is not shipped inside the plugin.

### Hooks per plugin

All 7 plugins have at least one hook. Risk-ranked per [`HOOK_STABILIZATION_REPORT.md`](../../HOOK_STABILIZATION_REPORT.md):

- **odoo** — `license-audit.py` (PreToolUse), `guard_core_odoo.py` (PreToolUse blocker)
- **rag** — `lock_conflict_check.py` (PreToolUse, Qdrant lock guardrail), `prompt_retrieval_reminder.py` (UserPromptSubmit, Tier-2 guided enforcement)
- **devops** — `pre-write-validate.sh`, `pre-bash-check.sh`, `post-bash-suggest.sh`, `session-start.sh`, etc.
- **paper**, **pandoc**, **remotion**, **ntfy** — lighter hook sets, mostly advisory

## Related and complementary plugins

| If you use... | You might want... | Why |
|---|---|---|
| `odoo` | `devops` | Track Odoo work items and sprints in Azure DevOps |
| `odoo` | `ntfy` | Long-running Odoo upgrades notify your phone when done |
| `rag` | (standalone) | No cross-integration — knowledge base is self-contained |
| `paper` | `pandoc` | Export design docs/specs from Markdown to PDF/Word with the same toolchain |
| `remotion` | `ntfy` | Render completions pushed to your phone |
| `devops` | `rag` | Search internal runbooks/SOPs while triaging PRs |
| Any plugin | `ntfy` | Always useful for long-running tasks |

## Version compatibility

| Plugin | Tested with Claude Code | Product compatibility |
|---|---|---|
| odoo | current | Odoo 14, 15, 16, 17, 18, 19 |
| devops | current | Azure DevOps Services (any organization) |
| rag | current | ragtools 2.5.x (MCP envelope contract stable) |
| paper | current | Figma (via external Figma MCP — install separately) |
| pandoc | current | Pandoc 3.0+ (auto-installed by `/pandoc setup` if missing) |
| remotion | current | Remotion 4.0+ (installed by `/remotion <name>`) |
| ntfy | current | ntfy.sh (public instance or self-hosted) |

## See also

- [[Marketplace Overview|Marketplace-Overview]] — conventions, registration, layout
- [[Installation and Usage|Installation-and-Usage]] — how to install the marketplace
- Individual plugin pages (left sidebar)
