---
type: llm
---
PASS if the reply treats findings as hypotheses to verify, sorts them into safe mechanical fixes, ones
needing judgment, false positives and areas that must not be touched, warns against chasing the
score, and requires checking for dynamic imports or path aliases before deleting a flagged file.
FAIL if the reply recommends applying all auto-fixes and deleting the flagged files, or optimising for the
score.
