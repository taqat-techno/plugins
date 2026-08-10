---
name: migration-safety
description: Runs risky migrations and cutovers through a fixed safe skeleton — read-only discovery of both sides, then timestamped backups, then build+validate in a staging copy, then additive-then-cutover-last, then archive old artifacts by rename (never delete). Owns destructive/CASCADE review (a soft-delete instance override does NOT protect bulk / admin / QuerySet deletes; audit cascade FKs that point at financial / audit / historical tables and prefer restrict / set-null) and migration DRIFT detection before deploy (un-applied, out-of-order, or model-vs-schema changes with no migration). For a cross-system data migration, builds the extractor from the LIVE information_schema (the running database's real columns, types, and constraints), never from committed schema or migration files (e.g. schema.prisma or an ORM model folder) that drift from the database; and warns that a DB dump is NOT a full migration when binary assets live on app-server local disk -- check the Dockerfile VOLUME, container bind-mounts, and the backup job's scope before calling a dump complete. Also detects environment-vs-environment SCHEMA DRIFT -- a constraint, index, or column present in one environment's live schema and missing in another. Provider-neutral across any database, ORM, and migration tool. Activates when someone asks to run a migration safely, cut over a table / database / queue / index, check whether a migration is destructive before deploy, move data between two systems or databases, or reconcile a schema difference between environments.
version: 0.2.0
last_reviewed: 2026-07-23
owns:
  - the risky-migration / cutover skeleton (discover -> backup -> stage -> additive-then-cutover -> archive)
  - the additive-then-cutover-last ordering rule (expand / contract)
  - destructive & CASCADE review (bulk-delete bypass of soft-delete, cascade-FK audit)
  - archive-by-rename-never-delete discipline
  - the one-gate-two-questions split (an availability decision and a destructive decision must not share a predicate; bias any unavoidable overlap to the recoverable error)
  - the both-directions post-apply check (new artifact present AND old artifact absent) and the structure-vs-data limit of that evidence
  - migration DRIFT detection before deploy
  - cross-system extraction from the live information_schema (not committed schema or migration files, which drift from the real database)
  - the completeness check that a DB dump is not a full migration when binary assets live on app-server local disk (Dockerfile VOLUME / bind-mount / backup scope)
  - environment-vs-environment schema-drift detection (a constraint / index / column present in one environment, absent in another)
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
- Moving data between two systems, databases, or ORMs (a cross-system migration), or building the extractor / ETL for one.
- Reconciling a schema difference between two environments (a constraint, index, or column present in one and missing in another).
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
7. **`schema_source_of_truth`** — where the REAL current schema lives: the live database's `information_schema` / system catalog. Distinct from committed schema definitions or migration files (an ORM schema file such as `schema.prisma`, a model module, a `migrations/` folder), which describe the *intended* schema and drift from the database after hotfixes or partial migrations.
8. **`binary_asset_locations`** — where non-row binary data lives (uploaded files, generated documents, media, thumbnails): in the database, in an external object store, or on the app server's local disk. Decides whether a database dump is a complete migration or only half of one.

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

### Verifying the change landed (both directions, and the limit of the evidence)

When you introspect an environment after applying, assert **both** directions: the new artifact is **present** *and* the old one is **absent**. A one-sided check cannot tell a rename-in-place from a new column added *beside* the old one — the new column exists in both stories, but in the second the values still sit in the orphaned original while the application reads an empty field. Only the old artifact's absence separates them.

Then state what the check actually proved. Structure and data are separate claims: introspecting an environment whose table holds **zero rows** proves the shape changed and says nothing whatsoever about whether values survived the move. Data preservation is proven by the staging rehearsal on a **populated** copy (step 3), so the report must say which of the two the evidence covers rather than letting a structural pass read as both.

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
- **Environment-vs-environment schema drift** — a constraint, index, column, or default present in one environment's live schema and **missing in another** (e.g. a UNIQUE or CHECK constraint that exists in production but not in staging, or the reverse). This is invisible to the migration tool's own status check, which compares the code's migrations to a **single** database — you see it only by introspecting **both** environments' live schemas (`information_schema` / system catalog) and diffing them. A constraint present in one env and absent in another means a row that inserts cleanly in one environment fails in the other, and a migration validated against the drifted copy proves nothing about the target.

Drift is a deploy-blocking finding: resolve it (generate the missing migration, reconcile history, align the environments) before promotion, not after. Use the migration tool's own status/check command for the engine in use, and introspect both environments' live schemas for the env-vs-env case.

## Cross-system data migration (extract from the live schema, not the committed one)

A migration that moves data between two systems, databases, or ORMs has two completeness traps the in-place skeleton does not cover.

### Trap 1 — the committed schema drifts from the live database

Build the extractor from the **live database's `information_schema`** (or the engine's system catalog) — the columns, types, defaults, and constraints that actually exist in the running database — **not** from a committed schema definition or migration files (an ORM schema file such as `schema.prisma`, a model module, a `migrations/` folder). Those describe what the schema was *supposed* to become; manual hotfixes, failed or partial migrations, and out-of-band DDL make the real schema diverge. An extractor built from the committed schema silently **omits columns that exist** or **references columns that do not**, and the gap surfaces only mid-migration.

