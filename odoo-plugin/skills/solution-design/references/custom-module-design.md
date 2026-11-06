# Designing the residual custom part

Only `CUSTOM` rows of the verdict table reach this file. The goal is the smallest extension of
what the standard (and accepted OCA) modules already do.

## Shape

- **Extend, never copy.** `_inherit` the standard model; inherit views with XPath; call
  `super()` in every override. A copied core method or view stops receiving upstream fixes and
  silently diverges at the next upgrade.
- **Before overriding, check the extension point is open.** Grep the chain for the method: a
  layer that replaces it without `super()` (a terminal override, common in OCA and vendor
  modules) means your override may never run. Declare an explicit `depends` on every module
  whose behaviour you rely on, so load order is a contract, not luck.
- **`depends` on the standard module that owns the concept** (`stock`, `mrp`, `sale_stock` …),
  not on a broad umbrella. Install the full custom + vendored set together on a fresh database
  before promoting: a missing `depends` hidden locally by an already-installed module surfaces
  as `unknown comodel_name` on the first clean build.
- **One module per business capability**, named for the capability, not the client or the
  sprint. A misnamed module is expensive to rename later.
- **Data before code.** Records the client will tune (parameters, crons, sequences, mail
  templates, default groups) ship as XML data; tunables as `noupdate="1"`.
- **No core edits, ever** — not in `odoo/`, not in the enterprise tree, not in vendored OCA.
- **No migration scripts by default.** Prefer additive, nullable fields and computed defaults.
  Migrations are for technical schema transitions only (the policy is owned by `odoo-upgrade`).

## Behaviour

- **Prefer native behaviour plus a helper over an invariant.** A rule that must be enforced at
  every core entry point (create, import, duplicate, RPC, onchange, write) will leak; ask
  whether a default, a helper button or a report achieves the business goal instead.
- **Derive state from native records** (pickings, quality checks, invoices) instead of
  building a parallel workflow engine.
- **Outbound integrations** never call the remote system inside a workflow button; mark the
  record and trigger a cron (the reviewer owns the full pattern).
- **Multi-company from day one**: `company_id` with `check_company=True` on transactional
  models, record rules on `company_ids`, and no hand-written `company_id =` domains (they
  break branch companies).

## Security from day one

- Groups with xmlids, an `ir.model.access.csv` line per model per group, record rules for
  multi-company and ownership, `groups=` on buttons that call restricted methods. A fresh
  install leaves the new groups empty — grant deliberately, as a documented step. Details:
  `odoo-security`.

## Tests from day one

- One `TransactionCase` per `CUSTOM` row proving the gap is closed, plus an access test as a
  user of the intended group. Register every test file in `tests/__init__.py`. Details and the
  non-blocking long-run rule: `odoo-test`.

## Upgrade safety checklist

- [ ] Manifest version written in full (`19.0.1.0.0`).
- [ ] No reference to a model/field the next version removes (see
      [standard-module-map.md](standard-module-map.md)).
- [ ] View inheritance by xmlid + XPath, no full-arch replacement.
- [ ] Every override calls `super()`.
- [ ] Fields used in `invisible=` / `readonly=` are present in the same view.

Then hand off to `/odoo:scaffold <module_name>` with the verdict table in the conversation.
