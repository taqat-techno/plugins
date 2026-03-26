---
title: 'Log Time'
read_only: false
type: 'command'
description: 'Log working hours against work items or general categories'
primary_agent: work-item-ops
---

# /log-time - Log Working Hours

Parse `$ARGUMENTS` for hours, work item ID, and optional category.

## Input Format

```
/log-time <hours>h [#WORK_ITEM_ID] ["description"]
/log-time <hours>h <category>
```

| Argument | Required | Description |
|----------|----------|-------------|
| Hours | Required | Number with `h` suffix (e.g., `3h`, `1.5h`) |
| `#ID` | Optional | Work item to log against (updates CompletedWork) |
| Category | Optional | General category: `meeting`, `research`, `learning`, `review`, `admin` |
| Description | Optional | Quoted text description of work done |

## Workflow

1. **Parse** hours, target (work item or category), description
2. If work item ID given:
   - Fetch current CompletedWork via `wit_get_work_item`
   - Calculate new CompletedWork (existing + logged hours)
   - Update RemainingWork if applicable
   - Present confirmation per `rules/write-gate.md`
   - Execute via `wit_update_work_item`
3. If category given:
   - Store locally in timesheet tracker
4. **Report** updated totals

## Example

```
User: /log-time 3h #1401 "Fixed geocoding timeout and added retry logic"

Output:
READY TO UPDATE: #1401 [Dev] Fix geocoding timeout
----------------------------------
CompletedWork:  5h -> 8h (+3h)
RemainingWork:  3h -> 0h
Description:    Fixed geocoding timeout and added retry logic

Proceed? (yes/no)

User: yes

Output:
Updated #1401: CompletedWork = 8h, RemainingWork = 0h
Today's total: 6h / 6h target ✓
```
