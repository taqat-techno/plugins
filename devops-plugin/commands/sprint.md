---
title: 'Sprint Summary'
read_only: true
type: 'command'
description: 'Generate sprint progress summary from Azure DevOps'
---

# Sprint Summary Generator

Generate a comprehensive sprint progress report.

## Instructions

1. Get current iteration/sprint information
2. Query all work items in the sprint
3. Calculate completion percentage
4. Identify at-risk items
5. Generate summary with metrics

## WIQL Query

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Scheduling.StoryPoints], [System.AssignedTo]
FROM WorkItems
WHERE [System.IterationPath] UNDER @CurrentIteration
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
