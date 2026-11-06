---
name: odoo-solution-design
description: >-
  Use when a client's business or a feature request has to become an Odoo implementation -
  someone describes what their factory, shop, clinic, charity or distributor does step by
  step, asks "how do I build X in Odoo", "design a module for...", "we need a feature
  that...", wants a fit-gap or blueprint for a new Odoo project, or is about to scaffold a
  custom module. Finds the standard Odoo app for each step in the target version first, then
  configuration, then OCA, then the Odoo Apps store, and designs custom code only for the gap
  that is left, as the smallest extension of what exists.
license: "MIT"
metadata:
  version: "1.0.0"
---

# Odoo solution design: standard first, custom last

**The rule: the less custom code, the more successful the system.** Every line of custom code
is upgraded, tested, secured and debugged by the client forever. Standard Odoo is maintained
by Odoo S.A.; OCA modules by a community. So a requirement earns custom code only after the
standard product, its configuration, and the maintained ecosystem have been checked for the
exact version and edition — and found not to fit, with the reason written down.

## The reuse ladder (mandatory order)

| Rung | Verdict | What counts |
|---|---|---|
| 1 | `STANDARD` | A standard app/feature of the **target version**. Community first, then Enterprise if the client is licensed. |
| 2 | `CONFIG` | Standard behaviour switched on or shaped by configuration: settings, routes and rules, operation types, record rules, groups, automated actions, server actions, mail templates, reports from standard layouts. No module. |
| 3 | `OCA` | A module on the OCA branch for that version, passing the maturity and behaviour check in [oca-search.md](references/oca-search.md). |
| 4 | `APPS` | A module from apps.odoo.com for that version, with licence, author, price and code quality recorded. |
| 5 | `CUSTOM` | Only the residual gap, as the smallest extension of the standard models from rungs 1-4. |

A row may skip a rung only with a written reason in the verdict table (for example: the OCA
module is unmaintained for this version, conflicts with an installed module, or swallows
errors from core call sites). The criteria and worked cases are in
[reuse-ladder.md](references/reuse-ladder.md). Read it before you accept any skip.

## Process

### 1. Pin the version and the edition first

Everything is per version. Read it from the project, never assume:

- the project's conf file (`addons_path` names the core tree), `odoo/release.py` in that tree,
  or a module's `__manifest__.py` version prefix (`19.0.x.y.z`);
- Enterprise: is an `odoo-ee` / enterprise path in `addons_path`, or does the client hold a
  licence? If unknown, design for Community and mark Enterprise-only rows `EE-conditional`.

A gap analysis run against the Community tree alone over-reports custom work: Rental, Quality,
Field Service, Payroll, Planning, Documents, Sign, Approvals and Barcode are Enterprise apps.

### 2. Break the narrative into numbered process steps

Turn the client's story into verbs on records: *procure → receive → QC → store → produce →
pack → sell → deliver → invoice → collect → report*. One row per step. Keep **current state**
(what they do today, or what staging shows) separate from **target state** (what they need): a
requirement is not refuted because staging doesn't have it yet.

### 3. Search the local core source for that version — never answer from memory

Grep the real tree for the version you pinned. Models, fields and menus are removed and
renamed between versions (Odoo 19 removed `product.packaging`, `uom.category` and
`hr.expense.sheet`, and renamed `stock.quant.package` to `stock.package`). Typical layout:

```bash
CE=$ODOO_SOURCES/19.0/odoo-ce/addons     # community addons
EE=$ODOO_SOURCES/19.0/odoo-ee            # enterprise addons sit at the repo root
grep -rln "_name = 'stock.package'" $CE/*/models          # does the model exist?
grep -rn "string=\"Dropship\"\|'dropship'" $CE/stock_dropshipping   # a feature by keyword
grep -rn "<menuitem" $CE/purchase_requisition/views | head          # where the user reaches it
```

