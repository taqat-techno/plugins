# Plugin Catalog

All 17 plugins in the **taqat-techno-plugins** marketplace, with current version, category, component inventory, and a link to each plugin's own documentation.

Listed in marketplace order. Component counts are the real contents of each plugin directory; versions are the value in each plugin's `.claude-plugin/plugin.json`.

## Catalog

| # | Plugin | Version | Category | Commands | Agents | Skills | Hooks | MCP | Docs |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **odoo** | `2.9.0` | development | 19 | 4 | 23 | 5 | yes | [[Odoo Plugin\|Odoo-Plugin]] · [README](../../odoo-plugin/README.md) |
| 2 | **devops** | `6.9.1` | productivity | 9 | 3 | 1 | 2 | yes | [[DevOps Plugin\|DevOps-Plugin]] · [README](../../devops-plugin/README.md) |
| 3 | **notification** | `1.0.0` | productivity | 1 | 0 | 0 | 5 | — | [[Notification Plugin\|Notification-Plugin]] · [README](../../notification-plugin/README.md) |
| 4 | **pandoc** | `2.2.0` | productivity | 1 | 0 | 1 | 0 | — | [[Pandoc Plugin\|Pandoc-Plugin]] · [README](../../pandoc-plugin/README.md) |
| 5 | **remotion** | `2.2.0` | development | 1 | 0 | 1 | 0 | — | [[Remotion Plugin\|Remotion-Plugin]] · [README](../../remotion-plugin/README.md) |
| 6 | **ui-ux-mechanics** | `3.2.0` | design | 1 | 2 | 3 | 0 | — | [[Ui Ux Mechanics Plugin\|Ui-Ux-Mechanics-Plugin]] · [README](../../ui-ux-mechanics-plugin/README.md) |
| 7 | **rag** | `0.18.0` | productivity | 9 | 1 | 4 | 2 | yes | [[Rag Plugin\|Rag-Plugin]] · [README](../../rag-plugin/README.md) |
| 8 | **react-kit** | `0.6.0` | development | 3 | 1 | 16 | 0 | — | [README](../../react-kit-plugin/README.md) |
| 9 | **qa-browser** | `0.5.0` | productivity | 5 | 2 | 13 | 2 | — | [README](../../qa-browser-plugin/README.md) |
| 10 | **docs-wiki** | `0.8.0` | productivity | 7 | 3 | 10 | 0 | — | [README](../../docs-wiki-plugin/README.md) |
| 11 | **claude-env-doctor** | `0.6.0` | productivity | 1 | 1 | 2 | 1 | — | [README](../../claude-env-doctor-plugin/README.md) |
| 12 | **agent-safety-guards** | `0.2.0` | productivity | 0 | 0 | 6 | 1 | — | [README](../../agent-safety-guards-plugin/README.md) |
| 13 | **release-safety** | `0.4.0` | productivity | 1 | 0 | 3 | 1 | — | [README](../../release-safety-plugin/README.md) |
| 14 | **django** | `0.2.0` | development | 4 | 3 | 7 | 3 | — | [README](../../django-plugin/README.md) |
| 15 | **fastapi** | `0.2.0` | development | 4 | 3 | 8 | 3 | — | [README](../../fastapi-plugin/README.md) |
| 16 | **git-safety** | `0.3.0` | productivity | 0 | 0 | 2 | 2 | — | [README](../../git-safety-plugin/README.md) |
| 17 | **worktree** | `1.0.0` | development | 0 | 0 | 5 | 0 | — | [README](../../worktree-plugin/README.md) |

**Totals:** 66 commands · 23 agents · 105 skills · 27 hook handlers · 3 bundled MCP servers.

Plugins without a dedicated wiki page are documented in their own `README.md`; the link column points there.

## One-line purpose

- **odoo** — "Do anything an Odoo developer needs, across Odoo 14–19, from upgrade to theme scaffolding to OWL app to security audit."
- **devops** — "Azure DevOps from inside Claude Code, with persistent identity, role-based permissions, and business-rule enforcement."
- **notification** — "Tell my desktop when Claude needs me. No AI, no service, no tokens."
- **pandoc** — "Convert between 50+ document formats with one command that understands what you mean."
- **remotion** — "Create narrated videos with a continuous audio pipeline that doesn't cut between slides."
- **ui-ux-mechanics** — "Turn Claude into a professional UI/UX designer with safe Figma MCP write mechanics and WCAG accessibility rigor."
- **rag** — "Make the local `ragtools` RAG product install, run, repair, and stay healthy — and teach Claude to search it correctly. Never re-implement search."
- **react-kit** — "Reusable React/Next.js patterns, from app architecture to admin panels to React-19 migration."
- **qa-browser** — "Prove the app actually works for each role, with evidence, without touching production."
- **docs-wiki** — "Create, organise, validate, and audit a project wiki — and catch it drifting from the code."
- **claude-env-doctor** — "Diagnose the local Claude Code environment. Never blindly mutate it."
- **agent-safety-guards** — "Keep agent sessions honest and multi-agent fan-out reliable."
- **release-safety** — "Prove the fix is deployed, not just merged."
- **django** — "Django and DRF done the safe way — ORM, migrations, config, security, tests, performance."
- **fastapi** — "FastAPI done the safe way — Pydantic v2, async correctness, Alembic, security, tests."
- **git-safety** — "Stop the git commands that quietly destroy someone else's work."
- **worktree** — "Make a worktree a place you can live in, not a command you have to remember."

