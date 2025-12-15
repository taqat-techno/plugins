---
title: 'Daily Standup'
read_only: true
type: 'command'
description: 'Generate daily standup notes from Azure DevOps work items'
---

# Daily Standup Generator

Generate a formatted daily standup report based on your Azure DevOps work items.

## Instructions

**IMPORTANT**:
- Use `mcp_ado_workitems_query_workitems` tool (NOT `search_work_items`)
- **ALWAYS query by project** - Never query without project scope

### Step-by-Step:

1. **First, list all projects** using `mcp_ado_core_list_projects`
2. **For EACH project**, run the WIQL query with `project` parameter
3. Identify items completed recently (yesterday/today) - state changed to Done/Closed
4. Identify items currently in progress - Active/In Progress state
5. Check for any blockers or issues
6. Format as standup notes grouped by project

## Correct Tool Usage

**DO NOT USE**: `mcp_ado_search_workitem` - TEXT SEARCH only!

**USE THIS**:
```
# Step 1: Get all projects
mcp_ado_core_list_projects()

# Step 2: Query each project
mcp_ado_workitems_query_workitems({
  "project": "ProjectName",  // ← ALWAYS REQUIRED
  "query": "SELECT ... FROM WorkItems WHERE ..."
})
```

## WIQL Query (for mcp_ado_workitems_query_workitems)

### Primary Query (with project scope)
```sql
SELECT [System.Id], [System.Title], [System.State], [System.ChangedDate],
       [System.WorkItemType], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = 'PROJECT_NAME'
  AND [System.AssignedTo] CONTAINS 'ahmed'
  AND ([System.State] = 'Active' OR [System.State] = 'In Progress' OR [System.State] = 'Done' OR [System.State] = 'Resolved')
  AND [System.ChangedDate] >= @Today - 2
ORDER BY [System.State], [System.ChangedDate] DESC
```

### Using @Me macro (with project)
```sql
SELECT [System.Id], [System.Title], [System.State], [System.ChangedDate],
       [System.WorkItemType], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = @Project
  AND [System.AssignedTo] = @Me
  AND ([System.State] = 'Active' OR [System.State] = 'In Progress' OR [System.State] = 'Done' OR [System.State] = 'Resolved')
  AND [System.ChangedDate] >= @Today - 2
ORDER BY [System.State], [System.ChangedDate] DESC
```

## Output Format

```markdown
## Daily Standup - [Today's Date]

### Completed (Yesterday)
- [Type] #ID: Title

### In Progress (Today)
- [Type] #ID: Title (X% complete)

### Planned
- [Type] #ID: Title

### Blockers
- None / List any blockers

### Notes
- Any additional notes
```

## Example Output

```markdown
## Daily Standup - December 11, 2025

### Completed (Yesterday)
- [Bug] #1234: Fixed login timeout issue
- [Task] #1235: Updated API documentation

### In Progress (Today)
- [Task] #1236: Implementing user authentication
- [Bug] #1237: Investigating payment gateway error

### Blockers
- Waiting for API keys from third-party provider

### Notes
- PR #45 ready for review
```
