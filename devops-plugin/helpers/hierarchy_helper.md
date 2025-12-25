---
title: 'Hierarchy Helper'
read_only: false
type: 'helper'
description: 'Auto-find or create parent work items and enforce hierarchy rules'
---

# Work Item Hierarchy Helper

## Purpose

Automatically find, suggest, or create parent work items when creating child items. Ensures proper hierarchy is maintained and prevents orphan work items.

## Problem Solved

```
User: "Create task: Fix login button"
Claude: wit_create_work_item({ type: "Task", title: "Fix login button" })
Result: Task created but ORPHANED (no parent User Story/PBI)

This causes:
• Task not visible in backlog hierarchy
• No traceability to business requirements
• Sprint planning issues
• Reporting gaps
```

---

## Hierarchy Rules

```
┌─────────────────────────────────────────────────────────────────┐
│              WORK ITEM HIERARCHY (TaqaTechno Standard)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Epic (Strategic Initiative)                                    │
│    └── Feature (Functional Area)                                │
│          └── User Story / PBI (Requirement)                     │
│                └── Task (Technical Work)                        │
│                      └── Bug (Defect found during task)         │
│                                                                  │
│  RULES:                                                         │
│  • Bug MUST have parent Task                                    │
│  • Task MUST have parent User Story/PBI                         │
│  • User Story MUST have parent Feature                          │
│  • Feature MUST have parent Epic                                │
│  • Epic is top-level (no parent required)                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Parent Requirements by Type

| Creating | Required Parent | Parent Type |
|----------|-----------------|-------------|
| **Bug** | **REQUIRED** | Task |
| **Task** | **REQUIRED** | User Story / PBI |
| **User Story / PBI** | REQUIRED | Feature |
| **Feature** | REQUIRED | Epic |
| **Epic** | None | Top-level |

---

## Helper Workflow

### When Creating Work Items

```
┌─────────────────────────────────────────────────────────────────┐
│              HIERARCHY HELPER WORKFLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Create task: Implement login validation"                │
│                                                                  │
│  STEP 1: Check if parent specified                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Does user message contain:                              │    │
│  │ • "under #123" / "for story #456" / "parent #789"       │    │
│  │ • Reference to existing work item                       │    │
│  │                                                         │    │
│  │ If YES → Use specified parent                           │    │
│  │ If NO → Go to STEP 2                                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: Find candidate parents                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Search for related User Stories:                        │    │
│  │                                                         │    │
│  │ Method 1: Keyword search                                │    │
│  │   search_workitem({ searchText: "login",                │    │
│  │     workItemType: ["User Story"] })                     │    │
│  │                                                         │    │
│  │ Method 2: Current sprint items                          │    │
│  │   wit_get_work_items_for_iteration({                    │    │
│  │     project, iterationId: currentIteration })           │    │
│  │                                                         │    │
│  │ Method 3: User's recent stories                         │    │
│  │   wit_my_work_items({ type: "myactivity" })             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: Present options to user                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "Found potential parent stories for this task:          │    │
│  │                                                         │    │
│  │  1. #100 - User Authentication Feature                  │    │
│  │  2. #105 - Login Page Implementation                    │    │
│  │  3. #110 - Form Validation System                       │    │
│  │  4. [Create new User Story]                             │    │
│  │                                                         │    │
│  │  Which should this task be under?"                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: Create and link                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ // Create the task                                      │    │
│  │ taskId = wit_create_work_item({ type: "Task", ... })    │    │
│  │                                                         │    │
│  │ // Link to parent                                       │    │
│  │ wit_work_items_link({                                   │    │
│  │   project, updates: [{                                  │    │
│  │     id: taskId,                                         │    │
│  │     linkToId: selectedParent,                           │    │
│  │     type: "child"                                       │    │
│  │   }]                                                    │    │
│  │ })                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Parent Detection Methods

### Method 1: Explicit Reference in User Message

```javascript
// Detect explicit parent references
const patterns = [
  /under #(\d+)/i,           // "under #123"
  /for story #(\d+)/i,       // "for story #456"
  /for pbi #(\d+)/i,         // "for PBI #789"
  /parent #(\d+)/i,          // "parent #100"
  /linked to #(\d+)/i,       // "linked to #200"
  /for task #(\d+)/i,        // "for task #300" (bug parent)
  /related to #(\d+)/i       // "related to #400"
];

function extractParentFromMessage(message) {
  for (const pattern of patterns) {
    const match = message.match(pattern);
    if (match) {
      return parseInt(match[1]);
    }
  }
  return null;
}

// Examples:
// "Create task under #123" → parentId = 123
// "Create bug for task #456" → parentId = 456
// "Add task for story #789" → parentId = 789
```

