---
type: llm
---
PASS if the reply describes the conversion as: type the props with the
framework's component-props type (which already includes ref in React 19),
destructure ref out of props instead of taking it as a second forwardRef
argument, drop the now-redundant displayName on named function components,
AND requires running a type-check then a build after each converted
component/file (the gate) before moving to the next one, doing one component
(or one small group) per commit rather than batching all 40 into a single
commit.
FAIL if the reply gives generic forwardRef-to-React-19 advice without the
type-check-then-build gate, or if it suggests converting and committing all
40 components in one batch/commit, or if it does not mention confirming
React 19 is actually installed before doing the conversion.
