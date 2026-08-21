# TAQAT Techno Plugins — Claude Code Marketplace

![Plugins](https://img.shields.io/badge/plugins-17-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Production-ready Claude Code plugins for professional development — Odoo ERP, Azure DevOps, desktop notifications, UI/UX design, video creation, document conversion, local RAG knowledge bases, reusable React/Next.js and Django/FastAPI patterns, browser QA, project wikis, git and release safety, worktree workspaces, and local-environment diagnosis.

> **Design policy:** every plugin is **generic and reusable** by any team in any workspace (see [Genericness & reusability](#genericness--reusability-policy)), and we deliberately **do not rebuild capabilities that official Claude plugins already cover well** (see [Official-plugin coverage boundary](#official-plugin-coverage-boundary)). Recent rationale and decisions: [`OFFICIAL_PLUGINS_COVERAGE_AUDIT.md`](./OFFICIAL_PLUGINS_COVERAGE_AUDIT.md), [`LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md`](./LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md), and the latest change log [`LOCAL_PLUGIN_ENHANCEMENT_IMPLEMENTATION_REPORT.md`](./LOCAL_PLUGIN_ENHANCEMENT_IMPLEMENTATION_REPORT.md).

---

## Available plugins

Listed in marketplace order. Versions are the value in each plugin's `.claude-plugin/plugin.json`.

| # | Plugin | Version | Category | Description | Documentation |
|---|--------|---------|----------|-------------|---------------|
| 1 | **odoo** | `2.9.0` | development | Unified Odoo development toolkit — upgrade, frontend themes, testing, security auditing, i18n/PO, reports, Docker infrastructure, server lifecycle, OWL app scaffolding, and a live-instance MCP connection across Odoo 14–19. | [README](./odoo-plugin/README.md) |
| 2 | **devops** | `6.9.1` | productivity | Azure DevOps HYBRID integration — work items, PRs, pipelines, repos, wiki via CLI + MCP, persistent profile, role-based state machine, plus a provider-neutral remote-write gate and CI-hardening checklist. | [README](./devops-plugin/README.md) |
| 3 | **notification** | `1.0.0` | productivity | Native desktop notifications when a session needs you — questions, permission prompts, task completions, turn completion, API failures. Hooks only, zero tokens at runtime, never blocks Claude, silent no-op on WSL and headless hosts. | [README](./notification-plugin/README.md) |
| 4 | **pandoc** | `2.2.0` | productivity | Universal document conversion powered by Pandoc — 50+ input and 60+ output formats, citations, Arabic/RTL support. | [README](./pandoc-plugin/README.md) |
| 5 | **remotion** | `2.2.0` | development | Create professional videos with smooth voice narration using Remotion — continuous audio pipeline, free edge-tts voices, video from text prompts. | [README](./remotion-plugin/README.md) |
| 6 | **ui-ux-mechanics** | `3.2.0` | design | UI/UX design + Figma-MCP execution mechanics — screen design, wireframing, design review, design systems, WCAG 2.1 AA accessibility auditing, plus safe Figma MCP write workflows. | [README](./ui-ux-mechanics-plugin/README.md) |
| 7 | **rag** | `0.18.0` | productivity | Operational console **and** retrieval guide for the ragtools local RAG product — install, configure, diagnose, repair, upgrade, run, and scope every search correctly. Does NOT re-implement search. | [README](./rag-plugin/README.md) |
| 8 | **react-kit** | `0.6.0` | development | Reusable React / Next.js patterns — architecture, admin panels, dashboards, CRUD/forms, role-aware UI, loading/error/empty/access states, data-fetching error handling, RTL/LTR, React-19 migration, and analyzer/lint finding triage. | [README](./react-kit-plugin/README.md) |
| 9 | **qa-browser** | `0.5.0` | productivity | Framework-agnostic browser QA + role-based smoke tests, layered over chrome-devtools / playwright MCP. Live identity/RBAC proof, host-scoped headers, disposable-data safety, production-URL gate. | [README](./qa-browser-plugin/README.md) |
| 10 | **docs-wiki** | `0.8.0` | productivity | Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki. Source-of-truth doctrine, page templates, flat-namespace + link conventions, code-vs-wiki drift. | [README](./docs-wiki-plugin/README.md) |
| 11 | **claude-env-doctor** | `0.6.0` | productivity | Diagnose (never blindly mutate) the local Claude Code / dev environment — MCP wiring, Windows/WSL networking, login/401, LSP/Node spawn, Python encoding, Playwright browser setup. | [README](./claude-env-doctor-plugin/README.md) |
| 12 | **agent-safety-guards** | `0.2.0` | productivity | Generic agent-session safety + multi-agent workflow-reliability guardrails — credential-compromise response, read-only immutability, authorization verification, no-fabrication discipline, reliable fan-out. | [README](./agent-safety-guards-plugin/README.md) |
| 13 | **release-safety** | `0.4.0` | productivity | Provider-neutral release / deployment / migration safety — verify a fix is actually deployed (not just merged), diff environment secrets before promotion, detect migration drift, run risky cutovers safely, keep CI signals honest. | [README](./release-safety-plugin/README.md) |
| 14 | **django** | `0.2.0` | development | Reusable Django / DRF engineering toolkit — ORM & model design, zero-downtime migration safety, views & DRF API patterns, 12-factor config, security auditing, pytest-django testing, performance/caching. | [README](./django-plugin/README.md) |
| 15 | **fastapi** | `0.2.0` | development | Reusable FastAPI engineering toolkit — Pydantic v2 schemas, async routing & DI, SQLAlchemy/SQLModel data layer, Alembic migration safety, pydantic-settings config, security auditing, pytest + httpx testing, async correctness. | [README](./fastapi-plugin/README.md) |
| 16 | **git-safety** | `0.3.0` | productivity | Generic local git-workflow safety guardrails — stage explicit paths, re-check the tree before commit/push, never silent-switch or discard when dirty, per-repo identity, plus shared-checkout safety. Advisory only. | [README](./git-safety-plugin/README.md) |
| 17 | **worktree** | `1.0.0` | development | Make git worktrees a first-class workspace — list, create, switch, and safely clean parallel worktrees, with the active worktree in the status line. Git stays the source of truth; registers **zero hooks**. | [README](./worktree-plugin/README.md) |

---

## Quick installation

### Method 1 — Claude Code UI (recommended)

```
/plugin marketplace add taqat-techno/plugins
/plugin install <plugin-name>@taqat-techno-plugins
```

Then restart Claude Code.

### Method 2 — Manual clone

**Windows**
```cmd
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

**macOS / Linux**
```bash
cd ~/.claude/plugins/marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

Then open `/plugins` inside Claude Code and enable what you want.

### Verify installation

```
/plugin marketplace list
/plugin list
```

If a plugin does not appear, restart Claude Code — plugins are loaded from
`~/.claude/plugins/cache/`, and hooks in particular are read once at session start.

---

## Genericness & reusability policy

Every plugin here must be usable by **any team in any workspace**. Concretely:

- No company, client, or project names in skills, commands, agents, or hooks.
- No absolute user paths, private URLs, or internal hostnames.
- Anything installation-specific is supplied by the user at runtime — a `.local.md`, a config file under `${CLAUDE_PLUGIN_DATA}`, or an environment variable.
- Illustrative examples are allowed, but must be labelled as examples.

Run a genericness sweep before shipping: grep every skill / command / agent / hook file for project-specific tokens and confirm zero hits outside labelled examples.

---

## Official-plugin coverage boundary

We do not rebuild what the official Claude Code plugins already do well. Where the two overlap, ours layers on top rather than replacing:

| Capability | Owner | Our plugins |
|---|---|---|
| Browser automation engine | official `playwright`, `chrome-devtools-mcp` | `qa-browser` layers role-based QA over them |
| Net-new visual aesthetics | official `frontend-design` | `react-kit` owns methodology, patterns, and triage |
| GitHub PR / commit ergonomics | official `code-review`, `commit-commands` | `devops` owns Azure DevOps; `git-safety` owns local-tree safety |
| Plugin authoring | official `plugin-dev`, `skill-creator` | consulted as reference, never forked |

Full rationale in [`OFFICIAL_PLUGINS_COVERAGE_AUDIT.md`](./OFFICIAL_PLUGINS_COVERAGE_AUDIT.md).

---

## Plugin details

Each plugin ships its own complete README. Click through for commands, configuration, architecture, and usage examples.

### 1. odoo — Unified Odoo development toolkit

> 📖 [**Full documentation → `odoo-plugin/README.md`**](./odoo-plugin/README.md)

The single consolidated Odoo plugin covering **eight capabilities**: upgrade (v14→19 migrations), frontend theme development, testing toolkit, security auditing, i18n/PO translation management, email templates and QWeb reports, Docker infrastructure, and server lifecycle management. Each capability lives as a sub-skill inside `odoo-plugin/skills/<area>/`. Also ships an OWL front-end domain (architecture, app scaffolding, diagnostics) and a live-instance MCP server for Odoo 14–19.

**Key commands:** `/upgrade`, `/precheck`, `/quickfix`, `/frontend`, `/create-theme`, `/docker`, `/service`, `/start`, `/stop`, `/init`, `/db`, `/ide`, `/scaffold`, `/test`, `/security`, `/i18n`, `/report`, `/owl`, `/mcp-setup`.

---

### 2. devops — Azure DevOps integration (HYBRID CLI + MCP)

> 📖 [**Full documentation → `devops-plugin/README.md`**](./devops-plugin/README.md)

Comprehensive Azure DevOps integration via a **HYBRID** architecture: CLI for high-volume work and MCP server for natural-language queries. Enforces a role-based state machine with mandatory work-item hierarchy, auto-sprint assignment, and state-transition permissions. Also ships a **provider-neutral remote-write gate** (`rules/git-remote-write-gate.md`) and a **CI-hardening checklist** (`devops/CI_HARDENING.md`); GitHub PR/commit ergonomics are delegated to the official `code-review` / `commit-commands` plugins.

**Key commands:** `/init`, `/create`, `/workday`, `/standup`, `/sprint`, `/log-time`, `/timesheet`, `/cli-run`, `/task-monitor`. **Agents:** `work-item-ops`, `sprint-planner`, `pr-reviewer`.

**Note:** deliberately pinned to `@azure-devops/mcp` **2.8.0** — 2.9.0 collapses 90 tools into 37 renamed ones and breaks every agent, hook, and rule.

---

### 3. notification — Native desktop notifications

> 📖 [**Full documentation → `notification-plugin/README.md`**](./notification-plugin/README.md)

Tells your desktop when a Claude Code session needs you: a question is waiting, a permission prompt has gone unanswered, a task finished, the turn ended, or the API failed. **Hooks only** — no skills, no agents, no MCP, no model call, no transcript parsing. Every character of every notification is a field the hook payload already carried, so it costs exactly zero tokens while it runs.

| Notification | Fires on | Class |
|---|---|---|
| ❓ Claude Needs Your Answer | `PreToolUse` / `AskUserQuestion` | attention |
| 🔐 Claude Needs Approval | `Notification` / `permission_prompt` | attention |
| ❌ Claude Failed | `StopFailure` | attention |
| ✅ Task Completed | `TaskCompleted` | informational |
| ✅ Claude Finished | `Stop` | informational |

Attention notifications are sticky where the OS allows it (Windows toast `reminder` scenario, `notify-send -u critical` on GNOME/KDE); informational ones are transient and silent. Every notification carries a `project · session` identity line so concurrent sessions stay distinguishable. WSL, SSH, headless Linux, and hosts with no notifier are detected and skipped **silently**.

**Command:** `/notification:doctor` (runs bare — reports platform, backend, config, task-tool availability, and sends test notifications).

**Safety:** every hook is `async: true`, which structurally removes any ability to block Claude — three of the five events it observes are blocking events where exit 2 would suppress a question, trap a turn, or refuse a task completion. The notifier writes nothing to stdout and never runs a shell. See [`docs/decisions.md`](./notification-plugin/docs/decisions.md).

**Replaces** the retired `ntfy-notifications` plugin, which pushed to the external ntfy.sh service.

---

### 4. pandoc — Universal document converter

> 📖 [**Full documentation → `pandoc-plugin/README.md`**](./pandoc-plugin/README.md)

Document conversion powered by [Pandoc](https://pandoc.org/) — 50+ input and 60+ output formats with intelligent automation (PDF, Word, HTML, EPUB, presentations, citations, Arabic/RTL). Describe what you want in natural language; no flags to memorize.

**Commands:** `/pandoc setup`, `/pandoc status`, `/pandoc convert`, `/pandoc formats`, `/pandoc help`.

---

### 5. remotion — Video creation with voice narration

> 📖 [**Full documentation → `remotion-plugin/README.md`**](./remotion-plugin/README.md)

Create professional videos with smooth voice narration using [Remotion](https://remotion.dev). Solves voice-cutting-between-slides with a Continuous Audio Pattern. Free edge-tts voices (200+), MP4/WebM/GIF output, video from text prompts.

**Commands:** `/remotion` (status / initialize project).

---

### 6. ui-ux-mechanics — UI/UX design + Figma-MCP execution mechanics

> 📖 [**Full documentation → `ui-ux-mechanics-plugin/README.md`**](./ui-ux-mechanics-plugin/README.md)

Transforms Claude into a professional UI/UX designer — screens, wireframes, and full design systems for web, iOS, Android, or desktop. Integrates with Figma via MCP and adds safe Figma MCP write mechanics (write-access probing, metadata-lossiness handling, auto-layout/variant mechanics, prototype-link-safe edits). Enforces WCAG 2.1 AA accessibility.

**Key commands:** `/design`, `/design-review`, `/design-system`, `/figma-sync`, `/wireframe`. **Agents:** `design-reviewer`, `wireframe-builder`.

---

### 7. rag — Ragtools operations console and retrieval guide

> 📖 [**Full documentation → `rag-plugin/README.md`**](./rag-plugin/README.md)

Operations and support layer for the [ragtools](https://github.com/taqat-techno/rag) local Markdown knowledge base. Installs, configures, diagnoses, repairs, upgrades, and runs ragtools; knows the Qdrant single-process lock, dual-mode MCP, and failure catalog. Also teaches Claude to *use* it correctly: scope every search (ragtools refuses unscoped calls), check a project's indexing mode before code questions, and validate citation paths. **Does NOT re-implement search.** Generic "MCP not loading" diagnosis defers to `claude-env-doctor`.

**Key commands:** `/doctor`, `/setup`, `/projects`, `/reset`, `/config`, `/project-focus`, `/report`, `/md-rag-enhance`.

---

### 8. react-kit — Reusable React / Next.js patterns

> 📖 [**Full documentation → `react-kit-plugin/README.md`**](./react-kit-plugin/README.md)

> *Renamed from `react-admin-kit`.* Admin-panel creation is now **one capability** inside a broader React/Next.js patterns kit, not the whole identity.

Reusable engineering patterns for React / Next.js apps — application & component architecture, a view-type chooser (list / tree / kanban / form / dashboard), admin panels, dashboards/KPIs, CRUD + nested hierarchies, kanban workflow state machines, forms with tabs/relations/attachments, role-aware UI, loading/error/empty/access states, import/export UI, RTL/LTR, accessibility, and **frontend quality discipline**. Complementary to the official `frontend-design` plugin (which owns net-new visual aesthetics); react-kit owns methodology, patterns, and triage.

**15 skills + 3 commands** (`/admin-scaffold`, `/admin-audit`, `/admin-role-matrix`) **+ agent** `admin-route-auditor`. Generic and adapter-driven — entities, roles, APIs, and libraries are project-supplied.

---

### 9. qa-browser — Role-based browser QA

> 📖 [**Full documentation → `qa-browser-plugin/README.md`**](./qa-browser-plugin/README.md)

Framework-agnostic browser QA and role-based smoke testing, **layered over** the official `playwright` / `chrome-devtools-mcp` engines (it does not reimplement browser automation). Logs in as each role, walks modals and table actions, verifies UI-vs-API permissions, captures console / network / screenshot evidence, and produces a PASS / BLOCKED / NOT-TESTABLE table for UAT signoff.

**Commands:** `/qa-target`, `/qa-smoke`, `/qa-roles`, `/qa-route`, `/qa-report`. **Agents:** `qa-evidence-collector`, `qa-failure-classifier`.

**Safety:** production-URL gate (case-insensitive host match), disposable-data + external-side-effect scope-out, cancel-first destructive pattern, credential redaction.

---

### 10. docs-wiki — Project Wiki toolkit

> 📖 [**Full documentation → `docs-wiki-plugin/README.md`**](./docs-wiki-plugin/README.md)

Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki. Owns flat-namespace + filename-uniqueness + internal-link conventions, Mermaid and PlantUML authoring, broken-link sweeps, code-vs-wiki drift, and a push-approval gate. Adapts to GitHub Wiki / GitLab / Azure DevOps / MkDocs.

**Commands:** `/wiki-init`, `/wiki-audit`, `/wiki-update`, `/wiki-new`, `/wiki-drift`, `/wiki-sync-audit`, `/wiki-swimlane`. **Agents:** `wiki-link-auditor`, `wiki-cleanup-validator`, `wiki-drift-reporter`. **Templates:** SOP, runbook, role-guide, user-manual, workflow, release-handover, onboarding, architecture, decision record.

**Explicit boundary:** wiki-to-memory sync is **out of scope** — a separate future plugin.

---

### 11. claude-env-doctor — Local environment diagnosis

> 📖 [**Full documentation → `claude-env-doctor-plugin/README.md`**](./claude-env-doctor-plugin/README.md)

Generic doctor for the local **Claude Code / dev environment**. It **diagnoses, never blindly mutates** — routes a symptom to the right branch, runs read-only probes, classifies the failure, and proposes one safe next action. Branches: MCP not loading, Windows/WSL networking (DNS/VPN/HCS), login/401 loops, LSP / Node-CLI spawn, Python output encoding, and Playwright / browser-MCP setup. It is the canonical environment-troubleshooting home other plugins reference.

**Command:** `/env-doctor` (works with no arguments). **Agent:** `env-probe-reporter` (read-only). **Hook:** non-blocking SessionStart advisory.

**Scope / non-goals:** NOT server ops, deployment runbooks, or DevOps/GitHub workflow logic — local environment diagnosis only.

---

### 12. agent-safety-guards — Agent-session safety and workflow reliability

> 📖 [**Full documentation → `agent-safety-guards-plugin/README.md`**](./agent-safety-guards-plugin/README.md)

Generic guardrails for agent sessions and multi-agent fan-out. Covers credential-compromise response, read-only immutability, authorization verification, no-fabrication discipline, defensive failure design, structural assertions, test-double seams, and reliable orchestration (small waves, null-safe reduce, journaled resume, verify-before-done).

**6 skills**, no commands. **Hook:** one non-fatal `UserPromptSubmit` advisory that prints a single reminder when a submitted prompt contains a token-shaped string. It never blocks, never denies, and never echoes the matched value.

---

### 13. release-safety — Release, deployment, and migration safety

> 📖 [**Full documentation → `release-safety-plugin/README.md`**](./release-safety-plugin/README.md)

Provider-neutral safety for the moment code leaves your machine. Verify a fix is actually **deployed to the target environment**, not merely merged; diff environment secrets before promotion; detect migration drift; run risky cutovers and migrations safely (discover → backup → stage + validate → additive cutover → archive-by-rename); and keep CI signals honest by sweeping for gates that swallow their exit code.

**Command:** `/release-verify`. **Skills:** `release-verification`, `migration-safety`, `github-actions-release-safety`. **Hook:** SessionStart advisory.

---

### 14. django — Django / DRF engineering toolkit

> 📖 [**Full documentation → `django-plugin/README.md`**](./django-plugin/README.md)

Reusable Django and Django REST Framework patterns — ORM & model design, migration safety (zero-downtime expand-contract), views & DRF API design, settings/12-factor configuration, security auditing, pytest-django testing, and performance/caching.

**7 auto-activating skills + 4 commands + 3 agents** (`django-security-auditor`, `migration-safety-analyzer`, `orm-query-optimizer`) **+ hooks** for version/layout detection at session start, risky-migration and hardcoded-secret advisories, and a destructive-management-command guard. Generic and adapter-driven.

---

### 15. fastapi — FastAPI engineering toolkit

> 📖 [**Full documentation → `fastapi-plugin/README.md`**](./fastapi-plugin/README.md)

Reusable FastAPI patterns — Pydantic v2 schema design, async routing & dependency injection, SQLAlchemy/SQLModel data layer (N+1 and async-session traps), Alembic migration safety, pydantic-settings configuration, security auditing (OAuth2/JWT, CORS, injection), pytest + httpx testing, and async correctness/performance.

**8 auto-activating skills + 4 commands + 3 agents** (`fastapi-security-auditor`, `alembic-migration-analyzer`, `async-query-optimizer`) **+ hooks** for version/layout detection, event-loop-blocking and wildcard-CORS advisories, and a destructive-command guard.

---

### 16. git-safety — Local git-workflow guardrails

> 📖 [**Full documentation → `git-safety-plugin/README.md`**](./git-safety-plugin/README.md)

The safety layer that git integrations, commit helpers, and PR-review plugins leave out. Stage explicit paths (never `git add -A`); re-check the working tree before commit/push; never silent-switch or discard with a dirty tree; know that `git rm --cached` deletes a shared file team-wide on merge; keep per-repo author and remote push identity straight. Plus **shared-checkout safety** for when more than one agent, session, or syncer shares one working tree.

**2 skills.** **Hook:** one non-fatal `PreToolUse` advisory on Bash and PowerShell that prints a single reminder when a command contains a risky git shape. **Advisory only — it warns, it never blocks.**

---

### 17. worktree — Git worktrees as first-class workspaces

> 📖 [**Full documentation → `worktree-plugin/README.md`**](./worktree-plugin/README.md)

List, create, switch, and safely clean parallel git worktrees, with the active worktree always visible in the status line. A worktree is a *place*, not a session: it survives session exit via a git lock that Claude Code's cleanup cannot override, and any number of sessions may share it. Git stays the source of truth — no registry, no cache, no plugin state.

**5 skills** (`list`, `new`, `switch`, `clean`, `init`) + status-line integration for PowerShell and POSIX shells. **Registers ZERO hooks**, so installing it cannot disturb a session. Windows / macOS / Linux, no WSL required.

---

## Repository structure

```
taqat-techno-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata (17 plugins)
├── odoo-plugin/                  # Unified Odoo development toolkit (v14-19)
├── devops-plugin/                # Azure DevOps HYBRID integration (CLI + MCP)
├── notification-plugin/          # Native desktop notifications (hooks only)
├── pandoc-plugin/                # Universal document conversion
├── remotion-plugin/              # Video creation with voice narration
├── ui-ux-mechanics-plugin/       # UI/UX design + Figma-MCP execution mechanics
├── rag-plugin/                   # Ragtools local RAG operations + retrieval guide
├── react-kit-plugin/             # Reusable React / Next.js patterns
├── qa-browser-plugin/            # Browser QA + role-based smoke tests
├── docs-wiki-plugin/             # Project Wiki toolkit
├── claude-env-doctor-plugin/     # Local Claude Code / dev environment doctor
├── agent-safety-guards-plugin/   # Agent-session safety + workflow reliability
├── release-safety-plugin/        # Release / deployment / migration safety
├── django-plugin/                # Django / DRF engineering toolkit
├── fastapi-plugin/               # FastAPI engineering toolkit
├── git-safety-plugin/            # Local git-workflow guardrails
├── worktree-plugin/              # Git worktrees as first-class workspaces
├── wiki/                         # GitHub Wiki source pages
├── agent_skills_spec.md          # Claude Code skills specification
├── CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md  # Plugin development guide
├── CONTRIBUTING.md               # Contribution guidelines
├── validate_plugin.py            # Per-plugin structure validator
├── validate_marketplace.py       # Cross-plugin architecture + discovery validator
├── validate_plugin_simple.py     # Fast structural check (no pyyaml)
├── LICENSE                       # MIT License
└── README.md                     # This file
```

---

## Validation

Both validators must pass. Neither is sufficient alone: `validate_plugin.py` checks one plugin's shape and structurally cannot see a runtime-discovery failure — which is how 15 unreachable skills once survived a fully green per-plugin run.

```bash
# Per-plugin shape: manifest, frontmatter, hooks, naming, docs
PYTHONIOENCODING=utf-8 python validate_plugin.py <plugin-dir>   # require 0 errors

# Cross-plugin: skill discovery, name collisions, identity, line endings,
# state-outside-plugin-root, MCP namespacing
python validate_marketplace.py                                  # require exit 0

# Fast structural check, no pyyaml needed
python validate_plugin_simple.py <plugin-dir>
```

Also run a **genericness sweep** before shipping — grep all skill / command / agent / hook files for project-specific tokens (company/client names, business-domain terms, absolute user paths, private URLs, token shapes) and confirm 0 hits outside labelled illustrative examples.

---

## Auto-updates

Enable auto-updates in Claude Code settings → **Plugins** → **taqat-techno-plugins** → **Auto-Update**. Or update manually:

```bash
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

Every plugin change ships with a `plugin.json` version bump and a CHANGELOG entry in the same commit. Without the bump, Claude Code's updater cannot detect the new version and users stay on stale code.

---

## Troubleshooting

### Plugins not appearing
```bash
ls ~/.claude/plugins/marketplaces/taqat-techno-plugins
cat ~/.claude/plugins/marketplaces/taqat-techno-plugins/.claude-plugin/marketplace.json
# Then restart Claude Code
```

### Plugin not loading
1. Verify YAML frontmatter in the plugin's `commands/*.md`, `agents/*.md`, and `skills/*/SKILL.md`.
2. Confirm every skill sits at exactly `skills/<name>/SKILL.md` — one level deeper never loads.
3. Check the plugin's `source` path in `.claude-plugin/marketplace.json`.
4. Look for manifest syntax errors: `python validate_plugin.py <plugin-dir>`.
5. Restart Claude Code.

### Edits to a plugin have no effect
Claude Code runs plugins from `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`, not from your development checkout, and hooks are read once at session start. Run `/reload-plugins`, or restart the session.

### Environment / MCP problems
Use the **claude-env-doctor** plugin (`/env-doctor`) for MCP-not-loading, WSL/Windows networking, login/401, LSP spawn, encoding, and Playwright setup issues.

### No desktop notifications
Use the **notification** plugin's `/notification:doctor` — it reports the resolved backend and explains any unsupported host.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`](./CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md) for the full authoring workflow. Every new plugin must be registered in `.claude-plugin/marketplace.json`, validate at 0 errors on both validators, pass the genericness sweep, and respect the official-plugin coverage boundary.

---

## About TAQAT Techno

TAQAT Techno is an Odoo development and consulting firm specializing in enterprise-grade ERP solutions.

**Contact:** GitHub [@taqat-techno](https://github.com/taqat-techno) · Website [taqatechno.com](https://www.taqatechno.com) · Email `info@taqatechno.com`

---

## License

MIT License — see [`LICENSE`](./LICENSE). Individual plugins may ship their own license (e.g., `odoo-plugin` uses LGPL-3.0-or-later). See each plugin's `plugin.json` or `LICENSE` / `LICENSES.md`.

---
