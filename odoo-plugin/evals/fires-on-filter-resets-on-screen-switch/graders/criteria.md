---
type: llm
---
PASS if the reply explains that component state is lost when the component unmounts, and moves the
value into a shared reactive store or service (or record-level UI state) that the screen reads back,
without copying store data into component useState.
FAIL if the main fix is localStorage or a global window variable.
