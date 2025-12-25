---
title: 'Create Task'
read_only: false
type: 'command'
description: 'Create a task with automatic parent User Story detection and linking'
---

# Create Task

Create a Task work item with **automatic parent detection and linking** to maintain proper hierarchy.

## 🔗 Hierarchy Helper Integration

**Reference**: `helpers/hierarchy_helper.md`

Tasks MUST be linked to a parent User Story or PBI. This command automatically:
1. Detects if a parent is specified
2. Searches for candidate parents if not specified
3. Presents options to the user
4. Creates the task and links it to the parent

```
┌─────────────────────────────────────────────────────────────────┐
│           TASK CREATION WITH HIERARCHY ENFORCEMENT               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Task MUST have parent User Story or PBI!                       │
│                                                                  │
│  User Story #100: User Authentication                           │
│    └── Task #150: Implement login form ← CORRECT                │
│                                                                  │
│  Task #999: Orphan task ← WRONG (no parent!)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### With Explicit Parent

```
/create-task "Implement login validation" under #100
/create-task "Add password hashing" for story #456
/create-task "Fix button alignment" parent #789
```

### Without Parent (Auto-Detection)

```
/create-task "Implement login validation"
→ Claude searches for related User Stories
→ Presents options to user
→ User selects parent
→ Task created and linked
```

### Natural Language

```
"Create task to implement login validation"
"Add a task for fixing the payment bug under story #100"
"Create a task: Refactor database queries"
```

## Complete Workflow

### Step 1: Parse User Request

```javascript
// Extract task details
const request = {
  title: "Implement login validation",
  description: null,
  parentId: null,  // Check if specified
  estimate: null
};

// Check for explicit parent reference
const parentPatterns = [
  /under #(\d+)/i,
  /for story #(\d+)/i,
  /for pbi #(\d+)/i,
  /parent #(\d+)/i,
  /linked to #(\d+)/i
];

for (const pattern of parentPatterns) {
  const match = userMessage.match(pattern);
  if (match) {
    request.parentId = parseInt(match[1]);
    break;
  }
}
```

### Step 2: Find or Validate Parent

#### If Parent Specified:

```javascript
// Validate parent exists and is correct type
const parent = await mcp__azure-devops__wit_get_work_item({
  "project": currentProject,
  "id": request.parentId
});

if (!parent) {
  return `Parent work item #${request.parentId} not found.`;
}

if (!["User Story", "Product Backlog Item"].includes(parent.workItemType)) {
  return `Tasks must be under User Stories or PBIs, not ${parent.workItemType}.`;
}

// Parent validated, proceed to creation
```

#### If No Parent Specified:

```javascript
// Search for candidate parents
const keywords = extractKeywords(request.title);
// "Implement login validation" → ["login", "validation"]

// Method 1: Search by keywords
const searchResults = await mcp__azure-devops__search_workitem({
  "searchText": keywords.join(" "),
  "project": [currentProject],
  "workItemType": ["User Story", "Product Backlog Item"],
  "state": ["New", "Active"],
  "top": 5
});

// Method 2: Current sprint items (fallback)
if (searchResults.length === 0) {
  const sprintItems = await mcp__azure-devops__wit_get_work_items_for_iteration({
    "project": currentProject,
    "iterationId": currentIterationId
  });
  // Filter for User Stories
}

// Present options to user
```

### Step 3: Present Parent Options

```
Found potential parents for "login validation":

| # | ID | Title | State | Sprint |
|---|-----|-------|-------|--------|
| 1 | #100 | User Authentication Feature | Active | Sprint 15 |
| 2 | #105 | Login Page Implementation | Active | Sprint 15 |
| 3 | [Create new User Story first] |

Which User Story should this task be under?
```

### Step 4: Create Task

```javascript
// Create the task
const task = await mcp__azure-devops__wit_create_work_item({
  "project": currentProject,
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": request.title },
    { "name": "System.Description", "value": request.description || "" },
    { "name": "System.IterationPath", "value": currentIterationPath },
    { "name": "Microsoft.VSTS.Scheduling.OriginalEstimate", "value": request.estimate }
  ].filter(f => f.value)  // Remove empty fields
});
```

### Step 5: Link to Parent

```javascript
// Link task as child of selected parent
await mcp__azure-devops__wit_work_items_link({
  "project": currentProject,
  "updates": [{
    "id": task.id,
    "linkToId": selectedParentId,
    "type": "child"
  }]
});
```

### Step 6: Confirm to User

```
✅ Task #150 created: "Implement login validation"
   └── Parent: User Story #100 - User Authentication Feature

Hierarchy:
Feature #50: Authentication Module
  └── User Story #100: User Authentication Feature
        └── Task #150: Implement login validation ← NEW

