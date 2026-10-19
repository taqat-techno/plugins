---
type: llm
---
PASS if the reply explains that editing the English source string changed the msgid, so the existing
translation no longer matches and is orphaned, and that the fix is to re-export the .pot and re-
merge the .po before updating the module; it may also check that the entry uses a typed model
reference rather than a source-file path.
FAIL if the only advice is clearing the browser cache, or it suggests editing translations directly
in the database as the fix.
