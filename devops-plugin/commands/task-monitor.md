---
title: 'Task Monitor'
read_only: false
type: 'command'
description: 'Periodic work item monitor - alerts on new Azure DevOps assignments. Use with /loop 15m /task-monitor'
---

# Task Monitor

Periodic work item monitor that detects NEW Azure DevOps assignments and alerts you.
Designed to run automatically via `/loop 15m /task-monitor` as a background cron job.

## Usage

```
/task-monitor                   # Run one check (first run: sets baseline)
/loop 15m /task-monitor         # Auto-check every 15 minutes
/loop 30m /task-monitor         # Auto-check every 30 minutes
/task-monitor --reset           # Clear state and re-baseline all current items
```

## Tool Selection Guard

```
+---------------------------------------------------------------+
|                    MANDATORY TOOL SELECTION                     |
+---------------------------------------------------------------+
|                                                                |
|  USE: wit_my_work_items        (purpose-built for my tasks)    |
|  NEVER: search_workitem        (TEXT SEARCH - returns 0!)      |
|                                                                |
|  Always bypass cache - use live API data for monitoring        |
|                                                                |
+---------------------------------------------------------------+
```

## State File

The monitor persists state between loop ticks in `~/.claude/task-monitor-state.json`:

```json
{
  "lastChecked": "2025-12-01T09:00:00Z",
  "knownItemIds": [1234, 1235, 1828],
  "alertCount": 0,
  "checkCount": 0
}
```

- `lastChecked` - ISO-8601 timestamp of last successful check
- `knownItemIds` - All work item IDs seen as of last check (used for diff)
- `alertCount` - Running count of alerts sent this session
- `checkCount` - Running count of checks performed this session

## Workflow

### Step 0: Bootstrap State File

```
1. Try to Read ~/.claude/task-monitor-state.json
2. If NOT found OR --reset flag:
   a. Set isFirstRun = true
   b. knownItemIds = []  (empty - will populate from API then save as baseline)
   c. alertCount = 0, checkCount = 0
3. If found:
   a. Parse JSON
   b. isFirstRun = false
   c. Load knownItemIds, alertCount, checkCount
```

### Step 1: Force-Fetch Current Work Items

Always call the API directly - never use the work-tracker cache for monitoring.

```javascript
// Step 1a: Get all projects
mcp__azure-devops__core_list_projects()

// Step 1b: For EACH project, fetch assigned items IN PARALLEL
mcp__azure-devops__wit_my_work_items({
  "project": "<project_name>",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 100
})

// Step 1c: Batch-fetch full details for all IDs across all projects
mcp__azure-devops__wit_get_work_items_batch_by_ids({
  "project": "<project_name>",
  "ids": [/* IDs from step 1b */],
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

Run Step 1b in parallel across all projects for speed.

Build `currentItems` array and `currentIds` set from results.

### Step 2: Compute Diff

```
newItemIds = currentIds - knownItemIds   (IDs in current but NOT in known)
removedIds = knownItemIds - currentIds   (IDs in known but NOT in current - completed/removed)

newItems = currentItems filtered to newItemIds
```

### Step 3: Output Results

#### Case A: First Run (isFirstRun = true)

```markdown
## Task Monitor - First Run Baseline

Scanned [N] projects. Found [X] active work items assigned to you.
All saved as baseline - no alerts for existing items.

### Current Work Items ([X] total)

| ID | Project | Type | Title | Priority |
|----|---------|------|-------|----------|
| #1234 | KhairGate | Task | [DEV] Wallet sync | P1 |
| #1235 | Relief | Bug | Geocoding fix | P2 |
...

---

### Start Automatic Monitoring

To get alerts for NEW assignments, run the loop:

  /loop 15m /task-monitor      # Alert me every 15 minutes
  /loop 30m /task-monitor      # Alert me every 30 minutes

Run /task-monitor manually anytime for an instant check.
```

#### Case B: New Items Found (newItems.length > 0)

```markdown
## ALERT: [N] New Work Item(s) Assigned to You

| ID | Project | Type | Title | Priority | Sprint |
|----|---------|------|-------|----------|--------|
| #1890 | KhairGate | Task | [DEV] Add wallet sync | P1 | Sprint 15 |
| #1891 | Relief Center | Bug | Fix geocoding error | P2 | Sprint 15 |

Run /my-tasks for full list | /workday for dashboard | /log-time to track hours

---

## Task Monitor Summary - [HH:MM AM/PM] (Check #[checkCount])

| Metric | Value |
|--------|-------|
| Total Active Items | [X] |
| High Priority (P1-P2) | [X] |
| New This Check | [N] |
| Completed/Removed | [R] |
| Last Checked | [previous lastChecked formatted] |
| Total Alerts This Session | [alertCount] |
```

#### Case C: No New Items

```markdown
## Task Monitor - [HH:MM AM/PM] (Check #[checkCount])

No new assignments since [lastChecked formatted as "Mon DD, HH:MM AM/PM"].

| Total Active | High Priority (P1-P2) | Completed/Removed |
|:------------:|:---------------------:|:-----------------:|
| [X] | [X] | [R] |

Next auto-check running via /loop | Run /my-tasks for full list
```

### Step 4: Update State File

```javascript
// Write updated state
Write("~/.claude/task-monitor-state.json", {
  "lastChecked": "<current ISO-8601 timestamp>",
  "knownItemIds": currentIds,          // Full current set (not just new ones)
  "alertCount": alertCount + (newItems.length > 0 ? 1 : 0),
  "checkCount": checkCount + 1
})
```

## Alert Priority Rules

- **P1 items**: Always show at top of alert block regardless of when assigned
- **P2 items**: Show in order they appear in the diff
- **P3-P4 items**: Show at bottom of alert block

## Error Handling

| Error | Recovery |
|-------|----------|
| API auth fails | Show "Auth error. Run /devops to reconfigure." Do not update state file. |
| No projects found | Show "No Azure DevOps projects found. Check organization config." |
| Some projects fail | Fetch successful projects, warn about failed ones. Partial update is OK. |
| State file corrupt | Treat as first run, rebuild baseline from API. |
| State file write fails | Show results but warn: "Could not save state. Alerts may repeat next check." |

## Integration with Work Tracker

The task monitor is intentionally separate from the work-tracker cache:

- `/task-monitor` - Always fetches live (for alert accuracy)
- `/workday --tasks` - Uses 4-hour cache (for speed)
- `/workday --sync` - Refreshes the cache (for other commands)

After an alert, you can run `/workday --sync` to refresh the main cache too.

## Related Commands

- `/workday --tasks` - View all assigned tasks (cache-first)
- `/workday` - Full daily dashboard with time tracking
- `/workday --sync` - Force-sync work items to local cache
- `/log-time` - Log hours against a work item
- `/loop 15m /task-monitor` - Start automatic monitoring

---

*Part of DevOps Plugin v4.0 - Task Monitor System*
*Tool Selection Guard: Enabled*
*State: ~/.claude/task-monitor-state.json*
