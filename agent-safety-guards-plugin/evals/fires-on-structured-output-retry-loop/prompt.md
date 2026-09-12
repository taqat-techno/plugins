---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

My agent workflow has a required structured-output tool that's supposed to return a catalog of several inventory items, but the agent just keeps calling the same tool over and over with slightly different payloads that all get rejected by schema validation, until it times out. I tried relaxing some of the required properties on the schema but it's still looping. What's actually going on?
