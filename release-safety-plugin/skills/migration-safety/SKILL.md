---
name: migration-safety
description: Runs risky migrations and cutovers through a fixed safe skeleton — read-only discovery of both sides, then timestamped backups, then build+validate in a staging copy, then additive-then-cutover-last, then archive old artifacts by rename (never delete). Owns destructive/CASCADE review (a soft-delete instance override does NOT protect bulk / admin / QuerySet deletes; audit cascade FKs that point at financial / audit / historical tables and prefer restrict / set-null) and migration DRIFT detection before deploy (un-applied, out-of-order, or model-vs-schema changes with no migration). Provider-neutral across any database, ORM, and migration tool. Activates when someone asks to run a migration safely, cut over a table / database / queue / index, or check whether a migration is destructive before deploy.
version: 0.1.0
last_reviewed: 2026-06-13
owns:
  - the risky-migration / cutover skeleton (discover -> backup -> stage -> additive-then-cutover -> archive)
  - the additive-then-cutover-last ordering rule (expand / contract)
  - destructive & CASCADE review (bulk-delete bypass of soft-delete, cascade-FK audit)
  - archive-by-rename-never-delete discipline
  - migration DRIFT detection before deploy
  - the MIGRATION SAFETY REPORT output contract
defers_to:
  - release-verification skill for proving the post-migration deploy reached the target environment
  - references/cutover-skeleton.md for the step-by-step expand/contract runbook
  - references/destructive-checks.md for the cascade-FK and bulk-delete audit procedure
  - the project's ORM / migration tool for the concrete generate / apply / status commands
user_invocable: false
---

# migration-safety

## Purpose

A risky migration or cutover fails safely or it fails catastrophically, and the difference is almost entirely *ordering and reversibility*. This skill encodes one fixed skeleton — discover read-only, back up, validate in a staging copy, apply additively with the destructive cutover LAST, archive old artifacts by rename — plus the destructive/CASCADE review that stops a "small" migration from silently dropping financial or audit history.

## When to use

Activate when any of these appear:

- "Run this migration safely", "apply the schema change", "cut over the table / database / queue / index."
- "Is this migration destructive?", "will this drop data?", "what does this CASCADE touch?"
- Renaming / merging / splitting a table or column, backfilling, or swapping a live resource.
- Before a deploy, to confirm there is no migration **drift** (un-applied or out-of-order migrations, or model/schema changes with no migration).
- Any change where rolling back after the fact would be hard or impossible.

Do NOT activate to prove the post-migration code reached the target environment — that is the **release-verification** skill.

## Inputs (adapter)

Every project-specific value is a named adapter input. Nothing below is hardcoded to a vendor.

1. **`db_engine` / `orm` / `migration_tool`** — discovered from the project (dependency manifest, migration folder, config). Selects the concrete generate / status / apply commands.
2. **`source_side` / `target_side`** — the two ends of the change (e.g. current schema vs. desired schema, old resource vs. new resource).
3. **`backup_mechanism`** — how this engine takes a restorable snapshot (dump, snapshot, copy). Discovered, not assumed.
4. **`staging_copy_location`** — where a throwaway copy can be built and validated without touching the live side.
5. **`soft_delete_convention`** — whether the model layer has a soft-delete override, and at which layer (instance vs. manager/QuerySet) — because the override's *layer* decides what it protects.
6. **`cascade_fk_inventory`** — the foreign keys with `ON DELETE` behaviour, especially any pointing at financial / audit / historical tables.

If an adapter value is unknown, the first step is to discover it read-only, never to assume it.

## The safe skeleton (run in this order — never reorder)

```
1. DISCOVER (read-only, BOTH sides)   -> what exists now vs. what is desired; diff; drift check
2. BACKUP (timestamped)               -> restorable snapshot of the live side BEFORE any change
3. STAGE (build + validate copy)      -> apply the migration to a throwaway copy; prove it succeeds
4. ADDITIVE FIRST                     -> add new columns/tables/indexes (nullable/defaulted), backfill, dual-write
   ... verify ...
5. CUTOVER LAST                       -> flip reads/writes to the new shape; the destructive step is the FINAL one
6. ARCHIVE by RENAME (never delete)   -> rename old artifacts aside (e.g. *_archived_<timestamp>); keep, do not drop
```

Each step gates the next. Never run the destructive cutover before the additive phase is verified, and never delete an old artifact when a rename preserves a rollback path.

### Why additive-then-cutover-last (expand / contract)

Additive changes are reversible and let old and new code coexist; destructive changes are not. By doing all additive work first, validating, and only then cutting over — with the drop/rename of the old shape as the very last step — you keep a working rollback target at every intermediate point. This is the expand/contract pattern; see `references/cutover-skeleton.md`.

## Destructive & CASCADE review (mandatory before any delete/drop)

### The soft-delete bypass trap

A **soft-delete override implemented at the instance level does NOT protect bulk / admin / QuerySet deletes.** Instance-level `delete()` overrides are skipped by:

- bulk / QuerySet deletes that operate at the set level,
- admin "delete selected" bulk actions,
- raw or direct database deletes,
- cascade deletes triggered by deleting a parent row.

So data you believe is "soft-deletable" can be hard-deleted through any of those paths. Confirm at which layer the soft-delete lives (`soft_delete_convention`) and treat instance-only overrides as **not** protecting bulk operations. See `references/destructive-checks.md`.

