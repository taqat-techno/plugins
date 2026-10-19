---
type: llm
---
PASS if the reply explains SCSS load order: palette and website-values variables belong in a file
loaded in the web._assets_primary_variables bundle and are extended with map-merge, not in the
frontend bundle where they are read too late or before definition.
FAIL if it suggests defining the variable in an arbitrary frontend SCSS file or only adding
!default.
