---
title: 'Create Task'
read_only: false
type: 'command'
description: 'Create a new task work item in Azure DevOps'
---

# Create Task

Create a new task work item with proper fields.

## Hierarchy Requirement

**IMPORTANT**: Tasks MUST have a parent work item (Bug or User Story/PBI).

```
Epic
  └── Feature
        └── User Story / PBI   ← Parent for Task
              └── Task         ← This is what we're creating
```

## Instructions

### Step 1: Identify Parent (MANDATORY)
Before creating the task, ask:
- "Which User Story, PBI, or Bug should this task be under?"
- If user doesn't know, list recent PBIs/Bugs in the project:
```
mcp__azure-devops__wit_my_work_items({
  "project": "ProjectName",
  "type": "assignedtome"
})
```

### Step 2: Validate Parent Exists
```
mcp__azure-devops__wit_get_work_item({
  "project": "ProjectName",
  "id": PARENT_ID
})
```
Verify parent type is Bug, User Story, or Product Backlog Item.

### Step 3: Gather Task Information
- Title (required)
- Description
- Estimated hours (optional)

### Step 4: Create Task
```
mcp__azure-devops__wit_create_work_item({
  "project": "ProjectName",
  "workItemType": "Task",
  "fields": [
    {"name": "System.Title", "value": "Task title"},
    {"name": "System.Description", "value": "Description"}
  ]
})
```

### Step 5: Link to Parent (MANDATORY)
```
mcp__azure-devops__wit_work_items_link({
  "project": "ProjectName",
  "updates": [{
    "id": NEW_TASK_ID,
    "linkToId": PARENT_ID,
    "type": "child"
  }]
})
```

### Step 6: Confirm Creation
Return task ID, URL, and parent link confirmation.

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
