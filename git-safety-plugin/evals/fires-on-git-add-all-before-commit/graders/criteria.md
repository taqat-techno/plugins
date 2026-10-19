---
type: llm
---
PASS if the reply advises against git add -A here because it would sweep the teammate's
generated files (files the user did not write) into the commit, recommends staging only
the explicit paths the user edited and checking what is staged (for example with
git diff --cached --name-only or git status) immediately before committing and pushing.

FAIL if the reply simply approves running git add -A, commit and push as proposed, or
gives only generic commit-message advice without warning that a broad add co-stages
files the user does not own.
