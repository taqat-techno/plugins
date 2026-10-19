---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

In my FastAPI app I have a pydantic-settings Settings class and a get_settings() function that returns Settings(), used with Depends(get_settings) in many routes. Profiling shows the .env file being read and parsed on every single request. How should this be set up, and how do I swap settings in tests?
