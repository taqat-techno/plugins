---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Our Django admin-style list API paginates with ?page=N using the standard Paginator over a 40 million row events table ordered by -created_at. Page 1 is instant but page 20000 takes 15 seconds, and even the total count query is slow. How should we fix this?