### Method 2: Keyword Search

```javascript
// Search for related work items by keywords from task title
async function findRelatedParents(title, workItemType, project) {
  // Extract keywords from title
  const keywords = extractKeywords(title);
  // e.g., "Implement login validation" → ["login", "validation"]

  // Search for User Stories containing these keywords
  const results = await mcp__azure-devops__search_workitem({
    "searchText": keywords.join(" "),
    "project": [project],
    "workItemType": [getParentType(workItemType)],
    "top": 5
  });

  return results;
}

function getParentType(childType) {
  const parentMap = {
    "Bug": "Task",
    "Task": "User Story",
    "User Story": "Feature",
    "Feature": "Epic"
  };
  return parentMap[childType];
}
```

### Method 3: Current Sprint Items

```javascript
// Get work items in current sprint as potential parents
async function findSprintParents(project, team, childType) {
  // Get current iteration
  const iterations = await mcp__azure-devops__work_list_team_iterations({
    "project": project,
    "team": team,
    "timeframe": "current"
  });

  if (!iterations || iterations.length === 0) {
    return [];
  }

  // Get work items in current sprint
  const sprintItems = await mcp__azure-devops__wit_get_work_items_for_iteration({
    "project": project,
    "iterationId": iterations[0].id
  });

  // Filter by parent type
  const parentType = getParentType(childType);
  return sprintItems.filter(item =>
    item.workItemType === parentType &&
    item.state !== "Done" &&
    item.state !== "Closed"
  );
}
```

### Method 4: Recent User Activity

```javascript
// Get user's recently touched work items
async function findRecentParents(project, childType) {
  const parentType = getParentType(childType);

  const recentItems = await mcp__azure-devops__wit_my_work_items({
    "project": project,
    "type": "myactivity",
    "top": 20
  });

  // Filter by parent type and active state
  return recentItems.filter(item =>
    item.workItemType === parentType &&
    item.state !== "Done" &&
    item.state !== "Closed"
  );
}
```

---

## Example Flows

### Example 1: Creating Task with Auto-Detection

**User**: "Create task: Implement login form validation"

**Claude**:
```
📁 Project: Relief Center

No parent specified. Searching for related User Stories...

Found potential parent stories containing "login" or "validation":

| # | ID | Title | Sprint | State |
|---|-----|-------|--------|-------|
| 1 | #100 | User Authentication Feature | Sprint 15 | Active |
| 2 | #105 | Login Page Implementation | Sprint 15 | Active |
| 3 | #110 | Form Validation System | Sprint 14 | Active |

Which User Story should this task be under?
(Or provide a different parent ID, or say "create new story")
```

**User**: "1" or "#100"

**Claude**:
```
Creating task under User Story #100...
```

```javascript
// Step 1: Create task
const task = await mcp__azure-devops__wit_create_work_item({
  "project": "Relief Center",
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "Implement login form validation" },
    { "name": "System.IterationPath", "value": "Relief Center\\Sprint 15" }
  ]
});

// Step 2: Link to parent
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
✅ Task #150 created: "Implement login form validation"
   └── Parent: User Story #100 - User Authentication Feature

Hierarchy:
Feature #50: Authentication Module
  └── User Story #100: User Authentication Feature
        └── Task #150: Implement login form validation ← NEW
```

### Example 2: Creating Task with Explicit Parent

**User**: "Create task under #100: Add password strength indicator"

**Claude**:
```
📁 Project: Relief Center

Parent specified: #100
Verifying parent exists and is correct type...
✅ Found: User Story #100 - User Authentication Feature

Creating task...
```

```javascript
// Parent already specified, skip search
const task = await mcp__azure-devops__wit_create_work_item({
  "project": "Relief Center",
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "Add password strength indicator" }
  ]
});

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
✅ Task #151 created under User Story #100
```

### Example 3: Creating Bug with Parent Task

**User**: "Create bug: Login button not responding on mobile"

