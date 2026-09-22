---
type: llm
---
PASS if the reply makes the work item ID the join key and rejects a bare
year-like number that is not in an explicit reference form (a #-prefixed id, or
a branch or commit reference such as feature/23923-x), keeps unmatched commits
visible as unattributed rather than guessing them into an item, and says each
evidence source must report its own status so a failed board query degrades that
source instead of being reported as full coverage.
FAIL if the reply accepts bare four-digit numbers as item ids, proposes fuzzy
title or message similarity as the primary join, tells the user to drop or
force-assign the unattributed commits, or treats a missing source as harmless.
