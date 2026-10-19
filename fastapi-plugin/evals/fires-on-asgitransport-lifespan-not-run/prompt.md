---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My async FastAPI tests use httpx.AsyncClient(transport=ASGITransport(app=app)). The app creates its DB engine and puts it on app.state inside the lifespan, but in tests every request fails with AttributeError: 'State' object has no attribute 'engine'. The app works fine under uvicorn. Why?
