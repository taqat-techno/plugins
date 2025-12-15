---
title: 'My Tasks'
read_only: true
type: 'command'
description: 'List all work items assigned to you'
---

# My Tasks

Display all active work items assigned to the current user.

## Instructions

**IMPORTANT**:
- Use `mcp_ado_workitems_query_workitems` tool (NOT `search_work_items`)
- **ALWAYS query by project** - Never query without project scope

### Step-by-Step:

1. **First, list all projects** using `mcp_ado_core_list_projects`
2. **For EACH project**, run the WIQL query with `project` parameter
3. Filter out closed/removed items
4. Group results by project, then by state and type
5. Display in organized format

## Correct Tool Usage

**DO NOT USE**: `mcp_ado_search_workitem` or `search_work_items` - TEXT SEARCH only!

**USE THIS**: `mcp_ado_workitems_query_workitems` with `project` parameter

```
mcp_ado_workitems_query_workitems({
  "project": "PROJECT_NAME",  // ← ALWAYS REQUIRED
  "query": "SELECT ... FROM WorkItems WHERE ..."
})
```

## Default Workflow

### Step 1: Get Projects
```
mcp_ado_core_list_projects()
```

### Step 2: Query Each Project
For each project found, run:

```
mcp_ado_workitems_query_workitems({
  "project": "ProjectName",
  "query": "SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [Microsoft.VSTS.Common.Priority], [System.IterationPath], [System.TeamProject] FROM WorkItems WHERE [System.AssignedTo] CONTAINS 'ahmed' AND [System.State] <> 'Closed' AND [System.State] <> 'Removed' ORDER BY [Microsoft.VSTS.Common.Priority], [System.WorkItemType]"
})
```

## WIQL Query Templates (Always with Project)

### Primary Query
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Common.Priority], [System.IterationPath], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = 'PROJECT_NAME'
  AND [System.AssignedTo] CONTAINS 'ahmed'
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [Microsoft.VSTS.Common.Priority], [System.WorkItemType]
```

### Using @Me macro
```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Common.Priority], [System.IterationPath], [System.TeamProject]
FROM WorkItems
WHERE [System.TeamProject] = @Project
  AND [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [Microsoft.VSTS.Common.Priority], [System.WorkItemType]
```

## Output Format

```markdown
## My Work Items

### Active (In Progress)
| ID | Type | Title | Priority | Sprint |
|----|------|-------|----------|--------|
| #1234 | Bug | Fix login issue | P1 | Sprint 15 |

### New (Not Started)
| ID | Type | Title | Priority | Sprint |
|----|------|-------|----------|--------|
| #1235 | Task | Add validation | P2 | Sprint 15 |

### Summary
- Total: X items
- Active: Y
- New: Z
- High Priority (P1-P2): W
```
