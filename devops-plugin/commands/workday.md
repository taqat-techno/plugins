---
title: 'Workday Dashboard'
read_only: false
type: 'command'
description: 'Daily login dashboard - see your work items, log hours, track compliance. Flags: --sync (force API sync), --tasks (work items table), --todo (sync to Claude TODO list)'
---

# Workday Dashboard

Your daily "login" command. One command to see everything: what you're working on, hours logged today, compliance status, and weekly alerts.

## Usage

```
/workday                    # Full daily dashboard (default)
/workday --quick            # Just compliance status + alerts (no sync)
/workday --sync             # Force sync with Azure DevOps API (ignores staleness)
/workday --tasks            # Show only work items table (cache-first)
/workday --todo             # Sync work items to Claude TODO list
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

**For `--sync` mode**: Skip staleness check, always fetch from API (replaces `/work-sync --force`).

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
[Run /workday --sync to refresh]

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
- `/workday --sync` - Refresh work items
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

## --tasks Mode (replaces /my-tasks)

Display all active work items assigned to the current user, using cache-first strategy.

### Step 0: Check Local Cache

```
1. Try to Read ~/.claude/work-tracker-data.json
2. If found AND lastSync is not null:
   a. Calculate hours since lastSync
   b. If hours <= stalenessThresholdHours (default 4):
      → Data is FRESH - display from cachedWorkItems
      → Show "Source: Local cache (synced Xh ago) | Run /workday --sync to refresh"
      → Group by project, sort by priority
      → STOP (no API calls needed)
   c. If hours > threshold:
      → Data is STALE - proceed to API fetch
3. If NOT found or lastSync is null:
   → No cache available - proceed to API fetch
4. After API fetch completes:
   a. Update cachedWorkItems in work-tracker-data.json
   b. Update lastSync timestamp
   c. Write updated work-tracker-data.json
   d. Show "Source: Azure DevOps API (cache updated)"
```

### Step 1: Query Work Items (if cache is stale/missing)

**Use `wit_my_work_items` - this is the CORRECT tool (never `search_workitem`)!**

```javascript
// For each project:
mcp__azure-devops__wit_my_work_items({
  "project": "Project Alpha",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 50
})
```

### Step 2: Get Full Details

```javascript
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "Project Alpha",
  "ids": [1746, 1828, 1651],
  "fields": [
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
    "Microsoft.VSTS.Common.Priority",
    "System.IterationPath",
    "System.TeamProject"
  ]
})
```

### Output Format

```markdown
## My Work Items

**Project**: Project Alpha | **Total**: 12 items

### Active (In Progress)
| ID | Type | Title | Priority | Sprint |
|----|------|-------|----------|--------|
| #1234 | Bug | Fix login issue | P1 | Sprint 15 |
| #1235 | Task | Add validation | P2 | Sprint 15 |

### New (Not Started)
| ID | Type | Title | Priority | Sprint |
|----|------|-------|----------|--------|
| #1240 | Task | Write unit tests | P2 | Sprint 15 |

### Summary
- **Total**: 12 items
- **Active**: 5
- **New**: 7
- **High Priority (P1-P2)**: 8
```

## --todo Mode (replaces /sync-my-tasks)

Sync Azure DevOps work items to Claude Code's built-in TODO list.

### Step 1: Fetch Work Items

Use the same fetch logic as `--tasks` mode (cache-first with staleness check, then `wit_my_work_items` + `wit_get_work_items_batch_by_ids` if needed).

### Step 2: State Mapping

| Azure DevOps State | TODO Status |
|-------------------|-------------|
| New, To Do | pending |
| Active, In Progress | in_progress |
| Done, Closed, Resolved | completed |
| Removed | (skip - don't add) |

### Step 3: Smart Update Logic

1. **Read existing TODOs** (if any)
2. **Match by work item ID** - Look for `#1234` pattern in content
3. **For existing items**: Update status if changed
4. **For new items**: Add to TODO list
5. **Preserve non-DevOps TODOs** - Don't remove manually added items (items without `#` prefix)

### Step 4: Use TodoWrite Tool

```
TodoWrite({
  "todos": [
    // Existing non-DevOps todos (preserved - no # pattern)
    {"content": "Manual todo item", "status": "pending", "activeForm": "Working on manual item"},

    // Synced Azure DevOps items (with project name and link)
    {"content": "[Project Alpha] #1234 Task: Fix login bug | https://dev.azure.com/YOUR-ORG/Relief%20Center/_workitems/edit/1234", "status": "in_progress", "activeForm": "Fixing login bug (#1234)"},
    {"content": "[Project Alpha] #1235 Bug: UI alignment issue | https://dev.azure.com/YOUR-ORG/Relief%20Center/_workitems/edit/1235", "status": "pending", "activeForm": "Fixing UI alignment (#1235)"},
    {"content": "[Project Gamma] #1236 PBI: Add dark mode | https://dev.azure.com/YOUR-ORG/Property%20Management/_workitems/edit/1236", "status": "pending", "activeForm": "Implementing dark mode (#1236)"}
  ]
})
```

### Step 5: Update Persistent Cache

Also update `~/.claude/work-tracker-data.json` with the fetched work items (same as sync workflow - update `cachedWorkItems` and `lastSync`).

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
- `/timesheet` - Detailed time tracking views (includes `--off` for time-off)
- `/standup` - Generate standup notes (enriched with time data)

> **Note**: `/my-tasks`, `/work-sync`, and `/sync-my-tasks` have been absorbed into this command as `--tasks`, `--sync`, and `--todo` flags respectively. Previously available as `/my-tasks`, `/work-sync`, `/sync-my-tasks`.

---

*Part of DevOps Plugin v4.0 - Work Tracking System*
