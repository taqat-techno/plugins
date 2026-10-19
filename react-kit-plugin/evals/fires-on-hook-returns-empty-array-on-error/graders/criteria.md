---
type: llm
---
PASS if the reply says the hook must surface the error instead of swallowing it into an empty array, maps
statuses to distinct UI states (401 or 403 to access-required, 404 to not-found, 5xx or network to a
retryable error) and checks error before empty.
FAIL if the reply keeps returning an empty array on error, or only adds console logging.
