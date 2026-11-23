---
type: llm
---
PASS if the reply says a merge and a first-pass review are not proof of delivery and asks for a comparison of the shipped commit with what the ticket requested, item by item: whether the retry, the data migration and the three tests are actually in the merged change, and whether the behaviour was verified on the deployed build (including that the migration ran on the target environment). Mentioning that tests and migrations are the parts most often dropped when someone else implements a ticket strengthens a PASS.
FAIL if the reply says a merged, review-passed ticket can be marked verified without checking the shipped change against the requested items.
