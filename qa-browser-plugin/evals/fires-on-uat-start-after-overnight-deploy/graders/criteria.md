---
type: llm
---
PASS if the reply says to first verify that the target is reachable and healthy and that it is running the
expected build (commit, version or deploy timestamp from a health or version endpoint) and the
expected environment, and to stop and label the run blocked if any of that does not match.
FAIL if the reply goes straight into executing test cases, or only suggests clearing the browser cache,
without verifying the build identity and environment first.
