# Odoo 17 Coding Guidelines — distilled

Source: [Coding guidelines](https://www.odoo.com/documentation/17.0/contributing/development/coding_guidelines.html)

## Stable-version rule (always check first)

When modifying files in a stable version, the **original file style strictly
supersedes any other style guideline**. Never re-format existing files to apply
these guidelines — that disrupts revision history. Diffs should be minimal.

In a master/development version, apply the guidelines only to *modified* code
or when most of the file is under revision. If you do restructure, make the
move-only commit first, then apply the feature changes.

## Canonical module tree

```
addons/<module_name>/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── <module_name>.py        # generally one controller file
│   ├── portal.py               # inheriting another module's controller
│   └── main.py                 # DEPRECATED, replaced by <module_name>.py
├── data/
│   ├── <main_model>_data.xml
│   ├── <main_model>_demo.xml
│   └── mail_data.xml
├── models/
│   ├── __init__.py
│   ├── <main_model>.py         # one main model per file
│   ├── <other_main_model>.py
│   └── res_partner.py          # inherited Odoo model in its own file
├── report/
│   ├── __init__.py
│   ├── <main_model>_report.py
│   ├── <main_model>_report_views.xml
│   ├── <main_model>_reports.xml      # report actions, paperformat
│   └── <main_model>_templates.xml    # xml report templates
├── security/
│   ├── ir.model.access.csv
│   ├── <module_name>_groups.xml
│   ├── <main_model>_security.xml
│   └── <other_main_model>_security.xml
├── static/
│   ├── img/
│   ├── lib/<external_lib>/
│   └── src/
│       ├── js/
│       ├── scss/
│       └── xml/
├── views/
│   ├── <module_name>_menus.xml        # optional, main menus only
│   ├── <main_model>_views.xml
│   ├── <main_model>_templates.xml     # portal / website templates
│   └── res_partner_views.xml
└── wizard/
    ├── <transient>.py                 # naming: <base_model>.<action>
    └── <transient>_views.xml
```

File names: `[a-z0-9_]` only. Folder perms 755, file perms 644.

## XML format

Order inside a `<record>`:

1. `id` first
2. `model` second
3. Inside `<field>`: `name`, then value (body or `eval=`), then other attrs by
   importance

Use `<menuitem>` and `<template>` sugar tags over the equivalent `<record>`.

Use `<data noupdate="1">` only for non-updatable records. If the whole file is
non-updatable, put `noupdate="1"` on the `<odoo>` root and drop the `<data>`
tag.

### XML IDs (mandatory naming patterns)

- Menus: `<model>_menu` or `<model>_menu_<action>` for submenus.
- Views: `<model>_view_<view_type>` where `view_type ∈ {form, tree, kanban,
  search, ...}`.
- Actions: main `<model>_action`; others suffixed `_<detail>`.
- Window actions: suffix with view info, `<model>_action_view_<view_type>`.
- Groups: `<module>_group_<group_name>` (user, manager, …).
- Rules: `<model>_rule_<group>` (user, public, company, …).

The `name` field on a view = its XML id with `_` → `.`
(e.g. id `model_name_view_form` → name `model.name.view.form`).

### Inheriting views

Keep **the same XML id** as the source record. Suffix the `name` with
`.inherit.{details}`. Inheritance:

```xml
<record id="model_view_form" model="ir.ui.view">
    <field name="name">model.view.form.inherit.module2</field>
    <field name="inherit_id" ref="module1.model_view_form"/>
    ...
</record>
```

A new *primary* view (a parallel layout) drops the `.inherit` and adds
`<field name="mode">primary</field>`.

## Python

PEP8 with three relaxed rules: E501 (line too long), E301, E302.

### Import order

```python
# 1. stdlib + external libs (alphabetical)
import base64
import re
import time
from datetime import datetime

# 2. odoo imports (alphabetical)
import odoo
from odoo import Command, _, api, fields, models
from odoo.tools.safe_eval import safe_eval as eval

# 3. odoo.addons.* imports
from odoo.addons.web.controllers.main import login_redirect
from odoo.addons.website.models.website import slug
```

### Idioms (each is a real review trigger)

- Don't `.clone()` dicts/lists; use `dict(d)`, `list(l)`.
- Don't `if len(coll):` — collections are truthy / falsy.
- Don't `for k in my_dict.keys():` — iterate the dict directly.
- `my_dict.get('k')` (no second arg = `None`).
- Use `dict.setdefault(k, []).append(v)` instead of guard-and-append.
- Comprehensions over `for + append`.
- Multiple `return`s OK when they make the flow clearer.
- Break methods at "one responsibility" so subclasses can override pieces.
- Use Odoo recordset helpers (`filtered`, `mapped`, `sorted`) over manual
  loops.

### Context propagation

`self.env.context` is a `frozendict` — you can't mutate it. Two valid forms:

```python
records.with_context(new_context).do_stuff()                # replace
records.with_context(**additional_context).do_other_stuff() # merge / override
```

Beware of context keys with global semantics: `default_my_field` will set the
default of `my_field` on *any* model created downstream that has that field
name. When you need a flag, prefix it with your module name to avoid spillover.

### Never `cr.commit()`

The framework opens a cursor at the start of each RPC, commits on success and
rolls back on failure. Calling `cr.commit()` yourself **breaks** the
transactional model and causes partial commits — inconsistent business data,
permanently stuck workflows, polluted test databases.

You do **not** need to commit in:
- `_auto_init()` (handled by addon init)
- reports
- `models.TransientModel` methods
- regular model/controller/wizard methods

The only valid case: you opened your own cursor explicitly. In that case you
also handle rollback and close. Every `cr.commit()` outside the framework must
carry an **explicit code comment** explaining why.

### Translation `_()`

```python
from odoo import _

# good
error = _('This record is locked!')
error = _('Record %s cannot be modified!', record)
error = _("Answer to question %(title)s is not valid.", title=question)

# BAD — formatting inside _() argument
error = _('Record %s cannot be modified!' % record)

# BAD — formatting outside _() result (no fallback)
error = _('Record %s cannot be modified!') % record

# BAD — concatenation / dynamic
error = _("'" + question + "'\n")

# BAD — wrapping a field value
error = _("Product %s is out of stock!") % _(product.name)
```

Field values are translated by the `translate=True` flag on the field
definition, not by wrapping at use-site.

Prefer `%` over `.format()`; prefer `%(name)s` named placeholders when there
are multiple variables.

## Symbols & conventions

### Model name (`_name`)

- Singular, dot-notation, module-prefixed (`sale.order`, not `saleS.orderS`).
- Transient (wizard): `<base_model>.<action>` — never the word "wizard".
- Report: `<base_model>.report.<action>`.

### Class & variable

- Class: PascalCase — `class SaleOrder(models.Model):`.
- Variable: snake_case. PascalCase only for *model* variables pulled from env:
  `Partner = self.env['res.partner']; partners = Partner.browse(ids)`.
- Field suffix:
  - `Many2one` → `_id` (e.g. `partner_id`)
  - `One2many` / `Many2many` → `_ids` (e.g. `sale_order_line_ids`)

### Method conventions

| Pattern | Form |
|---|---|
| Compute | `_compute_<field>` |
| Search | `_search_<field>` |
| Default | `_default_<field>` |
| Selection | `_selection_<field>` |
| Onchange | `_onchange_<field>` |
| Constraint | `_check_<constraint>` |
| Action (button) | `action_<verb>` + `self.ensure_one()` at start |

### Class attribute order

1. Private attributes (`_name`, `_description`, `_inherit`, `_order`,
   `_sql_constraints`, …)
2. Default methods + `default_get`
3. Field declarations
4. Compute / inverse / search methods — *same order as field declarations*
5. Selection methods (`_selection_*`)
6. `@api.constrains` + `@api.onchange`
7. CRUD overrides (`create`, `write`, `unlink`, `copy`, `_search`,
   `name_search`)
8. `action_*` methods
9. Other business methods

Skeleton:

```python
class Event(models.Model):
    _name = 'event.event'
    _description = 'Event'

    def _default_name(self):
        ...

    name = fields.Char(default=_default_name)
    seats_reserved = fields.Integer(store=True, readonly=True,
                                    compute='_compute_seats')

    @api.depends('seats_max', 'registration_ids.state',
                 'registration_ids.nb_register')
    def _compute_seats(self):
        ...

    @api.model
    def _selection_type(self):
        return []

    @api.constrains('seats_max', 'seats_available')
    def _check_seats_limit(self):
        ...

    @api.onchange('date_begin')
    def _onchange_date_begin(self):
        ...

    def create(self, values):
        ...

    def action_validate(self):
        self.ensure_one()
        ...

    def mail_user_confirm(self):
        ...
```

## JavaScript / static files

- `static/` is served at `/<module_name>/static/…`.
- Vendored libs in `static/lib/<vendor>/`.
- Generic source code under `static/src/{js,scss,xml}`.
- `static/src/js/tours/` = end-user *tutorials* (not tests).
- `static/tests/` = JS tests; `static/tests/tours/` = tour tests.
- `use strict;` recommended in JS files. Lint with jshint or equivalent.
- Never check in minified libraries.
- PascalCase for class declarations.

## CSS / SCSS

- 4-space indent, no tabs, ~80 cols.
- One declaration per line.
- Order properties outside-in: position → layout → decoration (font, filter).
- Scoped SCSS variables (`$-foo`) and CSS variables (`--foo`) declared at the
  top of the block, separated from other rules by a blank line.
- Avoid `id` selectors. Prefix classes with `o_<module_name>` (or `o_<route>`
  for website modules). The web client uses just `o_`.
- "Grandchild" naming — avoid hyper-specific class chains.

### SCSS variable conventions

- Global: `$o-[root]-[element]-[property]-[modifier]`
- Scoped: `$-[name]`
- Mixins/functions: `o-[name]`, with optional args in scoped form `$-[arg]`.

### CSS variable conventions

DOM-related only (used for contextual adaptation, not the design system).
Pattern: `--[root]__[element]-[property]--[modifier]` (BEM).

Define them inside the component's main block with default fallbacks. Avoid
defining CSS variables on the `:root` pseudo-class except for templates that
genuinely need cross-bundle contextual awareness.
