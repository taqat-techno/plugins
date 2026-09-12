---
type: llm
---
PASS if the reply names an explicit per-package ownership field (e.g. an
"Owns" list of files/paths) as the collision key that determines which
packages may run at the same time, AND a separate flag saying whether a
package may be delegated/run in parallel at all (a laneable/not-laneable
verdict), AND says that if this ownership is missing it should be reported
as unknown rather than guessed or eyeballed.
FAIL if the reply gives generic project-management advice (e.g. "break it
into independent tickets and use a dependency graph tool" or "just make sure
tasks don't overlap") without a concrete named ownership/collision field, or
if it suggests guessing which packages are independent by inspection instead
of requiring it to be stated explicitly.
