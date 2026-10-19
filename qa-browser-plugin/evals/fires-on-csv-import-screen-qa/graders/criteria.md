---
type: llm
---
PASS if the reply includes previewing and then cancelling to prove nothing was committed, a fixture set with
a good file plus a bad-row file and an over-the-row-cap file, committing only on a disposable
target, and re-running the same file to show the second run changes nothing (idempotency).
FAIL if the reply only covers uploading a valid file and checking the success message, or never verifies
that cancelling the preview commits nothing.
