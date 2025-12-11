---
title: 'My Tasks'
read_only: true
type: 'command'
description: 'List all work items assigned to you'
---

# My Tasks

Display all active work items assigned to the current user.

## Instructions

1. Query work items where AssignedTo = @Me
2. Filter out closed/removed items
3. Group by state and type
4. Sort by priority
5. Display in organized format

## WIQL Query

```sql
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [Microsoft.VSTS.Common.Priority], [System.IterationPath]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
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
