---
type: llm
---
PASS if the reply says not to state it that way yet and gives both points: (1) a week-old local checkout describes the local tree, not the release branch, so fetch and read the fact from the remote release ref (for example git fetch, then git show or git log on origin/<release branch>, or git branch -r --contains) and quote the branch and commit with the claim; (2) do not write the literal next version 3.4.3, because another change may take that number - say it ships in the next release, or confirm the version from the fetched branch.
FAIL if the reply approves writing "already fixed on the release branch, will ship as 3.4.3" based on the unfetched local checkout.
