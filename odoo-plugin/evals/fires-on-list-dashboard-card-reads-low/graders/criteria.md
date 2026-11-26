---
type: llm
---
PASS if the reply says ODOO.LIST only loads the rows that are written in the sheet, so rows the
view gained after the sheet was built are left out with no error, and tells the user to write more
ODOO.LIST rows than the view holds today (headroom, or re-sizing the data sheet) so growth is
covered.
FAIL if it blames the SUMIFS criteria, a cache, access rights or the SQL view without naming the
row limit of the data sheet, or if it proposes replacing the lists with a pivot as the fix.
