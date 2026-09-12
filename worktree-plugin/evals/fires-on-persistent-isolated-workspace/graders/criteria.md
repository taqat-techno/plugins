---
type: llm
---
PASS if the reply says that a clean isolated workspace like this is normally
removed automatically once the session that created it exits, and that
surviving that requires explicitly locking it (e.g. a git worktree lock) so
it persists across sessions, AND mentions that a freshly created workspace
like this starts without dependencies installed (a fresh checkout), so an
install step should not be assumed.
FAIL if the reply only explains how to create a separate working copy
generically (e.g. plain "git worktree add" or "clone the repo again")
without mentioning that it would otherwise be auto-removed on session exit,
or without mentioning the need to lock it for persistence.
