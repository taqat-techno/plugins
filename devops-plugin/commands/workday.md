---
title: 'Workday Dashboard'
read_only: false
type: 'command'
description: 'Daily login dashboard - see your work items, log hours, track compliance'
---

# Workday Dashboard

Your daily "login" command. One command to see everything: what you're working on, hours logged today, compliance status, and weekly alerts.

## Usage

```
/workday                    # Full daily dashboard
/workday --quick            # Just compliance status + alerts (no sync)
```

## Tool Selection Guard

**Reference**: `guards/tool_selection_guard.md`

```
+---------------------------------------------------------------+
|                    MANDATORY TOOL SELECTION                     |
+---------------------------------------------------------------+
|                                                                |
|  For work item fetching (when sync needed):                    |
|  USE: wit_my_work_items                                        |
|  NEVER: search_workitem (TEXT SEARCH ONLY - returns 0!)        |
|                                                                |
|  For file operations:                                          |
|  USE: Read tool for ~/.claude/work-tracker-data.json           |
|  USE: Write tool for updating tracker files                    |
|                                                                |
+---------------------------------------------------------------+
```

## Workflow

### Step 0: Bootstrap Check

Check if the work tracker files exist:

```
1. Try to Read ~/.claude/work-tracker-data.json
2. If file NOT found:
   a. Read plugin's data/work_tracker_defaults.json for default settings
   b. Create ~/.claude/work-tracker-data.json with:
      {
        "version": "1.0.0",
        "lastSync": null,
        "stalenessThresholdHours": 4,
        "organization": null,
        "settings": { /* copy from defaults */ },
        "timeOff": [],
        "cachedWorkItems": [],
        "timeLog": {}
      }
   c. Inform user: "First time setup! Syncing your work items from Azure DevOps..."
   d. Proceed to Step 1 with force sync
3. If file found: parse JSON and proceed
```

### Step 1: Staleness Check & Auto-Sync

```
1. Read lastSync from work-tracker-data.json
2. Calculate hours since last sync
3. If lastSync is null OR hours > stalenessThresholdHours:
   → Run sync workflow (same as /work-sync):
     a. List projects: mcp__azure-devops__core_list_projects()
     b. For each project, fetch work items:
        mcp__azure-devops__wit_my_work_items({
          "project": "<project>",
          "type": "assignedtome",
          "includeCompleted": false,
          "top": 100
        })
     c. Get full details:
        mcp__azure-devops__wit_get_work_items_batch_by_ids({
          "project": "<project>",
          "ids": [<ids>],
          "fields": ["System.Id", "System.Title", "System.State",
                     "System.WorkItemType", "Microsoft.VSTS.Common.Priority",
                     "System.IterationPath", "System.TeamProject"]
        })
     d. Update cachedWorkItems in JSON
     e. Update lastSync timestamp
     f. Write work-tracker-data.json
     g. Regenerate work-tracker.md
4. If data is FRESH:
   → Skip sync, show "Data fresh (synced Xh ago)"
```

**For `--quick` mode**: Skip sync entirely, use whatever data exists.

### Step 2: Build Today's Dashboard

Read the work-tracker-data.json and compute:

**A. Today's Date Info**
```
- Current date, day name, week number
- Is today a working day? (check settings.workingDays)
- Is today time-off? (check timeOff array)
```

**B. Active Work Items** (from cachedWorkItems)
```
- Filter: state NOT IN ('Done', 'Closed', 'Removed', 'Resolved')
- Group by project
- Sort by priority within each group
```

**C. Today's Time Log** (from timeLog[today])
```
- List all entries with hours, type, work item, description
- Calculate running total
```

**D. Compliance Status**
```
- Today: X/minHoursPerDay logged
- Remaining: max(0, minHoursPerDay - logged)
- This week: check each working day
- Flag any under-logged days
```

### Step 3: Display Dashboard

```markdown
## Workday Dashboard - [Day], [Date]

### Sync Status
Data synced [X hours ago] | [N] active work items across [M] projects
[Run /work-sync --force to refresh]

---

### Your Active Work Items

#### [Project Name] ([count] items)
| ID | Type | Title | State | Priority |
|----|------|-------|-------|----------|
| #1234 | Task | Fix login issue | Active | P1 |
| #1235 | Bug | UI alignment | New | P2 |

#### [Another Project] ([count] items)
| ID | Type | Title | State | Priority |
|----|------|-------|-------|----------|
| #2001 | Task | Wallet API | Active | P1 |

---

### Today's Time Log
| Hours | Type | Work Item | Description |
|-------|------|-----------|-------------|
| 3.0 | task | #1234 | Fixed login timeout handling |
| 1.0 | meeting | - | Sprint planning |
| **4.0** | **TOTAL** | | |

---

### Compliance
| Status | Today | This Week |
|--------|-------|-----------|
| Logged | 4.0h | 22.0h |
| Required | 6.0h | 30.0h |
| Remaining | 2.0h | 8.0h |

**!! 2.0 hours remaining today** - Log more time with `/log-time`

#### This Week's Days
| Day | Status | Hours |
|-----|--------|-------|
| Mon | OK | 6.5h |
| Tue | OK | 6.0h |
| Wed | TIME-OFF | - |
| Thu | OK | 6.0h |
| Fri | PENDING | 4.0h |

---

### Quick Actions
- `/log-time 2h #1234 "description"` - Log hours
- `/timesheet --week` - Full weekly view
- `/time-off today "reason"` - Mark today as time-off
- `/work-sync --force` - Refresh work items
```

### Step 4: Interactive Prompt (Full Mode Only)

After displaying the dashboard, ask:

> "What would you like to do? You can:
> 1. **Log time** - Tell me the hours, work item, and what you did
> 2. **View timesheet** - See your full week or month
> 3. **Continue working** - I'll keep this context for the session
>
> Or just start working on a task and I'll help track it!"

If the user provides time logging info, execute the `/log-time` workflow inline.

## --quick Mode Output

For `--quick` mode, show only:

```markdown
## Workday Quick Status - [Date]

**Today**: [X]h / [min]h logged ([remaining]h remaining)
**This Week**: [X]h / [required]h ([working_days] working days)

### Alerts
- [Day]: [X]h logged (under by [Y]h)
- No alerts - you're on track!
```

## Error Handling

| Error | Recovery |
|-------|----------|
| work-tracker-data.json not found | Bootstrap from defaults (Step 0) |
| Azure DevOps API fails during sync | Show cached data with warning: "Showing cached data. Sync failed: [error]" |
| No work items found | Show empty dashboard with "No active work items. Create tasks with /create-task" |
| Time log empty for today | Show 0h logged with reminder to use /log-time |

## Best Practices

1. **Run at session start** - Get oriented with your daily work
2. **Use --quick for fast checks** - No API calls, instant compliance view
3. **Log time throughout the day** - Don't wait until end of day
4. **Check weekly compliance** - Catch under-logged days early

## Related Commands

- `/log-time` - Log hours against work items
- `/timesheet` - Detailed time tracking views
- `/time-off` - Mark days as time-off
- `/work-sync` - Force sync with Azure DevOps
- `/my-tasks` - View work items (cache-first)
- `/standup` - Generate standup notes (enriched with time data)

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
