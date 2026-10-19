---
type: llm
---
PASS if the reply says the all-clear is not trustworthy because six producers did not
complete and an empty result from a failed agent is unverified rather than clean; it
recommends re-running the failed items in smaller sequential waves and only reporting
clean once every producer completed, ideally confirming with a deterministic scan.

FAIL if the reply accepts the zero-issues result, or only suggests retrying without
pointing out that the six failed agents make the aggregate unverified.