### Cascade-FK audit

Inventory every foreign key with a cascade `ON DELETE` and trace what deleting a parent row would remove. **Cascade FKs that point at financial, audit, or historical tables are the dangerous ones** — a routine parent delete can silently erase records that must be retained. Prefer `RESTRICT` (block the delete) or `SET NULL` (orphan, but retain) for those relationships rather than `CASCADE`. Flag any `CASCADE` reaching a retain-forever table as deploy-blocking until reviewed.

## Migration drift detection (before deploy)

Before promoting, confirm there is no drift:

- **Un-applied migrations** — migration files exist that the target has not applied.
- **Out-of-order / divergent history** — migrations applied in a different order than recorded, or branched migration history.
- **Model-vs-schema gap** — model/entity changes exist with no corresponding migration generated (the tell-tale "you have un-migrated changes" signal from the migration tool).

Drift is a deploy-blocking finding: resolve it (generate the missing migration, reconcile history) before promotion, not after. Use the migration tool's own status/check command for the engine in use.

## Safety gates

- **Never** reorder the skeleton: discover -> backup -> stage -> additive -> cutover -> archive.
- **Never** run a destructive step (drop/delete/truncate/overwrite) before the additive phase is verified in a staging copy.
- **Never** delete an old artifact when a rename preserves a rollback path — archive by rename with a timestamp.
- **Never** trust an instance-level soft-delete to protect bulk / admin / QuerySet / cascade deletes.
- **Never** ship a `CASCADE` that reaches a financial / audit / historical table without explicit review; prefer `RESTRICT` / `SET NULL`.
- **Never** promote with migration drift unresolved.
- **Never** take the migration as "done" until restore from the backup has been at least dry-checked.
- **Never** assume the engine / ORM / backup mechanism — discover each read-only.

## Validation checklist

- [ ] Both sides discovered read-only; source vs. desired diff produced.
- [ ] Migration drift check run (un-applied / out-of-order / model-vs-schema) — clean or resolved.
- [ ] Timestamped, restorable backup taken before any change; restore dry-checked.
- [ ] Migration applied and validated in a staging copy first.
- [ ] Additive changes applied and verified before any destructive cutover.
- [ ] Destructive step is the LAST step; old artifacts archived by rename, not deleted.
- [ ] Soft-delete layer confirmed; bulk/admin/QuerySet/cascade delete paths reviewed.
- [ ] Cascade FKs audited; none CASCADE into financial/audit/historical tables unreviewed.
- [ ] "Not done or blocked" lists anything skipped and why.

## Output format

The skill emits exactly one block:

```
MIGRATION SAFETY REPORT
  Change:             <what is migrating / cutting over>
  Engine / tool:      <db_engine> / <orm-or-migration-tool>   (discovered)
  Drift check:        <clean | DRIFT: un-applied=<n>, out-of-order=<y/n>, model-vs-schema=<y/n>>
  Backup:             <mechanism> @ <timestamp>   restore-dry-check=<ok|not-done>
  Staging validation: <passed | failed | not-done>
  Plan ordering:      additive=[...]  cutover(destructive)=[...]  archive(rename)=[...]
  Destructive review:
                      soft-delete layer=<instance|manager/QuerySet|none>  bulk-delete-protected=<yes|no>
                      cascade FKs into retain-forever tables=[<fk: table -> ON DELETE ...>]
  Verdict:            <SAFE TO PROCEED | BLOCKED: reason>
  Safe next action:   <single explicit step for the USER>
  Not done or blocked:
                      - <what was skipped and why>
```

## Anti-patterns

| Anti-pattern | Why it is wrong | Correct |
|---|---|---|
| Drop the old column in the same migration that adds the new one | No rollback target if the cutover misbehaves | Additive first, verify, drop/rename LAST (expand/contract) |
| `DELETE FROM ...` / bulk QuerySet delete, trusting soft-delete | Instance-level soft-delete is bypassed by bulk/admin/cascade | Confirm the soft-delete layer; treat bulk paths as hard deletes |
| `ON DELETE CASCADE` toward an audit/financial table | A routine parent delete silently erases retained records | Use RESTRICT / SET NULL; review every cascade into retain tables |
| Delete the old table after cutover | Throws away the rollback path | Rename to `*_archived_<timestamp>`; keep it |
| Apply straight to the live side | No proof the migration even succeeds | Validate in a staging copy first |
| Promote with un-migrated model changes | CI/runtime drift; schema diverges from code | Run the drift check; generate the missing migration first |
| Skip the backup because "it's a small change" | Small destructive changes still destroy | Always take a timestamped, restorable backup |

## Portability rationale

The skeleton, the expand/contract ordering, the destructive/CASCADE review, and the report contract describe *how to reason*, not *which engine to call*. The database, ORM, migration tool, and backup mechanism are adapter inputs discovered at run time; the concrete generate / status / apply / dump commands live in the reference docs. Supporting a new engine means adding command variants to a reference doc, not changing this skill.

## Cross-references

- `references/cutover-skeleton.md` — the step-by-step expand/contract runbook with provider-neutral command slots.
- `references/destructive-checks.md` — the soft-delete-layer audit, the bulk-delete bypass paths, and the cascade-FK inventory procedure.
- `release-verification` (skill) — after the migration, prove the deploy actually reached the target environment.
- `release-verify` (command) — user entry point; routes the migration/cutover and drift items to this skill.
