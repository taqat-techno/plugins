# WIQL Query Patterns

> **Purpose**: This memory provides common Work Item Query Language (WIQL) patterns for Azure DevOps. Use these queries with CLI (`az boards query --wiql`) for powerful work item filtering.

## Quick Reference

| Query Type | Key Fields | Example Use |
|------------|------------|-------------|
| My Items | `@Me` | Get assigned tasks |
| Sprint Items | `[System.IterationPath]` | Sprint planning |
| Recent Changes | `[System.ChangedDate]` | Standup reports |
| State Filter | `[System.State]` | Find active bugs |
| Team Items | `[System.AreaPath]` | Team workload |

---

## 1. Basic Query Structure

```sql
SELECT [Field1], [Field2], [Field3]
FROM WorkItems
WHERE [Condition1]
  AND [Condition2]
ORDER BY [SortField] [ASC|DESC]
```

### Common Fields

| Field | Description | Example Values |
|-------|-------------|----------------|
| `[System.Id]` | Work item ID | 123, 456 |
| `[System.Title]` | Title text | "Fix login bug" |
| `[System.State]` | State name | New, Active, Done, Closed |
| `[System.WorkItemType]` | Item type | Task, Bug, User Story |
| `[System.AssignedTo]` | Assigned user | @Me, email, display name |
| `[System.CreatedDate]` | Creation date | @Today, @Today-7 |
| `[System.ChangedDate]` | Last modified | @Today-1 |
| `[System.IterationPath]` | Sprint path | "Project\\Sprint 15" |
| `[System.AreaPath]` | Team area | "Project\\Team A" |
| `[System.Tags]` | Tags | "Blocked", "Priority" |
| `[Microsoft.VSTS.Common.Priority]` | Priority | 1, 2, 3, 4 |
| `[Microsoft.VSTS.Scheduling.StoryPoints]` | Story points | 1, 2, 3, 5, 8, 13 |

---

## 2. My Work Items

### 2.1 All My Active Items

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [System.ChangedDate] DESC
```

### 2.2 My Tasks in Current Sprint

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.WorkItemType] = 'Task'
  AND [System.IterationPath] = @CurrentIteration
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### 2.3 Items I Created

```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
FROM WorkItems
WHERE [System.CreatedBy] = @Me
ORDER BY [System.CreatedDate] DESC
```

### 2.4 My Recently Changed Items

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.ChangedDate] >= @Today-7
ORDER BY [System.ChangedDate] DESC
```

---

## 3. Sprint Queries

### 3.1 All Items in Current Sprint

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
  AND [System.TeamProject] = 'Relief Center'
ORDER BY [System.WorkItemType], [System.State]
```

### 3.2 Incomplete Sprint Items

```sql
SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] = @CurrentIteration
  AND [System.State] <> 'Done'
  AND [System.State] <> 'Closed'
  AND [System.State] <> 'Removed'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### 3.3 Sprint Items by Specific Path

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.IterationPath] = 'Relief Center\\Sprint 15'
ORDER BY [System.State]
```

### 3.4 Items Under Iteration (Including Children)

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.IterationPath] UNDER 'Relief Center\\2025'
ORDER BY [System.IterationPath], [System.Id]
```

---

## 4. Bug Queries

### 4.1 All Active Bugs

```sql
SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] IN ('New', 'Active', 'In Progress')
  AND [System.TeamProject] = 'Relief Center'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### 4.2 Critical Bugs (Priority 1)

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [Microsoft.VSTS.Common.Priority] = 1
  AND [System.State] <> 'Closed'
ORDER BY [System.CreatedDate] DESC
```

### 4.3 Unassigned Bugs

```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.AssignedTo] = ''
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC
```

### 4.4 Bugs Created This Week

```sql
SELECT [System.Id], [System.Title], [System.CreatedBy], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.CreatedDate] >= @Today-7
ORDER BY [System.CreatedDate] DESC
```

### 4.5 Bugs Fixed Yesterday

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] = 'Done'
  AND [System.ChangedDate] >= @Today-1
  AND [System.ChangedDate] < @Today
```

---

## 5. User Story Queries

### 5.1 Active User Stories

```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Scheduling.StoryPoints], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.State] IN ('New', 'Active')
ORDER BY [Microsoft.VSTS.Common.StackRank]
```

### 5.2 User Stories Without Tasks

```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.State] <> 'Closed'
  AND [System.Links.LinkCount] = 0
```

### 5.3 User Stories by Story Points

```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Scheduling.StoryPoints]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.IterationPath] = @CurrentIteration
ORDER BY [Microsoft.VSTS.Scheduling.StoryPoints] DESC
```

---

## 6. Team Queries

### 6.1 Team Workload

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo], [System.State]
FROM WorkItems
WHERE [System.AreaPath] UNDER 'Relief Center\\Development Team'
  AND [System.State] IN ('Active', 'In Progress')
ORDER BY [System.AssignedTo]
```

### 6.2 Unassigned Items in Area

