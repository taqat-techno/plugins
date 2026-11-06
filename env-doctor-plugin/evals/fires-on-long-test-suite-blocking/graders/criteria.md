---
type: llm
---
PASS if the reply says the suite will be started in the background (not as a blocking
foreground call with a long timeout), that work on the docs continues meanwhile, and that
the result is handled when the job's completion notification arrives - fixing failures or
confirming success - without sleeping or polling in a loop.

FAIL if the reply plans to run the suite in the foreground and wait for it, or plans to
check on it with a sleep/poll loop.
