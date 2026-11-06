# Integration patterns: external calls, crons, company scoping, overrides

Review-time rules for code that talks to other systems, runs in crons, scopes by company, or
extends a method another module owns. Each rule is one mechanism and one check. Baseline Odoo 17;
version notes are inline.

## Outbound sync on a workflow action: mark, then trigger a cron

Do not call a remote system inside `button_validate` (or any workflow button). It runs in the
user's transaction, so a later rollback leaves an orphan remote record; a network outage blocks
the click; and `button_validate` can return the backorder wizard and be re-entered.

- Mark the record and call `self.env.ref('<module>.<cron_xmlid>')._trigger()`. The trigger row is
  transactional, so a rollback cancels it; the cron reads only committed records, retries on its
  interval and never runs concurrently with itself.
- Make the push idempotent: store the remote id on the source record **and** look the record up on
  the remote side by origin or marker before creating, so a re-run never duplicates.
- Read endpoint and credentials from `ir.config_parameter`, so the sync is off until configured.
  Ship the cron inactive and add a neutralize step that clears the endpoint on staging copies.
- Enforce "field X required before validate" server-side in the action, not only in the view.
- Severity: a remote call inside the user's transaction = MAJOR (BLOCKER if it creates money or
  stock documents remotely).

## A cron loop that catches exceptions needs a savepoint per record

A cron that loops records and catches `UserError` (or any exception) to continue keeps the partial
writes of the failed record, and they commit with the batch. Wrap each iteration in
`with self.env.cr.savepoint():`, keep batches bounded (Postgres slows past about 64 savepoints per
transaction, see `v19_deltas.md`), and log the failed id.

## `check_company=True` ANDs with the field's own `domain=` (17+)

`check_company=True` does not replace an explicit `domain=`; the two are concatenated, so a
hand-written `[('company_id', '=', company_id)]` can only narrow the generated domain.

- Odoo 17 branch companies share the parent's chart of accounts and journals: core sets
  `_check_company_domain = models.check_company_domain_parent_of` on `account.account` and
  `account.journal`. A strict `company_id =` clause therefore shows a branch **zero** accounts or
  journals.
- The fix is to **delete** the company clause and let `check_company=True` supply it; do not
  rewrite it as `parent_of` by hand (a redundant clause, worse in a vendored module).
- The default `BaseModel._check_company_domain` is self-only. A custom model whose records a branch
  should see from its root needs `_check_company_domain = models.check_company_domain_parent_of`;
  that is a product decision, not a bug fix.
- A `domain=` on a `readonly=True` field is dead even in an editable list: changing it fixes nothing.

## Form helper fields: compute + `readonly=False`, no inverse

Friendly helper fields that resolve a technical field (pick a "screen" and "type" to set a
`view_id`) should be computed, `readonly=False`, non-stored, and drive the real field from an
`@api.onchange`. **Do not give them an `inverse`**: on save the inverse re-resolves the real field
from the helpers and overwrites a value the user set by hand. Without an inverse, the ORM caches and
drops the helper value, which is the wanted behaviour.

- Clearing the real field recomputes the helpers to empty (they depend on it): re-assign them in
  the same onchange, or the user is stranded with an unfillable required field.
- Never assign a Selection helper a value outside its own list (`convert_to_cache` raises
  `ValueError`, a traceback instead of a readable error); guard the compute.

## Terminal overrides are closed extension points

A layer that overrides a method without calling `super()` replaces every lower implementation, and
anything meant to extend that method must load above it, or its override silently never runs.

- Before extending a method another module already overrides, `grep -n "super(" <that module>` for
  that method. If it has none, declare an explicit `depends` on that module so load order is a
  contract, not an accident.
- Flag a terminal override itself as MAJOR unless its docstring states why it must replace the
  chain.

## A missing `depends` that a full local install hides

A module that uses another module's model without depending on it installs fine wherever the other
module happens to be installed, and fails with `unknown comodel_name` (or a view validation error)
on the first clean build. Before promoting, install every custom and vendored module together on a
fresh database, and install each module alone with only its declared dependency cone.

## Image conversion needs the Pillow plugins Odoo does not register

Odoo calls `Image.preinit()`, which registers only the common formats, so `image.save(fmt='WEBP')`
(and TIFF) fails inside Odoo even though it works in a plain Python shell. Import
`PIL.WebPImagePlugin` / `PIL.TiffImagePlugin` explicitly in conversion code, verify inside
`odoo-bin shell`, and log a failed conversion at WARNING instead of storing the original silently.
