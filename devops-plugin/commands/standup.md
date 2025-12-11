---
title: 'Daily Standup'
read_only: true
type: 'command'
description: 'Generate daily standup notes from Azure DevOps work items'
---

# Daily Standup Generator

Generate a formatted daily standup report based on your Azure DevOps work items.

## Instructions

1. Query work items assigned to the current user
2. Identify items completed recently (yesterday/today)
3. Identify items currently in progress
4. Check for any blockers or issues
5. Format as standup notes

## WIQL Query

```sql
SELECT [System.Id], [System.Title], [System.State], [System.ChangedDate]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND ([System.State] = 'Active' OR [System.State] = 'In Progress' OR [System.State] = 'Done')
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
