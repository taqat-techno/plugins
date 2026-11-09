---
type: llm
---
PASS if the reply says an imported .po applies only to record (model) terms and ignores code
terms such as =_t() labels, moves the card and chart texts into translatable records (for
example selection labels read with ODOO.PIVOT.HEADER), translates the records with the Export
Translation (Model) and Import Translation wizards or update_field_translations, and warns that
the live translations are lost when the records are rebuilt.
FAIL if it duplicates the boards per language, claims a .po import translates =_t() labels on a
live database, or says nothing can be translated without deploying a module.
