# TAQAT Techno Plugins — Marketplace Wiki

Welcome to the **taqat-techno-plugins** marketplace for Claude Code. This wiki is the operator and contributor guide for the 7 production plugins shipped from this repository.

## What this marketplace is

A curated Claude Code plugin catalog published at **[github.com/taqat-techno/plugins](https://github.com/taqat-techno/plugins)**. Each plugin delivers domain-specific capabilities: Odoo ERP development, Azure DevOps integration, local RAG knowledge bases, UI/UX design, universal document conversion, video creation with narration, and mobile push notifications.

The marketplace targets a single power-user workflow: real client projects at TAQAT Techno, not templates or demos. Every plugin is evidence-grounded in real operational incidents — Project Alpha migration, the Aqraboon emergency-assistance runbook retrieval incident, ragtools' v2.4.1 data-loss bug, etc.

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

| Plugin | Role | Wiki page |
|---|---|---|
| **odoo** | Unified Odoo 14–19 toolkit — upgrade, frontend, testing, security, i18n, reports, Docker, service lifecycle | [[Odoo Plugin\|Odoo-Plugin]] |
| **devops** | Azure DevOps HYBRID (CLI + MCP) — work items, PRs, pipelines, wiki, role-based state machine | [[DevOps Plugin\|DevOps-Plugin]] |
| **rag** | Ragtools local RAG operations console — install, diagnose, repair, ignore rules, project ops via MCP | [[Rag Plugin\|Rag-Plugin]] |
| **paper** | UI/UX design specialist — screens, wireframes, Figma MCP, WCAG 2.1 AA, design systems | [[Paper Plugin\|Paper-Plugin]] |
| **pandoc** | Universal document conversion — 50+ input × 60+ output formats, RTL support, Pandoc-powered | [[Pandoc Plugin\|Pandoc-Plugin]] |
| **remotion** | Video creation with smooth voice narration — continuous audio pipeline, edge-tts | [[Remotion Plugin\|Remotion-Plugin]] |
| **ntfy-notifications** | Mobile push notifications via ntfy.sh — free, no account, two-way Q&A | [[Ntfy Plugin\|Ntfy-Plugin]] |

## Repo essentials

- **Marketplace manifest:** `plugins/.claude-plugin/marketplace.json`
- **Plugin development guide (source):** `plugins/CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`
- **Skills spec:** `plugins/agent_skills_spec.md`
- **Structural validator:** `plugins/validate_plugin.py` (plus `validate_plugin_simple.py` for fast PyYAML-free checks)
- **Reference marketplace (read-only):** `claude-plugins-official-main/` — Anthropic's official patterns, consulted not modified

## Support and maintenance

- **Owner:** [TAQAT Techno](https://www.taqatechno.com)
- **Contact:** `info@taqatechno.com`
- **Issues:** [github.com/taqat-techno/plugins/issues](https://github.com/taqat-techno/plugins/issues)
- **License:** MIT for the marketplace and most plugins; individual plugins may use their own licenses (e.g. `odoo-plugin` uses LGPL-3.0-or-later).

---

_This wiki is generated from source files in `plugins/wiki/` in the main repo. Commit wiki changes alongside plugin changes. See [[Contribution Guide\|Contribution-Guide]] for the sync-to-GitHub-Wiki workflow._
