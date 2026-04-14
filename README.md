# TAQAT Techno Plugins — Claude Code Marketplace

![Plugins](https://img.shields.io/badge/plugins-7-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Production-ready Claude Code plugins for professional development — Odoo ERP, Azure DevOps, UI/UX design, video creation, document conversion, local RAG knowledge bases, and mobile push notifications.

---

## Available plugins

| # | Plugin | Version | Category | Description | Documentation |
|---|--------|---------|----------|-------------|---------------|
| 1 | **odoo** | `1.0.0` | development | Unified Odoo development toolkit — upgrade, frontend themes, testing, security auditing, i18n, reports, Docker infrastructure, and server lifecycle across Odoo 14–19. | [README](./odoo-plugin/README.md) |
| 2 | **devops** | `6.3.0` | productivity | Azure DevOps HYBRID integration — work items, PRs, pipelines, repos, wiki via CLI + MCP with 100+ tools, persistent user profile, unified `/create` command, `/workday` dashboard, time logging, and role-based state machine. | [README](./devops-plugin/README.md) |
| 3 | **rag** | `0.4.0` | productivity | Operational console for the ragtools local RAG product — install, configure, diagnose, repair, upgrade, and run the local Markdown knowledge base. Knows the Qdrant single-process lock, dual-mode MCP, and known failure modes. Does NOT re-implement search. | [README](./rag-plugin/README.md) |
| 4 | **paper** | `3.0.0` | design | UI/UX design specialist — screen design, wireframing, design review, Figma MCP sync, design systems, WCAG 2.1 AA accessibility auditing for web, iOS, Android, and desktop. | [README](./paper-plugin/README.md) |
| 5 | **pandoc** | `2.1.0` | productivity | Universal document conversion powered by Pandoc — convert between 50+ input and 60+ output formats. PDF, Word, HTML, EPUB, presentations, citations, Arabic/RTL support. | [README](./pandoc-plugin/README.md) |
| 6 | **remotion** | `2.1.0` | development | Create professional videos with smooth voice narration using Remotion. Continuous audio pipeline that prevents voice cutting between slides, free edge-tts voice generation, full video creation from text prompts. | [README](./remotion-plugin/README.md) |
| 7 | **ntfy-notifications** | `3.0.0` | productivity | Push notifications to your phone via [ntfy.sh](https://ntfy.sh) when Claude completes tasks, needs input, or encounters errors. Two-way Q&A. 100% free, no account required. | [README](./ntfy-plugin/README.md) |

---

## Quick installation

### Method 1 — Claude Code UI (recommended)

1. Open Claude Code.
2. Run `/plugins`.
3. Click **Add Marketplace**.
4. Enter the repository URL: `https://github.com/taqat-techno/plugins.git`
5. Click **Install**.

All 7 plugins will become available automatically.

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

In Claude Code, run `/plugins` and confirm all 7 plugins appear under the **taqat-techno-plugins** marketplace.

---

## Plugin details

Each plugin ships its own complete README. Click through for commands, configuration, architecture, and usage examples.

### 1. Odoo — Unified development toolkit

> 📖 [**Full documentation → `odoo-plugin/README.md`**](./odoo-plugin/README.md)

The single consolidated Odoo plugin covering **eight previously separate capabilities**: upgrade (v14→19 migrations), frontend theme development, testing toolkit, security auditing, i18n/translation management, email templates and QWeb reports, Docker infrastructure, and server lifecycle management. Each capability lives as a sub-skill inside `odoo-plugin/skills/<area>/`.

**Key commands:** `/odoo-upgrade`, `/odoo-precheck`, `/odoo-quickfix`, `/odoo-frontend`, `/create-theme`, `/odoo-docker`, `/odoo-service`, `/odoo-start`, `/odoo-stop`, `/odoo-init`, `/odoo-db`, `/odoo-ide`, `/odoo-scaffold`, `/odoo-test`, `/odoo-security`, `/odoo-i18n`, `/odoo-report`.

**Typical usage:** `"Upgrade my_module from Odoo 16 to Odoo 19"` / `"Create a new Odoo 17 website theme"` / `"Audit my_module for access rule gaps"`.

---

### 2. DevOps — Azure DevOps integration (HYBRID CLI + MCP)

> 📖 [**Full documentation → `devops-plugin/README.md`**](./devops-plugin/README.md)

Comprehensive Azure DevOps integration via a **HYBRID** architecture: CLI for high-volume work and MCP server for natural-language queries. Enforces a role-based state machine (Developer, QA/QC, PM/Lead) with mandatory work-item hierarchy (Epic > Feature > User Story/PBI > Task | Bug | Enhancement), auto-sprint assignment, and state-transition permissions.

**Key commands:** `/init`, `/init profile`, `/create`, `/workday`, `/standup`, `/sprint`, `/log-time`, `/timesheet`, `/cli-run`, `/task-monitor`.

**Agents:** `work-item-ops`, `sprint-planner`, `pr-reviewer`.

**Business rules:** hierarchy enforcement, User Story format (How? > What? > Why?), task prefixes from project settings, state-permission matrix, PBI must pass through "Ready for QC" before "Done", bug creation restricted to QA/QC roles.

---

### 3. Rag — Ragtools operations console

> 📖 [**Full documentation → `rag-plugin/README.md`**](./rag-plugin/README.md)

Operations and support layer for the [ragtools](https://github.com/taqat-techno/rag) local-first Markdown knowledge base product. Installs, configures, diagnoses, repairs, upgrades, and runs ragtools; knows the Qdrant single-process lock, dual-mode MCP (proxy vs direct), and the F-001..F-012 failure catalog. **Does NOT re-implement search** — the ragtools MCP server handles that directly.

**Key commands (v0.4.0 smart surface):** `/rag-doctor` (diagnose + status + repair, absorbs former `/rag-status` and `/rag-repair`), `/rag-setup` (install + upgrade + verify, absorbs former `/rag-upgrade`), `/rag-projects` (HTTP API project CRUD), `/rag-reset` (three-level destructive reset), `/rag-config` (plugin-layer config: telemetry, CLAUDE.md rule, MCP dedupe, hook observability), `/rag-sync-docs` (maintainer-only).

**Components:** 6 user-facing commands + 1 maintainer-only, 1 skill (`ragtools-ops`), 1 Haiku agent (`rag-log-scanner`), PreToolUse + UserPromptSubmit hooks, plugin-level `.mcp.json` auto-wiring.

---

### 4. Paper — UI/UX design specialist

> 📖 [**Full documentation → `paper-plugin/README.md`**](./paper-plugin/README.md)

Transforms Claude into a professional UI/UX designer. Designs screens, wireframes, and full design systems for any platform — web, iOS, Android, or desktop. Integrates with Figma via MCP for design-to-code and code-to-design workflows. Enforces WCAG 2.1 AA accessibility compliance.

**Key commands:** `/paper` (status), `/design`, `/design-review`, `/design-system`, `/figma-sync`, `/wireframe`.

**Agents:** `design-reviewer` (systematic 6-dimension UI review), `wireframe-builder` (ASCII wireframes + HTML prototypes).

**Features:** multi-platform design (web / iOS / Android / desktop), Figma MCP integration (13 tools), design system generation, color theory, typography scales, spacing grids, responsive layouts, accessibility auditing.

---

### 5. Pandoc — Universal document converter

> 📖 [**Full documentation → `pandoc-plugin/README.md`**](./pandoc-plugin/README.md)

Document conversion powered by [Pandoc](https://pandoc.org/). Convert between 50+ input formats and 60+ output formats with intelligent automation — PDF, Word, HTML, EPUB, presentations (reveal.js / Beamer / PowerPoint), citations, academic papers, and Arabic/RTL support.

**Commands:** `/pandoc setup`, `/pandoc status`, `/pandoc convert`, `/pandoc formats`, `/pandoc help`.

**Natural language:** you do not need to memorize flags — describe what you want.
- `"Convert my thesis to PDF with table of contents and bibliography"`
- `"Turn these markdown files into a Word document"`
- `"Make a reveal.js presentation from slides.md with the moon theme"`
- `"Create an EPUB from ch1.md, ch2.md, ch3.md with a cover image"`

---

### 6. Remotion — Video creation with voice narration

> 📖 [**Full documentation → `remotion-plugin/README.md`**](./remotion-plugin/README.md)

Create professional videos with smooth voice narration using [Remotion](https://remotion.dev) and Claude Code. Solves the **voice-cutting-between-slides** problem with a Continuous Audio Pattern — a single audio track at the root level that plays through all visual transitions.

**Commands:** `/remotion` (status / initialize project).

**Features:** free edge-tts voices (200+ voices, 75+ languages), continuous audio pipeline (no voice cutting), TailwindCSS styling, MP4 / WebM / GIF output, full video creation from text prompts.

**Typical usage:** `"Create a 60-second product demo with voice narration about our new feature"` / `"Render my video as a high-quality MP4"`.

---

### 7. ntfy notifications — Mobile push notifications

> 📖 [**Full documentation → `ntfy-plugin/README.md`**](./ntfy-plugin/README.md)

Push notifications to your phone via [ntfy.sh](https://ntfy.sh) whenever Claude Code completes tasks, needs input, or encounters errors. **Two-way Q&A** lets Claude ask questions and wait for your phone response. 100% free, no account required, no credit card, no vendor lock-in.

**Commands:** `/ntfy <message>`, `/ntfy setup`, `/ntfy test`, `/ntfy status`, `/ntfy history`, `/ntfy config`.

**Setup in 5 minutes:**
1. Install the ntfy app on your phone (iOS App Store / Google Play).
2. Subscribe to a unique topic (e.g., `claude-yourname-abc123`).
3. Run `/ntfy setup` in Claude Code.
4. Run `/ntfy test` to verify delivery.
5. Done — Claude will notify you automatically.

---

## Repository structure

```
taqat-techno-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata (7 plugins)
├── odoo-plugin/                  # Unified Odoo development toolkit (v14-19)
├── devops-plugin/                # Azure DevOps HYBRID integration (CLI + MCP)
├── rag-plugin/                   # Ragtools local RAG operations console
├── paper-plugin/                 # UI/UX design specialist (Figma MCP)
├── pandoc-plugin/                # Universal document conversion
├── remotion-plugin/              # Video creation with voice narration
├── ntfy-plugin/                  # Mobile push notifications (ntfy.sh)
├── agent_skills_spec.md          # Claude Code skills specification
├── CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md  # Plugin development guide
├── CONTRIBUTING.md               # Contribution guidelines
├── validate_plugin.py            # Plugin structure validator
├── validate_plugin_simple.py     # Fast structural check (no pyyaml)
├── LICENSE                       # MIT License
└── README.md                     # This file
```

---

## Auto-updates

Enable auto-updates to receive new features automatically:

1. Open Claude Code settings.
2. Navigate to the **Plugins** section.
3. Find **taqat-techno-plugins**.
4. Toggle **Auto-Update** to ON.

Or update manually:
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
3. Look for manifest syntax errors: `python plugins/validate_plugin.py <plugin-dir>`.
4. Restart Claude Code.

### Still stuck?
Open an issue at [github.com/taqat-techno/plugins/issues](https://github.com/taqat-techno/plugins/issues) with Claude Code version, plugin name, error messages, and steps to reproduce.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the [`CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md`](./CLAUDE_CODE_PLUGIN_DEVELOPMENT_GUIDE.md) for the full authoring workflow.

**Quick flow for adding a new plugin:**
1. Fork this repository.
2. Create the plugin directory: `mkdir -p my-plugin/.claude-plugin && mkdir -p my-plugin/commands`.
3. Write `my-plugin/.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, `homepage`, `license`, `keywords`.
4. Add your commands, skills, agents, hooks, or MCP `.mcp.json` under the appropriate subdirectories.
5. Write `my-plugin/README.md` with: H1 title, description paragraph, Quick Start section, Commands section, license note.
6. Register the plugin in `plugins/.claude-plugin/marketplace.json` (set `source: "./my-plugin"`).
7. Validate: `python validate_plugin.py my-plugin`.
8. Update this marketplace README — add a row to the **Available plugins** table and a section under **Plugin details** linking to your new plugin's README.
9. Submit a pull request.

---

## About TAQAT Techno

TAQAT Techno is an Odoo development and consulting firm specializing in enterprise-grade ERP solutions.

**Services:**
- Custom Odoo module development
- Multi-version upgrade and migration (Odoo 10–19)
- Performance optimization
- DevOps automation
- Technical consulting

**Contact:**
- GitHub: [@taqat-techno](https://github.com/taqat-techno)
- Website: [taqatechno.com](https://www.taqatechno.com)
- Email: `info@taqatechno.com`

---

## License

MIT License — free to use, modify, and distribute. See [`LICENSE`](./LICENSE) for the full text.

Individual plugins may ship their own license (e.g., `odoo-plugin` uses LGPL-3.0-or-later). See each plugin's `plugin.json` or `LICENSE` / `LICENSES.md` for details.

---

**Plugins:** 7 &nbsp;·&nbsp; **Maintainer:** TAQAT Techno &nbsp;·&nbsp; **Marketplace:** `taqat-techno-plugins`
