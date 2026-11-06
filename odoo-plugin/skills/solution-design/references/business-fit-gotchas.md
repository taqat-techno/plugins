# Business-fit gotchas — native mechanics that decide fit

Each of these changed a verdict in a real design. Check the ones that touch your process steps
in the target version's source before you write `STANDARD`, `CONFIG` or `CUSTOM`.

## Reading the source correctly

- **Field-level constraints decide fit.** Before mapping a business concept onto a native
  field, read `required`, `store`, `compute` and any `_should_*` / `_get_*` filter, and quote
  `file:line`. Examples of constraints that ruled a fit out: quant `owner_id` stock is excluded
  from valuation; a quality point's operation types are required; loyalty programs refuse a
  third-party payer; a stock rule's destination location is static.
- **Read the edition-correct tree.** Community has roughly half the addons Enterprise has. A
  gap audit against Community over-reports custom work. Label conclusions `EE-conditional`.
- **Classify a mystery constant before "creating the missing record".** If code references an
  xmlid/code nobody can find, grep custom and core, query every database including pristine
  restores, and check the localization chart. Absent everywhere means a code defect, not
  missing data.
- **Keep current state apart from target state.** A requirement is not refuted because staging
  lacks it.

## Stock and warehouse

- **Products default to Consumable in Odoo 17.** No quants are created, and the type locks
  after the first done move. Every loader/import must set storable (`detailed_type='product'`
  in 17; `type` + `is_storable` in 18+).
- **Website stock is per warehouse.** There is no core "website location" field. Answer the
  website and POS questions separately. Options, cheapest first: a dedicated warehouse (a
  warehouse is only a container label — re-parent the location), the whole warehouse, or a
  small module.
- **POS stock source is configuration**: `pos.config.picking_type_id.default_location_src_id`.
  A new warehouse auto-creates its PoS operation type and auto-enables multi-warehouse, so
  per-shop isolation needs no code. Stock moves at payment or at session closing depending on
  the company setting.
- **Reservation includes child locations** of the source; hand-typed MO component quantities
  don't reserve; a sibling source location reserves nothing.
- **Chained routes**: with pick→ship, the ship move is created only when the pick is validated;
  a chained ship reserves only from its origin move; returning more than was issued is allowed;
  serial-number restrictions beyond core are custom.
- **`stock.quant` import**: create lots first; the importable columns are a strict whitelist
  (`_get_inventory_fields_create`); `inventory_quantity_auto_apply` skips the tracking wizards;
  split sheets by tracking mode (none / lot / serial).
- **Company of stock/POS records is immutable**: warehouse, location and operation-type
  `company_id` cannot change; a `pos.session` cannot be deleted over the API; multi-company
  rules hide records even from admin. Confirm before any company-merge plan.
- **Warehouse install hooks** that create operation types must write each `*_pull_id`
  pointer exactly once; every re-blank orphans an active rule and `_search_rule` picks the
  oldest. Assert one active rule per source→destination.

## Sales and POS

- **pos_sale and settled orders**: editing a settled, POS-linked sale order creates a delivery
  nothing cancels when "Lock Confirmed Sales" is off. Configuration, not code.
- **Settings that won't save** because another installed app marks a settings field required
  unconditionally: look for a missing per-company `ir.default` before writing code.

## Companies and accounting

- **Branch companies (17+) use the parent's chart of accounts and journals**
  (`check_company_domain_parent_of`). Hand-written `company_id =` domains break branches; the
  reviewer owns the code rule.
- **Installing Invoicing on a fresh 19 database loads a chart that can switch the company
  currency.** Set the company country/currency before installing accounting apps.

## Notifications

- **Auto-installed bridges**: installing sale/stock/account can auto-install SMS/WhatsApp
  bridges whose sending gates are already open. After any module-set change, list newly
  auto-installed modules and audit the company notification toggles.
