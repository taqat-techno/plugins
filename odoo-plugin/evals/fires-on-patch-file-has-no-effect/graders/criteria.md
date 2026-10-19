---
type: llm
---
PASS if the reply first checks whether the file is in an asset bundle at all (the manifest assets
globs), then forces an asset rebuild or module update and uses debug=assets, and shows how to
confirm from the browser console that the module is loaded and the patch target is the right class
or method.
FAIL if it only suggests restarting again or clearing the browser cache, without checking bundle
membership.
