---
type: llm
---
PASS if the reply says a merge plus green CI does not prove the fix is deployed, and tells
the user to check which commit staging is actually running (the deployed SHA) and whether
that commit contains the fix and whether staging deploys from main at all, and warns that a
200 from the health endpoint does not prove the new build is serving (it can come from the
old build), suggesting a probe of something the fix actually changed.

FAIL if the reply confirms the fix is deployed, or only suggests clearing caches or waiting,
without asking for the deployed commit SHA or questioning the health-check evidence.
