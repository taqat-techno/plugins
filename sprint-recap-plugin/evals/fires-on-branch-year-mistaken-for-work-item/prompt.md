---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

We are putting together the sprint review for Sprint 24. I wrote something that
scans our Azure DevOps board, the git history and my saved session logs, then
matches each commit back to the item it belongs to. It mostly works, but it
decided a branch named release/2026-planning belongs to item 2026, and a commit
message that says "bumped to 2025 pricing" got filed under item 2025. Meanwhile
about half the real commits ended up in a bucket called unattributed, and when
the board query failed entirely it still reported the sprint as fully covered.
How should the matching actually work?
