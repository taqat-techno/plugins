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

## Estimating time from session transcripts

When the user asks to reconstruct hours from Claude session logs (e.g. "how long did I spend today?") instead of giving an explicit `<hours>h`, do **not** estimate by summing only the gaps between consecutive human messages and cutting every idle gap. That naive idle-cut **undercounts**: a long gap is often the agent working, not the user idle.

- **Count agent/workflow runtime.** A background agent, a `/loop`, or a long tool run can occupy a **20–90 minute** gap in which real work happened even though no human message was sent. Treat a gap that brackets active tool/agent activity as worked time, not idle time — only trim gaps with no activity on either side.
- **De-overlap parallel sessions.** Two concurrent sessions (or an agent running while you work elsewhere) cover the **same wall-clock minutes**. Summing each session's span double-counts. Merge overlapping intervals across sessions and count the union once.
- **Present the estimate as an estimate.** Show the derived total and the assumption (which gaps were counted as worked) and confirm per `rules/write-gate.md` before writing it to any work item — a reconstructed number is an input to review, not a fact to log silently.
