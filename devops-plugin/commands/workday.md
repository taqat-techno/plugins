---
title: 'Workday Dashboard'
read_only: false
type: 'command'
description: 'Daily login dashboard - see your work items, log hours, track compliance. Flags: --sync (force API sync), --tasks (work items table), --todo (sync to Claude TODO list)'
primary_agent: work-item-ops
---

# /workday - Daily Login Dashboard

Parse `$ARGUMENTS` for flags:

## Input Format

```
/workday [--sync] [--tasks] [--todo]
```

| Flag | Action |
|------|--------|
| `--sync` | Force API sync (refresh from Azure DevOps) |
| `--tasks` | Show work items as formatted table only |
| `--todo` | Sync work items to Claude TODO list |
| *(no flags)* | Full dashboard (work items + hours + compliance) |

## Workflow

1. **Load profile** per `rules/profile-loader.md`
2. **Query work items** via `wit_my_work_items` for current project
3. **Calculate hours** — compare logged CompletedWork against expected (from `data/project_defaults.json` workTracking)
4. **Generate dashboard** with sections:
   - Active tasks (sorted by priority)
   - Hours logged today vs target
   - Compliance status (on track / behind)
5. If `--todo`: sync active items to Claude TODO list

## Example

```
User: /workday

Output:
## Workday Dashboard - 2026-03-26
Project: My Project | Sprint: Sprint 15

### My Active Work (5 items)
| ID | Type | Title | State | Hours |
|----|------|-------|-------|-------|
| #1401 | Task | [Dev] Fix geocoding timeout | In Progress | 3h/8h |
| #1398 | Bug | Map marker offset on zoom | Approved | 0h/4h |
| #1395 | Task | [Dev] Add disaster category filter | To Do | 0h/6h |

### Hours Today
Logged: 3h | Target: 6h | Status: Behind

### Quick Actions
- "mark #1401 as done" to complete with hours
- "/log-time 2h #1398" to log time
- "/create" to add new work item
```
