---
type: llm
---
PASS if the reply uses a publicWidget (publicWidget.Widget.extend with a selector and events,
registered in publicWidget.registry), handles the website builder's edit mode (editableMode or
disabledInEditableMode), cleans up in destroy, and loads the file through the web.assets_frontend
bundle in the manifest.
FAIL if it puts an inline script tag in a QWeb template, or relies on a global jQuery document-ready
handler with no publicWidget.
