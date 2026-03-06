---
title: 'Work Sync'
read_only: false
type: 'command'
description: 'Sync Azure DevOps work items to persistent local tracker files'
---

# Work Sync

Synchronize your Azure DevOps work items to the persistent local work tracker files (`~/.claude/work-tracker-data.json` and `~/.claude/work-tracker.md`).

## Usage

```
/work-sync                              # Sync if data is stale (>4h old)
/work-sync --force                      # Force sync regardless of staleness
/work-sync --project "Project Alpha"    # Sync only specific project
```

## Tool Selection Guard

**Reference**: `guards/tool_selection_guard.md`

```
+---------------------------------------------------------------+
|                    MANDATORY TOOL SELECTION                     |
+---------------------------------------------------------------+
|                                                                |
|  USE: wit_my_work_items        (purpose-built for my tasks)    |
|  NEVER: search_workitem        (TEXT SEARCH - returns 0!)      |
|                                                                |
+---------------------------------------------------------------+
```

## Workflow

### Step 1: Bootstrap & Staleness Check

```
1. Try to Read ~/.claude/work-tracker-data.json
2. If NOT found:
   a. Read data/work_tracker_defaults.json from plugin
   b. Create work-tracker-data.json with defaults + empty arrays
   c. Set forceSyncNeeded = true
3. If found AND NOT --force:
   a. Parse lastSync timestamp
   b. Calculate age in hours
   c. If age <= stalenessThresholdHours:
      → Report "Data is fresh (synced Xh ago). Use --force to refresh."
      → STOP (no API calls needed)
   d. If age > threshold: continue to sync
4. If --force: continue to sync regardless
```

### Step 2: Fetch Work Items from Azure DevOps

**If --project is specified**: query only that project.
**Otherwise**: list all projects and query each.

```javascript
// Step 2a: Get projects (skip if --project specified)
mcp__azure-devops__core_list_projects()

// Step 2b: For EACH project, get my work items
mcp__azure-devops__wit_my_work_items({
  "project": "<project_name>",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 100
})

// Step 2c: Get full details for returned IDs
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "<project_name>",
  "ids": [/* IDs from step 2b */],
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

**Run multiple project queries in parallel** for speed.

### Step 3: Update Local Cache

```
1. Transform each work item to cached format:
   {
     "id": <System.Id>,
     "project": "<System.TeamProject>",
     "type": "<System.WorkItemType>",
     "title": "<System.Title>",
     "state": "<System.State>",
     "priority": <Microsoft.VSTS.Common.Priority>,
     "iterationPath": "<System.IterationPath>",
     "url": "https://dev.azure.com/{ORG}/{PROJECT_URL_ENCODED}/_workitems/edit/{ID}",
     "lastFetched": "<current ISO-8601 timestamp>"
   }
2. REPLACE the cachedWorkItems array entirely (full refresh)
3. Update lastSync to current ISO-8601 timestamp
4. Auto-detect organization from project URLs if organization is null
5. Write updated work-tracker-data.json
```

**URL encoding**: Encode project names with spaces (e.g., "Relief Center" -> "Relief%20Center")

### Step 4: Regenerate work-tracker.md

Build the full markdown file from JSON data:

```markdown
<!-- WORK TRACKER - Auto-managed by DevOps Plugin -->
<!-- Last Synced: {lastSync} -->

# Work Tracker

## Sync Status
| Property | Value |
|----------|-------|
| Last Sync | {formatted lastSync} |
| Stale After | {lastSync + stalenessThresholdHours} |
| Total Active Items | {count of non-Done items} |
| Projects | {comma-separated project names} |

---

## Current Sprint

| ID | Project | Type | Title | State | Priority |
|----|---------|------|-------|-------|----------|
| #{id} | {project} | {type} | {title} | {state} | P{priority} |
...

---

## Time Log

{existing time log sections - preserve from previous data}

---

## Compliance Dashboard

{regenerate from timeLog + timeOff + settings}

---

## Completed Items (Recent)

| ID | Project | Type | Title | Completed |
|----|---------|------|-------|-----------|
{items where state = Done/Closed, from last 7 days if available}
```

### Step 5: Also Sync to TodoWrite (Existing Behavior)

Preserve compatibility with `/sync-my-tasks` by also updating Claude's built-in TODO list:

```
TodoWrite({
  "todos": [
    // Preserve non-DevOps manual TODOs
    // Add synced work items with project name and link
    {
      "content": "[{project}] #{id} {type}: {title} | {url}",
      "status": "{mapped_status}",
      "activeForm": "Working on {title} (#{id})"
    }
  ]
})
```

**State mapping**: New/To Do -> pending, Active/In Progress -> in_progress, Done/Closed -> completed

### Step 6: Report Results

```markdown
## Work Items Synced

| Project | Active | New | Total |
|---------|--------|-----|-------|
| {project1} | {n} | {n} | {n} |
| {project2} | {n} | {n} | {n} |
| **Total** | **{n}** | **{n}** | **{n}** |

### Files Updated
- ~/.claude/work-tracker-data.json (cache + {n} items)
- ~/.claude/work-tracker.md (dashboard regenerated)
- Claude TODO list (synced)

Last synced: {timestamp}
Next refresh after: {timestamp + threshold}
```

## Error Handling

| Error | Recovery |
|-------|----------|
| API authentication fails | Show: "Auth failed. Run /devops to reconfigure." |
| No projects found | Show: "No projects found. Check your DevOps organization." |
| Some projects fail, others succeed | Sync successful projects, warn about failures |
| File write permission error | Show: "Cannot write to ~/.claude/. Check permissions." |

## Related Commands

- `/workday` - Daily dashboard (auto-triggers sync if stale)
- `/my-tasks` - View tasks (uses cache first)
- `/sync-my-tasks` - Legacy sync to TODO list only
- `/log-time` - Log hours against synced work items

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
