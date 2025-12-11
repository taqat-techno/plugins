---
title: 'Create Task'
read_only: false
type: 'command'
description: 'Create a new task work item in Azure DevOps'
---

# Create Task

Create a new task work item with proper fields.

## Instructions

1. Gather task information:
   - Title (required)
   - Description
   - Estimated hours (optional)
   - Parent work item (optional)
2. Ask for project if not specified
3. Create the task work item
4. Link to parent if specified
5. Return task ID and URL

## Required Fields

| Field | Description | Values |
|-------|-------------|--------|
| Title | Clear task description | Text |
| Description | What needs to be done | HTML/Text |
| Original Estimate | Estimated hours | Number |
| Remaining Work | Hours remaining | Number |
| Activity | Type of work | Development, Testing, Documentation, etc. |

## Task Template

```
Title: [Action verb] [Object] [Context]

Description:
## Objective
[What this task accomplishes]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Technical Notes
[Any technical details]

## Dependencies
[List any dependencies]
```

## Example

```
User: Create task: Add email validation to registration form

Response: Creating task in [Project]...

Created Task #1235: Add email validation to registration form
- State: New
- Activity: Development
- Estimate: 4 hours
- URL: https://dev.azure.com/TaqaTechno/Project/_workitems/edit/1235

Would you like to:
1. Add estimated hours
2. Link to a user story
3. Assign to someone
4. Add to current sprint
```
