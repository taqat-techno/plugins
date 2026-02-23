# Smart Project Context Manager

## Purpose

This context manager **automatically tracks and maintains** the current project context, eliminating the need for users to specify the project in every query.

**Problem Solved**: Users say "show my tasks" but the query fails because `project` parameter is missing.

---

## 🎯 Core Principle: Context Persistence

```
┌─────────────────────────────────────────────────────────────────┐
│              SMART PROJECT CONTEXT MANAGEMENT                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GOAL: User should never have to repeat project name            │
│                                                                  │
│  Session 1: "Show my tasks in Project Alpha"                    │
│             → Sets context: Project Alpha                       │
│                                                                  │
│  Session 2: "Show my tasks"                                     │
│             → Uses context: Project Alpha (automatic)           │
│                                                                  │
│  Session 3: "Switch to Project Beta"                               │
│             → Updates context: Project Beta                        │
│                                                                  │
│  Session 4: "Create a bug"                                      │
│             → Uses context: Project Beta (automatic)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Context Detection Workflow

### Initial Context Setup (First Use)

```
┌─────────────────────────────────────────────────────────────────┐
│              INITIAL CONTEXT DETECTION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Show my tasks" (no project specified)                   │
│                                                                  │
│  STEP 1: Check if context already set                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ currentProject = getContext()                           │    │
│  │ if (currentProject) → Use it                            │    │
│  │ else → Go to Step 2                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: Auto-detect from user's activity                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ // Get all projects                                     │    │
│  │ projects = core_list_projects()                         │    │
│  │                                                         │    │
│  │ // Check user's work items in each                      │    │
│  │ for each project:                                       │    │
│  │   items = wit_my_work_items({ project, top: 5 })        │    │
│  │   activity[project] = items.count                       │    │
│  │                                                         │    │
│  │ // Find most active project                             │    │
│  │ mostActive = max(activity)                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: Confirm with user                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "I found you have work items in multiple projects:      │    │
│  │                                                         │    │
│  │  • Project Alpha (8 active items)                       │    │
│  │  • Project Beta (3 active items)                           │    │
│  │  • Project Gamma (2 active items)                 │    │
│  │                                                         │    │
│  │  I'll use Project Alpha as default.                     │    │
│  │  Say 'switch to [project]' to change."                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: Set context and proceed                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ setContext("Project Alpha")                             │    │
│  │ // Now execute original request                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Context Switching

```
User: "switch to Project Beta"

Claude:
┌─────────────────────────────────────────────────────────────────┐
│ ✓ Switched to Project Beta                                         │
│                                                                  │
│ All subsequent commands will use Project Beta as the default       │
│ project until you switch again.                                 │
│                                                                  │
│ Previous context: Project Alpha                                 │
│ Current context: Project Beta                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Explicit Project Override

```
User: "show tasks in Project Gamma"

Claude:
┌─────────────────────────────────────────────────────────────────┐
│ Querying Project Gamma (one-time override)                │
│                                                                  │
│ Note: Your default project is still Project Beta.                  │
│ To permanently switch, say "switch to Project Gamma"      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Context Rules

### Rule 1: Context Persistence

```
Context persists throughout the conversation session.

Once set:
  currentProject = "Project Alpha"

All subsequent queries use it automatically:
  wit_my_work_items({ project: currentProject, ... })
  wit_create_work_item({ project: currentProject, ... })
  wit_get_work_items_for_iteration({ project: currentProject, ... })
```

### Rule 2: Explicit Override (Temporary)

```
IF user specifies project in command:
  → Use specified project for THIS query only
  → DO NOT change the default context

Example:
  Context: Project Alpha
  User: "bugs in Project Beta"
  → Query Project Beta (this time)
  → Context still: Project Alpha
```

### Rule 3: Switch Command (Permanent)

```
IF user says "switch to [project]":
  → Change default context
  → Confirm the switch
  → Use new context for all subsequent queries

Trigger phrases:
  - "switch to [project]"
  - "use [project]"
  - "change project to [project]"
  - "set project [project]"
  - "work on [project]"
```

### Rule 4: Multi-Project Queries

```
IF user asks for "all projects" or "across all projects":
  → Loop through all available projects
  → Aggregate results
  → Group by project in output
  → DO NOT change context

Example:
  User: "all my tasks across all projects"
  → Query each project
  → Show combined results grouped by project
```

### Rule 5: No Context Available

```
IF no context set AND user doesn't specify project:
  → Auto-detect most active project
  → INFORM user of the selection
  → ASK for confirmation or alternative
  → DO NOT silently pick a project

Example:
  "I'll use Project Alpha (your most active project).
   Is this correct, or would you prefer a different project?"
```

---

## Context Detection Methods

### Method 1: User Activity Analysis

```javascript
// Get projects with user's work items
async function detectMostActiveProject() {
  // Step 1: Get all projects
  const projects = await mcp__azure-devops__core_list_projects();

  const activity = {};

  // Step 2: Check each project for user's items
  for (const project of projects) {
    const items = await mcp__azure-devops__wit_my_work_items({
      project: project.name,
      type: "assignedtome",
      includeCompleted: false,
      top: 10
    });
    activity[project.name] = items.length;
  }

  // Step 3: Return most active
  return Object.entries(activity)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, count }));
}
```

### Method 2: Recent Activity

```javascript
// Check user's most recently modified items
async function detectFromRecentActivity() {
  // Use myactivity type to get recently touched items
  const activity = await mcp__azure-devops__wit_my_work_items({
    project: projectName,
    type: "myactivity",
    top: 20
  });

  // Group by project, find most frequent
  const projectCounts = {};
  for (const item of activity) {
    const proj = item.teamProject;
    projectCounts[proj] = (projectCounts[proj] || 0) + 1;
  }

  return Object.entries(projectCounts)
    .sort((a, b) => b[1] - a[1])[0][0];
}
```

