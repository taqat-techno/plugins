---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My Django view does Order.objects.values("status").annotate(count=Count("id")) to show order totals by status, but when I add up all the bucket counts I get way more than the real number of rows in the table. The Order model has ordering = ["-created_at"] set in its Meta class. I don't get why grouping would care about that at all. Any idea what's causing the inflated counts?
