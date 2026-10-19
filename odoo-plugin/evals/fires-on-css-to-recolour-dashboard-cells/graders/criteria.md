---
type: llm
---
PASS if the reply explains that the sheet body is drawn on a canvas that CSS cannot reach, so cell
colours must be set as cell styles in the dashboard workbook, and that only figures are DOM elements
that CSS can scope (for example by their data-id).
FAIL if it gives CSS selectors and claims they will recolour the cells.
