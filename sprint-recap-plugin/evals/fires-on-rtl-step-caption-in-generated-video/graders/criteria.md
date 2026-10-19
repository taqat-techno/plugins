---
type: llm
---
PASS if the reply warns that the generated Remotion project is regenerated on every
build, so hand edits to its source files are lost, and directs the fix to the step
script / build inputs or the plugin's template instead; and explains that captions
containing Arabic characters are rendered right-to-left (dir="rtl") with the badge row
reversed, so a mirrored caption over a right-to-left app is the intended result.
FAIL if the reply recommends patching the generated project's files as the lasting fix,
or treats left-to-right layout as correct for Arabic captions, or gives generic CSS
direction advice without mentioning that the project is regenerated.
