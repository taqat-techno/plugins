---
type: llm
---
PASS if the reply uses an upload, parse, preview, confirm, commit pipeline, applies a default row cap,
reports typed errors per row, makes re-imports idempotent through an external id, and refuses to
auto-create missing related categories (reporting them as row errors instead).
FAIL if the reply imports directly on upload without a preview step, or silently creates the missing
categories.
