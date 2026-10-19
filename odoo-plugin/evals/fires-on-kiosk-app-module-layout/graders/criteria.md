---
type: llm
---
PASS if the reply gives a module layout with a controller that renders an index document, a
dedicated asset bundle with the boot file kept separate, a root component that is mounted, a store
or data service that owns loading, and layer rules that keep screens from fetching data ad hoc.
FAIL if it puts everything in one component, or turns the answer into a backend client action
without addressing the standalone layout.
