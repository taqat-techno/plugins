# TAQAT Techno Plugins — Marketplace Wiki

Welcome to the **taqat-techno-plugins** marketplace for Claude Code. This wiki is the operator and contributor guide for the 17 production plugins shipped from this repository.

## What this marketplace is

A curated Claude Code plugin catalog published at **[github.com/taqat-techno/plugins](https://github.com/taqat-techno/plugins)**. Each plugin delivers domain-specific capabilities: Odoo ERP development, Azure DevOps integration, desktop notifications, local RAG knowledge bases, UI/UX design, document conversion, video creation, React / Django / FastAPI engineering patterns, browser QA, project wikis, and git, release, and environment safety.

> **Upstream products powering these plugins.** Some plugins in this marketplace are operator consoles for external products that live in their own repositories:
>
> | Plugin | Upstream product repo |
> |---|---|
> | [[Rag Plugin\|Rag-Plugin]] | **[github.com/taqat-techno/rag](https://github.com/taqat-techno/rag)** — the ragtools local RAG application (installers, source, release history, product docs) |
> | [[DevOps Plugin\|DevOps-Plugin]] | [Azure DevOps Services](https://dev.azure.com/) via the [`@azure-devops/mcp`](https://www.npmjs.com/package/@azure-devops/mcp) server |
> | [[Ui Ux Mechanics Plugin\|Ui-Ux-Mechanics-Plugin]] | [Figma](https://www.figma.com/) via the user-installed Figma MCP (separate install) |
> | [[Pandoc Plugin\|Pandoc-Plugin]] | [Pandoc](https://pandoc.org/) — auto-installed by `/pandoc setup` |
> | [[Remotion Plugin\|Remotion-Plugin]] | [Remotion](https://remotion.dev) — installed by `/remotion <name>` |

The marketplace targets a single power-user workflow: real client projects at TAQAT Techno, not templates or demos. Every plugin is evidence-grounded in real operational incidents — the Project Alpha migration, a client runbook-retrieval failure, ragtools' v2.4.1 data-loss bug, etc.

## Quick navigation

| If you want to... | Go to |
|---|---|
| Install the marketplace in Claude Code | [[Installation and Usage\|Installation-and-Usage]] |
| See every plugin at a glance | [[Plugin Catalog\|Plugin-Catalog]] |
| Understand how the marketplace is structured | [[Marketplace Overview\|Marketplace-Overview]] |
| Learn the conventions for authoring a new plugin | [[Plugin Development Guide\|Plugin-Development-Guide]] |
| Understand the layer/architecture patterns shared across plugins | [[Architecture]] |
| Troubleshoot a broken plugin or cache-vs-source drift | [[Troubleshooting]] |
| Contribute a change | [[Contribution Guide\|Contribution-Guide]] |
| See the release history and major milestones | [[Change History\|Change-History]] |

## Plugins (quick links)

| Plugin | Role | More |
|---|---|---|
| **odoo** | Unified Odoo 14-19 toolkit - upgrade, frontend, OWL, testing, security, i18n, reports, Docker, service lifecycle | [[Odoo Plugin\|Odoo-Plugin]] |
| **devops** | Azure DevOps HYBRID (CLI + MCP) - work items, PRs, pipelines, wiki, role-based state machine | [[DevOps Plugin\|DevOps-Plugin]] |
| **notification** | Native desktop notifications when a session needs you - hooks only, no AI, no service | [[Notification Plugin\|Notification-Plugin]] |
| **pandoc** | Universal document conversion - 50+ input x 60+ output formats, RTL support | [[Pandoc Plugin\|Pandoc-Plugin]] |
| **remotion** | Video creation with smooth voice narration - continuous audio pipeline, edge-tts | [[Remotion Plugin\|Remotion-Plugin]] |
| **ui-ux-mechanics** | UI/UX design - screens, wireframes, safe Figma MCP write mechanics, WCAG 2.1 AA | [[Ui Ux Mechanics Plugin\|Ui-Ux-Mechanics-Plugin]] |
| **rag** | Ragtools local RAG operations console and retrieval guide | [[Rag Plugin\|Rag-Plugin]] |
| **react-kit** | Reusable React / Next.js patterns - architecture, admin panels, states, React-19 migration | [README](../../react-kit-plugin/README.md) |
| **qa-browser** | Role-based browser QA with evidence - UI-vs-API permission proof, UAT signoff | [README](../../qa-browser-plugin/README.md) |
| **docs-wiki** | Project wiki toolkit - authoring, link validation, code-vs-wiki drift | [README](../../docs-wiki-plugin/README.md) |
| **claude-env-doctor** | Local Claude Code / dev environment diagnosis - MCP, WSL, login, LSP, encoding | [README](../../claude-env-doctor-plugin/README.md) |
| **agent-safety-guards** | Agent-session safety and multi-agent workflow reliability | [README](../../agent-safety-guards-plugin/README.md) |
| **release-safety** | Prove a fix is deployed, not just merged; migration and CI-signal safety | [README](../../release-safety-plugin/README.md) |
| **django** | Django / DRF toolkit - ORM, migrations, DRF, config, security, tests, performance | [README](../../django-plugin/README.md) |
| **fastapi** | FastAPI toolkit - Pydantic v2, async routing, SQLAlchemy, Alembic, security, tests | [README](../../fastapi-plugin/README.md) |
| **git-safety** | Local git-workflow guardrails, including shared-checkout safety. Advisory only | [README](../../git-safety-plugin/README.md) |
| **worktree** | Git worktrees as first-class workspaces, with status-line integration. Zero hooks | [README](../../worktree-plugin/README.md) |

Full inventory with versions and component counts: [[Plugin Catalog\|Plugin-Catalog]].

## Repo essentials

- **Marketplace manifest:** `plugins/.claude-plugin/marketplace.json`
- **Plugin development guide (source):** `plugins/CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`
- **Skills spec:** `plugins/agent_skills_spec.md`
- **Structural validator:** `plugins/validate_plugin.py` (plus `validate_plugin_simple.py` for fast PyYAML-free checks)
- **Reference marketplace (read-only):** `claude-plugins-official/` — Anthropic's official patterns, consulted not modified

## Support and maintenance

- **Owner:** [TAQAT Techno](https://www.taqatechno.com)
- **Contact:** `info@taqatechno.com`
- **Issues:** [github.com/taqat-techno/plugins/issues](https://github.com/taqat-techno/plugins/issues)
- **License:** MIT for the marketplace and most plugins; individual plugins may use their own licenses (e.g. `odoo-plugin` uses LGPL-3.0-or-later).

---

_This wiki is generated from source files in `plugins/wiki/` in the main repo. Commit wiki changes alongside plugin changes. See [[Contribution Guide\|Contribution-Guide]] for the sync-to-GitHub-Wiki workflow._
