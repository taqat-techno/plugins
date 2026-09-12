---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

We're on FastAPI with Alembic and need to rename a column in our users table from full_name to display_name. The app runs several instances behind a load balancer doing rolling deploys, and the table gets constant traffic. How should we structure the migration so we don't break anything mid-deploy?
