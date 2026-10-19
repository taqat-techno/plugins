---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I added a lifespan= function to my FastAPI app to open an httpx client, and since then the database connection I set up in @app.on_event('startup') is never created, so every request fails with an attribute error on app.state.db. Nothing else changed. Why did my startup handler stop running?
