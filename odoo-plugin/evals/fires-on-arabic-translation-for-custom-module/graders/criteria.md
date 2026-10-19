---
type: llm
---
PASS if the reply exports a .pot for the module (odoo-bin --i18n-export or the Export Translation
wizard), creates or merges ar.po in the module's i18n folder, checks for empty msgstr and fuzzy
entries, and loads the Arabic language and updates the module to apply it.
FAIL if it hardcodes Arabic strings in Python or views, or says no translation template is needed.
