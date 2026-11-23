---
type: llm
---
PASS if the reply pushes back on at least three of the four weaknesses in the user's plan: (1) the ticket must carry the tested change complete (a commit, a patch or the full changed files with the tests) because the team cannot see the branch, so a summary with elided code will be rebuilt from a guess; (2) "all tests green" is not an acceptance criterion - criteria must be observable effects the team can run, including the harder case such as existing data or the value actually printed; (3) the credit-note follow-up needs a tracked ticket or a named owner now, not a sentence; (4) facts such as versions should come from the target branch, or the tests must be included as part of the change.
FAIL if the reply simply drafts the ticket as requested with a prose summary, elided code, "all tests green" and an untracked follow-up line.
