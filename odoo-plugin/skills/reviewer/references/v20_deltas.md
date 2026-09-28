# Odoo 20 deltas (reviewer reference)

What changes for a reviewer on **20.0 / master**, in the same spirit as `v19_deltas.md`.

**Provenance.**
- Access model: verified against the 20.0 source (`odoo/addons/base/models/ir_access.py`,
  `odoo/addons/base/security/ir.access.csv`; `ir_rule.py` and `IrModelAccess` are gone).
- Everything else comes from Odoo's own `skills/` on 20.0. On a 20.0 project, prefer those
  skills (`/official-skills`) and treat this file as the fallback.

**Before applying anything here, confirm the project is on 20.** Every row is wrong for
14–19.

## Access control: `ir.access` replaces `ir.model.access` and `ir.rule`

One model now holds both the group grants and the record-level domains.

| Field | Meaning |
|---|---|
| `model_id` | The model |
| `group_id` | The group. Set means a **permission** row (adds access); empty means a **restriction** row (limits everyone) |
| `operation` | A subset of `crud`: `r`, `ru`, `cru`, `crud`, ... |
| `domain` | Optional. The operations apply only to records in this domain |

Security CSV: `security/ir.access.csv` with the header
`id,name,model_id,group_id/id,operation,domain`. `model_id` is the model name, for
example `sale.order`, not `model_sale_order`. There is no `ir.model.access.csv`.

Review rules:
- Restrictions are evaluated per operation. A restriction declared for `r` says nothing
  about `u`, so updates are decided by the permission rows with no domain at all. A
  group that may update can therefore edit records it cannot even read. Give the
  restriction every operation it is meant to limit (`ru`, `crud`, ...).
- Flag `c`/`u`/`d` granted to `base.group_portal`, `base.group_public` or
  `base.group_everyone`. Scrutinise even `r` on personal or business-sensitive models.
- Multi-company models need a company restriction row, not only group permissions.
- Migrating a 19 module: every `ir.model.access.csv` row plus every `ir.rule` becomes
  `ir.access` rows. A dropped rule is a silent widening, so diff the effective access
  before and after.

## ORM

- **`_sql_constraints` is ignored with a warning.** The constraint is never created.
  Declare `models.Constraint(...)`, `models.Index(...)` and `models.UniqueIndex(...)` as
  `_`-prefixed class attributes. These exist since 19.0 (`v19_deltas.md`); on 20 the old
  form no longer works at all.
- Compose domains with `odoo.fields.Domain` (`&`, `|`, `~`, `Domain.AND` / `Domain.OR`,
  available since 19.0). Hand-built `'&'` / `'|'` prefix lists are review findings, and
  concatenating a request-provided list onto a security domain is an injection.

## QWeb / templates

- `t-raw` and `t-esc` are gone from server QWeb and OWL. `t-out` is the only output
  directive. A leftover server-side `t-esc` renders nothing, so it is a functional bug.
  The raw-HTML vector is a `Markup` / `markup()` value reaching `t-out`.

## Unchanged, still load-bearing

These carry over from 17.0+ (see `security_pitfalls.md`):
- `@api.private`
- `related_sudo`
- `_allow_sudo_commands`
- `file_open`
- `consteq`
- `SQL.identifier`
- the rule that any public method can be called over RPC
