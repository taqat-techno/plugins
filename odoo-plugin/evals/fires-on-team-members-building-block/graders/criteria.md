---
type: llm
---
PASS if the reply writes a QWeb template for the snippet, registers it in the website.snippets
template with the version-appropriate xpath, gives it a thumbnail, and optionally adds snippet
options.
FAIL if it only creates a static page template, or injects the markup with JavaScript instead of
registering a snippet.
