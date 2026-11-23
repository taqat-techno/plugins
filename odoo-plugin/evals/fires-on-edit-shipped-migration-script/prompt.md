---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Our Odoo 17 module has migrations/17.0.1.4.0/post-migrate.py, which shipped two weeks ago. I found a bug in it: it skips partners that have no country. Staging and production are both on 17.0.1.6.0 now. I plan to fix the script in place in that same 17.0.1.4.0 folder and push it. Is that fine?
