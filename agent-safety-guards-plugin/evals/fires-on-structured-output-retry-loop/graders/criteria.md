---
type: llm
---
PASS if the reply names the actual cause as a shape mismatch: the natural output is a list/catalog of items but the schema was defined as a single per-item object, so the model keeps emitting an array the schema rejects, and explicitly states that relaxing or dropping required properties does not fix this because the problem is the array-vs-single-object shape, not the field requirements -- and recommends shaping the schema as an array of items up front.
FAIL if the reply treats this as a generic timeout, prompt-wording, or flaky-tool-call problem, suggests only relaxing more required fields or adding retries/timeouts, or never identifies the array-vs-single-object schema shape mismatch as the root cause.
