# Work Tracking Memory

> **Purpose**: Patterns for reading, writing, and managing the persistent work tracker files. These files live in the user's `~/.claude/` directory and persist across all Claude CLI sessions.

## File Locations

| File | Purpose | Format |
|------|---------|--------|
| `~/.claude/work-tracker.md` | Human-readable dashboard | Markdown |
| `~/.claude/work-tracker-data.json` | Machine-readable data store | JSON |
| Plugin: `data/work_tracker_defaults.json` | Default settings template | JSON |

## First-Run Bootstrapping

On first use of `/workday`, `/workday --sync`, or `/log-time`:

1. Check if `~/.claude/work-tracker-data.json` exists
2. If NOT: read `data/work_tracker_defaults.json` from plugin directory
3. Create `work-tracker-data.json` with defaults + empty arrays:
   ```json
   {
     "version": "1.0.0",
     "lastSync": null,
     "stalenessThresholdHours": 4,
     "organization": null,
     "settings": { /* from defaults */ },
     "timeOff": [],
     "cachedWorkItems": [],
     "timeLog": {}
   }
   ```
4. Trigger a `/workday --sync` to populate `cachedWorkItems`
5. Generate `work-tracker.md` from the JSON data

## Staleness Check Pattern

```
1. Read work-tracker-data.json
2. Parse lastSync as ISO-8601 timestamp
3. Calculate age = currentTime - lastSync (in hours)
4. If age > stalenessThresholdHours (default 4):
   → Data is STALE → trigger API refresh
5. If age <= threshold:
   → Data is FRESH → use cached data
6. If lastSync is null:
   → Never synced → trigger first sync
```

## Time Entry Logging Pattern

### Adding a Time Entry
```
1. Read work-tracker-data.json
2. Get today's date as "YYYY-MM-DD" string
3. Get or create timeLog[dateStr] with empty entries array
4. Append new entry:
   {
     "hours": <number>,
     "type": "task|meeting|research|learning|review|admin",
     "workItemId": <number|null>,
     "description": "<string>"
   }
5. Recalculate total = sum of all entries[].hours
6. Write back work-tracker-data.json
7. Regenerate the day section in work-tracker.md
8. Run compliance check
```

### Hour Types

| Type | Description | Requires Work Item |
|------|-------------|-------------------|
| `task` | Direct work on a DevOps work item | YES (#ID required) |
| `meeting` | Team meetings, standups, planning, reviews | NO |
| `research` | Technical research, reading docs, investigation | NO |
| `learning` | Training, courses, tutorials, skill development | NO |
| `review` | Code reviews, PR reviews, design reviews | NO |
| `admin` | Administrative tasks, emails, coordination | NO |

## Compliance Check Logic

```
1. Get today's date and day name (Mon-Sun)
2. Check if today is in settings.workingDays → if NO, skip (weekend)
3. Check if today is in timeOff array → if YES, skip (time-off)
4. Get timeLog[today].total (default 0)
5. Compare with settings.minHoursPerDay (default 6)
6. If total < minHoursPerDay:
   → ALERT: "Today: {total}h / {min}h logged. {remaining}h remaining."
7. If total >= minHoursPerDay:
   → OK: "Today: {total}h / {min}h logged. Target met!"
```

### Weekly Compliance
```
1. Get all dates in current week (Mon-Fri)
2. For each date:
   - Skip if in timeOff array
   - Skip if weekend (not in workingDays)
   - Check if total >= minHoursPerDay
3. Count: working days, time-off days, compliant days, under-logged days
4. Calculate: total hours, required hours, average per day
5. Flag any under-logged days with specific shortfall
```

## Cache Update Pattern

### After API Fetch (used by /workday --sync, /workday --todo)
```
1. Receive work items from wit_my_work_items + wit_get_work_items_batch_by_ids
2. Transform each item to cached format:
   {
     "id": System.Id,
     "project": System.TeamProject,
     "type": System.WorkItemType,
     "title": System.Title,
     "state": System.State,
     "priority": Microsoft.VSTS.Common.Priority,
     "iterationPath": System.IterationPath,
     "url": "https://dev.azure.com/{ORG}/{PROJECT}/_workitems/edit/{ID}",
     "lastFetched": new Date().toISOString()
   }
3. Replace cachedWorkItems array entirely
4. Update lastSync timestamp
5. Write work-tracker-data.json
6. Regenerate work-tracker.md sections: Sync Status, Current Sprint
```

## Markdown Regeneration Pattern

When regenerating `work-tracker.md`, build it from `work-tracker-data.json`:

1. **Sync Status**: from `lastSync`, count of `cachedWorkItems`, unique projects
2. **Current Sprint**: filter `cachedWorkItems` where state != Done/Closed/Removed
3. **Time Log**: iterate `timeLog` entries, group by month → week → day
4. **Compliance Dashboard**: calculate from `timeLog` + `timeOff` + `settings`
5. **Completed Items**: filter `cachedWorkItems` where state == Done/Closed (recent only)

Always regenerate the ENTIRE file from JSON — do not try to patch individual sections.

## Related Commands

| Command / Workflow | Reads JSON | Writes JSON | Reads MD | Writes MD |
|-------------------|-----------|------------|---------|----------|
| `/workday` | YES | YES (if stale) | NO | YES (if stale) |
| `/workday --sync` | YES | YES | NO | YES |
| `/workday --tasks` | YES | YES (if stale) | NO | NO |
| `/workday --todo` | YES | YES | NO | YES |
| `/log-time` | YES | YES | NO | YES |
| `/timesheet` | YES | NO | NO | NO |
| `/timesheet --off` | YES | YES | NO | YES |
| `/standup` | YES | NO | NO | NO |
| Update work item (skill) | YES | YES (if auto-log) | NO | YES (if auto-log) |
