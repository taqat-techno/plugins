---
type: llm
---
PASS if the reply defines an ir.actions.report for sale.order with report_type qweb-pdf and a print
binding, writes a QWeb template that loops over docs inside t-call web.external_layout (or a custom
layout), and mentions the paper format or the wkhtmltopdf requirement.
FAIL if it generates the PDF in Python with an external library, or answers with an email template
instead.
