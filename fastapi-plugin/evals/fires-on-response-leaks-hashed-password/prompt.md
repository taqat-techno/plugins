---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My FastAPI GET /users/{id} endpoint returns the SQLAlchemy User object directly, and I just noticed the JSON includes hashed_password and is_admin. The same User model is also what POST /users accepts as its body. What is the right way to structure this?
