---
title: 'Scaffold Odoo Module'
read_only: false
type: 'command'
description: 'Generate a complete Odoo module skeleton with models, views, security, and tests'
argument-hint: '<module_name> <project> [--version N]'
---

# /odoo-scaffold — Scaffold New Module

```
/odoo-scaffold <module_name> <project> [--version=17]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `module_name` | Yes | Module name in `snake_case` |
| `project` | Yes | Project directory under `projects/` |
| `--version` | No | Odoo version (14-19). Auto-detected if omitted |

## Generated Structure

```
projects/<project>/<module_name>/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <module_name>.py
├── views/
│   └── <module_name>_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── <module_name>_groups.xml
├── data/
├── static/src/{js,scss,img}/
├── i18n/
├── controllers/__init__.py
└── tests/
    ├── __init__.py
    └── test_<module_name>.py
```

## Version-Specific Views

| Odoo | List View Tag | Visibility Syntax |
|------|---------------|-------------------|
| 19 | `<list>` | Inline `invisible="expr"` |
| 17-18 | `<tree>` | `attrs="{'invisible': [(...)]}"` |

## Manifest

Author, website, and license values are read from `odoo-service.local.md` if present. Defaults:

```python
'author': 'Your Company',
'license': 'LGPL-3',
'version': '{odoo_version}.1.0.0',
```

## Post-Scaffold

1. Verify `projects/<project>` is in the config's `addons_path`
2. Refresh module list: `python -m odoo -c conf/<CONFIG>.conf -d <DB> --update-list`
3. Install: `python -m odoo -c conf/<CONFIG>.conf -d <DB> -i <module_name> --stop-after-init`
