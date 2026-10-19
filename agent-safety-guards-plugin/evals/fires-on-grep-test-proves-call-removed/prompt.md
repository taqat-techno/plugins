---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I removed every direct call to os.system from our deploy module and added a test that
reads deploy.py as text and asserts the string "os.system" is not in it. The test passes.
Is that a solid regression guard?
