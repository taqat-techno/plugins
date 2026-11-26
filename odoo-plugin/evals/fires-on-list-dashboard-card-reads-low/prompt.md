---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Our Odoo 17 spreadsheet dashboard has no pivots. A data sheet holds =ODOO.LIST(1,n,"x_count") rows
reading a grouped SQL view, and the cards are SUMIFS over that sheet. It was right last week. Today
the "Open requests" card shows 2, while the view itself has 4 matching rows when I open it as a
list. No cell shows an error. What is wrong, and how do I stop it happening again?
