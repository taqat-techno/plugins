---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I'm renaming the customer_email column to email on our production orders table. My plan is
one migration that adds the new column, copies the data across and drops the old column,
then deploy. The table has about 40 million rows and the app reads it constantly. Good plan?
