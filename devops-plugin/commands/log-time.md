---
title: 'Log Time'
read_only: false
type: 'command'
description: 'Log working hours against work items or general categories'
---

# Log Time

Log working hours against Azure DevOps work items or general categories (meetings, research, learning, etc.).

## Usage

```
/log-time 3h #1828 "Map duration investigation"
/log-time 1.5h meeting "Sprint planning session"
/log-time 2h research "MapTiler 3D performance docs"
/log-time 1h learning "Odoo 19 migration patterns"
/log-time 0.5h review "PR #45 code review"
/log-time 1h admin "Email coordination with client"
/log-time 4h #2001 "Wallet API models" --date 2026-03-05
```

## Parsing Rules

Parse the user's input to extract:

| Component | Pattern | Required | Examples |
|-----------|---------|----------|---------|
| **Hours** | Number followed by `h` | YES | `3h`, `1.5h`, `0.5h`, `2h` |
| **Target** | `#ID` for work item, or type name | YES | `#1828`, `meeting`, `research` |
| **Description** | Quoted string or remaining text | YES | `"Sprint planning"` |
| **Date** | `--date YYYY-MM-DD` | NO (defaults to today) | `--date 2026-03-05` |

**Valid hour types**: `task`, `meeting`, `research`, `learning`, `review`, `admin`

When a `#ID` is provided, the type is automatically set to `task`.

## Workflow

### Step 1: Parse Input

```
1. Extract hours (number before 'h')
2. Extract target:
   - If starts with '#': workItemId = number, type = "task"
   - If matches a valid hourType: type = that type, workItemId = null
3. Extract description (quoted or remaining text)
4. Extract --date if provided, otherwise use today
5. Validate:
   - Hours must be > 0 and <= 24
   - If type = "task", verify #ID exists in cachedWorkItems
   - If #ID not in cache, warn but allow (item may not be synced yet)
```

### Step 2: Read Tracker Data

```
1. Read ~/.claude/work-tracker-data.json
2. If NOT found: run bootstrap (same as /workday Step 0)
3. Parse JSON
```

### Step 3: Add Time Entry

```
1. Get date string (YYYY-MM-DD format)
2. Get or create timeLog[dateStr]:
   {
     "entries": [],
     "total": 0,
     "isTimeOff": false
   }
3. Check if day is marked as time-off:
   - If YES: warn "This day is marked as time-off. Log anyway? (y/n)"
4. Append new entry:
   {
     "hours": <parsed hours>,
     "type": "<parsed type>",
     "workItemId": <parsed ID or null>,
     "description": "<parsed description>"
   }
5. Recalculate total = sum of all entries[].hours for that date
6. Write updated work-tracker-data.json
```

### Step 4: Regenerate Day Section in work-tracker.md

```
1. Read existing work-tracker.md (or create from scratch if missing)
2. Find or create the section for the target date:
   ### [Month Year]
   #### Week N (Mon Date - Fri Date)
   ##### [DayName], [Month] [Day]
3. Regenerate the day's table:
   | Hours | Type | Work Item | Description |
   |-------|------|-----------|-------------|
   | 3.0 | task | #1828 | Map duration investigation |
   | 1.0 | meeting | - | Sprint planning |
   | **{total}** | **TOTAL** | | |
4. Update Compliance Dashboard section
5. Write updated work-tracker.md
```

### Step 5: Compliance Check & Report

```markdown
## Time Logged

| Field | Value |
|-------|-------|
| Date | [date] |
| Hours | [hours]h |
| Type | [type] |
| Work Item | [#ID or -] |
| Description | [description] |

### Today's Status
| Logged | Required | Remaining |
|--------|----------|-----------|
| [total]h | [min]h | [max(0, min - total)]h |

[If total >= min]: "Target met! You've logged enough hours for today."
[If total < min]: "!! [remaining]h still needed today. Log more with /log-time"
```

If the work item ID was provided and exists in cache, also show the work item title:
```
Logged 3.0h against #1828: "Investigate map duration" (Relief Center)
```

## Batch Logging

Users may provide multiple entries at once. Handle naturally:

```
User: "I spent 3h on #1828, 1h in a meeting, and 1.5h on research today"

→ Log 3 separate entries for today
→ Show combined report with total
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Invalid hours format | "Could not parse hours. Use format: /log-time 3h #1234 'description'" |
| Unknown hour type | "Unknown type '{type}'. Valid types: task, meeting, research, learning, review, admin" |
| Work item not in cache | "#{id} not found in local cache. Logging anyway. Run /work-sync to refresh cache." |
| Tracker file missing | Bootstrap from defaults, then proceed |
| Hours would exceed 24h for day | "Warning: Total for {date} would be {total}h (over 24h). Continue? (y/n)" |

## Related Commands

- `/workday` - See full daily dashboard with time log
- `/timesheet` - View time tracking by week or month
- `/time-off` - Mark a day as time-off
- `/work-sync` - Refresh work item cache

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
