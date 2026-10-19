---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My useOrders hook catches every fetch error and returns an empty array so the page never crashes.
Now some users just see an empty orders table and nobody knows why. What's the right pattern?
