---
type: llm
---
PASS if the reply replaces spinner-on-blank with a skeleton that matches the final layout, separates an
empty state (nothing exists yet, with a create action) from a no-results state (filters matched
nothing, with a clear-filters action), and gives errors a message plus a next step.
FAIL if the reply keeps one generic message for empty and no-results, or keeps the blank-page spinner.
