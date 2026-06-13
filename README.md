# TAQAT Techno Plugins — Claude Code Marketplace

![Plugins](https://img.shields.io/badge/plugins-11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Production-ready Claude Code plugins for professional development — Odoo ERP, Azure DevOps, UI/UX design, video creation, document conversion, local RAG knowledge bases, mobile push notifications, reusable React/Next.js patterns, browser QA, project wikis, and local-environment diagnosis.

> **Design policy:** every plugin is **generic and reusable** by any team in any workspace (see [Genericness & reusability](#genericness--reusability-policy)), and we deliberately **do not rebuild capabilities that official Claude plugins already cover well** (see [Official-plugin coverage boundary](#official-plugin-coverage-boundary)). Recent rationale and decisions: [`OFFICIAL_PLUGINS_COVERAGE_AUDIT.md`](./OFFICIAL_PLUGINS_COVERAGE_AUDIT.md), [`LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md`](./LESSONS_TO_PLUGINS_GLOBAL_RECOMMENDATION_PLAN.md), and the latest change log [`LOCAL_PLUGIN_ENHANCEMENT_IMPLEMENTATION_REPORT.md`](./LOCAL_PLUGIN_ENHANCEMENT_IMPLEMENTATION_REPORT.md).

---

## Available plugins

| # | Plugin | Version | Category | Description | Documentation |
|---|--------|---------|----------|-------------|---------------|
| 1 | **odoo** | `2.3.0` | development | Unified Odoo development toolkit — upgrade, frontend themes, testing, security auditing, i18n/PO, reports, Docker infrastructure, stack & DB lifecycle safety, and server lifecycle across Odoo 14–19. | [README](./odoo-plugin/README.md) |
| 2 | **devops** | `6.5.0` | productivity | Azure DevOps HYBRID integration — work items, PRs, pipelines, repos, wiki via CLI + MCP, persistent profile, role-based state machine, plus a provider-neutral remote-write gate and CI-hardening checklist. | [README](./devops-plugin/README.md) |
| 3 | **rag** | `0.13.2` | productivity | Operational console for the ragtools local RAG product — install, configure, diagnose, repair, upgrade, run. Knows the Qdrant lock, dual-mode MCP, and failure modes. Defers generic environment/MCP diagnosis to `claude-env-doctor`. | [README](./rag-plugin/README.md) |
| 4 | **ui-ux-mechanics** | `3.1.0` | design | UI/UX design + Figma-MCP execution mechanics — screen design, wireframing, design review, design systems, WCAG 2.1 AA accessibility auditing, plus safe Figma MCP write workflows (write-access probing, metadata-lossiness handling, auto-layout/variant mechanics, prototype-link-safe edits). | [README](./ui-ux-mechanics-plugin/README.md) |
| 5 | **pandoc** | `2.1.0` | productivity | Universal document conversion powered by Pandoc — 50+ input and 60+ output formats, citations, Arabic/RTL support. | [README](./pandoc-plugin/README.md) |
| 6 | **remotion** | `2.1.0` | development | Create professional videos with smooth voice narration using Remotion — continuous audio pipeline, free edge-tts voices, video from text prompts. | [README](./remotion-plugin/README.md) |
| 7 | **ntfy-notifications** | `3.0.0` | productivity | Push notifications to your phone via [ntfy.sh](https://ntfy.sh) when Claude completes tasks, needs input, or errors. Two-way Q&A. Free, no account. | [README](./ntfy-plugin/README.md) |
| 8 | **react-kit** | `0.5.0` | development | Reusable React / Next.js patterns — architecture, admin panels, dashboards, CRUD/forms, role-aware UI, loading/error/empty/access states, data-fetching error handling, RTL/LTR, React-19 migration, and analyzer/lint finding triage. 11 skills + 3 commands + `admin-route-auditor` agent. | [README](./react-kit-plugin/README.md) |
| 9 | **qa-browser** | `0.4.0` | productivity | Framework-agnostic browser QA + role-based smoke tests, layered over chrome-devtools / playwright MCP. Live identity/RBAC proof, host-scoped headers, disposable-data safety. 11 skills + 5 commands + 2 agents + production-URL gate. | [README](./qa-browser-plugin/README.md) |
| 10 | **docs-wiki** | `0.4.0` | productivity | Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki. Source-of-truth doctrine, page templates, flat-namespace + link conventions, code-vs-wiki drift. 8 skills + 6 commands + 3 agents + hooks. No wiki-to-memory sync. | [README](./docs-wiki-plugin/README.md) |
| 11 | **claude-env-doctor** | `0.2.0` | productivity | Diagnose (never blindly mutate) the local Claude Code / dev environment — MCP wiring, Windows/WSL networking, login/401, LSP/Node spawn, Python encoding, Playwright browser setup, IDE remote-dev OOM, `/doctor` ambiguity. The canonical environment-troubleshooting home other plugins reference. | [README](./claude-env-doctor-plugin/README.md) |
| 12 | **agent-safety-guards** | `0.1.0` | productivity | Generic agent-session safety + multi-agent workflow-reliability guardrails — credential-compromise response, read-only immutability, authorization verification, no-fabrication discipline, and reliable fan-out orchestration. Advisory, never auto-mutates. | [README](./agent-safety-guards-plugin/README.md) |
| 13 | **release-safety** | `0.1.0` | productivity | Provider-neutral release / deployment / migration safety — verify a fix is actually deployed to the target environment (not just merged), diff environment secrets before promotion, detect migration drift, run risky cutovers/migrations safely. | [README](./release-safety-plugin/README.md) |

---

## Quick installation

### Method 1 — Claude Code UI (recommended)

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace**.
4. Enter the repository URL: `https://github.com/taqat-techno/plugins.git`
5. Click **Install**.

All 11 plugins will become available automatically.

### Method 2 — Manual clone

**Linux / macOS:**
```bash
cd ~/.claude/plugins/marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

**Windows:**
```cmd
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

### Verify installation

In Claude Code, run `/plugins` and confirm all 11 plugins appear under the **taqat-techno-plugins** marketplace.

---

## Genericness & reusability policy

Every plugin in this marketplace MUST be usable by any team, in any workspace, with no edits:

- **No project-specific paths** (no absolute user paths, no machine names).
- **No private URLs** (no production/staging hosts, no internal endpoints).
- **No hardcoded business domains** (no company/client names, no domain entities) — these are **adapter inputs** the user supplies, never baked in.
- **No secrets** (tokens, credentials, `.env` values) anywhere.
- **Examples are illustrative only** — concrete examples are clearly labeled and the plugin's behavior never depends on them.

Validate genericness with a token sweep before shipping any change (see [Validation](#validation)).

## Official-plugin coverage boundary

We do **not** rebuild capabilities the official Anthropic marketplace already covers professionally. Where an official plugin provides primitives, our local plugins **layer methodology on top** rather than duplicating the engine:

| Don't rebuild locally | Use the official plugin | Local plugins layer… |
|---|---|---|
| Plugin/skill/hook/MCP authoring | `plugin-dev`, `skill-creator`, `mcp-server-dev`, `hookify` | — (use official directly) |
| Static + diff security review, secrets, injection | `security-guidance` | `qa-browser` adds **live** RBAC proof only |
| Raw browser automation + evidence | `playwright`, `chrome-devtools-mcp` | `qa-browser` adds QA methodology (roles, RBAC, UAT report) |
| GitHub PR review / commit / API | `code-review`, `pr-review-toolkit`, `commit-commands`, `github` | `devops` adds a provider-neutral safety gate + CI checklist |

See [`OFFICIAL_PLUGINS_COVERAGE_AUDIT.md`](./OFFICIAL_PLUGINS_COVERAGE_AUDIT.md) for the full coverage matrix.

---

## Plugin details

Each plugin ships its own complete README. Click through for commands, configuration, architecture, and usage examples.

### 1. Odoo — Unified development toolkit

> 📖 [**Full documentation → `odoo-plugin/README.md`**](./odoo-plugin/README.md)

The single consolidated Odoo plugin covering **eight capabilities**: upgrade (v14→19 migrations), frontend theme development, testing toolkit, security auditing, i18n/PO translation management, email templates and QWeb reports, Docker infrastructure, and server lifecycle management. Each capability lives as a sub-skill inside `odoo-plugin/skills/<area>/`. Recent additions: PO/gettext discipline, Docker volume + Postgres-version safety, and theme-load/CLI-upgrade references.

**Key commands:** `/upgrade`, `/precheck`, `/quickfix`, `/frontend`, `/create-theme`, `/docker`, `/service`, `/start`, `/stop`, `/init`, `/db`, `/ide`, `/scaffold`, `/test`, `/security`, `/i18n`, `/report`.

---

### 2. DevOps — Azure DevOps integration (HYBRID CLI + MCP)

> 📖 [**Full documentation → `devops-plugin/README.md`**](./devops-plugin/README.md)

Comprehensive Azure DevOps integration via a **HYBRID** architecture: CLI for high-volume work and MCP server for natural-language queries. Enforces a role-based state machine with mandatory work-item hierarchy, auto-sprint assignment, and state-transition permissions. Now also ships a **provider-neutral remote-write gate** (`rules/git-remote-write-gate.md` — permission-first + identity-correctness) and a **CI-hardening checklist** (`devops/CI_HARDENING.md`); GitHub PR/commit ergonomics are delegated to the official `code-review` / `commit-commands` / `github` plugins.

**Key commands:** `/init`, `/create`, `/workday`, `/standup`, `/sprint`, `/log-time`, `/timesheet`, `/cli-run`, `/task-monitor`. **Agents:** `work-item-ops`, `sprint-planner`, `pr-reviewer`.

---

### 3. Rag — Ragtools operations console

> 📖 [**Full documentation → `rag-plugin/README.md`**](./rag-plugin/README.md)

Operations and support layer for the [ragtools](https://github.com/taqat-techno/rag) local Markdown knowledge base. Installs, configures, diagnoses, repairs, upgrades, and runs ragtools; knows the Qdrant single-process lock, dual-mode MCP, and failure catalog. **Does NOT re-implement search.** Generic "MCP not loading" diagnosis now defers to the `claude-env-doctor` plugin; ragtools-specific checks stay local.

**Key commands:** `/doctor`, `/setup`, `/projects`, `/reset`, `/config`, `/project-focus`, `/report`, `/md-rag-enhance`, `/sync-docs`.

---

### 4. UI-UX-Mechanics — UI/UX design + Figma-MCP execution mechanics

> 📖 [**Full documentation → `ui-ux-mechanics-plugin/README.md`**](./ui-ux-mechanics-plugin/README.md)

Transforms Claude into a professional UI/UX designer — screens, wireframes, and full design systems for web, iOS, Android, or desktop. Integrates with Figma via MCP and adds safe Figma MCP write mechanics (write-access probing, metadata-lossiness handling, auto-layout/variant mechanics, prototype-link-safe edits). Enforces WCAG 2.1 AA accessibility.

**Key commands:** `/ui-ux-mechanics`, `/design`, `/design-review`, `/design-system`, `/figma-sync`, `/wireframe`. **Skills:** `design`, `figma-workflow`, `figma-mcp-mechanics`. **Agents:** `design-reviewer`, `wireframe-builder`.

---

### 5. Pandoc — Universal document converter

> 📖 [**Full documentation → `pandoc-plugin/README.md`**](./pandoc-plugin/README.md)

Document conversion powered by [Pandoc](https://pandoc.org/) — 50+ input and 60+ output formats with intelligent automation (PDF, Word, HTML, EPUB, presentations, citations, Arabic/RTL). Describe what you want in natural language; no flags to memorize.

**Commands:** `/pandoc setup`, `/pandoc status`, `/pandoc convert`, `/pandoc formats`, `/pandoc help`.

---

### 6. Remotion — Video creation with voice narration

> 📖 [**Full documentation → `remotion-plugin/README.md`**](./remotion-plugin/README.md)

Create professional videos with smooth voice narration using [Remotion](https://remotion.dev). Solves voice-cutting-between-slides with a Continuous Audio Pattern. Free edge-tts voices (200+), MP4/WebM/GIF output, video from text prompts.

**Commands:** `/remotion` (status / initialize project).

---

### 7. ntfy notifications — Mobile push notifications

> 📖 [**Full documentation → `ntfy-plugin/README.md`**](./ntfy-plugin/README.md)

Push notifications to your phone via [ntfy.sh](https://ntfy.sh) when Claude completes tasks, needs input, or errors. **Two-way Q&A**. 100% free, no account required.

**Commands:** `/ntfy <message>`, `/ntfy setup`, `/ntfy test`, `/ntfy status`, `/ntfy history`, `/ntfy config`.

---

### 8. react-kit — Reusable React / Next.js patterns *(v0.3.0)*

> 📖 [**Full documentation → `react-kit-plugin/README.md`**](./react-kit-plugin/README.md)

> *Renamed from `react-admin-kit`.* Admin-panel creation is now **one capability** inside a broader React/Next.js patterns kit, not the whole identity.

Reusable engineering patterns for React / Next.js apps — application & component architecture, admin panels, dashboards, CRUD list/detail/filter, role-aware UI, loading/error/empty/access states, import/export UI, RTL/LTR, accessibility, and **frontend quality discipline**. Complementary to the official `frontend-design` plugin (which owns net-new visual aesthetics); react-kit owns methodology, patterns, and triage.

**Skills (11):** the 8 admin-* skills (`admin-roles-and-permissions`, `admin-shell`, `admin-crud`, `admin-forms`, `admin-dangerous-actions`, `admin-import-export`, `admin-states`, `admin-rtl-ltr`) **plus** `react-lint-triage` (classify analyzer findings safe-mechanical / needs-judgment / false-positive / forbidden-zone; never chase the score), `data-fetching-states` (surface errors by status — 403→access-required, 404→not-found — never an empty shell), and `react19-migration` (forwardRef→ref-prop, useContext→use, server/client metadata split).

**Commands:** `/admin-scaffold`, `/admin-audit`, `/admin-role-matrix`. **Agent:** `admin-route-auditor`.

---

### 9. qa-browser — Role-based browser QA *(v0.3.0)*

> 📖 [**Full documentation → `qa-browser-plugin/README.md`**](./qa-browser-plugin/README.md)

Framework-agnostic browser QA and role-based smoke testing, **layered over** the official `playwright` / `chrome-devtools-mcp` engines (it does not reimplement browser automation). Logs in as each role, walks modals and table actions, verifies UI-vs-API permissions, captures console / network / screenshot evidence, and produces a PASS / BLOCKED / NOT-TESTABLE table for UAT signoff.

**Skills (11):** `browser-qa-discipline`, `runtime-reality-check`, `role-smoke-tests`, `route-access-matrix`, `modal-and-action-walkthroughs`, `import-export-ui-checks`, `console-and-network-capture`, `safe-destructive-testing`, `uat-readiness-report`, **plus** `verify-identity-and-rbac` (trust the auth endpoint over UI labels; prove RBAC via 401/403-vs-400/409; report UI-hides-but-API-allows) and `host-scoped-auth-headers` (inject bypass/auth headers host-scoped to avoid CORS-killing data calls).

**Commands:** `/qa-target`, `/qa-smoke <role>`, `/qa-roles`, `/qa-route <url>`, `/qa-report`. **Agents:** `qa-evidence-collector`, `qa-failure-classifier`.

**Safety:** production-URL gate (case-insensitive host match), disposable-data + external-side-effect scope-out, cancel-first destructive pattern, credential redaction.

---

### 10. docs-wiki — Project Wiki toolkit *(v0.3.0)*

> 📖 [**Full documentation → `docs-wiki-plugin/README.md`**](./docs-wiki-plugin/README.md)

Generic toolkit for creating, organising, editing, validating, and auditing a project Wiki. Owns flat-namespace + filename-uniqueness + internal-link conventions, Mermaid authoring, broken-link sweeps, code-vs-wiki drift, and a push-approval gate. Adapts to GitHub Wiki / GitLab / Azure DevOps / MkDocs.

**Skills (8):** `wiki-code-vs-docs-discrepancy`, `wiki-structure`, `wiki-mermaid`, `wiki-link-validation`, `wiki-safe-updates`, `wiki-authoring`, `wiki-vs-stray-docs`, **plus** `wiki-source-of-truth` (declare a knowledge-layer order; separate current-state vs target docs; distrust stale checkboxes; flag config-constant drift).

**Commands:** `/wiki-init`, `/wiki-audit`, `/wiki-update`, `/wiki-new`, `/wiki-drift`, `/wiki-sync-audit`. **Agents:** `wiki-link-auditor`, `wiki-cleanup-validator`, `wiki-drift-reporter`. **Templates:** SOP, runbook, role-guide, user-manual, workflow (Mermaid), release-handover, onboarding.

**Explicit boundary:** wiki-to-memory sync is **out of scope** — a separate future plugin.

---

### 11. claude-env-doctor — Local environment diagnosis *(v0.1.0)*

> 📖 [**Full documentation → `claude-env-doctor-plugin/README.md`**](./claude-env-doctor-plugin/README.md)

Generic doctor for the local **Claude Code / dev environment**. It **diagnoses, never blindly mutates** — routes a symptom to the right branch, runs read-only probes, classifies the failure, and proposes one safe next action. Branches: MCP not loading, Windows/WSL networking (DNS/VPN/HCS), login/401 loops, LSP / Node-CLI spawn, Python output encoding, and Playwright / browser-MCP setup. It is the canonical environment-troubleshooting home other plugins reference.

**Command:** `/env-doctor` (works with no arguments — bare invocation runs a general triage). **Skill:** `env-doctor` + 6 reference docs. **Agent:** `env-probe-reporter` (read-only). **Hook:** non-blocking SessionStart advisory.

**Scope / non-goals:** NOT server ops, deployment runbooks, or DevOps/GitHub workflow logic — local environment diagnosis only.

---

## Repository structure

```
taqat-techno-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata (13 plugins)
├── odoo-plugin/                  # Unified Odoo development toolkit (v14-19)
├── devops-plugin/                # Azure DevOps HYBRID integration (CLI + MCP)
├── rag-plugin/                   # Ragtools local RAG operations console
├── ui-ux-mechanics-plugin/       # UI/UX design + Figma-MCP execution mechanics
├── pandoc-plugin/                # Universal document conversion
├── remotion-plugin/              # Video creation with voice narration
├── ntfy-plugin/                  # Mobile push notifications (ntfy.sh)
├── react-kit-plugin/             # Reusable React / Next.js patterns (admin + quality + migration)
├── qa-browser-plugin/            # Browser QA + role-based smoke tests
├── docs-wiki-plugin/             # Project Wiki toolkit
├── claude-env-doctor-plugin/     # Local Claude Code / dev environment doctor
├── agent-safety-guards-plugin/   # Agent-session safety + multi-agent workflow reliability
├── release-safety-plugin/        # Provider-neutral release / deployment / migration safety
├── agent_skills_spec.md          # Claude Code skills specification
├── CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md  # Plugin development guide
├── CONTRIBUTING.md               # Contribution guidelines
├── validate_plugin.py            # Plugin structure validator
├── validate_plugin_simple.py     # Fast structural check (no pyyaml)
├── LICENSE                       # MIT License
└── README.md                     # This file
```

---

## Validation

Validate any plugin before committing (run from `plugins/`):

```bash
PYTHONIOENCODING=utf-8 python validate_plugin.py <plugin-dir>   # full check; require 0 errors
python validate_plugin_simple.py <plugin-dir>                  # fast structural check, no pyyaml
```

The two `hooks.json` "unknown top-level key" warnings (`description` / `hooks`) are a known validator quirk and are non-blocking. Also run a **genericness sweep** before shipping — grep all skill / command / agent / hook files for project-specific tokens (company/client names, business-domain terms, absolute user paths, private URLs, token shapes) and confirm 0 hits outside labeled illustrative examples.

---

## Auto-updates

Enable auto-updates in Claude Code settings → **Plugins** → **taqat-techno-plugins** → **Auto-Update**. Or update manually:
```bash
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

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
2. Check the plugin's `source` path in `.claude-plugin/marketplace.json`.
3. Look for manifest syntax errors: `python validate_plugin.py <plugin-dir>`.
4. Restart Claude Code.

### Environment / MCP problems
Use the **claude-env-doctor** plugin (`/env-doctor`) for MCP-not-loading, WSL/Windows networking, login/401, LSP spawn, encoding, and Playwright setup issues.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and [`CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`](./CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md) for the full authoring workflow. Every new plugin must be registered in `.claude-plugin/marketplace.json`, validate at 0 errors, pass the genericness sweep, and respect the official-plugin coverage boundary.

---

## About TAQAT Techno

TAQAT Techno is an Odoo development and consulting firm specializing in enterprise-grade ERP solutions.

**Contact:** GitHub [@taqat-techno](https://github.com/taqat-techno) · Website [taqatechno.com](https://www.taqatechno.com) · Email `info@taqatechno.com`

---

## License

MIT License — see [`LICENSE`](./LICENSE). Individual plugins may ship their own license (e.g., `odoo-plugin` uses LGPL-3.0-or-later). See each plugin's `plugin.json` or `LICENSE` / `LICENSES.md`.

---

**Plugins:** 11 &nbsp;·&nbsp; **Maintainer:** TAQAT Techno &nbsp;·&nbsp; **Marketplace:** `taqat-techno-plugins`
