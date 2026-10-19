---
type: llm
---
PASS if the reply separates a failed metric (shown as an error state on that card, with retry) from a
legitimate zero or no-data value, uses a loading skeleton per card, and adds a data-freshness
indicator or last-updated time.
FAIL if the reply keeps rendering 0 on failure, or only adds a global error banner without distinguishing a
failed card from a real zero.
