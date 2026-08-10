# Destructive & CASCADE checks — before any delete/drop

Run this review before the cutover step and before any migration that deletes, drops, truncates, or overwrites. The two failure modes that bite hardest are the **soft-delete bypass** and the **unreviewed cascade FK**.

## The soft-delete bypass trap

Teams often add a soft-delete (a flag/timestamp instead of a real delete) and then assume data is protected. **An instance-level soft-delete override does NOT protect bulk / admin / QuerySet / cascade deletes.**

### Which delete paths bypass an instance-level override

| Delete path | Bypasses instance-level soft-delete? | Why |
|---|---|---|
| Single-record delete through the model instance | No (override runs) | the override is on the instance method |
| Bulk / set-level / QuerySet delete | **Yes** | operates on the set, never instantiates each row |
| Admin "delete selected" bulk action | **Yes** | uses the bulk/set path |
| Raw SQL / direct database delete | **Yes** | never touches the ORM at all |
| Cascade delete from a parent row | **Yes** | the database removes children directly |

### What to confirm (`soft_delete_convention`)

1. **At which layer does the soft-delete live?** Instance method only, or also the manager/QuerySet/set layer (and a default manager that filters out soft-deleted rows)?
2. If it is **instance-only**, treat every bulk/admin/raw/cascade path as a **hard delete** of supposedly-protected data — that is a blocking finding for any migration or admin flow that uses those paths.
3. The robust pattern is to enforce soft-delete (or a delete *guard*) at the manager/QuerySet layer too, or to block bulk hard-deletes on protected models — but this skill's job is to **flag the gap**, not silently rely on the override.

## Cascade-FK audit

Inventory every foreign key whose `ON DELETE` is `CASCADE` and trace what deleting a parent row removes.

### The dangerous shape

A `CASCADE` foreign key that points at — or transitively reaches — a **financial, audit, or historical** table means a routine parent delete can silently erase records that must be retained (invoices, ledger entries, audit logs, immutable history). This is the highest-severity finding in a destructive review.

### The audit procedure

1. List all FKs with `ON DELETE CASCADE`.
2. For each, identify the child table and ask: is it (or anything it cascades into) a **retain-forever** table — money, audit, legal, or historical record?
3. For every cascade that reaches a retain-forever table, the finding is **deploy-blocking** until reviewed. Prefer:
   - `ON DELETE RESTRICT` / `NO ACTION` — block the parent delete while children exist (safest for financial/audit).
   - `ON DELETE SET NULL` — orphan the child but **retain** the record (when the relationship is optional).
   - `CASCADE` only when the child genuinely has no independent retention value.
4. Watch for **cascade chains**: A cascades to B, B cascades to C. Trace the full chain, not just the first hop.

### Reporting format

```
cascade FK review:
  <child_table>.<fk> -> ON DELETE CASCADE  (parent: <parent_table>)
     reaches retain-forever? <yes: audit/financial/historical | no>
     recommendation: <RESTRICT | SET NULL | ok-as-cascade>  [BLOCKING if reaches retain]
```

## One gate must not answer two questions with opposite costs

A cutover that rebuilds a new artifact, verifies it, then removes the old one tends to grow a **single** predicate — a `validate()` / `is_ready()` / verification helper — that ends up answering two different questions:

- *"Is the new artifact complete enough to serve?"* — being wrong costs the **service**. This wants to **fail open**.
- *"Is it verified well enough that the old one may be deleted?"* — being wrong costs the **data**. This wants to **fail closed**.

Those biases are opposite and one predicate can only carry one of them. Sharing it forces the conservative bias onto both, so a purely **diagnostic** mismatch — a row/document count that does not line up, a sampler that cannot read one shard — disables the working product indefinitely without bringing the delete decision any closer. Wiring it the other way is worse: the permissive bias then authorises the destructive step.

**Rule:** split the predicate. Compute the availability decision and the destructive decision separately, each from the evidence it actually needs, and allow them to disagree — *"serving from the new artifact, old artifact retained"* is a legitimate state to sit in indefinitely, and it is the state a half-verified cutover should land in.

**The question to ask of every check in a cutover:** *if this check is wrong, do I lose data or do I lose the service?* If both answers show up under one condition, that is the bug. Where a single check genuinely cannot be split, bias it toward the **recoverable** error: a wrong "not ready yet" is retried and self-corrects, a wrong "verified — delete it" has no recovery.

## Pre-destructive gate (checklist)

- [ ] Every `DROP` / `DELETE` / `TRUNCATE` in this change enumerated.
- [ ] Soft-delete layer identified; bulk/admin/raw/cascade paths classified as protected or NOT.
- [ ] All `ON DELETE CASCADE` FKs inventoried, including cascade chains.
- [ ] No cascade reaches a financial/audit/historical table unreviewed (else BLOCKING).
- [ ] A timestamped, restorable backup exists (see `cutover-skeleton.md`) before any destructive step.
- [ ] The predicate authorising the destructive step is separate from any predicate deciding availability; each was asked "if this is wrong, do I lose data or the service?"
- [ ] Old artifacts will be archived by rename, not dropped, in this change.

## Platform note (labeled examples only)

> Example (illustrative — not required): in one ORM a model's instance `delete()` is overridden to set a `deleted_at` timestamp, but the framework's bulk/set delete and its admin bulk action call the set-level delete that never runs that override — so "delete selected" hard-deletes rows the team believed were soft-deletable. The bypass set (bulk / admin / raw / cascade) is the same idea across ORMs; only the method and manager names differ.
