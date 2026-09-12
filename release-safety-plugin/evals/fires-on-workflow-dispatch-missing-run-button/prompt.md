---
max_turns: 12
allowed_tools: [Skill]
tags: [routing]
---

I just added a new GitHub Actions workflow with a workflow_dispatch trigger on my feature branch, but there's no "Run workflow" button showing up in the Actions tab, and when I try `gh workflow run` it tells me the workflow has no workflow_dispatch trigger. The YAML definitely has workflow_dispatch in it though. What's going on?