## Category breakdown

| Category | Plugins |
|---|---|
| **development** | `odoo`, `remotion`, `react-kit`, `django`, `fastapi`, `worktree` |
| **productivity** | `devops`, `notification`, `pandoc`, `rag`, `qa-browser`, `docs-wiki`, `claude-env-doctor`, `agent-safety-guards`, `release-safety`, `git-safety` |
| **design** | `ui-ux-mechanics` |

## Components at a glance

### Bundled MCP servers

- **devops** — Azure DevOps MCP (`@azure-devops/mcp`, pinned to **2.8.0** deliberately; 2.9.0 collapses 90 tools into 37 renamed ones and breaks every agent, hook, and rule)
- **rag** — ragtools MCP (spawns `rag serve` directly)
- **odoo** — live-instance Odoo MCP for Odoo 14–19

Plugin-provided MCP tools are namespaced `mcp__plugin_<plugin>_<server>__<tool>`. A hook matcher or agent tool list written against the bare `mcp__<server>__` form silently never fires.

The `ui-ux-mechanics` plugin's Figma integration uses an external Figma MCP that the user configures separately — it is not shipped inside the plugin. The `figma-mcp-mechanics` skill adds the safe-write layer on top of whatever that external server exposes.

### Hooks

11 of 17 plugins register hooks; 6 register none at all. The house posture is **advisory over blocking**:

| Plugin | Hooks | Posture |
|---|---|---|
| `odoo` | 5 | SessionStart detection + `guard_core_odoo.py` **blocks** edits to core Odoo files (the one true data-loss guard) |
| `notification` | 5 | All `async: true` — structurally cannot block Claude |
| `django`, `fastapi` | 3 each | SessionStart detection + advisory write/bash guards |
| `devops`, `rag`, `qa-browser`, `git-safety` | 2 each | Advisory; `qa-browser`'s production-URL gate is the only other blocker |
| `claude-env-doctor`, `agent-safety-guards`, `release-safety` | 1 each | Advisory only, exit 0 always |
| `pandoc`, `remotion`, `ui-ux-mechanics`, `react-kit`, `docs-wiki`, `worktree` | 0 | No hooks registered |

`worktree` advertises zero hooks as a feature: installing it cannot disturb a session. `notification` reaches the same guarantee a different way — every hook is async, so it cannot block or control Claude even if the script is broken.

## Related and complementary plugins

| If you use... | You might want... | Why |
|---|---|---|
| `odoo` | `devops` | Track Odoo work items and sprints in Azure DevOps |
| `odoo`, `remotion` | `notification` | Long upgrades and renders tell your desktop when they finish |
| Any plugin | `notification` | Questions and permission prompts stop being something you have to watch for |
| `django`, `fastapi` | `release-safety` | Verify the migration actually landed in the target environment |
| `django`, `fastapi` | `qa-browser` | Prove the API's RBAC holds at runtime, not just in the code |
| `react-kit` | `qa-browser` | Smoke-test the admin panel you just scaffolded, per role |
| `worktree` | `git-safety` | Parallel checkouts are exactly where `reset --hard` and `stash` bite |
| `devops` | `rag` | Search internal runbooks and SOPs while triaging PRs |
| `docs-wiki` | `rag` | Index the wiki you just wrote so Claude can retrieve it |
| Any plugin | `agent-safety-guards` | Guardrails for fan-out and credential handling |

## Version compatibility

| Plugin | Claude Code | Product compatibility |
|---|---|---|
| odoo | current | Odoo 14, 15, 16, 17, 18, 19 |
| devops | current | Azure DevOps Services (any organization); `@azure-devops/mcp` **2.8.0** only |
| notification | **v2.1.202+** (v2.1.233+ recommended) | Windows 10/11, macOS, Linux desktop. Python 3.8+ on `PATH` |
| pandoc | current | Pandoc 3.0+ (auto-installed by `/pandoc setup`) |
| remotion | current | Remotion 4.0+ (installed by `/remotion <name>`) |
| ui-ux-mechanics | current | Figma via external Figma MCP (install separately) |
| rag | current | ragtools 3.0.x (scoped-search contract) |
| react-kit | current | React 18/19, Next.js 14+ |
| qa-browser | current | chrome-devtools-mcp or playwright MCP |
| docs-wiki | current | GitHub Wiki, GitLab Wiki, Azure DevOps Wiki, MkDocs, in-repo `wiki/` |
| claude-env-doctor | current | Windows, WSL, macOS, Linux |
| agent-safety-guards | current | Any |
| release-safety | current | Provider-neutral (GitHub Actions patterns included) |
| django | current | Django 4.2 / 5.x + DRF |
| fastapi | current | FastAPI 0.11x+, Pydantic v2, SQLAlchemy 2.x, Alembic |
| git-safety | current | Any git ≥ 2.20 |
| worktree | current | Any git with `worktree` support. Windows / macOS / Linux, no WSL required |

## See also

- [[Marketplace Overview|Marketplace-Overview]] — conventions, registration, layout
- [[Installation and Usage|Installation-and-Usage]] — how to install the marketplace
- [[Architecture]] — cross-cutting layering patterns
- Individual plugin pages (left sidebar); plugins without a page are documented in their own README
