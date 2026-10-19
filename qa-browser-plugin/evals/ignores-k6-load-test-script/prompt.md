---
max_turns: 8
allowed_tools: [Skill]
tags: [routing]
---

Write me a k6 script that sends GET requests to our orders API with 200 virtual users for five
minutes and fails if p95 latency goes over 800 ms.
