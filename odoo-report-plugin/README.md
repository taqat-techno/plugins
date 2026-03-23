# Odoo Report Plugin v2.1.0

Odoo Email Templates & QWeb Reports toolkit for Claude Code.

## Overview

A skill for creating, managing, debugging, and migrating email templates and PDF reports across **Odoo 14-19** with version-aware syntax and intelligent pattern selection.

## Features

- **Version-Aware**: Automatic syntax selection based on detected Odoo version (14-19)
- **Smart Validation**: Pre-flight checks for XML syntax, field references, and security
- **Migration Tools**: Template migration between Odoo versions with automatic transformations
- **Arabic/RTL Support**: UTF-8 encoding guidance, bilingual label patterns
- **wkhtmltopdf Setup**: Installation, configuration, and troubleshooting
- **Natural Language**: All workflows triggered by describing what you need

## Installation

1. Place this directory in your Claude Code plugins location:
   - Per-project: `.claude/plugins/odoo-report-plugin/`
   - Global: `~/.claude/plugins/odoo-report-plugin/`
2. Claude Code automatically detects the plugin on next session start
3. Optionally copy `odoo-report.local.example.md` to your project's `.claude/odoo-report.local.md` and customize defaults

## Usage

All workflows are skill-driven via natural language. No slash commands needed.

### Creating Templates

```
"Create an email template for sale.order quotation"
"Create a QWeb PDF report for purchase.order"
"Create a bilingual invoice report with Arabic headers"
```

### Managing Templates

```
"Analyze this email template for issues and improvements"
"Debug why my email template shows plain text instead of HTML"
"Fix common issues in my email template"
"Validate my QWeb report template before deployment"
"List all email templates for sale.order in my module"
"Preview this email template with sample data"
```

### Migrating Templates

```
"Migrate my templates from Odoo 14 to 17"
"Upgrade this template to Odoo 19 with company branding"
```

## Supported Versions

| Version | Key Differences |
|---------|----------------|
| Odoo 14 | `t-esc` syntax, `report_template` (singular) |
| Odoo 15 | `t-out` replaces `t-esc`/`t-raw` |
| Odoo 16 | `template_category` field added |
| Odoo 17 | `report_template_ids` M2M replaces singular |
| Odoo 18 | Layout variants |
| Odoo 19 | Company branding colors (`email_primary_color`, `email_secondary_color`) |

## Plugin Structure

```
odoo-report-plugin/
├── .claude-plugin/
│   └── plugin.json               # Plugin manifest
├── odoo-report/
│   └── SKILL.md                  # Main skill definition
├── hooks/
│   └── hooks.json                # 3 PostToolUse hooks (email, report, manifest)
├── memories/                     # Decision-making knowledge
│   ├── version_routing.md        # Version-specific rules and migration paths
│   ├── template_patterns.md      # Pattern selection by purpose/model
│   └── qweb_best_practices.md    # Safety, performance, email/report guidelines
├── data/                         # Reference data
│   ├── template_fields.json      # mail.template and ir.actions.report field definitions
│   ├── context_variables.json    # Rendering context variables by version
│   ├── layouts.json              # Email layout template definitions
│   └── module_templates.md       # Known Odoo template IDs by module
├── validators/
│   └── template_validator.md     # Pre-flight validation checklist
├── helpers/
│   └── version_helper.md         # Version detection logic and feature map
├── templates/                    # Starter XML templates
│   ├── email/
│   │   ├── basic_notification.xml
│   │   └── document_email.xml
│   └── qweb/
│       ├── basic_report.xml
│       └── table_report.xml
├── odoo-report.local.example.md  # User configuration example
└── README.md
```

## Customization

### User Configuration

Copy `odoo-report.local.example.md` to `.claude/odoo-report.local.md` in your project:

```yaml
---
default_version: 19
author: "Your Company"
website: "https://yourcompany.com/"
default_layout: "mail.mail_notification_layout"
auto_delete: true
---
```

### Adding Custom Templates

Add your own starter XML files to `templates/email/` or `templates/qweb/`. The skill references these directories when creating new templates.

### Extending Patterns

Add custom pattern files to `memories/` following the same markdown format as `template_patterns.md`. Reference them from the skill by updating the Reference Files section.

## Hooks

The plugin includes 3 scoped PostToolUse hooks that provide reminders when editing relevant files:

| Hook | Triggers On | What It Checks |
|------|-------------|----------------|
| `email-template-check` | `**/data/mail_template*.xml` | body_html, syntax, version fields |
| `qweb-report-check` | `**/report*/**/*.xml` | Template structure, UTF-8, layout |
| `manifest-report-data` | `**/__manifest__.py` | Data list entries, asset bundles |

Hooks only fire on matching file patterns — they will not trigger on unrelated files.

## Author

**TaqaTechno** — https://www.taqatechno.com/

## License

LGPL-3.0
