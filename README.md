# TAQAT Techno Plugins - Claude Code Skills Marketplace

![Skills](https://img.shields.io/badge/skills-1-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)

Production-ready Claude Code skills for professional Odoo ERP development, specializing in multi-version upgrades, code migrations, and automated transformations.

## Overview

This marketplace provides **agent skills** for Claude Code - structured instruction sets that enable autonomous execution of complex Odoo development tasks. Each skill contains:

- **Domain expertise**: Odoo-specific patterns and best practices
- **Automated transformations**: Python, XML, JavaScript, SCSS code migrations
- **Safety mechanisms**: Validation, backups, and rollback procedures
- **Testing integration**: Module installation and sanity checks

## 📦 Available Skills

### 🔄 Odoo Module Upgrade

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](./odoo-development/odoo-upgrade/)
[![Odoo](https://img.shields.io/badge/Odoo-14--19-purple.svg)](./odoo-development/odoo-upgrade/)

Automatically upgrade custom Odoo modules and themes across major versions (14→19) with intelligent code transformations, testing, and comprehensive reporting.

**Features**:
- Multi-version jumps with cumulative changes
- Automatic Python, XML, JavaScript, SCSS transformations
- Safe migration with backups and testing
- Detailed upgrade reports with manual steps

[**📚 Read More**](./odoo-development/odoo-upgrade/) | [**⚡ Quick Install**](#-quick-install)

---

## 🚀 Quick Install

### Install via Claude Code UI (Recommended)

1. Open Claude Code
2. Type `/plugins` command
3. Click "Add Marketplace"
4. Enter repository URL: `https://github.com/taqat-techno-eg/plugins.git`
5. Click "Install"

All skills will be automatically available!

**Verify Installation:**
```
Ask Claude: "Show me available skills"
```

You should see `odoo-upgrade` listed.

### Manual Installation (Alternative)

If you prefer manual installation:

```bash
# Navigate to marketplaces directory
cd ~/.claude/plugins/marketplaces

# Clone the marketplace
git clone https://github.com/taqat-techno-eg/plugins.git taqat-techno-plugins

# Restart Claude Code
```

**Windows:**
```cmd
cd %USERPROFILE%\.claude\plugins\marketplaces
git clone https://github.com/taqat-techno-eg/plugins.git taqat-techno-plugins
```

## Usage

Skills are invoked automatically when Claude Code detects relevant tasks. Use natural language to describe your objective:

### Practical Examples

**Single module upgrade:**
```
"Upgrade custom_inventory in projects/TAQAT/ from odoo16 to odoo19"
```

**Theme migration with Bootstrap:**
```
"Migrate theme_construction from v14 to v17, update Bootstrap classes"
```

**Multi-version jump with testing:**
```
"Upgrade custom_pos module from odoo15 to odoo18, run tests in test database"
```

**Batch project upgrade:**
```
"Upgrade all modules in projects/client_xyz/ from version 16 to 18"
```

### How It Works

1. **Detection**: Claude Code identifies the task matches `odoo-upgrade` skill trigger
2. **Loading**: Skill instructions (SKILL.md) are loaded into context
3. **Execution**: Claude follows step-by-step procedures autonomously
4. **Validation**: Changes are tested against target Odoo version
5. **Reporting**: Detailed report generated with manual review items

## Technical Architecture

### Repository Structure

```
taqat-techno-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata (JSON)
├── odoo-development/             # Plugin group
│   └── odoo-upgrade/             # Individual skill
│       ├── SKILL.md              # Skill instructions with YAML frontmatter
│       └── README.md             # User documentation
├── agent_skills_spec.md          # Skills specification reference
├── README.md                     # This file
└── LICENSE                       # MIT License
```

### Skill Format

Each `SKILL.md` contains:

1. **YAML Frontmatter**: Metadata including name, description, allowed-tools, version
2. **Markdown Body**: Step-by-step instructions, transformation patterns, error handling
3. **Tool Declarations**: Pre-approved tools (Read, Write, Edit, Bash, Grep, Glob)

Example structure:
```markdown
---
name: odoo-upgrade
description: "Upgrade Odoo modules across versions..."
allowed-tools: [Read, Write, Edit, Bash, Grep]
metadata:
  version: "1.0.0"
  odoo-versions: "14,15,16,17,18,19"
---
# Skill instructions...
```

### Transformation Engine

The `odoo-upgrade` skill includes 100+ transformation patterns:

- **Python**: ORM changes, hook signatures, context keys, deprecated methods
- **XML**: `attrs={}` to expressions, `<tree>` → `<list>`, settings restructure
- **JavaScript**: OWL v1/v2 migration, ES6 modules, widget → component
- **SCSS**: Bootstrap 5 migration, `.less` → `.scss`, modern grid classes

## Skills Roadmap

**Production Ready:**
- [x] `odoo-upgrade` - Multi-version module upgrade (v1.0.0)

**In Development:**
- [ ] `odoo-testing` - Automated unit/integration test generation
- [ ] `odoo-performance` - Performance profiling and optimization
- [ ] `odoo-docker` - Docker/docker-compose setup automation

**Planned:**
- [ ] `odoo-migration` - Database migration with OpenUpgrade integration
- [ ] `odoo-security` - Security audit and vulnerability scanning
- [ ] `odoo-ci-cd` - GitHub Actions / GitLab CI pipeline generator

## Contributing

See [agent_skills_spec.md](./agent_skills_spec.md) for skill creation guidelines.

**Quick Start:**
1. Fork this repository
2. Create skill: `mkdir -p plugin-name/skill-name && cd $_`
3. Create `SKILL.md` with YAML frontmatter
4. Update `.claude-plugin/marketplace.json`
5. Test locally in `~/.claude/plugins/marketplaces/`
6. Submit pull request

## 🔧 Troubleshooting

### Skills Not Appearing

```bash
# Check installation location
ls ~/.claude/plugins/marketplaces/taqat-techno-plugins

# Verify marketplace.json
cat ~/.claude/plugins/marketplaces/taqat-techno-plugins/.claude-plugin/marketplace.json

# Restart Claude Code
```

### Skill Not Loading

1. Verify YAML frontmatter in `SKILL.md`
2. Check skill path in `marketplace.json`
3. Ensure directory name matches skill `name` field
4. Look for syntax errors in SKILL.md

### Still Having Issues?

[Open an issue](https://github.com/taqat-techno-eg/plugins/issues) with:
- Claude Code version
- Installation method used
- Error messages (if any)
- Steps to reproduce

## About TAQAT Techno

TAQAT Techno is an Odoo development and consulting firm specializing in enterprise-grade ERP solutions for the Egyptian and Middle Eastern markets. Our expertise includes:

**Core Services:**
- Custom Odoo module development and localization
- Multi-version upgrade and migration services (Odoo 10-19)
- Performance optimization and scaling for high-volume deployments
- DevOps automation: Docker, CI/CD, monitoring, backups
- Technical consulting and architecture design

**Technical Focus:**
- Complex business logic implementation (manufacturing, logistics, finance)
- Third-party system integrations (APIs, EDI, legacy systems)
- Custom report engines and BI dashboards
- Mobile application development (Odoo native + custom)
- Security hardening and compliance (GDPR, SOC2)

**Open Source Contributions:**
- Claude Code skills marketplace for Odoo development
- Odoo module upgrades automation tooling
- Custom addons published on [GitHub](https://github.com/taqat-techno-eg)

**Contact:**
- GitHub: [@taqat-techno-eg](https://github.com/taqat-techno-eg)
- Email: contact@taqat-techno.com

## Support & Contributions

**Found a bug?** [Open an issue](https://github.com/taqat-techno-eg/plugins/issues) with error details and steps to reproduce.

**Need a feature?** Submit a feature request with your use case and expected behavior.

**Want to contribute?** See [agent_skills_spec.md](./agent_skills_spec.md) for skill creation guidelines.

---

**License**: MIT | **Version**: 1.0.0 | **Maintainer**: TAQAT Techno