State: New
Sprint: Sprint 15
```

## Example Flows

### Example 1: With Explicit Parent

**User**: "Create task under #100: Implement form validation"

**Claude**:
```
📁 Project: Relief Center

Parent specified: #100
Verifying parent...
✅ Found: User Story #100 - User Authentication Feature

Creating task...
```

```javascript
// Create task
const task = await mcp__azure-devops__wit_create_work_item({
  "project": "Relief Center",
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "Implement form validation" }
  ]
});

// Link to parent
await mcp__azure-devops__wit_work_items_link({
  "project": "Relief Center",
  "updates": [{
    "id": task.id,
    "linkToId": 100,
    "type": "child"
  }]
});
```

```
✅ Task #150 created: "Implement form validation"
   └── Parent: User Story #100 - User Authentication Feature
```

### Example 2: Auto-Detection (Success)

**User**: "Create task: Add password strength indicator"

**Claude**:
```
📁 Project: Relief Center

No parent specified. Searching for related User Stories...

Found potential parents for "password strength":

| # | ID | Title | State | Sprint |
|---|-----|-------|-------|--------|
| 1 | #100 | User Authentication Feature | Active | Sprint 15 |
| 2 | #105 | Password Management | Active | Sprint 15 |
| 3 | #110 | Security Enhancements | New | Sprint 16 |

Which User Story should this task be under?
```

**User**: "2" or "#105"

**Claude**:
```
Creating task under User Story #105...

✅ Task #151 created: "Add password strength indicator"
   └── Parent: User Story #105 - Password Management

Hierarchy:
Feature #50: Authentication Module
  └── User Story #105: Password Management
        └── Task #151: Add password strength indicator ← NEW
```

### Example 3: No Parents Found

**User**: "Create task: Implement AI chatbot integration"

**Claude**:
```
📁 Project: Relief Center

No parent specified. Searching for related User Stories...

⚠️ No User Stories found matching "AI chatbot integration".

Options:
1. Create a new User Story first (recommended)
2. Select from existing User Stories in current sprint:
   • #100 - User Authentication Feature
   • #120 - Data Export Feature
   • #130 - Admin Panel Enhancements
3. Enter a specific parent ID

What would you like to do?
```

### Example 4: With Estimate

**User**: "Create task under #100: Implement OAuth2 login, estimate 8 hours"

**Claude**:
```javascript
const task = await mcp__azure-devops__wit_create_work_item({
  "project": "Relief Center",
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "Implement OAuth2 login" },
    { "name": "Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" }
  ]
});
```

```
✅ Task #152 created: "Implement OAuth2 login"
   └── Parent: User Story #100
   └── Estimate: 8 hours
```

### Example 5: Wrong Parent Type

**User**: "Create task under #200: Fix login issue"

**Claude**:
```
📁 Project: Relief Center

Parent specified: #200
Verifying parent...

⚠️ Cannot create Task under Bug #200.

Tasks can only be children of User Stories or PBIs.
Work item #200 is a Bug.

Please specify a User Story as the parent, or let me search for one.
```

## Required Fields

| Field | Required | Description |
|-------|----------|-------------|
| `System.Title` | **Yes** | Clear task description |
| Parent Link | **Yes** | Link to User Story/PBI |
| `System.Description` | Recommended | What needs to be done |
| `Microsoft.VSTS.Scheduling.OriginalEstimate` | Recommended | Estimated hours |
| `System.IterationPath` | Recommended | Sprint assignment |

## Task Template

```markdown
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
```

## Error Handling

### Parent Not Found

```
⚠️ Work item #999 not found.

Please check the ID and try again.
Tip: Use "show user stories in current sprint" to see available parents.
```

### Wrong Parent Type

```
⚠️ Cannot create Task under {parentType} #{id}.

Tasks can only be children of:
• User Story
• Product Backlog Item

Please specify a valid parent type.
```

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              CREATE TASK QUICK REFERENCE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  WITH PARENT:                                                   │
│  • "Create task under #123: Task title"                         │
│  • "Add task for story #456: Description"                       │
│                                                                  │
│  WITHOUT PARENT (auto-detect):                                  │
│  • "Create task: Task title"                                    │
│  → Searches for related User Stories                            │
│  → Presents options                                             │
│  → Links after selection                                        │
│                                                                  │
│  WITH ESTIMATE:                                                 │
│  • "Create task under #123: Title, estimate 8 hours"            │
│                                                                  │
│  NEVER create orphan tasks!                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Related Commands

| Command | Description |
|---------|-------------|
| `/create-bug` | Create a bug (requires parent Task) |
| `/create-story` | Create a User Story |
| `/show-hierarchy` | Display work item hierarchy |

---

*Part of DevOps Plugin v3.0*
*Hierarchy Helper: Enabled*
*Always link tasks to parent stories!*