- Introspect the live catalog first; produce the real column / constraint inventory from it.
- Diff the live schema against the committed schema; treat every difference as a finding to resolve **before** extracting, not a surprise during.

### Trap 2 — a DB dump is not a full migration when binaries live on local disk

A `dump` / snapshot captures **rows, not files**. If the system stores binary assets — uploaded files, generated documents, media, thumbnails — on the **app server's local disk** rather than in the database or an external object store, a database dump migrates the metadata and leaves the actual bytes behind. The migrated system then references files that were never moved.

Before calling a dump a complete migration, determine where binaries **physically** live:

- **Dockerfile `VOLUME`** declarations and container **bind-mounts** / mount points — a `VOLUME` is a strong signal that state lives on a path, not in the DB.
- The app's **file-storage configuration** (a local-disk backend vs. an object-store backend).
- **What the existing backup job actually copies** — its scope. A backup that only dumps the database is itself evidence that on-disk binaries are unprotected and un-migrated.

If binaries are on local disk, the plan must copy them **separately** (and reconcile paths on the target); a dump-only plan is incomplete. Record the binary-asset location as an explicit discovery output.

## Safety gates

- **Never** reorder the skeleton: discover -> backup -> stage -> additive -> cutover -> archive.
- **Never** run a destructive step (drop/delete/truncate/overwrite) before the additive phase is verified in a staging copy.
- **Never** delete an old artifact when a rename preserves a rollback path — archive by rename with a timestamp.
- **Never** let one predicate gate both an availability decision ("may the new artifact serve?") and a destructive one ("may the old artifact be deleted?") — a wrong availability answer costs the service, a wrong destructive answer costs the data, and the two want opposite biases; split the check (see `references/destructive-checks.md`).
- **Never** trust an instance-level soft-delete to protect bulk / admin / QuerySet / cascade deletes.
- **Never** ship a `CASCADE` that reaches a financial / audit / historical table without explicit review; prefer `RESTRICT` / `SET NULL`.
- **Never** promote with migration drift unresolved.
- **Never** take the migration as "done" until restore from the backup has been at least dry-checked.
- **Never** build a cross-system extractor from a committed schema or migration file (an ORM schema file, model modules, `migrations/`) — introspect the LIVE `information_schema` / system catalog; the committed schema drifts.
- **Never** treat a database dump as a complete migration until you have confirmed where binary assets live (Dockerfile `VOLUME` / bind-mount / storage config / backup scope); binaries on app-server local disk are not in the dump.
- **Never** trust a migration validated against one environment when another environment's live schema may have drifted (a constraint present in one, absent in the other) — introspect and diff both.
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
- [ ] No single predicate gates both an availability decision and a destructive one; each computed from its own evidence, any unavoidable overlap biased to the recoverable error.
- [ ] Post-apply check asserted BOTH directions (new artifact present AND old artifact absent), and the report says whether the evidence covers data preservation or structure only (an empty table proves structure only).
- [ ] For a cross-system move, the extractor built from the live `information_schema` / system catalog, not committed schema/migration files; a live-vs-committed diff was produced.
- [ ] Binary-asset location determined (in-DB / object store / local disk via `VOLUME` / bind-mount / backup scope); if on local disk, a separate copy step is planned — a DB dump alone is not complete.
- [ ] Environment-vs-environment schema drift checked by introspecting BOTH environments' live schemas and diffing (constraints / indexes / columns / defaults), not just the tool's single-DB status check.
- [ ] "Not done or blocked" lists anything skipped and why.

