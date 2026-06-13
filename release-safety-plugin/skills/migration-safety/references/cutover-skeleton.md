# Cutover skeleton — expand / contract runbook (provider-neutral)

The fixed order for any risky migration or live-resource cutover. Each step gates the next; never reorder. Command slots are filled from the discovered `db_engine` / `orm` / `migration_tool` — the *behaviour* below is engine-neutral.

```
DISCOVER -> BACKUP -> STAGE -> ADDITIVE -> (verify) -> CUTOVER (destructive, last) -> ARCHIVE (rename)
```

## 1. DISCOVER (read-only, both sides)

- Read the current shape of the live side and the desired shape. Produce a concrete diff (added / changed / removed columns, tables, indexes, constraints).
- Run the migration tool's **status/drift** check (see `destructive-checks.md` and the skill's drift section). Do not proceed past unresolved drift.
- Inventory foreign keys and their `ON DELETE` behaviour for the destructive review.

Output of this step: a diff + a drift verdict + a cascade-FK list. No writes.

## 2. BACKUP (timestamped, restorable)

- Take a snapshot of the live side using the engine's `backup_mechanism` (dump, snapshot, or copy). Name it with a timestamp.
- **Dry-check the restore path**: confirm the backup is restorable (restore into a scratch location or at least verify the artifact is complete and readable). A backup you cannot restore is not a backup.
- Record where the backup is and how to restore it, so rollback is a known command, not an improvisation.

Never skip this for a "small" change — small destructive changes still destroy.

## 3. STAGE (build + validate a throwaway copy)

- Build a copy at `staging_copy_location` (from the backup or a clone of the live schema).
- Apply the full migration to the copy. Prove it **succeeds end to end** and that the application boots/queries against the migrated copy.
- This is where a broken migration is supposed to fail — never on the live side.

If staging validation fails, stop. Fix the migration; re-stage.

## 4. ADDITIVE FIRST (reversible changes only)

Apply only changes that keep old and new code working simultaneously:

- Add new columns as **nullable or with a default** (not `NOT NULL` without a default on a populated table).
- Add new tables / indexes alongside the old ones.
- **Backfill** data into the new shape in batches.
- Where reads/writes are moving, **dual-write** (write old + new) so either side is consistent.

Verify after this phase: new shape populated and correct, old shape still intact. At this point a rollback is just "stop using the new shape" — nothing has been destroyed.

## 5. CUTOVER LAST (the single destructive step)

Only after the additive phase is verified:

- Flip reads (and then writes) to the new shape.
- Make the previously-nullable column `NOT NULL` if required, now that it is backfilled.
- This is the **only** step that is hard to reverse, and it is the LAST step. Run the destructive review (`destructive-checks.md`) before it.

Keep the cutover small and atomic where the engine allows (single transaction / single switch), so a failure here reverts cleanly.

## 6. ARCHIVE by RENAME (never delete)

- Do **not** `DROP` the old table/column immediately. Rename it aside: `<name>_archived_<timestamp>`.
- Keep the archived artifact for a defined retention window so rollback remains possible after cutover.
- Schedule the eventual drop as a *separate, later* migration once the new shape has proven itself in the target environment.

## Rollback posture at each step

| After step | Rollback action |
|---|---|
| DISCOVER | nothing applied; abandon freely |
| BACKUP | nothing applied |
| STAGE | discard the staging copy |
| ADDITIVE | stop using new shape; old shape intact |
| CUTOVER | revert the switch; restore from backup if needed |
| ARCHIVE (rename) | rename the archived artifact back |

The reason the destructive drop is deferred to a *separate later migration* is that it removes the last rollback target — so it only happens once the cutover is proven, never in the same change.

## Platform note (labeled examples only)

> Example (illustrative — not required): one project's `migration_tool` generates a forward migration file and applies it with an `apply`/`migrate` command and reports state with a `status` command; another uses an ORM that auto-generates from model diffs. The expand/contract ordering and the archive-by-rename rule are identical; only the generate / apply / status command text differs.
