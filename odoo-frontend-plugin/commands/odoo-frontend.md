---
title: 'Odoo Frontend'
read_only: true
type: 'command'
description: 'Show Odoo frontend environment status and available capabilities'
argument-hint: ''
---

# /odoo-frontend

Display the current Odoo frontend development environment status.

## Environment Detection

1. Walk up from `$CWD` looking for `odoo-bin` or `odoo/__init__.py`
2. Read version from `odoo/release.py` → `version_info`
3. Map to Bootstrap version:
   - Odoo 14-15 → Bootstrap 4.x
   - Odoo 16-19 → Bootstrap 5.1.3
4. Scan for `projects/` directory and list theme modules (`theme_*`)
5. Check for active conf files in `conf/`

## Display

```
Odoo Frontend Toolkit v8.0
==========================

Environment
  Odoo version : {detected}
  Bootstrap    : {mapped}
  Owl          : {v1/v2/none}

Project
  Path         : projects/{project}
  Config       : conf/{project}{ver}.conf
  Themes found : {list}

Available Skills
  theme-create    Generate complete theme modules
  theme-scss      SCSS variable reference (115+ keys)
  theme-design    Figma workflow + page templates
  theme-snippets  Snippet system (81+ templates)
  frontend-js     JavaScript patterns + version handling

Commands
  /create-theme   Generate a theme from Figma or manual specs
```

## Version Compatibility

| Odoo | Bootstrap | Owl | JS Classes |
|------|-----------|-----|------------|
| 14 | 4.x | — | `ml-*`, `mr-*` |
| 15 | 4.x | v1 | `ml-*`, `mr-*` |
| 16 | 5.1.3 | v1 | `ms-*`, `me-*` |
| 17 | 5.1.3 | v2 | `ms-*`, `me-*` |
| 18-19 | 5.1.3 | v2 | `ms-*`, `me-*` |