```sql
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AreaPath] = 'Relief Center\\Development Team'
  AND [System.AssignedTo] = ''
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

### 6.3 Items by Specific User

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = 'ahmed@taqatechno.com'
  AND [System.State] <> 'Closed'
ORDER BY [System.ChangedDate] DESC
```

---

## 7. Tag-Based Queries

### 7.1 Blocked Items

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'Blocked'
  AND [System.State] <> 'Closed'
```

### 7.2 Items with Specific Tag

```sql
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'API'
ORDER BY [System.WorkItemType]
```

### 7.3 High Priority Tagged Items

```sql
SELECT [System.Id], [System.Title], [System.Tags]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'Priority'
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Common.Priority]
```

---

## 8. Date-Based Queries

### 8.1 Created Today

```sql
SELECT [System.Id], [System.Title], [System.CreatedBy]
FROM WorkItems
WHERE [System.CreatedDate] >= @Today
ORDER BY [System.CreatedDate] DESC
```

### 8.2 Modified in Last 7 Days

```sql
SELECT [System.Id], [System.Title], [System.ChangedBy], [System.ChangedDate]
FROM WorkItems
WHERE [System.ChangedDate] >= @Today-7
ORDER BY [System.ChangedDate] DESC
```

### 8.3 Completed Yesterday

```sql
SELECT [System.Id], [System.Title], [System.AssignedTo]
FROM WorkItems
WHERE [System.State] = 'Done'
  AND [System.ChangedDate] >= @Today-1
  AND [System.ChangedDate] < @Today
```

### 8.4 Overdue Items (Past Due Date)

```sql
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Scheduling.TargetDate]
FROM WorkItems
WHERE [Microsoft.VSTS.Scheduling.TargetDate] < @Today
  AND [System.State] <> 'Done'
  AND [System.State] <> 'Closed'
ORDER BY [Microsoft.VSTS.Scheduling.TargetDate]
```

---

## 9. Relationship Queries

### 9.1 Items with Parent

```sql
SELECT [System.Id], [System.Title], [System.Parent]
FROM WorkItemLinks
WHERE [Source].[System.WorkItemType] = 'Task'
  AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Reverse'
MODE (MustContain)
```

### 9.2 Parent with Children Count

```sql
SELECT [System.Id], [System.Title], [System.Links.LinkCount]
FROM WorkItems
WHERE [System.WorkItemType] = 'User Story'
  AND [System.State] <> 'Closed'
ORDER BY [System.Links.LinkCount] DESC
```

---

## 10. Standup Queries

### 10.1 Standup - Completed Yesterday

```sql
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] = 'Done'
  AND [System.ChangedDate] >= @Today-1
  AND [System.ChangedDate] < @Today
```

### 10.2 Standup - In Progress Today

```sql
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.State] IN ('Active', 'In Progress')
ORDER BY [Microsoft.VSTS.Common.Priority]
```

### 10.3 Standup - Blocked

```sql
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND ([System.Tags] CONTAINS 'Blocked' OR [System.State] = 'Blocked')
```

---

## 11. CLI Usage Examples

### Running WIQL Queries

```bash
# Simple query
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"

# With project
az boards query --wiql "SELECT * FROM WorkItems WHERE [System.State] = 'Active'" --project "Relief Center"

# Output formats
az boards query --wiql "SELECT [System.Id] FROM WorkItems" --output json
az boards query --wiql "SELECT [System.Id] FROM WorkItems" --output table
az boards query --wiql "SELECT [System.Id] FROM WorkItems" --output tsv
```

### Multi-line Query (Bash)

```bash
az boards query --wiql "
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = 'Relief Center'
  AND [System.State] = 'Active'
  AND [System.AssignedTo] = @Me
ORDER BY [System.ChangedDate] DESC
" --project "Relief Center" -o table
```

### Multi-line Query (PowerShell)

```powershell
$wiql = @"
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = 'Relief Center'
  AND [System.State] = 'Active'
  AND [System.AssignedTo] = @Me
ORDER BY [System.ChangedDate] DESC
"@

az boards query --wiql $wiql --project "Relief Center" -o table
```

---

## 12. Special Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `@Me` | Current user | `[System.AssignedTo] = @Me` |
| `@Today` | Today's date | `[System.CreatedDate] >= @Today` |
| `@Today-N` | N days ago | `[System.ChangedDate] >= @Today-7` |
| `@CurrentIteration` | Current sprint | `[System.IterationPath] = @CurrentIteration` |
| `IN (...)` | Multiple values | `[System.State] IN ('New', 'Active')` |
| `CONTAINS` | Text contains | `[System.Tags] CONTAINS 'API'` |
| `UNDER` | Path hierarchy | `[System.AreaPath] UNDER 'Project\\Team'` |
| `<>` | Not equal | `[System.State] <> 'Closed'` |
| `=` | Equal | `[System.State] = 'Active'` |

---

## Related Memories

- `cli_best_practices.md` - How to run WIQL queries via CLI
- `automation_templates.md` - Scripts using WIQL queries
- `hybrid_routing.md` - When to use CLI queries vs MCP
