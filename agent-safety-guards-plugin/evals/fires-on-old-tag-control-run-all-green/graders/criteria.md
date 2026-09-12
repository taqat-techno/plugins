---
type: llm
---
PASS if the reply identifies that an editable install (pip install -e, npm link, PYTHONPATH, or a go.work replace) pins the working tree's src onto the import path permanently, so cd-ing into the worktree at the old tag does not change what import resolves to and the "old version" run actually executed the new code -- and recommends printing the resolved module's file path (e.g. via `python -c "import pkg; print(pkg.__file__)"`) before trusting the run, plus disabling the test runner's cache for the cross-version comparison.
FAIL if the reply only suggests generic debugging (add more assertions, check for flaky tests, add logging), concludes the tests genuinely don't discriminate and should be rewritten, or gives no concrete mechanism for why a worktree checkout can still execute the new code.
