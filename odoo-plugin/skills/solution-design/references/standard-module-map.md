# Standard apps per business process — starting points, not answers

Use this to know **where to grep first**. It is not evidence: confirm every row in the target
version's source tree (`file:line`) before it enters a verdict table. `EE` = Enterprise only.

## Process → standard apps

| Business process | Start with (technical names) | Typical configuration lever |
|---|---|---|
| Purchasing, RFQ, vendor bills | `purchase`, `purchase_stock`, `account` | Purchase settings: 3-way match (`account_3way_match` EE), approvals by amount |
| Calls for tender / blanket orders | `purchase_requisition` | Agreement types |
| Receiving, putaway, multi-step | `stock` | Warehouse → Incoming 1/2/3 steps, putaway rules, storage categories |
| Delivery, pick-pack-ship | `stock`, `delivery` | Warehouse → Outgoing steps, routes, carriers |
| Dropship | `stock_dropshipping` | Route on product / sale line |
| Subcontracting | `mrp_subcontracting` | BoM type "Subcontracting" |
| Manufacturing | `mrp`; `mrp_workorder` (EE, tablet/work orders); `mrp_plm` (EE, engineering change) | Work centers, operations, routes "Manufacture" |
| Quality control | `quality`, `quality_control` (EE) | Quality points per operation type / product |
| Maintenance | `maintenance` | Equipment categories, preventive frequency |
| Repairs | `repair` | Repair operation type |
| Barcode warehouse operations | `stock_barcode` (EE) | Operation types, GS1 nomenclature |
| Retail shop | `point_of_sale`, `pos_restaurant` | PoS config per shop: operation type, source location, payment methods |
| E-commerce | `website_sale`, `website_sale_stock` | Website warehouse, stock display |
| Sales, quotations | `sale`, `sale_management`, `sale_stock` | Quotation templates, pricelists, "Lock Confirmed Sales" |
| Rental | `sale_renting` (EE) | Rental periods/prices on product |
| Subscriptions | `sale_subscription` (EE) | Recurring plans |
| Services, projects | `project`, `hr_timesheet`, `sale_timesheet` | Invoicing policy on service products |
| Field service | `industry_fsm` (EE) | Worksheet templates |
| Helpdesk | `helpdesk` (EE) | Teams, SLA policies |
| Planning / shifts | `planning` (EE) | Roles, templates |
| Approvals | `approvals` (EE) | Approval categories |
| Documents, signatures | `documents`, `sign` (EE) | Workspaces, templates |
| Expenses | `hr_expense` | Expense products; v19 has no expense *sheet* |
| Fleet | `fleet` | — |
| Events | `event`, `website_event` | Event templates |
| Accounting | `account` (CE invoicing), `account_accountant` (EE full accounting) | Fiscal positions, journals, analytic plans |
| Multi-branch | native child `res.company` (branches share the parent's chart) | Company hierarchy |
| Packaging units | 17/18: `product.packaging`; 19+: hierarchical `uom.uom` | Units on product |

Enterprise addons sit at the root of the enterprise repository (no `addons/` folder):
`ls $ODOO_SOURCES/<ver>/odoo-ee/<module>/__manifest__.py`.

## Removed or renamed — grep before you design on it

| Version | Gone / renamed | Use instead |
|---|---|---|
| 19.0 | `product.packaging` model | hierarchical units of measure (`uom.uom` with a relative unit) |
| 19.0 | `uom.category` | units grouped by their reference unit |
| 19.0 | `hr.expense.sheet` | expenses reported directly (`hr.expense`) — OCA modules built on sheets are dead |
| 19.0 | `stock.quant.package` | `stock.package` |
| 19.0 | `res.users.groups_id` | `group_ids` (direct groups) / `all_group_ids` (effective, incl. implied) |
| 19.0 | `stock.valuation.layer` | value carried on the stock move |
| 18.0 | `<tree>` view tag | `<list>` |
| 17.0 | `attrs=` / `states=` in views | inline `invisible=` / `readonly=` / `required=` expressions |

The full per-version deltas are owned by `odoo-upgrade` (`skills/upgrade/`) and the reviewer's
`v19_deltas.md` / `v20_deltas.md`; this table only lists what most often changes a design.

Quick existence check for a model in a version:

```bash
grep -rln "_name = ['\"]product.packaging['\"]" $ODOO_SOURCES/19.0/odoo-ce/addons $ODOO_SOURCES/19.0/odoo-ee || echo "absent in 19.0"
```
