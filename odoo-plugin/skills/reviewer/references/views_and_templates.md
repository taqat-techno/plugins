# Views, buttons and templates: review traps that pass a full install

Rules for backend views, form buttons and portal/website QWeb that look correct and fail for a
specific user, a specific install set, or a specific value. Baseline Odoo 17.

## View modifiers must contain the fields they reference

Every field used in `invisible=`, `readonly=`, `required=` or `column_invisible=` must be present
in the same combined view (add `<field name="x" invisible="1"/>`). Odoo 17+ validates this at load
time. A sibling module that injects the field can hide the gap on full installs, so the view
breaks only when the module is installed in its own dependency cone. Fix it in the view itself, not
by adding a dependency; check by installing the module alone.

## Buttons need `groups` that match the method's access rights

A `<button type="object">` without `groups` is shown to everyone who can open the form, and the
method runs as the clicking user: users without write ACL get a raw `AccessError`. Set `groups` to
the groups that hold the needed rights, or check up front and raise a readable `UserError`.

Two related form defects to flag in the same pass:

- A model with no `name`, `_rec_name` or `_compute_display_name` titles its records "model.name,ID".
  Give transactional models a display name.
- A one2many whose comodel has no form view opens an auto-generated form listing every field,
  internal ones included. Ship a form view (or `editable` list) for every comodel users can open.

## `_rec_names_search` does not change list-view search

`_rec_names_search` affects `name_search` only, i.e. many2one dropdowns. A search view builds its
domain from its own `<field>` elements and never calls `name_search`. To make list search match
another column, inherit the search view and set
`filter_domain="['|', ('name', 'ilike', self), ('barcode', 'ilike', self)]"` on the field.

## Portal and website QWeb

- **Datetimes from a dict print in UTC.** A controller that builds `{'date': record.date}` and a
  template that prints it with `t-out` show the raw UTC value. Use
  `t-options="{'widget': 'datetime'}"`, or `t-field` on the record, so it renders in the user's
  timezone.
- **Do not gate controls on a quantity's truthiness.** `-1.0` is truthy, so `disabled` when
  `line['qty_open']` is set misfires once the value goes negative, and a disabled button sends
  nothing, so the user is silently stuck. Compare explicitly (`> 0`, `!= 0`), decide the over-count
  behaviour, and show why a control is blocked.
- **HTML `max=` / `min=` validate nothing** server-side: the posted value is whatever was typed.
  Enforce bounds in the controller or model.
- Public-page injection sinks (raw `t-att-src`, unsanitized `Html`) are security findings: see
  `security_pitfalls.md` and the security skill.
