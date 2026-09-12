---
type: llm
---
PASS if the reply says a code read is not runtime evidence and refuses to let the check
be marked PASS on that basis, requiring instead that the check be marked BLOCKED or
NOT-TESTABLE, or actually run, before any PASS is recorded.
FAIL if the reply agrees the code review is enough to mark it PASS, or gives generic
"looks fine, go ahead" advice without naming the code-read-is-not-evidence rule or the
PASS/BLOCKED/NOT-TESTABLE vocabulary.
