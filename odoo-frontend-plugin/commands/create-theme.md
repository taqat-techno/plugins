---
title: 'Create Theme'
read_only: false
type: 'command'
description: 'Generate a complete Odoo website theme module from Figma or manual specs'
argument-hint: '[theme_name] [project_path] [--figma <url>] [--version=17] [--colors="..."] [--font="..."]'
primary_agent: theme-generator
---

# /create-theme

Generate a complete, installable Odoo theme module.

## Parse Arguments

From `$ARGUMENTS`, extract:
- `theme_name` — module name (auto-prefixed with `theme_` if needed)
- `project_path` — target directory under `projects/`
- `--figma <url>` — Figma design URL for extraction
- `--version=N` — Odoo version (14-19, default: auto-detect)
- `--colors="..."` — comma-separated hex colors (o-color-1 through o-color-5)
- `--font="..."` — Google Font name

If arguments are missing, prompt the user interactively.

## Pipeline

### Phase 1: Design Extraction
- **Figma mode**: Open Figma via MCP, navigate to PAGES (not components), extract colors + fonts + sizes
- **Manual mode**: Use provided `--colors` and `--font` values
- **Auto-derive**: If only 2 colors found, derive o-color-3/4/5 automatically

### Phase 2: Color & Typography Mapping
- Map colors to o-color-1 through o-color-5 (semantic system)
- Calculate typography multipliers (base = 16px, H6 always 16px)

### Phase 3: Theme Generation
- Scaffold complete module structure (see theme-create skill for full structure)
- Generate `primary_variables.scss` with `$o-website-values-palettes`
- Generate `theme.utils` model with `_theme_xxx_post_copy()`
- Generate page templates, menu, assets

### Phase 4: Installation & Testing
- Update module list → Install theme → Auto-fix errors (up to 3 retries)
- Run testing checklist

## Quick Examples

```bash
# Figma mode
/create-theme --figma https://www.figma.com/file/abc123/MyDesign

# Full arguments
/create-theme my_theme projects/client --figma <url> --version=17

# Manual mode
/create-theme modern_corp projects/client --colors="#207AB7,#FB9F54,#F6F4F0,#FFFFFF,#191A19" --font="Inter"
```

## Deep Reference

For complete file templates, SCSS variable details, and page creation patterns, the `theme-create` and `theme-scss` skills are automatically loaded alongside this command.
