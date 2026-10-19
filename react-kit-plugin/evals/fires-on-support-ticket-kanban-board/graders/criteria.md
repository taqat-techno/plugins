---
type: llm
---
PASS if the reply takes the columns from the project's workflow state set instead of hard-coding them, and
treats each drag as a typed transition with allowed-from states, a role check, validation,
confirmation for destructive moves and an audit entry, with a clear optimistic-update rule.
FAIL if the reply hard-codes the three columns and lets any card move anywhere with a plain state update and
no role check or audit.
