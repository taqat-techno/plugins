---
title: 'Sprint Summary'
read_only: true
type: 'command'
description: 'Generate sprint progress summary from Azure DevOps'
---

# Sprint Summary Generator

Generate a comprehensive sprint progress report.

## Instructions

**IMPORTANT**:
- Use `mcp_ado_workitems_query_workitems` for WIQL queries (NOT `search_work_items`)
- **ALWAYS query by project** - Never query without project scope

### Step-by-Step:

1. **First, list all projects** using `mcp_ado_core_list_projects`
2. **For EACH project**, get current sprint using `mcp_ado_work_get_current_iteration`
3. **Query sprint work items** using `mcp_ado_workitems_query_workitems` with project
4. Calculate completion percentage
5. Identify at-risk items
6. Generate summary with metrics grouped by project

## Correct Tool Usage

**DO NOT USE**: `mcp_ado_search_workitem` - TEXT SEARCH only!

**USE THIS**:
```
# Step 1: Get all projects
mcp_ado_core_list_projects()

# Step 2: For each project, get current iteration
mcp_ado_work_get_current_iteration({ "project": "ProjectName" })

# Step 3: Query sprint work items
mcp_ado_workitems_query_workitems({
  "project": "ProjectName",  // ← ALWAYS REQUIRED
  "query": "SELECT ... FROM WorkItems WHERE ..."
})
```

## WIQL Query (for mcp_ado_workitems_query_workitems)

### Query with Project Scope
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Scheduling.StoryPoints], [System.AssignedTo], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = 'PROJECT_NAME'
  AND [System.IterationPath] UNDER @CurrentIteration
ORDER BY [System.WorkItemType], [System.State]
```

### Query All Sprint Items (with project)
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Scheduling.StoryPoints], [System.AssignedTo], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = @Project
  AND [System.IterationPath] UNDER @CurrentIteration
ORDER BY [System.WorkItemType], [System.State]
```

## Output Format

```markdown
## Sprint Summary - [Sprint Name]

### Progress
- Total Items: X
- Completed: Y (Z%)
- In Progress: A
- Not Started: B

### By Type
| Type | Total | Done | In Progress | Not Started |
|------|-------|------|-------------|-------------|
| User Story | X | Y | Z | W |
| Bug | X | Y | Z | W |
| Task | X | Y | Z | W |

### Story Points
- Committed: X points
- Completed: Y points
- Remaining: Z points

### At Risk Items
- [Type] #ID: Title (Reason)

### Team Progress
| Member | Assigned | Completed | In Progress |
|--------|----------|-----------|-------------|
| Name | X | Y | Z |

### Notes
- Sprint ends: [Date]
- Days remaining: X
```
