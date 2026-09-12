---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I have an async def endpoint in FastAPI that calls a third-party pricing API using the requests library to get a quote. Under load, all our other endpoints start timing out too, even ones that have nothing to do with pricing. A single request works fine when I test it locally. What's going on?
