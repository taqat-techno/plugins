---
title: 'Workday Dashboard'
read_only: false
type: 'command'
description: 'Daily login dashboard - see your work items, log hours, track compliance. Flags: --sync (force API sync), --tasks (work items table), --todo (sync to Claude TODO list)'
---

# /workday - Daily Login Dashboard

Parse `$ARGUMENTS` for flags:

| Flag | Action |
|------|--------|
| `--sync` | Force API sync (refresh from Azure DevOps) |
| `--tasks` | Show work items as formatted table |
| `--todo` | Sync work items to Claude TODO list |
| *(no flags)* | Full dashboard (work items + hours + compliance) |

Use the devops skill for:
- Work item query and display formatting
- Time tracking integration
- Compliance status (logged hours vs expected)
- TODO list synchronization patterns
- Dashboard layout and presentation
