---
type: llm
---
PASS if the reply patches the existing component with patch() (calling super where it overrides a
method), extends its template with t-inherit and an xpath, and loads the files in the POS asset
bundle from the addon's manifest.
FAIL if it copies the core component, edits core files, or force-replaces a registry entry.
