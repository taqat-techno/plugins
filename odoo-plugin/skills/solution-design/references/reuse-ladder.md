# The reuse ladder — rules, override criteria and evidence

Read this when you are about to skip a rung, accept an OCA/Apps module, or justify custom code.

## The ladder

1. **Standard** (target version; Community, then Enterprise if licensed).
2. **Configuration** of standard — settings, routes/rules, operation types, groups, record
   rules, automated actions, server actions, mail templates, standard report layouts.
3. **OCA** module on the version branch, after the behaviour check.
4. **Odoo Apps store** module for the version, licence and quality recorded.
5. **Custom** — only the residual gap, extending the models found above.

Classify each process step as *configuration*, *data migration* or *custom development*.
Normal configuration is not "development" — never estimate it as such.

## When a rung may be skipped (write the reason in the verdict table)

| Skip | Valid reason | Not a valid reason |
|---|---|---|
| Standard → custom | The standard field/model has a constraint that contradicts the requirement (quote it: `required=True`, static `location_dest_id`, excluded from valuation…) | "Users find the standard screen confusing" (that is training or a view tweak) |
| OCA → custom | No module on the version branch; module is Alpha/unmaintained for the version; it swallows core exceptions or is inert under tests; its semantics differ (e.g. its quantity includes incoming stock) | "We don't like dependencies" |
| OCA → Apps | Licence fits, the author maintains the version, code reviewed | Price alone |
| Any → custom | A conflict with an already installed module, proven on a scratch DB | A guess |

A requirement with a corner case may override the ladder, but only with that written reason.

## Behaviour check for any OCA/Apps candidate

An OCA module counts as reuse only after it passes a fit **and** behaviour check against the
core call sites it hooks:

- Does core catch and swallow the exception it raises (e.g. POS order sync catches errors, so
  a "no negative stock" check silently desyncs stock instead of blocking)?
- Is it disabled under `--test-enable` or by a context key, so your tests prove nothing?
- Does it change semantics the requirement depends on (quantity definitions, reservation)?
- Does it patch `create`/`write` at load time in a way later overrides skip?
- Does a one-line fix make it fit (then it is still `OCA`, with the patch recorded and pushed
  upstream), or does it need a rewrite (then reimplement the small part you need)?

If the evaluation says reject, do not vendor it "for now". A rejected module that ships anyway
becomes the system's least understood dependency.

## Evidence cases (generic)

1. **A hard invariant fought core entry points.** "Every POS product must have a barcode" needed
   a separate patch for template create, variant create, import, duplicate, RPC and single-field
   write, and each patch produced a follow-up defect. It was retired back to native behaviour
   (barcode optional, sell by tap or search) and the guard tests deleted; the barcode generator
   was kept as a helper. **Prefer native behaviour plus an optional helper over an invariant
   that must guard every entry point.**
2. **A port removed an OCA stack.** On a version port, tier-validation modules and a role
   module were replaced by native groups and privileges (one job-role selector implying
   capability groups). Only two OCA modules survived. **Re-run the ladder on every port: the
   new version may cover what OCA did.**
3. **A version upgrade erased a planned module.** Odoo 19's hierarchical units of measure
   express "a box contains N units" with zero custom code; a planned packaging module was
   dropped. Conversely, OCA expense modules shortlisted for 19 were dead on arrival because
   `hr.expense.sheet` no longer exists. **Grep the target tree before shortlisting.**
4. **Reading the edition-correct tree cut custom scope in half.** A gap estimate fell from ~46%
   custom to ~20% once the Enterprise source was read (rental serial overlap, quality photo
   checks already existed).
5. **A native widget option already did it.** Hover zoom on images was built as a custom web
   module although the standard image widget supports `options="{'zoom': true, 'zoom_delay':
   300}"`. **Check the native widget/field options before any frontend module.**
6. **A vendored module against its own evaluation.** An OCA "no negative stock" module was
   rejected in evaluation (core POS swallows its error; inert under tests) and vendored anyway;
   the stock desync it was meant to stop kept happening.
7. **"Sell only from location X" on the website** had no OCA module; the answer was standard,
   no code: a dedicated warehouse whose stock location is the re-parented location. POS stock
   source is configuration (`picking_type_id.default_location_src_id`).
8. **Per-POS warehouse isolation was configuration only** — a new warehouse auto-creates its
   PoS operation type; no routes and no module were needed.
9. **Stray deliveries were a setting.** Editing a settled POS-linked sale order created a
   delivery nothing cancelled; the cause was "Lock Confirmed Sales" switched off.
10. **A justified custom module.** Restricting manufacturing users to their work centers: no
    standard ACL, OCA `manufacture` checked on the version branch (none fits; the warehouse
    security module is Alpha and warehouse-level only). A custom module depending only on
    `mrp`/`mrp_workorder` with one record rule was the right answer — with the verdict table
    to prove it.
11. **Clean reset over a heavy rename.** A misnamed custom module with no production data was
    uninstalled and rebuilt instead of carrying a multi-part rename and migration.
12. **A real uninstall over a code patch.** An orphaned Community-only module stuck in the
    database was resolved by a proper Odoo uninstall, not a code or SQL hack.
13. **Branches as native child companies.** A warehouse-as-branch plus analytic-plan design was
    retired for native parent/child companies (shared chart, native per-branch P&L).
14. **State derived from native records.** A custom step/template/approval engine was removed;
    the business object now derives its state from native pickings and quality checks.
