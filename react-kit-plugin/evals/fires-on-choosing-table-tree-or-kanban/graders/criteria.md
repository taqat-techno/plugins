---
type: llm
---
PASS if the reply ties the choice to the data shape and the user's main task (a tree when browsing the
parent and child hierarchy is the task, a board when moving work through status stages is the task,
a list otherwise), picks one primary view and explains why, possibly with a secondary view.
FAIL if the reply builds all three without a reason, or picks one without relating it to the hierarchy, the
status pipeline and the user's task.
