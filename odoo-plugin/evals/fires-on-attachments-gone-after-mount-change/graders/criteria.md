---
type: llm
---
PASS if the reply explains that the old named volume was orphaned rather than deleted, shows how to
find it (docker volume ls or inspect) and copy its data forward into the new mount (for example cp
-a in a throwaway container), and warns against down -v or volume prune.
FAIL if it recommends docker compose down -v, pruning volumes, or says the data is lost.
