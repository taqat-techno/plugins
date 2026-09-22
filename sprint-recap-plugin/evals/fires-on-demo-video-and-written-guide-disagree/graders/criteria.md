---
type: llm
---
PASS if the reply establishes one step script as the single source both
artifacts are generated from, with each step's caption authored once and reused
as the on-screen text, the written instruction and the narration line, treats a
step as a unit of narration (a few related actions under one caption) rather
than a single click, and requires each step to declare its own starting URL so
it is self-contained and independently re-runnable.
FAIL if the reply keeps the captions and the written text as two separately
authored copies kept in sync by review or diffing, equates one UI click with one
step, or never names a single source of truth for both artifacts.
