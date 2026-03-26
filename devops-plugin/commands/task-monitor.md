---
title: 'Task Monitor'
read_only: false
type: 'command'
description: 'Periodic work item monitor - alerts on new Azure DevOps assignments. Use with /loop 15m /task-monitor'
primary_agent: work-item-ops
---

# /task-monitor - New Assignment Alerts

Monitor for new work item assignments. Designed for use with `/loop 15m /task-monitor`.

## Input Format

```
/task-monitor [--reset]
```

| Flag | Action |
|------|--------|
| `--reset` | Clear saved snapshot and create fresh baseline |
| *(no flags)* | Compare current assignments against last snapshot |

## Workflow

1. **Load** previous snapshot from session state (or create baseline on first run)
2. **Query** current assignments via `wit_my_work_items`
3. **Diff** against snapshot:
   - New items assigned since last check
   - State changes on existing items
   - Items removed from assignment
4. **Report** changes (or "No new assignments" if quiet)
5. **Save** updated snapshot for next check

## Example

```
User: /loop 15m /task-monitor

[First run]
Output:
Task Monitor: Baseline created with 5 active items.
Next check in 15 minutes.

[Subsequent run - new assignment detected]
Output:
## Task Monitor Alert - 14:30

### New Assignments (1)
| ID | Type | Title | State | Assigned By |
|----|------|-------|-------|-------------|
| #1410 | Bug | Map crash on large datasets | Approved | Omar Khalil |

### State Changes (1)
| ID | Title | Change |
|----|-------|--------|
| #1398 | Map marker offset | Approved -> In Progress |

Next check in 15 minutes.
```
