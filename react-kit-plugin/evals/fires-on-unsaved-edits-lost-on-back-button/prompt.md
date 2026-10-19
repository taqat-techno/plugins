---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

In our React admin edit form, people lose unsaved changes when they press the browser Back button.
We already have a beforeunload handler, but it only seems to fire when the tab closes. What are we
missing?
