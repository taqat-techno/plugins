---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

In our Django app we need to rename a column on the Order model's orders table in Postgres from "stat" to "status" but the app runs with rolling deploys and that table has millions of rows getting hit constantly. What's the safe way to do this so we don't break anything mid-deploy?
