---
max_turns: 8
allowed_tools: [Skill]
tags: [routing]
---

This PostgreSQL query is slow on a 50 million row table: SELECT * FROM orders WHERE
customer_id = 42 ORDER BY created_at DESC LIMIT 20. Which index should I add?
