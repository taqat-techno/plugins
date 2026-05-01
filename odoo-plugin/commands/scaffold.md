---
title: 'Scaffold Odoo Module'
read_only: false
type: 'command'
description: 'Generate a complete Odoo module skeleton with models, views, security, and tests'
argument-hint: '[<module_name>] [<project>] [--version N]'
---

# /scaffold — Scaffold New Module

## Bare-invocation behavior (no args)

Module scaffolding requires a name — there is no sensible filesystem-derived default. So when invoked with no arguments, the command does **not** error: it prompts.

1. Detect candidate `project` from `$CWD`: if `$CWD/projects/` exists, list its subdirectories and ask which to scaffold inside; if `$CWD` itself is named `projects/` or is inside one, default to it; otherwise ask.
2. Ask for the **module name** (snake_case).
3. Detect Odoo version from `$CWD/odoo/release.py` if present; otherwise ask. Default to 19 if the user doesn't specify.

Show the resolved values and ask for confirmation before generating any files.

## Explicit form

```
/scaffold <module_name> <project> [--version=19]
```

## Arguments

| Argument | Source | Description |
|----------|--------|-------------|
| `module_name` | required (positional or prompt) | Module name in `snake_case` |
| `project` | auto-detected from `$CWD/projects/` or prompted | Project directory under `projects/` |
| `--version` | auto-detected from `odoo/release.py` or prompted (default 19) | Odoo version (14-19) |

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