### Method 3: Explicit Selection

```javascript
// Let user choose from list
async function promptForProject() {
  const projects = await mcp__azure-devops__core_list_projects();

  // Show options
  console.log("Available projects:");
  projects.forEach((p, i) => {
    console.log(`${i + 1}. ${p.name}`);
  });

  // Get user selection
  return askUser("Which project would you like to work with?");
}
```

---

## Context Storage

### Session Context (In-Memory)

```javascript
// Context stored during conversation
const sessionContext = {
  currentProject: null,
  projectHistory: [],
  lastUpdated: null
};

function setContext(projectName) {
  sessionContext.currentProject = projectName;
  sessionContext.projectHistory.push({
    project: projectName,
    timestamp: new Date()
  });
  sessionContext.lastUpdated = new Date();
}

function getContext() {
  return sessionContext.currentProject;
}
```

### Context Indicators in Output

```
Always show current context in responses:

┌─────────────────────────────────────────────────────────────────┐
│ 📁 Project: Project Alpha                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ My Work Items (8)                                               │
│ ...                                                             │
│                                                                  │
│ Tip: Say "switch to [project]" to change projects               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example Conversations

### Example 1: First Time User

**User**: "show my tasks"

**Claude**:
```
I noticed you haven't set a default project yet.

Checking your activity across projects...

Found work items in:
• Project Alpha (8 active items) ← Most active
• Project Beta (3 active items)
• Project Gamma (2 active items)

I'll use **Project Alpha** as your default project.

📁 Project: Project Alpha

## My Work Items (8)
| ID | Type | Title | State |
|----|------|-------|-------|
| #1234 | Task | Fix login bug | Active |
| #1235 | Bug | UI alignment | New |
...

💡 Say "switch to Project Beta" to change projects.
```

### Example 2: Subsequent Queries

**User**: "create a bug: Button not working"

**Claude**:
```
📁 Project: Project Alpha (using default)

Creating bug in Project Alpha...

✅ Bug #1300 created: "Button not working"
   State: New
   Assigned to: You
```

### Example 3: Switch Projects

**User**: "switch to Project Beta"

**Claude**:
```
✓ Switched project context

Previous: Project Alpha
Current: Project Beta

All subsequent commands will use Project Beta.
```

**User**: "my tasks"

**Claude**:
```
📁 Project: Project Beta

## My Work Items (3)
| ID | Type | Title | State |
|----|------|-------|-------|
| #500 | Task | API integration | Active |
...
```

### Example 4: One-Time Override

**User**: "bugs in Project Gamma"

**Claude**:
```
📁 Querying: Project Gamma (one-time)
📌 Default remains: Project Beta

## Bugs in Project Gamma (2)
| ID | Title | State |
|----|-------|-------|
| #200 | Login fails | Active |
...

💡 To switch permanently: "switch to Project Gamma"
```

### Example 5: All Projects Query

**User**: "all my tasks across all projects"

**Claude**:
```
📁 Querying all projects...

## My Work Items Across All Projects

### Project Alpha (8 items)
| ID | Type | Title | State |
|----|------|-------|-------|
| #1234 | Task | Fix login | Active |
...

### Project Beta (3 items)
| ID | Type | Title | State |
|----|------|-------|-------|
| #500 | Task | API work | Active |
...

### Project Gamma (2 items)
| ID | Type | Title | State |
|----|------|-------|-------|
| #200 | Bug | Login issue | New |
...

📊 Total: 13 items across 3 projects
📌 Default project: Project Beta
```

---

## Trigger Phrases

### Set/Switch Context

| Phrase | Action |
|--------|--------|
| "switch to [project]" | Set new default |
| "use [project]" | Set new default |
| "change project to [project]" | Set new default |
| "set project [project]" | Set new default |
| "work on [project]" | Set new default |
| "default project [project]" | Set new default |

### Temporary Override

| Phrase | Action |
|--------|--------|
| "in [project]" | One-time query |
| "for [project]" | One-time query |
| "[query] in [project]" | One-time query |
| "from [project]" | One-time query |

### Multi-Project

| Phrase | Action |
|--------|--------|
| "all projects" | Query all |
| "across all projects" | Query all |
| "every project" | Query all |
| "all my work" | Query all |

---

## Integration with Other Components

### Tool Calls with Context

```javascript
// Before making any project-scoped call:
function withProjectContext(toolCall) {
  const context = getContext();

  if (!toolCall.params.project && context) {
    toolCall.params.project = context;
  }

  return executeToolCall(toolCall);
}

// Usage:
wit_my_work_items({
  // project auto-filled from context
  type: "assignedtome",
  top: 50
});
```

### Output Headers

```
Always include context indicator in output:

📁 Project: {currentProject}
or
📁 Querying: {tempProject} (one-time)
📌 Default: {currentProject}
```

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                 PROJECT CONTEXT QUICK REFERENCE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SET DEFAULT:                                                   │
│    "switch to Project Alpha"                                    │
│    "use Project Beta"                                              │
│    "work on Project Gamma"                                │
│                                                                  │
│  ONE-TIME QUERY:                                                │
│    "tasks in Project Alpha" (doesn't change default)            │
│    "bugs from Project Beta" (doesn't change default)               │
│                                                                  │
│  QUERY ALL:                                                     │
│    "all my tasks across all projects"                           │
│    "work items in every project"                                │
│                                                                  │
│  CHECK CURRENT:                                                 │
│    "what project am I in?"                                      │
│    "current project"                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Project Context Manager v1.0*
*Part of DevOps Plugin v3.0 Enhancement*
*YOUR-ORG - December 2025*
