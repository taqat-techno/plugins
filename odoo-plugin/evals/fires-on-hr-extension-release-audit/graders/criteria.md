---
type: llm
---
PASS if the reply checks ir.model.access.csv coverage for every model, record rules for multi-user
data, routes declared with auth public or none and their CSRF handling, each sudo() call for a
justification and narrow scope, and raw cr.execute calls for string-formatted SQL.
FAIL if it gives a generic web-security checklist with no Odoo-specific checks.
