---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

We just bumped our Next app to React 19 and the linter is now flagging every
single forwardRef component as deprecated, about 40 of them. I want to
convert them all to the new ref-as-prop style without breaking anything.
What is the safe way to do a migration this size?
