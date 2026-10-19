---
type: llm
---
PASS if the reply explains that TestCase wraps each test in a transaction that is rolled back and never committed, so on_commit callbacks never fire, and gives a fix such as TestCase.captureOnCommitCallbacks(execute=True) or switching that test to TransactionTestCase.
FAIL if the reply blames the mock target path, async execution, or the test client without naming the never-committed test transaction, or suggests removing on_commit from production code.
