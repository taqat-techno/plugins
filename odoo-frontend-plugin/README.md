# Odoo Frontend Plugin for Claude Code v8.4

Odoo website theme development plugin for Claude Code. Provides theme scaffolding, SCSS variable management, Figma integration, snippet creation, and JavaScript patterns for Odoo 14-19.

## Installation

### Via Claude Code CLI
```bash
claude plugin install /path/to/odoo-frontend-plugin
```

### Manual
Clone this repository into your Claude Code plugins directory.

## Commands

| Command | Description |
|---------|-------------|
| `/create-theme` | Generate a complete Odoo theme module from Figma or manual specs |
| `/odoo-frontend` | Show environment status and available capabilities |

### Quick Start

```bash
# Create theme from Figma design
/create-theme --figma https://www.figma.com/file/abc123/MyDesign

# Create theme with manual colors
/create-theme my_theme projects/client --colors="#207AB7,#FB9F54,#F6F4F0,#FFFFFF,#191A19"
```

## Skills

| Skill | Triggers On | Coverage |
|-------|------------|----------|
| **theme-create** | "create theme", "scaffold theme", "generate theme" | Module structure, manifest, SCSS template, pages, mirror models, theme.utils, install/test |
| **theme-scss** | "SCSS variables", "color palette", "o-website-values-palettes" | 115+ configuration keys, font configs, color system, load order rules |
| **theme-design** | "Figma to Odoo", "header template", "footer template" | Figma extraction, 11 headers, 9 footers, shop/blog/cart templates |
| **theme-snippets** | "create snippet", "snippet options", "dynamic snippet" | 81+ snippet inventory, options system, version-aware creation |
| **frontend-js** | "publicWidget", "Owl component", "Bootstrap migration" | publicWidget patterns, Owl v1/v2, _t() translation, BS4-to-BS5 |

## Hooks

| Event | Action |
|-------|--------|
| **SessionStart** | Auto-detects Odoo version, Bootstrap version, existing themes |
| **PreToolUse** (Write/Edit) | Blocks inline `<script>` in XML templates |
| **PostToolUse** (Write/Edit) | Advises on SCSS regeneration, JS annotation, Bootstrap 4 classes, publicWidget editableMode |

## Agent

| Agent | Model | Purpose |
|-------|-------|---------|
| **theme-generator** | Sonnet | Executes `/create-theme` pipeline: Figma extraction, color mapping, SCSS generation, scaffolding, installation + auto-fix |

## Rules

| Rule | Purpose |
|------|---------|
| `rules/core-odoo-guard.md` | Never modify core Odoo directories |
| `rules/scss-load-order.md` | SCSS prepend requirement, map-merge prohibition, H6 baseline |

## Version Compatibility

| Odoo | Bootstrap | Owl | JavaScript |
|------|-----------|-----|------------|
| 14 | 4.x | — | ES6+ |
| 15 | 4.x | v1 | ES6+ |
| 16 | 5.1.3 | v1 | ES2020+ |
| 17 | 5.1.3 | v2 | ES2020+ |
| 18-19 | 5.1.3 | v2 | ES2020+ |

## Key Rules

- **NEVER** use `map-merge()` with core Odoo variables in theme SCSS (load order issue)
- **NEVER** use `ir.asset` records for Google Fonts — use `$o-theme-font-configs`
- **ALWAYS** use `('prepend', ...)` for `primary_variables.scss` in asset bundles
- **ALWAYS** use `publicWidget` for website themes (not Owl or vanilla JS)
- **H6 is ALWAYS 16px** (1rem) — the fixed base reference

## Project Structure

```
odoo-frontend-plugin/
├── .claude-plugin/plugin.json      # Plugin manifest (5 skills, 2 commands)
├── skills/                         # 5 focused skills (~300-450 lines each)
│   ├── theme-create/SKILL.md
│   ├── theme-scss/SKILL.md
│   ├── theme-design/SKILL.md
│   ├── theme-snippets/SKILL.md
│   └── frontend-js/SKILL.md
├── commands/                       # Slash commands
│   ├── create-theme.md
│   └── odoo-frontend.md
├── hooks/                          # Pre/Post tool use hooks
│   ├── hooks.json
│   ├── pre_write_check.py
│   └── post_write_check.py
├── scripts/                        # Python utilities
├── data/                           # JSON configuration data
└── templates/                      # Module templates
```

## License

MIT License — See LICENSE file for details.

Developed by [TaqaTechno](https://github.com/taqat-techno).
