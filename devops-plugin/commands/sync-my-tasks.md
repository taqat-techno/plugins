---
title: 'Sync My Tasks'
read_only: false
type: 'command'
description: 'Sync Azure DevOps tasks to Claude Code TODO list'
---

# Sync My Tasks

Synchronize Azure DevOps work items assigned to you with Claude Code's TODO list.

## What This Command Does

1. **Fetches** ALL work items assigned to you using a **single global WIQL query** (fast!)
2. **Extracts** project name and generates direct links for each item
3. **Adds/Updates** items in Claude Code TODO list using TodoWrite tool
4. **Reports** sync summary grouped by project

## Usage

```
/sync-my-tasks                           # Sync ALL your tasks across all projects (recommended)
/sync-my-tasks --project "Relief Center" # Filter to specific project only
```

## Workflow

### Step 1: Execute Global WIQL Query (Single Fast Query)

**Use this WIQL query to get ALL work items assigned to you across ALL projects:**

```
mcp__azure-devops__wit_get_query_results_by_id({
  "id": "custom",
  "wiql": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.TeamProject], [System.AreaPath] FROM WorkItems WHERE [System.AssignedTo] = @Me AND [System.State] NOT IN ('Done', 'Closed', 'Removed', 'Resolved') ORDER BY [System.ChangedDate] DESC"
})
```

**Alternative - Using search_workitem for faster results:**
```
mcp__azure-devops__search_workitem({
  "searchText": "*",
  "assignedTo": ["@Me"],
  "state": ["New", "Active", "In Progress", "To Do"],
  "top": 100
})
```

**Or use wit_my_work_items without project filter:**
```
mcp__azure-devops__wit_my_work_items({
  "project": "*",
  "type": "assignedtome",
  "includeCompleted": false,
  "top": 100
})
```

### Step 2: Transform to TODO Format with Project & Link

**Azure DevOps State → TODO Status Mapping:**

| Azure DevOps State | TODO Status |
|-------------------|-------------|
| New, To Do | pending |
| Active, In Progress | in_progress |
| Done, Closed, Resolved | completed |
| Removed | (skip - don't add) |

**TODO Format (MUST include project name and link):**
```json
{
  "content": "[Relief Center] #1234 Task: Fix login bug | https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1234",
  "status": "in_progress",
  "activeForm": "Fixing login bug (#1234)"
}
```

**URL Format:**
```
https://dev.azure.com/TaqaTechno/{PROJECT_NAME_URL_ENCODED}/_workitems/edit/{WORK_ITEM_ID}
```

**Important**: URL-encode project names with spaces (e.g., "Relief Center" → "Relief%20Center")

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
    {"content": "[Relief Center] #1234 Task: Fix login bug | https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1234", "status": "in_progress", "activeForm": "Fixing login bug (#1234)"},
    {"content": "[Relief Center] #1235 Bug: UI alignment issue | https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1235", "status": "pending", "activeForm": "Fixing UI alignment (#1235)"},
    {"content": "[Property Management] #1236 PBI: Add dark mode | https://dev.azure.com/TaqaTechno/Property%20Management/_workitems/edit/1236", "status": "pending", "activeForm": "Implementing dark mode (#1236)"}
  ]
})
```

### Step 5: Report Results

```markdown
## Tasks Synced ✓

### Summary by Project
| Project | Active | New | Total |
|---------|--------|-----|-------|
| Relief Center | 3 | 2 | 5 |
| Property Management | 1 | 2 | 3 |
| **Total** | **4** | **4** | **8** |

### Work Items (8)
| Project | ID | Type | Title | Status | Link |
|---------|-----|------|-------|--------|------|
| Relief Center | #1636 | Bug | Broken Checksum Validation | 🔄 in_progress | [Open](https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1636) |
| Relief Center | #1629 | Bug | SQL Injection in Email | ⏳ pending | [Open](https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1629) |
| Relief Center | #1828 | Task | Investigate map duration | 🔄 in_progress | [Open](https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1828) |
| Property Management | #1230 | Task | Update user profile | ⏳ pending | [Open](https://dev.azure.com/TaqaTechno/Property%20Management/_workitems/edit/1230) |

### Changes
- **Added**: 5 new items
- **Updated**: 2 items (state changed)
- **Preserved**: 3 manual TODOs

Your TODO list has been updated!
```

## Example Session

**User**: `/sync-my-tasks`

**Claude**:
```
Fetching all work items assigned to you...

Running global WIQL query across all projects...
Found 8 work items in 2 projects.

## Tasks Synced ✓

### Summary by Project
| Project | Items |
|---------|-------|
| Relief Center | 5 |
| Property Management | 3 |
| **Total** | **8** |

### Work Items
| Project | ID | Type | Title | Link |
|---------|-----|------|-------|------|
| Relief Center | #1636 | Bug | Broken Checksum Validation | [Open](https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1636) |
| Relief Center | #1629 | Bug | SQL Injection in Email | [Open](https://dev.azure.com/TaqaTechno/Relief%20Center/_workitems/edit/1629) |
| Property Management | #1837 | Task | Deploy to Production | [Open](https://dev.azure.com/TaqaTechno/Property%20Management/_workitems/edit/1837) |
...

Your TODO list has been updated with 8 Azure DevOps items!
```

## WIQL Query Reference

### Get All My Active Tasks (Recommended)
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.TeamProject]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] NOT IN ('Done', 'Closed', 'Removed', 'Resolved')
ORDER BY [System.ChangedDate] DESC
```

### Get Tasks from Specific Projects
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.TeamProject]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] IN ('Relief Center', 'Property Management')
  AND [System.State] NOT IN ('Done', 'Closed', 'Removed')
ORDER BY [System.TeamProject], [System.ChangedDate] DESC
```

### Get Only Tasks and Bugs (Exclude PBIs)
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.TeamProject]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.WorkItemType] IN ('Task', 'Bug')
  AND [System.State] NOT IN ('Done', 'Closed', 'Removed')
ORDER BY [Microsoft.VSTS.Common.Priority], [System.ChangedDate] DESC
```

## Performance Notes

**Why Global Query is Faster:**
- ❌ Old approach: N queries (one per project) = N * ~500ms = slow
- ✅ New approach: 1 global WIQL query = ~500ms total = fast!

**Fields Retrieved:**
- `System.Id` - Work item ID (for #1234 format)
- `System.Title` - Task title
- `System.State` - For status mapping
- `System.WorkItemType` - Task, Bug, PBI, etc.
- `System.TeamProject` - Project name for grouping and URL

## Best Practices

1. **Run at session start** - Keep TODO list in sync with DevOps
2. **Use global query** - Faster than per-project queries
3. **Click links to open** - Direct access to work items in Azure DevOps
4. **Manual items preserved** - Your non-DevOps TODOs won't be affected

## Related Commands

- `/my-tasks` - View Azure DevOps tasks (read-only, no TODO sync)
- `/standup` - Generate standup notes from recent activity
- `/sprint` - View sprint progress