**Claude**:
```
📁 Project: Relief Center

Bugs must be linked to a Task. Searching for related tasks...

Found tasks related to "login" or "button":

| # | ID | Title | State | Assigned |
|---|-----|-------|-------|----------|
| 1 | #150 | Implement login form validation | Active | Ahmed |
| 2 | #151 | Add password strength indicator | Active | Eslam |
| 3 | #145 | Create login button component | Done | Ahmed |

Which Task is this bug related to?
```

**User**: "3" or "#145"

**Claude**:
```
Creating bug under Task #145...

✅ Bug #200 created: "Login button not responding on mobile"
   └── Parent: Task #145 - Create login button component

Note: Task #145 was Done but this bug was found in that work.
Consider reopening or creating a follow-up task.
```

### Example 4: No Parents Found

**User**: "Create task: Implement new reporting dashboard"

**Claude**:
```
📁 Project: Relief Center

No parent specified. Searching for related User Stories...

⚠️ No User Stories found matching "reporting" or "dashboard".

Options:
1. Create a new User Story first (recommended)
2. Select from existing User Stories in current sprint:
   • #100 - User Authentication Feature
   • #120 - Data Export Feature
   • #130 - Admin Panel Enhancements
3. Create task without parent (not recommended)

What would you like to do?
```

**User**: "Create a new user story"

**Claude**:
```
Creating User Story first...

Please provide:
• Title for the User Story: ___
• Description (What/How/Why): ___

Or I can use:
• Title: "Reporting Dashboard Feature"
• Description: Based on the task requirements

Confirm?
```

### Example 5: Creating Entire Hierarchy

**User**: "Create a feature for payment processing with user story and tasks"

**Claude**:
```
📁 Project: Relief Center

I'll create the full hierarchy:

Epic (existing): #10 - E-Commerce Platform
  └── Feature (new): Payment Processing Module
        └── User Story (new): Implement Payment Gateway
              ├── Task (new): Design payment flow
              ├── Task (new): Integrate Stripe API
              └── Task (new): Add payment confirmation UI

Creating hierarchy...
```

```javascript
// Step 1: Create Feature
const feature = await wit_create_work_item({
  project, workItemType: "Feature",
  fields: [{ name: "System.Title", value: "Payment Processing Module" }]
});
await wit_work_items_link({ project, updates: [
  { id: feature.id, linkToId: 10, type: "child" }  // Link to Epic
]});

// Step 2: Create User Story
const story = await wit_create_work_item({
  project, workItemType: "User Story",
  fields: [{ name: "System.Title", value: "Implement Payment Gateway" }]
});
await wit_work_items_link({ project, updates: [
  { id: story.id, linkToId: feature.id, type: "child" }
]});

// Step 3: Create Tasks
const tasks = ["Design payment flow", "Integrate Stripe API", "Add payment confirmation UI"];
for (const title of tasks) {
  const task = await wit_create_work_item({
    project, workItemType: "Task",
    fields: [{ name: "System.Title", value: title }]
  });
  await wit_work_items_link({ project, updates: [
    { id: task.id, linkToId: story.id, type: "child" }
  ]});
}
```

```
✅ Hierarchy created successfully!

Epic #10: E-Commerce Platform
  └── Feature #250: Payment Processing Module (NEW)
        └── User Story #251: Implement Payment Gateway (NEW)
              ├── Task #252: Design payment flow (NEW)
              ├── Task #253: Integrate Stripe API (NEW)
              └── Task #254: Add payment confirmation UI (NEW)

5 work items created and linked.
```

---

## Hierarchy Visualization

When displaying work items, show their hierarchy context:

### Single Item View

```
📋 Task #150: Implement login form validation

Hierarchy:
Epic #10: Platform Modernization
  └── Feature #50: Authentication Module
        └── User Story #100: User Authentication Feature
              └── Task #150: Implement login form validation ← YOU ARE HERE
                    └── Bug #200: Login fails on Safari

State: Active
Assigned: Ahmed Abdelkhaleq
Sprint: Sprint 15
```

### Tree View

```
📊 User Story #100: User Authentication Feature

Child Items:
├── Task #150: Implement login form validation [Active]
│     └── Bug #200: Login fails on Safari [New]
├── Task #151: Add password strength indicator [Active]
├── Task #152: Implement remember me feature [New]
└── Task #153: Add OAuth integration [Done]

Progress: 1/4 tasks done (25%)
```

