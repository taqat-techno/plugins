# TAQAT Techno Plugins - Claude Code Skills Marketplace

![Plugins](https://img.shields.io/badge/plugins-13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)
![Azure DevOps](https://img.shields.io/badge/Azure_DevOps-Integrated-0078D7.svg)

Production-ready Claude Code plugins for professional development - Odoo ERP, Azure DevOps, UI/UX Design, Video Creation, Document Conversion, and more.

---

## Available Plugins

| # | Plugin | Description | Version |
|---|--------|-------------|---------|
| 1 | [**odoo-upgrade**](./odoo-upgrade-plugin/README.md) | Odoo module upgrade assistant (v14-19) | 1.0.0 |
| 2 | [**odoo-frontend**](./odoo-frontend-plugin/README.md) | Website theme development with Bootstrap | 1.0.0 |
| 3 | [**codex**](./codex-plugin/README.md) | Universal code analysis & generation | 1.0.0 |
| 4 | [**devops**](./devops-plugin/README.md) | Azure DevOps integration via MCP | 1.0.0 |
| 5 | [**ntfy-notifications**](./ntfy-plugin/README.md) | Push notifications to your phone | 2.0.0 |
| 6 | [**odoo-report**](./odoo-report-plugin/README.md) | Email templates & QWeb reports (v14-19) | 1.0.0 |
| 7 | [**pandoc**](./pandoc-plugin/README.md) | Universal document conversion (50+ formats) | 1.0.0 |
| 8 | [**remotion**](./remotion-plugin/README.md) | Video creation with voice narration | 1.0.0 |
| 9 | [**odoo-test**](./odoo-test-plugin/README.md) | Odoo testing toolkit & coverage analysis | 1.0.0 |
| 10 | [**odoo-security**](./odoo-security-plugin/README.md) | Security audit & risk scoring | 1.0.0 |
| 11 | [**odoo-i18n**](./odoo-i18n-plugin/README.md) | Internationalization & translation management | 1.0.0 |
| 12 | [**odoo-service**](./odoo-service-plugin/README.md) | Server lifecycle manager (venv, Docker, IDE) | 1.0.0 |
| 13 | [**paper**](./paper-plugin/README.md) | UI/UX design specialist with Figma MCP | 1.0.0 |

---

## Quick Installation

### Method 1: Claude Code UI (Recommended)

1. Open Claude Code
2. Type `/plugins` command
3. Click **"Add Marketplace"**
4. Enter repository URL:
   ```
   https://github.com/taqat-techno/plugins.git
   ```
5. Click **"Install"**

All plugins will be automatically available!

### Method 2: Manual Installation

**Linux/macOS:**
```bash
cd ~/.claude/plugins/marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

**Windows:**
```cmd
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno/plugins.git taqat-techno-plugins
```

### Verify Installation

Ask Claude:
```
"Show me available skills"
```

You should see all 13 plugins listed.

---

## Plugin Details

### Odoo Module Upgrade

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-upgrade-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()

Automatically upgrade custom Odoo modules across major versions with intelligent code transformations.

**Features:**
- Multi-version jumps (14 -> 19)
- Python, XML, JavaScript, SCSS transformations
- 100+ upgrade patterns
- Safe migration with backups

**Usage:**
```
"Upgrade my_module from odoo16 to odoo19"
```

[**Read Full Documentation**](./odoo-upgrade-plugin/README.md)

---

### Odoo Frontend Development

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-frontend-plugin/README.md)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.1.3-7952B3.svg)]()

Comprehensive website theme development with auto-detection, MCP integration, and Bootstrap version management.

**Features:**
- Theme scaffold generation
- Bootstrap 5.1.3 integration
- SCSS variable system
- publicWidget patterns
- Multi-website support

**Usage:**
```
"Create a new Odoo 17 website theme"
```

[**Read Full Documentation**](./odoo-frontend-plugin/README.md)

---

### Codex - Universal Code Assistant

[![Docs](https://img.shields.io/badge/docs-README-blue)](./codex-plugin/README.md)
[![Languages](https://img.shields.io/badge/languages-All-green.svg)]()

Universal development assistant with comprehensive code analysis, generation, refactoring, and optimization.

**Features:**
- Multi-language support
- Code analysis & refactoring
- Pattern detection
- Best practices enforcement
- Documentation generation

**Usage:**
```
"Analyze this Python file for improvements"
"Refactor this function to be more efficient"
```

[**Read Full Documentation**](./codex-plugin/README.md)

---

### Azure DevOps Integration

[![Docs](https://img.shields.io/badge/docs-README-blue)](./devops-plugin/README.md)
[![Azure](https://img.shields.io/badge/Azure_DevOps-MCP-0078D7.svg)]()

Complete Azure DevOps integration for TaqaTechno organization via MCP server.

**Features:**
- Work items: create, update, query, link
- Pull requests: create, review, approve
- Pipelines: run, monitor, view logs
- Wiki & code search
- Sprint reports & standups

**Commands:**
| Command | Description |
|---------|-------------|
| `/devops` | Setup & status |
| `/devops:my-tasks` | Your assigned work items |
| `/devops:sprint` | Sprint progress |
| `/devops:standup` | Daily standup notes |
| `/devops:create-pr` | Create pull request |

[**Read Full Documentation**](./devops-plugin/README.md)

---

### ntfy Push Notifications

[![Docs](https://img.shields.io/badge/docs-README-blue)](./ntfy-plugin/README.md)
[![Free](https://img.shields.io/badge/cost-FREE-brightgreen.svg)]()
[![ntfy](https://img.shields.io/badge/ntfy.sh-v2.0-orange.svg)]()

Push notifications to your phone when Claude completes tasks, needs input, or encounters errors.

**Features:**
- Instant push notifications (iOS/Android/Desktop)
- No account required (uses ntfy.sh)
- Auto-retry with exponential backoff
- Deduplication & rate limiting
- Local notification history
- Self-hosted server support

**Commands:**
| Command | Description |
|---------|-------------|
| `/ntfy <message>` | Quick send notification |
| `/ntfy-setup` | Interactive setup wizard |
| `/ntfy-test` | Test notification delivery |
| `/ntfy-status` | Check configuration |
| `/ntfy-history` | View notification history |
| `/ntfy-config` | Update settings |

[**Read Full Documentation**](./ntfy-plugin/README.md)

---

### Odoo Email Templates & QWeb Reports

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-report-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()

Complete toolkit for creating, managing, and debugging email templates and PDF reports across Odoo versions.

**Features:**
- Email template generation with version-aware syntax
- QWeb PDF report creation with action binding
- Template validation and debugging
- Migration between Odoo versions
- Preview with sample data

**Commands:**
| Command | Description |
|---------|-------------|
| `/odoo-report` | Main entry point |
| `/odoo-report:create-email-template` | Create email template |
| `/odoo-report:create-qweb-report` | Create PDF report |
| `/odoo-report:validate-template` | Validate syntax |
| `/odoo-report:migrate-template` | Migrate between versions |

[**Read Full Documentation**](./odoo-report-plugin/README.md)

---

### Pandoc - Universal Document Converter

[![Docs](https://img.shields.io/badge/docs-README-blue)](./pandoc-plugin/README.md)
[![Formats](https://img.shields.io/badge/formats-50%2B-green.svg)]()
[![Pandoc](https://img.shields.io/badge/Pandoc-3.0%2B-blue.svg)]()

Universal document conversion powered by Pandoc. Transform documents between 50+ input and 60+ output formats.

**Features:**
- PDF generation with LaTeX (academic, report, book presets)
- Word document conversion with templates
- HTML generation with CSS and syntax highlighting
- EPUB eBook creation with covers and metadata
- Presentations (reveal.js, Beamer, PowerPoint)
- Batch conversion support

**Commands:**
| Command | Description |
|---------|-------------|
| `/pandoc` | Main help and status |
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-html` | Convert to HTML |
| `/pandoc-epub` | Create eBooks |
| `/pandoc-slides` | Create presentations |
| `/pandoc-convert` | General conversion |

[**Read Full Documentation**](./pandoc-plugin/README.md)

---

### Remotion - Video Creation

[![Docs](https://img.shields.io/badge/docs-README-blue)](./remotion-plugin/README.md)
[![Remotion](https://img.shields.io/badge/Remotion-4.0-blue.svg)]()
[![TTS](https://img.shields.io/badge/TTS-edge--tts-green.svg)]()

Create professional videos with smooth voice narration using Remotion and Claude Code.

**Features:**
- Full video creation from text prompts
- Free edge-tts voices (200+ voices, 75+ languages)
- Continuous audio pipeline (no voice cutting)
- TailwindCSS for visual styling
- MP4, WebM, and GIF output

**Commands:**
| Command | Description |
|---------|-------------|
| `/remotion` | Status & quick start |
| `/remotion:create-video` | Full video pipeline |
| `/remotion:add-voice` | Add narration to existing composition |
| `/remotion:render-video` | Render to MP4/WebM/GIF |
| `/remotion:remotion-setup` | Set up new project |

[**Read Full Documentation**](./remotion-plugin/README.md)

---

### Odoo Testing Toolkit

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-test-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()

Comprehensive testing toolkit for Odoo modules - generate, run, and analyze tests.

**Features:**
- Generate test skeletons from model definitions
- Run tests with formatted, colored output
- Create realistic mock data for any model
- Analyze test coverage gaps
- Tag filtering and JUnit XML reports

**Commands:**
| Command | Description |
|---------|-------------|
| `/odoo-test` | Full testing workflow |
| `/odoo-test:test-generate` | Generate test skeleton |
| `/odoo-test:test-run` | Run test suite |
| `/odoo-test:test-data` | Generate mock data |
| `/odoo-test:test-coverage` | Analyze coverage |
| `/odoo-test:e2e-test` | Playwright E2E tests |

[**Read Full Documentation**](./odoo-test-plugin/README.md)

---

### Odoo Security Audit

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-security-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()
[![Security](https://img.shields.io/badge/audit-security-red.svg)]()

Security audit toolkit for Odoo modules with risk scoring and actionable recommendations.

**Features:**
- Model access rule completeness checks
- HTTP route authentication audit
- sudo() usage analysis with context classification
- Detailed security reports with severity ratings
- Actionable fix suggestions

**Commands:**
| Command | Description |
|---------|-------------|
| `/odoo-security` | Full security audit |
| `/odoo-security:check-access` | Check model access rules |
| `/odoo-security:check-routes` | Audit HTTP routes |
| `/odoo-security:find-sudo` | Analyze sudo() calls |
| `/odoo-security:security-audit` | Targeted audit with filtering |

[**Read Full Documentation**](./odoo-security-plugin/README.md)

---

### Odoo Internationalization (i18n)

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-i18n-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()
[![i18n](https://img.shields.io/badge/i18n-RTL%20support-orange.svg)]()

Internationalization toolkit for Odoo modules - extract, validate, and manage translations.

**Features:**
- Extract translatable strings to .pot/.po files
- Validate translation completeness by language
- Find missing translations
- Arabic/RTL localization support
- Full Odoo 14-19 version support

**Commands:**
| Command | Description |
|---------|-------------|
| `/odoo-i18n` | Main i18n workflow |

[**Read Full Documentation**](./odoo-i18n-plugin/README.md)

---

### Odoo Server Manager

[![Docs](https://img.shields.io/badge/docs-README-blue)](./odoo-service-plugin/README.md)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)]()
[![Docker](https://img.shields.io/badge/Docker-supported-2496ED.svg)]()

Complete Odoo server lifecycle manager - start, stop, deploy, initialize across local venv, Docker, and IDEs.

**Features:**
- Server startup/shutdown management
- Environment initialization (venv, PostgreSQL, configs)
- Database operations (backup, restore, create, drop)
- Docker orchestration (build, run, logs)
- IDE config generation (PyCharm, VSCode)

**Commands:**
| Command | Description |
|---------|-------------|
| `/odoo-service` | Main entry point |
| `/odoo-start` | Start Odoo server |
| `/odoo-stop` | Stop Odoo server |
| `/odoo-init` | Initialize environment |
| `/odoo-db` | Database operations |
| `/odoo-docker` | Docker management |
| `/odoo-ide` | Generate IDE configs |

[**Read Full Documentation**](./odoo-service-plugin/README.md)

---

### Paper - UI/UX Design Specialist

[![Docs](https://img.shields.io/badge/docs-README-blue)](./paper-plugin/README.md)
[![Figma](https://img.shields.io/badge/Figma-MCP%20integrated-F24E1E.svg)]()
[![WCAG](https://img.shields.io/badge/WCAG-2.1%20AA-green.svg)]()

UI/UX design specialist that transforms Claude into a professional designer. Works with Figma MCP for design-to-code and code-to-design workflows.

**Features:**
- Multi-platform design (web, iOS, Android, desktop)
- Figma MCP integration (13 tools)
- Design system generation & analysis
- Color theory, typography scales, spacing grids
- WCAG 2.1 AA accessibility compliance
- Odoo/Bootstrap theme support
- ASCII wireframes + HTML/CSS prototypes

**Commands:**
| Command | Description |
|---------|-------------|
| `/design` | Design a screen or component |
| `/design-review` | Review UI for quality |
| `/design-system` | Generate or analyze design system |
| `/figma-sync` | Sync Figma designs with code |
| `/wireframe` | Quick wireframe generation |

**Agents:**
| Agent | Description |
|-------|-------------|
| `design-reviewer` | Systematic 6-dimension UI review |
| `wireframe-builder` | ASCII wireframes + HTML prototypes |

[**Read Full Documentation**](./paper-plugin/README.md)

---

## Auto-Updates

Enable auto-updates to receive new features automatically:

1. Open Claude Code settings
2. Navigate to **Plugins** section
3. Find **taqat-techno-plugins**
4. Toggle **Auto-Update** to ON

Or manually update:
```bash
cd ~/.claude/plugins/marketplaces/taqat-techno-plugins
git pull
```

---

## Repository Structure

```
taqat-techno-plugins/
├── .claude-plugin/
│   └── marketplace.json           # Marketplace metadata (13 plugins)
├── odoo-upgrade-plugin/           # Odoo version migration
├── odoo-frontend-plugin/          # Website theme development
├── codex-plugin/                  # Universal code assistant
├── devops-plugin/                 # Azure DevOps integration
├── ntfy-plugin/                   # Push notifications
├── odoo-report-plugin/            # Email templates & QWeb reports
├── pandoc-plugin/                 # Universal document conversion
├── remotion-plugin/               # Video creation with narration
├── odoo-test-plugin/              # Odoo testing toolkit
├── odoo-security-plugin/          # Security audit toolkit
├── odoo-i18n-plugin/              # Internationalization & i18n
├── odoo-service-plugin/           # Server lifecycle manager
├── paper-plugin/                  # UI/UX design specialist
├── agent_skills_spec.md           # Skills specification
├── CONTRIBUTING.md                # Contribution guidelines
├── LICENSE                        # MIT License
└── README.md                      # This file
```

---

## Troubleshooting

### Plugins Not Appearing

```bash
# Check installation
ls ~/.claude/plugins/marketplaces/taqat-techno-plugins

# Verify marketplace.json
cat ~/.claude/plugins/marketplaces/taqat-techno-plugins/.claude-plugin/marketplace.json

# Restart Claude Code
```

### Plugin Not Loading

1. Verify YAML frontmatter in SKILL.md
2. Check skill path in marketplace.json
3. Look for syntax errors
4. Restart Claude Code

### Still Having Issues?

[Open an issue](https://github.com/taqat-techno/plugins/issues) with:
- Claude Code version
- Plugin name
- Error messages
- Steps to reproduce

---

## Contributing

See [agent_skills_spec.md](./agent_skills_spec.md) for skill creation guidelines.

**Quick Start:**
1. Fork this repository
2. Create plugin directory: `mkdir -p my-plugin/skill-name`
3. Create `SKILL.md` with YAML frontmatter
4. Update `.claude-plugin/marketplace.json`
5. Add `README.md` documentation
6. Test locally
7. Submit pull request

---

## About TAQAT Techno

TAQAT Techno is an Odoo development and consulting firm specializing in enterprise-grade ERP solutions.

**Services:**
- Custom Odoo module development
- Multi-version upgrade and migration (Odoo 10-19)
- Performance optimization
- DevOps automation
- Technical consulting

**Contact:**
- GitHub: [@taqat-techno](https://github.com/taqat-techno)
- Email: support@example.com
- Website: [taqatechno.com](https://www.taqatechno.com)

---

## License

MIT License - Free to use, modify, and distribute.

---

**Plugins**: 13 | **Version**: 1.6.0 | **Maintainer**: TAQAT Techno
