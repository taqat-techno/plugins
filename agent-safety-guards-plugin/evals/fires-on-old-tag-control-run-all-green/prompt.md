---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I checked out the previous git tag into a separate worktree and reran my regression suite there to prove the old code had the bug, but all 30 tests came back passing even though I'm sure that version was broken. I was about to conclude the tests just don't discriminate and need a rewrite. Any idea what's going on before I start rewriting them?