## Output format

The skill emits exactly one block:

```
MIGRATION SAFETY REPORT
  Change:             <what is migrating / cutting over>
  Engine / tool:      <db_engine> / <orm-or-migration-tool>   (discovered)
  Schema source:      <n/a | live information_schema | committed-schema (DRIFT RISK)>   live-vs-committed=<clean|DIFFERS|n/a>
  Binary assets:      <n/a | in-DB | object-store | LOCAL DISK -> separate copy required>   (VOLUME/bind-mount/backup-scope checked)
  Drift check:        <clean | DRIFT: un-applied=<n>, out-of-order=<y/n>, model-vs-schema=<y/n>>
  Env drift:          <n/a | clean | DRIFT: <constraint/index/column> present in <env> missing in <env>>
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
| One `validate()` decides both "may it serve?" and "may the old one be deleted?" | The two want opposite biases — a diagnostic mismatch then takes the service down, or authorises the delete | Split the predicate; let "serving on the new, old one retained" be a legitimate state |
| Confirm a rename by checking the new column exists | A new column added *beside* the old one looks identical; the data stays in the orphaned original | Assert both directions — new present AND old absent |
| Call a rename verified from an empty environment | Zero rows prove the shape changed, never that values survived | Prove preservation on a populated staging copy; label the structural check as structure-only |
| Apply straight to the live side | No proof the migration even succeeds | Validate in a staging copy first |
| Promote with un-migrated model changes | CI/runtime drift; schema diverges from code | Run the drift check; generate the missing migration first |
| Skip the backup because "it's a small change" | Small destructive changes still destroy | Always take a timestamped, restorable backup |
| Build the extractor from `schema.prisma` / migration files | The committed schema drifts from the live DB (hotfixes, partial migrations) | Introspect the live `information_schema`; diff it against the committed schema first |
| Call a DB dump a complete cross-system migration | Binaries on app-server local disk are not in the dump | Check `VOLUME` / bind-mount / storage config / backup scope; copy binaries separately |
| Validate against staging, promote to prod, assume parity | A constraint present in prod but absent in staging (env drift) makes the staging proof meaningless | Introspect BOTH environments' live schemas and diff before promoting |

## Portability rationale

The skeleton, the expand/contract ordering, the destructive/CASCADE review, and the report contract describe *how to reason*, not *which engine to call*. The database, ORM, migration tool, and backup mechanism are adapter inputs discovered at run time; the concrete generate / status / apply / dump commands live in the reference docs. Supporting a new engine means adding command variants to a reference doc, not changing this skill.

## Cross-references

- `references/cutover-skeleton.md` — the step-by-step expand/contract runbook with provider-neutral command slots.
- `references/destructive-checks.md` — the soft-delete-layer audit, the bulk-delete bypass paths, and the cascade-FK inventory procedure.
- `release-verification` (skill) — after the migration, prove the deploy actually reached the target environment; also owns the CI env-var false-FAILURE case (the other half of the env-drift / masking concern this skill's env-vs-env drift detection covers).
- `release-verify` (command) — user entry point; routes the migration/cutover and drift items to this skill.
