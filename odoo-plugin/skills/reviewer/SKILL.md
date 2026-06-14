---
name: odoo-reviewer
description: Authoritative Odoo 17 and Odoo 19 code-review and technical-debt knowledge base, including the cross-version deltas needed for mixed-version environments. ALWAYS USE this skill when reviewing, auditing, refactoring, or estimating technical debt for any Odoo 17 or Odoo 19 module — including OCA modules, custom addons, third-party addons, manifests (__manifest__.py), models, views, security (ir.model.access.csv / ir.rule), QWeb, Owl components, performance, ORM patterns, or migration work. Trigger on phrases like "review this Odoo module", "Odoo code review", "audit the addon", "Odoo technical debt", "is this Odoo best practice", "refactor Odoo", "manifest review", "mixed-version cluster", "multi-cluster review", "Odoo 17 vs Odoo 19", "migrate to Odoo 19", or whenever a .py / .xml / __manifest__.py from an Odoo addon is in scope. Use this skill BEFORE making any judgment about Odoo code quality or before producing a tech-debt estimate.
---

# Odoo 17 / 19 Reviewer

A reference distilled from the official Odoo documentation:

- v17: [Reference index](https://www.odoo.com/documentation/17.0/developer/reference.html)
  · [Coding guidelines](https://www.odoo.com/documentation/17.0/contributing/development/coding_guidelines.html)
  · [Tutorials](https://www.odoo.com/documentation/17.0/developer/tutorials.html)
- v19: [Reference index](https://www.odoo.com/documentation/19.0/developer/reference.html)
  · [Coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html)
  · [Tutorials](https://www.odoo.com/documentation/19.0/developer/tutorials.html)

Use it when reviewing code, planning refactors, or producing technical-debt
estimates for any Odoo module. The goal is to ground every judgement in a
documented Odoo rule, not in personal taste.

This skill primarily targets **Odoo 17**. Where a rule has changed in
**Odoo 19**, the section below points at `references/v19_deltas.md`. In
mixed-version environments (a fleet where some clusters/instances run v17
and others v19), always identify the target's Odoo version before applying
a finding — many rules are version-specific.

## How to use this skill

1. **Identify the scope and version.** Is the review for a single file, a
   module, a repo, a cluster, or a cross-module pattern? Which Odoo version
   does the target run on (17 or 19)? In a multi-cluster fleet, this is
   per-cluster.
2. **Walk the checklist below in order.** Each section names a *category of
   risk* with the specific rule and a pointer to the deep-dive reference file.
3. **Cross-check the v19 deltas.** Any rule that names a renamed API or a
   v19-only construct (e.g. `<list>`, `Domain` class, `aggregator=`) is in
   `references/v19_deltas.md`. Apply it only on the version it targets.
4. **Score severity, not aesthetics.** A violation is BLOCKER, MAJOR, MINOR, or
   STYLE. The severity model is in `references/severity_model.md`.
5. **Cite the rule.** When flagging a finding, include the relevant rule name
   and (when possible) the Odoo docs anchor. Never invent rules.
6. **For tech-debt estimation**, count violations by severity per module and
   multiply by the rough effort table in `references/severity_model.md`.

## What's in this skill

```
reviewer/
├── SKILL.md                              ← this file (review checklist; v17 baseline)
└── references/
    ├── coding_guidelines.md              ← module layout, file naming, Python/XML/JS/SCSS
    ├── orm_patterns.md                   ← _inherit / computed / related / depends / batch ops
    ├── security_pitfalls.md              ← sudo / SQL / t-raw / public methods / Markup
    ├── performance.md                    ← N+1, prefetch, store=True, profiling
    ├── module_manifest.md                ← manifest keys + versioning rules
    ├── testing.md                        ← TransactionCase, HttpCase, tours, naming
    ├── severity_model.md                 ← how to grade findings & estimate debt
    └── v19_deltas.md                     ← every rule that changed in Odoo 19 + mixed-cluster checklist
```

Read a reference file when a check requires the detail it holds. Otherwise the
checklist below is enough to make the call.

---

## The 12-section review checklist

### 1. Manifest hygiene (`__manifest__.py`)

Check, in order:

- `name`, `version`, `license`, `category`, `depends` all present.
- `version` follows `<odoo_major>.<x>.<y>.<z>` (e.g. `17.0.1.0.0`). A bare
  `1.0` or `17.0` is MINOR debt — bumps lose meaning.
- `license` is one of `LGPL-3`, `AGPL-3`, `GPL-3`, `OPL-1`, `OEEL-1`, `Other
  proprietary`. Missing license = MAJOR (legal risk).
- `depends` lists every module whose models / views / data the addon uses. A
  `base` dep is required even when implicit. Hidden transitive deps =
  install-order BLOCKER.
- `auto_install` semantics: `True` = install when all deps present;
  `list` = install when that subset is present and pull the rest. Misuse on a
  module that creates user-visible UI = MAJOR (unwanted ghost installs).
- `external_dependencies` declares Python / binary deps that must be on the
  host. Importing `phonenumbers` or `qrcode` without declaring it = MAJOR.
- `data` and `demo` paths exist and load in the right order (security CSVs
  before views; data before demos).
- `application` is `True` only for full-fledged apps, not technical link
  modules.

→ Details in `references/module_manifest.md`.

### 2. Module layout & file naming

- Directory layout matches the canonical tree: `models/`, `views/`,
  `security/`, `data/`, `demo/`, `wizard/`, `report/`, `controllers/`,
  `static/`, `tests/`.
- File naming rules (these are explicit Odoo conventions):
  - One main model per file; file name = model name with dots → underscores
    (e.g. `sale_order.py` for `sale.order`).
  - Inherited models in their own file: `res_partner.py`.
  - Views: `<model>_views.xml`; templates `<model>_templates.xml`; menus
    optionally split into `<module>_menus.xml`.
  - Security: `ir.model.access.csv`, `<module>_groups.xml`,
    `<model>_security.xml`.
  - Wizards in `wizard/`, naming `<transient>.py` + `<transient>_views.xml`.
    The transient model name follows `<related_base_model>.<action>`,
    avoiding the literal word "wizard".
  - File names use only `[a-z0-9_]`.
- Controllers consolidate in `<module_name>.py`; `main.py` is deprecated.
- Static files under `static/src/{js,scss,xml}` and `static/lib/` for vendored
  libs. Never link external URLs for images/libs; copy them in.

A module that scatters files in `/models/<random>.py` or mixes view files
with model files = STYLE/MINOR but compounds into review fatigue.

→ Details in `references/coding_guidelines.md`.

### 3. XML conventions

- `<record>` order: `id` before `model`. Inside fields, `name` first, then
  value (`<field>` body or `eval=`), then other attrs by importance.
- `<data noupdate="1">` only for non-updatable seed data. Prefer
  `noupdate="1"` on the `<odoo>` root if the whole file is non-updatable.
- Prefer the sugar tags `<menuitem>` and `<template>` over a full `<record>`.
- XML ID naming patterns (all MUST follow):
  - menus → `<model>_menu` or `<model>_menu_do_stuff`
  - views → `<model>_view_<form|tree|kanban|search|...>`
  - actions → `<model>_action` (main) or `<model>_action_<detail>`
  - groups → `<module>_group_<name>` (user, manager, …)
  - rules → `<model>_rule_<group>` (user, public, company, …)
- View `name` field = XML id with `_` → `.` (e.g. id `sale_order_view_form`
  → name `sale.order.view.form`).
- Inheriting views: keep the **same XML id** as the original; suffix the
  `name` with `.inherit.<details>`. New primary views drop the `.inherit`.

Violating ID conventions = MAJOR (breaks community tooling, migration
scripts, and grep-ability).

**Odoo 19 note**: the `<tree>` tag is renamed to `<list>` in v19, and the
view-type enum changes from `tree` to `list` (so XML ids become
`<model>_view_list`). See `references/v19_deltas.md` for the mixed-cluster
handling rule — sharing a view file across v17 and v19 clusters is a
BLOCKER until the file is split.

### 4. Python style & idioms

The Odoo project relaxes only three PEP8 rules: E501 (line length), E301,
E302. Everything else applies.

Import ordering — three groups, alphabetized inside each:

1. stdlib + 3rd-party external libs
2. `odoo` imports (`from odoo import api, fields, models, _`)
3. `odoo.addons.*` imports

Idiom rules (each is a real review trigger):

- No `.clone()` on dicts/lists — use `dict(d)`, `list(l)`.
- No `if len(coll):` — collections are truthy/falsy.
- No `for k in my_dict.keys():` — iterate the dict directly.
- `my_dict.get('k')` not `my_dict.get('k', None)`.
- Prefer `dict.setdefault(k, []).append(v)` over guard-and-append.
- Use list/dict comprehensions where they read better.
- Multiple `return`s OK if they simplify the flow.
- Split methods at "one responsibility"; long monolithic action methods
  block subclass overrides.
- `_(...)` translation: **only** `_('literal string', var1, var2)`. Never
  `_('foo %s' % x)`, never `_('foo') % x`, never `_('a' + b)`. Use named
  placeholders `_('… %(name)s …', name=…)` when multiple vars.
- `cr.commit()` is **forbidden** in normal model/controller/report/wizard
  code. The only exception is when *you* opened the cursor explicitly, in
  which case you must add an `# explicit comment` justifying it. **In v19,
  `cr.rollback()` outside the framework is also forbidden by the docs**
  (treat it as a v17 rule too — it was already best practice).
- **(v19 only)** Avoid broad `except Exception:`. Catch the specific
  exception you can recover from. If you must handle framework exceptions,
  wrap the body in `with self.env.cr.savepoint():` so partial state is
  rolled back. Postgres slows down beyond 64 savepoints per transaction —
  don't loop savepoints over large batches.

→ Details in `references/coding_guidelines.md`.

### 5. Symbols, conventions, model attribute order

Naming:

- Model `_name`: singular, dot-notation, module-prefixed
  (`sale.order`, not `saleS.orders`).
- Transient: `<base_model>.<action>` — never the word "wizard".
- Report model: `<base_model>.report.<action>`.
- Class name: PascalCase (`SaleOrder`).
- Variable name: snake_case; PascalCase only for *model* variables you've
  pulled from the env (`Partner = self.env['res.partner']`).
- Field naming suffixes:
  - `Many2one` → `_id`
  - `One2many`/`Many2many` → `_ids`
- Method-naming patterns (Odoo greps for these):
  - compute → `_compute_<field>`
  - search → `_search_<field>`
  - default → `_default_<field>`
  - selection → `_selection_<field>`
  - onchange → `_onchange_<field>`
  - constraint → `_check_<constraint>`
  - action (button) → `action_<verb>` and starts with `self.ensure_one()`

Required class attribute order:

1. Private attrs (`_name`, `_description`, `_inherit`, `_order`,
   `_sql_constraints`, …)
2. Default methods + `default_get`
3. Field declarations
4. Compute/inverse/search methods, *in field-declaration order*
5. Selection methods
6. `@api.constrains` + `@api.onchange`
7. CRUD overrides (`create`, `write`, `unlink`, `copy`, `_search`,
   `name_search`)
8. `action_*` methods
9. Other business methods

Out-of-order attributes = STYLE; misnamed compute/onchange = MAJOR (Odoo's
binding magic relies on the convention).

**Odoo 19 note**: v19 moves `_sql_constraints` out of the private-attribute
bucket and into a new "SQL constraints and indexes" bucket between
*field declarations* and *compute methods*. Apply the v17 order on v17
code and the v19 order on v19 code; don't flag either as a violation
against the other version's rule. See `references/v19_deltas.md`.

### 6. ORM patterns & inheritance

Three inheritance modes:

- **Classic** (`_inherit = 'sale.order'`): extend in place. Same `_name`
  implied.
- **Prototypal** (`_name = 'x.y'; _inherit = 'sale.order'`): create a new
  model that copies fields/methods from the source.
- **Delegation** (`_inherits = {'res.partner': 'partner_id'}`): composition
  with a required Many2one; exposes fields without storing them.

Computed-field rules:

- A `@api.depends(...)` must list *every* field the compute reads. Dotted
  paths allowed (`line_ids.value`).
- `compute=` without `store=True` is recomputed on every read — fine for
  display, harmful in domain filters and reports.
- `store=True` + `@api.depends` is required if the field is searchable or
  used by downstream stored computes.
- `compute_sudo`: defaults to `True` for stored, `False` for non-stored.
  Override only with a written justification.
- Recursive depends (`parent_id.X`) **must** set `recursive=True` —
  otherwise recomputation is silently wrong.
- `related='a.b.c'` is shorthand for compute; chains of `One2many` /
  `Many2many` are **not** allowed in `related`.

Common ORM anti-patterns to flag:

- Looping `record.write(...)` inside a `for` over recordset — should be a
  single recordset `write`.
- `self.env['x.y'].search(...)` inside a loop — N+1; pull outside.
- Bypassing the ORM with `self.env.cr.execute(...)` when an
  `.search()` / `.read()` would work. ORM bypass = MAJOR (skips ACL,
  cache invalidation, `active`, translations).
- `self.sudo()` used as a workaround for failing ACL = BLOCKER (security).
  Only use `sudo()` when the operation legitimately requires elevated
  rights and the access is unrelated to the calling user's identity.
- `with_context(...)` mutating a dict — context is a frozendict. Use
  `with_context(**extra)` or `with_context(new_dict)`.

**Odoo 19 ORM deltas** (apply only on v19 code; details in
`references/v19_deltas.md`):

- Aggregation field attr renamed: `group_operator='sum'` → `aggregator='sum'`.
- `read_group()` → `_read_group()` (canonical private name in v19).
- `_search_<field>` methods can `return NotImplemented` so the ORM retries
  with semantically-equivalent operators.
- `Domain` class (`from odoo.fields import Domain`) is the v19 way to
  compose domains safely; raw list-concatenation with user input is a
  v19 MAJOR (domain-injection risk).
- `company_dependent` fields are stored as jsonb on the model table in
  v19 (was `ir.property` in v17) — adds a v17→v19 data migration step.
- `BaseModel` lives at `odoo.orm.models.BaseModel` in v19 (was
  `odoo.models.BaseModel`).

→ Details in `references/orm_patterns.md` (v17 baseline) and
`references/v19_deltas.md` (v19 deltas).

### 7. Security — access rights, rules, field groups

- Every new model **must** have at least one row in `ir.model.access.csv`.
  Missing access row = BLOCKER (model is invisible / un-CRUDable in UI).
- Access rights are *additive* across groups (union); record rules are
  filters (intersection within global rules, union within group rules).
- Field-level: `groups='module.group_xxx'` on a field strips it from views
  and `fields_get`. Useful, but easy to miss in test setups.

Security pitfalls (each is BLOCKER unless noted):

- **Unsafe public methods.** Anything not prefixed with `_` is callable by
  RPC with arbitrary args. If business logic mutates state, expose it via
  a `_set_state(...)` private method and have the public `action_done()`
  enforce preconditions before delegating.
- **SQL injection** via `cr.execute('… ' + user_input + ' …')`. Use
  parameterised queries `cr.execute('… WHERE x = %s', (val,))`. Use
  `tuple(ids)` for `IN %s`. Never `%-format` SQL strings yourself.
- **Unescaped QWeb (`t-raw`).** Frequent XSS vector. Default to `t-esc`;
  use `Markup(...)` for safe HTML and let `_(...)` / `%`-formatting work
  with it.
- **Sudo'd writes from a public method** without sanity checks.
- **Trusting context keys** like `default_*` to enforce policy — context
  is user-controlled.
- **(v19)** **Domain injection.** Building a search domain by
  concatenating user input with a security predicate is unsafe — a user
  can inject `'|'` to OR-out the predicate. Use the v19 `Domain` class
  to compose with `&`. On v17 (no `Domain` class), always append the
  security predicate last and normalize the input.

**Odoo 19 security notes** (details in `references/v19_deltas.md`):

- `user_has_groups('module.group')` → `env.user.has_group('module.group')`
  in v19 examples; flag the older form as MINOR drift on v19 code.
- v19 ships an `SQL(...)` query wrapper plus `env.execute_query(SQL(...))`
  for safer raw queries; use it when an ORM bypass is justified.

→ Details in `references/security_pitfalls.md` (v17 baseline) and
`references/v19_deltas.md` (v19 deltas).

### 8. Performance

Hotspots to look for:

- Compute methods that don't iterate `self` (`for record in self: ...`)
  but write to `self.field_x = ...` — only works on a singleton; otherwise
  silently ignores extra records.
- Stored computes whose `@api.depends` is incomplete — leads to stale data
  with no obvious symptom.
- Reading a field in a loop that triggers a per-record SQL query — flush
  via `.mapped('field')` or prefetch the recordset.
- `search([...])` returning thousands of records when a `search_count` or
  a `read_group` would do.
- `for r in self: r.write({...})` instead of a single
  `recordset.write({...})`.
- Disabled or missing indexes on heavily filtered columns (set
  `index=True` on the field, or add a `_sql_constraints` index).

Use `odoo.tools.profiler.Profiler` (Python) or the developer-mode profiler
(UI) to confirm hotspots before "fixing" them.

→ Details in `references/performance.md`.

### 9. Views

- One file per main model, suffix `_views.xml`.
- For inheriting a view: keep the **same XML id** as the source view; set
  `name` with `.inherit.<details>` suffix.
- New primary views (different layout for same model) drop the `.inherit`
  in the name and set `<field name="mode">primary</field>`.
- Domain expressions in views: prefer Python-list domains over string
  domains when possible; both are evaluated server-side.
- Don't put presentation logic in models — use `widget=` attributes,
  `attrs`/`invisible`/`readonly`, or QWeb in templates.

### 10. JS / Owl / assets

- `static/src/{js,scss,xml}` for source; `static/lib/<vendor>/` for
  vendored libs; `static/tests/` for tests (and `tours/`).
- No minified JS in repo. No URL-linked images/libs — copy them in.
- One Owl component per file with a meaningful name.
- `use strict;` recommended.
- Assets bundles declared in the manifest `assets` key.
- CSS classes prefixed `o_<module>` (or `o_<route>` for website modules).
- SCSS variable convention: `$o-[root]-[element]-[property]-[modifier]`;
  scoped vars `$-name`. CSS vars BEM-style:
  `--[root]__[element]-[property]--[modifier]`.

### 11. Testing

- Tests live in `tests/`, named `test_*.py`, imported from
  `tests/__init__.py`. **Tests not imported from `__init__.py` will not
  run.**
- Pick the base class deliberately:
  - `TransactionCase` — per-method savepoint; fast & isolated.
  - `SingleTransactionCase` — shared transaction across methods.
  - `HttpCase` — for routes, tours, browser tests.
- Common helpers: `self.ref('module.xmlid')`,
  `self.browse_ref('module.xmlid')`, `self.assertQueryCount(N)`,
  `self.profile()`.
- Mocking the database with mocks is an anti-pattern — Odoo tests run in
  a sub-transaction, use real records.

→ Details in `references/testing.md`.

### 12. Translation (`_()`)

- v17 import: `from odoo import _` → `_(...)`.
- v19 canonical form: `self.env._(...)`. `from odoo import _` still works
  on v19 for backward compatibility and is the recommended form for
  modules that must run on both versions.
- Only literal strings:
  `_('Record %s cannot be modified', record)`. Use `%(name)s` named
  placeholders when there are multiple variables.
- Field values are translated via the `translate=True` flag on the field,
  not by wrapping in `_()`. Wrapping a field value in `_()` is a no-op and
  *wrong* — flag as MINOR (sometimes MAJOR if user-facing).
- Never `_(a + b)`, never `_(f'{x}')`, never `_('… %s' % x)`.

→ Cross-version detail in `references/v19_deltas.md`.

---

## Producing a tech-debt estimate from a review

1. Walk the 12 sections for each module under review.
2. Bucket each finding into BLOCKER / MAJOR / MINOR / STYLE (rubric in
   `references/severity_model.md`).
3. For each module, report counts per severity + a one-line top risk.
4. Use the effort table in `references/severity_model.md` to convert
   counts to hours.
5. When listing findings, **cite the rule** ("Coding guidelines → Symbols
   and Conventions → method-naming") so the user can re-check.

## What to NOT do

- Don't invent rules. If a rule isn't in this skill or the Odoo docs,
  flag the issue as "convention question, not a docs rule".
- Don't grade on personal style. PEP8 already excludes E501/E301/E302 in
  Odoo.
- Don't conflate OCA conventions with Odoo official conventions —
  reference them as "OCA convention" when relevant.
- Don't recommend `sudo()` as a fix for ACL errors.
- Don't recommend `cr.commit()` to "make sure data persists" — see §4.

## Mixed-cluster (v17 + v19) shortcut

When clusters in a fleet straddle versions, the lowest-common-denominator
wins for any module that must install on both:

- `<tree>` everywhere a list view is declared → won't render on v19 (use
  `<list>`). Shared XML view files = BLOCKER until split.
- `group_operator=` on fields → invalid in v19 (use `aggregator=`).
- `_(...)` via `from odoo import _` → works on both; `self.env._` is v19
  only.
- List-domain composition with user input → unsafe; v19 wants `Domain(...)`.
- `_sql_constraints` belongs in the private-attr group on v17, in its own
  bucket below fields on v19.
- `company_dependent` storage differs — every v17→v19 cluster migration
  needs a data migration step.

The full checklist and rationale: `references/v19_deltas.md`.

## Source of truth

All rules in this skill trace back to:

- v17: [Coding guidelines](https://www.odoo.com/documentation/17.0/contributing/development/coding_guidelines.html)
  · [Reference](https://www.odoo.com/documentation/17.0/developer/reference.html)
  · [Tutorials](https://www.odoo.com/documentation/17.0/developer/tutorials.html)
- v19: [Coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html)
  · [Reference](https://www.odoo.com/documentation/19.0/developer/reference.html)
  · [Tutorials](https://www.odoo.com/documentation/19.0/developer/tutorials.html)

When in doubt, read the source. The reference files in this skill paraphrase
those pages; they do not replace them.
