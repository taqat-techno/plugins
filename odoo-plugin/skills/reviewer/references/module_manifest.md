# Odoo 17 Module Manifest — review reference

Source: [Module Manifests](https://www.odoo.com/documentation/17.0/developer/reference/backend/module.html)

A `__manifest__.py` is a single Python dictionary at the root of an addon.

## Required fields

| Key | Type | Notes |
|---|---|---|
| `name` | str | Human-readable module name |
| `version` | str | `<odoo_major>.<x>.<y>.<z>`, semver-ish |
| `depends` | list[str] | Modules to load first |
| `data` | list[str] | Data files always loaded |
| `license` | str | Default `LGPL-3` |

## All manifest keys

| Key | Type / default | Purpose |
|---|---|---|
| `name` | str (required) | Display name |
| `version` | str | Module version. Convention: `17.0.1.0.0` |
| `description` | str (reST) | Long description; appears in apps list |
| `author` | str | Author name |
| `website` | str | Author / module URL |
| `license` | str — default `LGPL-3` | One of: `GPL-2`, `GPL-2 or any later version`, `GPL-3`, `GPL-3 or any later version`, `AGPL-3`, `LGPL-3`, `Other OSI approved licence`, `OEEL-1`, `OPL-1`, `Other proprietary` |
| `category` | str — default `Uncategorized` | Business domain. Supports `/`-separated hierarchies (`Foo/Bar` creates both, with `Bar` as the module's leaf) |
| `depends` | list[str] | Required modules. `base` should be listed explicitly even though it's always installed |
| `data` | list[str] | Paths to data files (XML, CSV) loaded on install / upgrade |
| `demo` | list[str] | Data files loaded only with `--with-demo` |
| `auto_install` | bool or list[str] — default `False` | `True` = install when all `depends` are installed. List = install when the listed subset is installed (the rest get pulled in too). Empty list = always install (and pull every dep) |
| `external_dependencies` | dict | `{'python': ['name1'], 'bin': ['exec1']}` — pip/binary deps |
| `application` | bool — default `False` | `True` only for full-fledged apps; not for link / technical modules |
| `assets` | dict | Asset bundle declarations |
| `installable` | bool — default `True` | If `False`, hidden from the UI |
| `maintainer` | str | Defaults to `author` |
| `pre_init_hook` | str | Function name in `__init__.py` to run *before* install |
| `post_init_hook` | str | Function name to run *after* install |
| `uninstall_hook` | str | Function name to run *after* uninstall |
| `active` | bool | **Deprecated**, replaced by `auto_install` |

Hooks take a single `env` argument. Use them only when setup/cleanup is
genuinely impossible through the data files.

## Version-string convention

`17.0.1.0.0`:

- `17.0` — Odoo major version the module targets.
- `1` — module major version (breaking changes).
- `0` — minor version (additive features).
- `0` — patch version (bugfixes).

Bare `1.0` or `17.0` strings strip out three of the four signals — flag as
MINOR debt because release notes become useless.

## License rules of thumb

- `LGPL-3` for OCA / community-friendly modules.
- `OPL-1` is the Odoo Proprietary License (paid).
- `OEEL-1` is the Enterprise Edition license — only inside the Odoo
  enterprise repo.
- `Other proprietary` if internal-only and unlicensed externally.

Missing `license` defaults to `LGPL-3` *silently*. If the code isn't actually
LGPL-3 compatible, this is a legal landmine — flag MAJOR.

## `depends` hygiene

Common review failures:

- A model `_inherits` or `_inherit`s a model from another module without
  declaring that module in `depends` → install fails on a clean DB.
- A view `inherit_id="ref('other.view')"` without the other module in
  `depends` → registry error.
- Demo data referencing records from another module that isn't depended
  on → demo install fails.
- `base` missing — your module never gets re-evaluated when `base` is
  upgraded.
- Listing `base` *and* a module that already depends on `base` is fine
  (redundant but harmless).

A clean rule: every module name appearing in any `_inherit`, `<field
ref="…">`, `<menuitem parent="…">`, or `<template inherit_id="…">` of your
module must appear in `depends`.

## `auto_install` patterns

```python
# 'link' module: glue between two unrelated apps
'depends': ['sale', 'crm'],
'auto_install': True,
```

If both `sale` and `crm` are installed, the link module installs
automatically — no user action needed.

```python
# Pull in deps when one of them is installed
'depends': ['sale', 'crm', 'helpdesk'],
'auto_install': ['sale'],
```

Installs as soon as `sale` is installed, and pulls in `crm` and `helpdesk`
as well. Use sparingly — surprise installs are user-hostile.

### The consumer side: a manifest dependency closure is not the install set

Reading `depends` forward from the `-i` list gives an **incomplete** answer. An
`auto_install` module is pulled in by *its own* deps being satisfied, not by
anything in your list, so it joins the closure uninvited — and it can drag its
whole `depends` list in with it. This is what makes "just trim the module list
to dodge the broken module" fail: a trimmed install reproduces the identical
error because the offending module was never in the list to begin with.

When planning a minimal install set (or trimming one to avoid a failing
module), scan `auto_install` across the **whole addons path**, not just the
modules you named:

```bash
grep -rl "auto_install" --include=__manifest__.py <addons-path> \
  | xargs grep -l "'depends'"
```

For each hit, ask whether your set satisfies its `depends`. If it does, that
module is in your install whether you listed it or not. The only real escape is
a set (or a base DB) that leaves at least one of its deps unsatisfied.

## `external_dependencies`

```python
'external_dependencies': {
    'python': ['phonenumbers', 'qrcode'],
    'bin': ['wkhtmltopdf'],
},
```

Odoo refuses to install if any listed Python module isn't importable or any
binary isn't on `PATH`. **If you `import phonenumbers` in code, declare it
here.** Undeclared imports cause runtime tracebacks on fresh hosts and break
CI in obscure ways.

## `data` ordering

Files in `data` are loaded *in order*. Key dependencies:

1. **Security CSV** (`ir.model.access.csv`) must load before views that
   reference the model.
2. **Groups XML** must load before record rules referencing them.
3. **Record rules** must load before any data that needs ACL evaluation.
4. **Data XML** typically loads before **demo XML**.
5. **Reports XML** can load after views.

A common idiom:

```python
'data': [
    'security/<module>_groups.xml',
    'security/ir.model.access.csv',
    'security/<model>_security.xml',
    'data/<main_model>_data.xml',
    'views/<main_model>_views.xml',
    'views/<module>_menus.xml',
    'report/<model>_reports.xml',
    'report/<model>_templates.xml',
],
```

`demo` list is separate:

```python
'demo': ['demo/<main_model>_demo.xml'],
```

## `application` vs technical module

- `application: True` → the module shows up in the Apps screen as a
  primary app and contributes to the user-form group selector.
- `application: False` (or unset) → technical / utility / link module.

Flipping a tiny utility to `application: True` clutters the Apps screen
and the user-form. Flag MINOR / MAJOR depending on visibility impact.

## Common manifest review failures

| Smell | Severity | Why |
|---|---|---|
| Missing `license` | MAJOR | Legal risk; defaults to LGPL-3 silently |
| `version` is `1.0` or `17.0` | MINOR | Bumps lose meaning |
| `depends` missing a referenced module | BLOCKER | Install fails on clean DB |
| `external_dependencies` missing an `import` | MAJOR | Runtime traceback on fresh host |
| `data` order violates ACL → views chain | BLOCKER | Install fails on clean DB |
| `auto_install: True` on user-visible module | MAJOR | Surprise ghost installs |
| `application: True` on a technical link module | MINOR | UI clutter |
| `demo` files in `data` list | MAJOR | Demo data installed in production |
| `installable: False` shipped to prod | MINOR | Module disappears from upgrade tool |
| Hooks doing things the data files could do | MAJOR | Brittle; bypass declarative loading |