Search by model name, field name, menu label and selection value. Quote `file:line` for every
claim. Before mapping a concept onto a native feature, read the field's `required`, `store`,
`compute` flags and any `_should_*` / `_get_*` filter: field-level constraints decide fit.
[business-fit-gotchas.md](references/business-fit-gotchas.md) lists the ones that have burned
real designs. [standard-module-map.md](references/standard-module-map.md) gives the usual
starting apps per business process and the removed/renamed table.

When the mechanics are subtle (stock chains, reservations, returns, POS sessions), **spike them
on a scratch database** of the target version and record the approved mechanism before
planning on it.

### 4. If uncovered: search OCA for the version branch

Search the OCA repository that owns the domain on branch `<version>` (e.g. `OCA/stock-logistics-warehouse`
`19.0`). Record repo, module, `development_status`, last commit date, dependencies and open
migration PRs. Then run the behaviour check: does it swallow exceptions raised from core call
sites, is it inert under `--test-enable`, does its quantity/semantics match the requirement?
How to search reliably: [oca-search.md](references/oca-search.md).

### 5. Then the Apps store, then custom

Apps store candidates: confirm the version tab, licence (OPL-1 / LGPL / proprietary), author,
price, last update and whether the code can be reviewed before purchase. Only then mark the
row `CUSTOM`.

### 6. Output the fit-gap verdict table

Always produce this table, even when everything is standard:

```markdown
**Target:** Odoo 19.0 Enterprise (licensed) · project conf `conf/<name>.conf`

| # | Process step | Standard module / feature (file:line) | Config needed | OCA / Apps candidate | Verdict | Reason | Risk |
|---|---|---|---|---|---|---|---|
| 1 | Receive from vendor in 2 steps | `stock` reception routes (stock/data/stock_data.xml:…) | Warehouse → Incoming: 2 steps | — | CONFIG | native route | low |
| 2 | Block sale below cost | — | — | `OCA/sale-workflow` `<module>` on 19.0, Beta, last commit <date> | OCA | fits, maintained, behaviour check passed | medium: Beta |
| 3 | Per-work-center operator access | `mrp_workorder` (EE) has no per-center ACL | — | none on 19.0 (`OCA/manufacture` checked) | CUSTOM | no fit | low: 1 record rule |
```

Then list:

- **Modules to install** — standard, OCA (with pinned commit), Apps — in dependency order.
- **Configuration steps** — the settings and records rung 2 needs, in order.
- **Residual custom scope** — one line per `CUSTOM` row: the model it extends, the field or
  method it adds, and why nothing above fitted.

### 7. Only for CUSTOM rows: design the smallest extension

Follow [custom-module-design.md](references/custom-module-design.md): inherit and extend (never
copy core), `depends` on the standard module that owns the concept, data before code, no core
edits, upgrade-safe hooks, multi-company and security from day one, tests from day one. Then
hand off to `/odoo:scaffold`, which asks for this verdict table before generating anything.

## Delegating the search

For more than about five process steps, dispatch the `solution-analyst` agent with the pinned
version/edition, the source paths and the numbered steps. It runs steps 3-5 and returns the
verdict table; you review every `CUSTOM` and every skipped rung before presenting it.

## Red flags — stop and go back a rung

| Thought | Reality |
|---|---|
| "I know Odoo has no feature for this." | You grepped which version? Answer with `file:line` or don't answer. |
| "A small module is quicker than configuring." | It is quicker today and costs every upgrade after. Configure first. |
| "This OCA module does it, vendor it." | Run the behaviour check. An OCA module that fights core call sites is worse than custom. |
| "The client asked for a module." | The client asked for an outcome. A module is one possible answer. |
| "Enforce it in code everywhere." | An invariant that must patch every core entry point (create, import, duplicate, RPC) is a maintenance sink. Prefer the native behaviour plus a helper. |
| "Copy the core view/method and change it." | Inherit with XPath / `super()`. A copied core method silently stops receiving fixes. |

## Related skills

- `odoo-reviewer` — its reuse check flags custom code that re-implements standard or OCA.
- `odoo-upgrade` — removed/renamed models per version when porting an existing design.
- `odoo-security` — groups, ACLs and record rules for the residual custom models.
- `odoo-test` — the tests the custom rows need.
