---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

Using SQLAlchemy 2.0 AsyncSession in FastAPI, my route loads an Order and then returns order.customer.name. It crashes with sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here. The same code worked when I used a sync Session. What's going on and how do I fix it?