---

## Link Types

| Link Type | Use For | API Value |
|-----------|---------|-----------|
| Parent-Child | Standard hierarchy | `"child"` |
| Related | Cross-references | `"related"` |
| Duplicate | Duplicate items | `"duplicate"` |
| Successor | Dependencies | `"successor"` |
| Predecessor | Dependencies | `"predecessor"` |
| Tested By | Test cases | `"tested by"` |

### Linking Code

```javascript
// Add child link (Task under Story)
mcp__azure-devops__wit_work_items_link({
  "project": "Relief Center",
  "updates": [{
    "id": childId,      // The new Task
    "linkToId": parentId,  // The User Story
    "type": "child"     // Link type
  }]
});

// Add related link
mcp__azure-devops__wit_work_items_link({
  "project": "Relief Center",
  "updates": [{
    "id": itemA,
    "linkToId": itemB,
    "type": "related"
  }]
});
```

---

## Validation Rules

### Before Creating Work Item

```
┌─────────────────────────────────────────────────────────────────┐
│              PRE-CREATION VALIDATION                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Creating a BUG?                                                │
│  ├── Parent Task specified? → Proceed                           │
│  └── No parent? → MUST find/create parent Task first            │
│                                                                  │
│  Creating a TASK?                                               │
│  ├── Parent Story specified? → Proceed                          │
│  └── No parent? → MUST find/create parent Story first           │
│                                                                  │
│  Creating a USER STORY?                                         │
│  ├── Parent Feature specified? → Proceed                        │
│  └── No parent? → SHOULD find/create parent Feature             │
│                                                                  │
│  Creating a FEATURE?                                            │
│  ├── Parent Epic specified? → Proceed                           │
│  └── No parent? → SHOULD find/create parent Epic                │
│                                                                  │
│  Creating an EPIC?                                              │
│  └── No parent needed → Proceed                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Parent Type Validation

```javascript
// Ensure correct parent type
function validateParentType(childType, parentItem) {
  const validParents = {
    "Bug": ["Task"],
    "Task": ["User Story", "Product Backlog Item"],
    "User Story": ["Feature"],
    "Product Backlog Item": ["Feature"],
    "Feature": ["Epic"]
  };

  const allowed = validParents[childType] || [];
  if (!allowed.includes(parentItem.workItemType)) {
    return {
      valid: false,
      message: `${childType} cannot be a child of ${parentItem.workItemType}. ` +
               `Valid parent types: ${allowed.join(", ")}`
    };
  }

  return { valid: true };
}
```

---

## Error Handling

### Parent Not Found

```
⚠️ Work item #999 not found.

Please provide a valid parent ID or let me search for one.

Tip: Use "show user stories in current sprint" to see available parents.
```

### Wrong Parent Type

```
⚠️ Cannot create Task under Bug #200.

Tasks must be under a User Story or Product Backlog Item.
Bug #200 is a Bug, which cannot be a parent of Task.

Correct hierarchy:
• Bug → under Task
• Task → under User Story/PBI
• User Story → under Feature

Please specify a User Story as the parent.
```

### Circular Reference

```
⚠️ Cannot link #150 as child of #200.

This would create a circular reference:
#200 is already a descendant of #150.

Current hierarchy:
#150 → #175 → #200

Please choose a different parent.
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              HIERARCHY HELPER QUICK REFERENCE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PARENT REQUIREMENTS:                                           │
│  • Bug MUST have parent Task                                    │
│  • Task MUST have parent User Story/PBI                         │
│  • User Story SHOULD have parent Feature                        │
│  • Feature SHOULD have parent Epic                              │
│                                                                  │
│  SPECIFY PARENT:                                                │
│  • "Create task under #123"                                     │
│  • "Create bug for task #456"                                   │
│  • "Add task to story #789"                                     │
│                                                                  │
│  AUTO-DETECTION:                                                │
│  • Keywords from title searched                                 │
│  • Current sprint items checked                                 │
│  • Recent activity reviewed                                     │
│  • Options presented to user                                    │
│                                                                  │
│  NEVER create orphan Tasks or Bugs!                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Part of DevOps Plugin v3.0*
*Hierarchy Helper: Enabled*
*Always link work items to their parents!*
