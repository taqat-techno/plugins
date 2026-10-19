---
type: llm
---
PASS if the reply advises against dropping the old column in the same step, and lays out an
expand-then-contract sequence: take a backup first, add the new column, backfill, switch the
application to the new column (dual-write or read-new), verify, and only later remove or
archive the old column in a separate step, keeping a rollback path until then.

FAIL if the reply approves the single migration as proposed, or only discusses batching the
copy for performance without separating the destructive drop from the additive change.
