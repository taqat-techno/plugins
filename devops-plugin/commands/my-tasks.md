---
title: 'My Tasks'
read_only: true
type: 'command'
description: 'List all work items assigned to you'
---

# My Tasks

Display all active work items assigned to the current user.

## 🛡️ TOOL SELECTION GUARD

**Reference**: `guards/tool_selection_guard.md`

```
┌─────────────────────────────────────────────────────────────────┐
│                    MANDATORY TOOL SELECTION                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ CORRECT: wit_my_work_items                                   │
│     Fast, reliable, purpose-built for this exact task            │
│                                                                  │
│  ❌ WRONG: search_workitem                                       │
│     TEXT SEARCH ONLY - Returns 0 results for "my tasks"!         │
│                                                                  │
│  ⚠️ ALTERNATIVE: CLI WIQL (for complex filters)                  │
│     Use when wit_my_work_items doesn't support your filter       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Instructions

### Step 0: Check Local Cache (Work Tracker)

Before making API calls, check if cached data in the work tracker is fresh:

```
1. Try to Read ~/.claude/work-tracker-data.json
2. If found AND lastSync is not null:
   a. Calculate hours since lastSync
   b. If hours <= stalenessThresholdHours (default 4):
      → Data is FRESH - display from cachedWorkItems
      → Show "Source: Local cache (synced Xh ago) | Run /work-sync --force to refresh"
      → Group by project, sort by priority
      → Use the same Output Format below
      → STOP (no API calls needed)
   c. If hours > threshold:
      → Data is STALE - proceed to Step 1 (API fetch)
3. If NOT found or lastSync is null:
   → No cache available - proceed to Step 1 (API fetch)
4. After API fetch completes (Steps 1-3):
   a. Update cachedWorkItems in work-tracker-data.json
   b. Update lastSync timestamp
   c. Write updated work-tracker-data.json
   d. Show "Source: Azure DevOps API (cache updated)"
```

### Step 1: Get Projects (Optional Context)

If user hasn't specified a project:

```javascript
mcp__azure-devops__core_list_projects()
```

### Step 2: Query My Work Items (PRIMARY METHOD)

**Use `wit_my_work_items` - this is the CORRECT tool!**

```javascript
// For each project (or user's default project):
mcp__azure-devops__wit_my_work_items({
  "project": "Project Alpha",      // ← REQUIRED
  "type": "assignedtome",          // or "myactivity"
  "includeCompleted": false,       // Exclude Done/Closed
  "top": 50                        // Max items
})
```

### Step 3: Get Full Details

The above returns IDs only. Get full details:

```javascript
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "Project Alpha",
  "ids": [1746, 1828, 1651],  // IDs from step 2
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

## DO NOT USE These Tools

### ❌ search_workitem - TEXT SEARCH ONLY

```javascript
// WRONG - Returns 0 results! Filters are IGNORED!
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["@Me"],     // ❌ IGNORED
  "state": ["Active"]        // ❌ IGNORED
})
```

**Why it fails**: `search_workitem` searches TEXT in title/description. It does NOT filter by AssignedTo or State.

## Alternative: CLI WIQL Query

For complex filters not supported by `wit_my_work_items`:

```bash
az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
         [Microsoft.VSTS.Common.Priority], [System.IterationPath]
  FROM WorkItems
  WHERE [System.TeamProject] = 'Project Alpha'
    AND [System.AssignedTo] = @Me
    AND [System.State] <> 'Closed'
    AND [System.State] <> 'Removed'
  ORDER BY [Microsoft.VSTS.Common.Priority], [System.WorkItemType]
" --output json
```

## Output Format

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

## Guard Checklist

Before executing, verify:

- [ ] Tool is `wit_my_work_items` (NOT `search_workitem`)
- [ ] Project parameter is provided
- [ ] `includeCompleted` set based on user preference
- [ ] Will use `wit_get_work_items_batch_by_ids` for full details
- [ ] Check local cache first (Step 0) before API calls

## Related Commands

- `/workday` - Full daily dashboard with time tracking
- `/work-sync` - Force sync work items to local cache
- `/sync-my-tasks` - Sync tasks to Claude TODO list
- `/log-time` - Log hours against work items

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
*Tool Selection Guard: Enabled*
*Cache-First: Enabled*
