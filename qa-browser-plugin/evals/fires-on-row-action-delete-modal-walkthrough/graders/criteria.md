---
type: llm
---
PASS if the reply describes an open, assert, cancel pattern that proves the action is reachable and that
cancelling has no effect, checks that the modal is really gone after cancel or Esc (no orphaned
modal left mounted), and only confirms destructive actions on disposable records.
FAIL if the reply simply clicks through and confirms each action, or never checks that cancel leaves no
effect and no leftover modal.
