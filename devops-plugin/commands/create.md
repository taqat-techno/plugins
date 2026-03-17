---
title: 'Create'
read_only: false
type: 'command'
description: 'Create a work item (task, bug, enhancement, or user story). Auto-detects type from context. Enforces hierarchy, naming conventions, and sprint assignment.'
argument-hint: '[--task|--bug|--enhancement|--story] "Title" [under #ID]'
---

# Create Work Item

Create a Task, Bug, Enhancement, or User Story with **auto-type detection**, **hierarchy enforcement**, **naming conventions**, and **auto-sprint assignment**.

> Previously available as `/create-task`, `/create-bug`, `/create-user-story`.

## Usage

```
/create "Fix login validation" under #100
/create --task "Implement OAuth2 login" under #100
/create --bug "Button not working on mobile" severity 2
/create --enhancement "Improve login form validation UX"
/create --story "Implement dark mode"
/create "Add password hashing" for story #456
```

### Explicit Type Flags

| Flag | Work Item Type |
|------|---------------|
| `--task` | Task |
| `--bug` | Bug |
| `--enhancement` | Enhancement |
| `--story` | User Story / Product Backlog Item |
| *(none)* | Auto-detect from context |

---

## WRITE OPERATION GATE

**Reference**: `guards/write_operation_guard.md`

Before creating ANY work item, present a confirmation summary and **wait for explicit user approval**. NEVER call `wit_create_work_item` without the user saying "yes".

```
READY TO CREATE: {Type}
------------------------------
Title:     {title}
Type:      {Task|Bug|Enhancement|User Story}
Project:   {project}
Parent:    #{parentId} - {parentTitle}
Sprint:    {iterationPath} (if task)
Prefix:    {[DEV]/[FRONT]/[QA]/[IMP]} (if task)
Severity:  {1-4} (if bug)

Proceed? (yes/no)
```

**Only proceed after explicit "yes" from user.**

If in Plan Mode: STOP HERE. Only describe what would be created. Do not call any write tools.

---

## Step 0: Load Profile Defaults

Before processing the create request, load user profile for intelligent defaults:

```
1. Try to Read ~/.claude/devops.md
2. If found:
   a. taskPrefix = preferences.taskPrefix (from user's role)
   b. defaultAssignee = identity.guid (assign to current user)
   c. defaultProject = profile.defaultProject (if no project context)
   d. Log: "Profile loaded: prefix={taskPrefix}, project={defaultProject}"
3. If NOT found:
   a. taskPrefix = auto-detect from keywords (existing behavior)
   b. defaultAssignee = null (don't auto-assign)
   c. defaultProject = ask user
```

### Profile-Aware Behavior

| Feature | Without Profile | With Profile |
|---------|----------------|--------------|
| Task prefix | Auto-detect from keywords | Use `preferences.taskPrefix` (override with keywords if different) |
| Assignee | Not set | Auto-assign to current user (`identity.guid`) |
| Project | Ask or auto-detect | Use `defaultProject` |

---

## Step 1: Auto-Type Detection

When no explicit flag is provided, detect the work item type automatically:

```
DETECTION PRIORITY ORDER:

1. EXPLICIT FLAG (highest priority):
   --task → Task
   --bug → Bug
   --enhancement → Enhancement
   --story → User Story

2. KEYWORD DETECTION:
   Bug keywords: "bug", "defect", "broken", "crash", "error", "issue",
                  "not working", "fails", "regression"
   Enhancement keywords: "enhance", "improve", "optimize", "refactor",
                          "extend", "upgrade", "polish", "improvement"
   Story keywords: "story", "user story", "PBI", "requirement",
                   "feature request", "as a user"
   Task keywords: "task", "implement", "add", "create", "build",
                  "update", "migrate"

3. STRUCTURAL CUES:
   Has "repro steps" or "expected vs actual" → Bug
   Has "current behavior" + "proposed improvement" → Enhancement
   Has "How/What/Why" or "acceptance criteria" only → User Story
   Has "under #ID" or "for story #ID" → Task

4. DEFAULT: Task (most common work item type)

5. IF AMBIGUOUS: Ask user
   "Is this a Task, Bug, Enhancement, or User Story?"
```

---

## Step 2: Find or Validate Parent (Hierarchy Helper)

**Reference**: `helpers/hierarchy_helper.md`

### Hierarchy Requirements

```
+---------------------------------------------------------------+
|           WORK ITEM HIERARCHY ENFORCEMENT                      |
+---------------------------------------------------------------+
|                                                                |
|  Bug         → MUST have parent User Story / PBI              |
|  Enhancement → MUST have parent User Story / PBI              |
|  Task        → MUST have parent User Story / PBI              |
|  Story       → MUST have parent Feature                       |
|                                                                |
|  Orphan work items are NOT allowed!                           |
|                                                                |
+---------------------------------------------------------------+
```

### If Parent Specified

```javascript
// Validate parent exists and is correct type
const parent = await mcp__azure-devops__wit_get_work_item({
  "project": currentProject,
  "id": request.parentId
});

// Validate parent type matches hierarchy
const validParents = {
  "Bug": ["User Story", "Product Backlog Item"],
  "Enhancement": ["User Story", "Product Backlog Item"],
  "Task": ["User Story", "Product Backlog Item"],
  "User Story": ["Feature"],
  "Product Backlog Item": ["Feature"]
};

if (!validParents[type].includes(parent.workItemType)) {
  return `Cannot create ${type} under ${parent.workItemType}. Required parent: ${validParents[type].join(" or ")}`;
}
```

### If No Parent Specified (Auto-Detection)

```javascript
// Search for candidate parents by keywords
const keywords = extractKeywords(request.title);

const searchResults = await mcp__azure-devops__search_workitem({
  "searchText": keywords.join(" "),
  "project": [currentProject],
  "workItemType": validParents[type],
  "state": ["New", "Active"],
  "top": 5
});

// Fallback: Current sprint items
if (searchResults.length === 0) {
  const sprintItems = await mcp__azure-devops__wit_get_work_items_for_iteration({
    "project": currentProject,
    "iterationId": currentIterationId
  });
}

// Present options to user
```

### Parent Selection Prompt

```
Found potential parents for "{title}":

| # | ID | Title | State | Sprint |
|---|-----|-------|-------|--------|
| 1 | #100 | User Authentication Feature | Active | Sprint 15 |
| 2 | #105 | Login Page Implementation | Active | Sprint 15 |
| 3 | [Create new parent first] |

Which one should this {type} be under?
```

---

## Type-Specific Rules

### Task Rules

**Reference**: `rules/business_rules.md` — Rules 4, 5

#### MANDATORY: Task Naming Prefixes

All Task titles MUST start with a template prefix. These prefixes come from the **project's Task Templates** in Azure DevOps settings.

##### Dynamic Template Loading

**Best approach**: Fetch templates from the project during `/init profile`:

```javascript
// Fetch task templates from project settings
// Templates are defined at: Project Settings → Boards → Templates → Task
// The plugin stores them in ~/.claude/devops.md under taskTemplates
```

If templates are cached in the user's profile (`~/.claude/devops.md`), use those.
If no profile exists, use the default templates below.

##### Default Templates (TaqaTechno Scrum Process)

```
+---------------------------------------------------------------+
|                TASK NAMING CONVENTIONS                          |
+---------------------------------------------------------------+
|                                                                |
|  [Dev]              Backend/Full-Stack Developer               |
|  [Front]            Frontend Developer                         |
|  [QC Bug Fixing]    QA - Bug fixing and verification           |
|  [QC Test Execution] QA - Test case execution                  |
|  [IMP]              Implementation, config, deploy, migration  |
|  [Dev-Internal-fix] Developer self-identified fix (auto)       |
|                                                                |
|  EXAMPLES:                                                     |
|  [Dev] Implement user authentication API                      |
|  [Front] Create login form component                          |
|  [QC Bug Fixing] Fix and verify login timeout issue           |
|  [QC Test Execution] Execute test cases for login flow        |
|  [IMP] Configure OAuth2 settings on staging                   |
|                                                                |
+---------------------------------------------------------------+
```

##### Auto-Detection Keywords

| Keywords | Prefix |
|----------|--------|
| API, endpoint, database, model, backend, server, ORM, query, schema, implement | `[Dev]` |
| UI, component, form, page, style, CSS, SCSS, frontend, template, React, Vue | `[Front]` |
| fix, bug, patch, hotfix, debug, resolve, verification, reproduce | `[QC Bug Fixing]` |
| test, QA, execute, test case, regression, scenario, validate, check | `[QC Test Execution]` |
| deploy, config, setup, install, migration, infrastructure, CI/CD, server hosting | `[IMP]` |

> **Profile Override**: If a user profile exists at `~/.claude/devops.md` with `taskTemplates` populated from the project settings, those templates are used instead of the defaults above. The user's `preferences.taskPrefix` sets their personal default. Keyword detection can still override this if the task clearly belongs to a different category (e.g., a developer creating a task with "fix bug" keywords will get `[QC Bug Fixing]` instead of `[Dev]`).

#### MANDATORY: Auto-Sprint Detection

Tasks MUST be assigned to the **current working sprint** based on today's date:

```javascript
// Get team iterations
const iterations = await mcp__azure-devops__work_list_team_iterations({
  "project": currentProject,
  "team": currentTeam
});

// Find sprint where today falls between start and end dates
const today = new Date();
const currentSprint = iterations.find(iter => {
  const start = new Date(iter.attributes.startDate);
  const finish = new Date(iter.attributes.finishDate);
  return today >= start && today <= finish;
});

if (currentSprint) {
  iterationPath = currentSprint.path;
} else {
  // Present available sprints to user
  askUserToSelectSprint(iterations);
}
```

#### Task Template

```markdown
Title: [PREFIX] [Action verb] [Object] [Context]

Description:
## Objective
[What this task accomplishes]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Technical Notes
[Any technical details]
```

---

### Bug Rules

**Reference**: `rules/business_rules.md` — Rule 8

#### BUG CREATION AUTHORITY GATE (MANDATORY)

```
+---------------------------------------------------------------+
|           BUG CREATION AUTHORITY CHECK                          |
+---------------------------------------------------------------+
|                                                                |
|  BEFORE creating any Bug, CHECK the user's role:              |
|                                                                |
|  1. Read role from ~/.claude/devops.md profile                |
|                                                                |
|  2. IF role = tester / qa / qc-bugfix / qc-test:             |
|     -> ALLOWED: Proceed with standard bug creation below      |
|                                                                |
|  3. IF role = developer / frontend / fullstack / devops /     |
|     pm / lead / ANY non-QA role:                              |
|     -> BLOCKED: Cannot create Bugs                            |
|     -> Show: "As a {role}, bugs are reserved for QA/QC.       |
|        I'll help you create a [Dev-Internal-fix] Task."       |
|     -> ASK: "Is the parent PBI still In Progress or Done?"    |
|       - In Progress -> Log fix on existing Task (Scenario A)  |
|       - Done -> Create [Dev-Internal-fix] Task (Scenario B)   |
|     -> ASK: "Does this fix change user-facing behavior?"      |
|       - Yes -> Flag QA Lead from team members                 |
|       - No -> Close normally                                  |
|                                                                |
|  4. IF no profile exists:                                     |
|     -> ASK: "Are you QA/QC? Only QA can create Bugs.          |
|        If you're a developer, I'll create a Task instead."    |
|                                                                |
+---------------------------------------------------------------+
```

#### Developer Redirect: [Dev-Internal-fix] Task

When a non-QA user tries to create a bug, redirect to a Task:

**Scenario A** — PBI still In Progress:
- Find developer's active Task under the PBI
- Add a comment describing the issue and fix (using the Bug Report Template body format)
- Log time on the existing Task
- No new work item needed
- **ALWAYS** add a FYI comment mentioning QC (see Auto-Mention below)

**Scenario B** — PBI already Done:
- Create new Task with prefix `[Dev-Internal-fix]`
- Use the **Bug Report Template** for the Task description body (same structured format)
- Link as child of the original User Story / PBI
- Move parent PBI back to In Progress
- Developer applies fix, logs time, closes Task
- **ALWAYS** add a FYI comment mentioning QC (see Auto-Mention below)

#### MANDATORY: Auto-Mention QC on Every [Dev-Internal-fix]

**EVERY** `[Dev-Internal-fix]` Task must notify QC — this is not conditional. After creating the Task, ALWAYS post a comment:

```javascript
// 1. Find QC/QA member from profile teamMembers (where role = "tester" or "qa")
// 2. Resolve GUID from profile cache
// 3. Post HTML comment with mention

mcp__azure-devops__wit_add_work_item_comment({
  "project": currentProject,
  "workItemId": taskId,
  "comment": "<a href=\"#\" data-vss-mention=\"version:2.0,guid:{QC_GUID}\">@{QC_Name}</a> FYI: Developer-identified fix created.<br><br><b>[Dev-Internal-fix]</b> {title}<br>Parent PBI: #{pbiId} - {pbiTitle}<br><br>Please monitor for any QC implications.",
  "format": "html"
})
```

**Additionally**, if the fix changes user-facing behavior, escalate:
```
"@{QC_Lead} ATTENTION: This [Dev-Internal-fix] changes user-facing behavior:
{description}. Please assess if regression testing is needed."
```

---

#### Bug Report Template (Official — for Bugs AND [Dev-Internal-fix] Tasks)

**Reference**: `data/bug_report_template.md`

This template is MANDATORY for all bug-type work items, whether created as Bug (by QA) or as [Dev-Internal-fix] Task (by developers).

##### Title Format

```
[Module/Feature] - [What is broken] - [Where it happens]
```

##### Severity Guide

| Severity | When to Use |
|----------|-------------|
| **1 - Critical** | System down, data loss, security breach |
| **2 - High** | Major feature broken, no workaround |
| **3 - Medium** | Feature partially broken, workaround exists |
| **4 - Low** | Cosmetic issue, typo, minor UI glitch |

##### Body Template

```
SEVERITY: [1-Critical | 2-High | 3-Medium | 4-Low]

REPRO STEPS:
Environment: [Production / Staging / Dev] | [Browser/Tool] | [Date tested]
Endpoint/Page: [URL or screen name]

Steps:
1. [First action]
2. [Second action]
3. [Observe the result]

Expected: [What should happen]
Actual: [What actually happens]

Evidence: [Screenshot link / Postman response / error log]

ACCEPTANCE CRITERIA:
- [ ] [Fix condition 1]
- [ ] [Fix condition 2]
- [ ] [Regression test passed]
```

##### Agent Guidance: Gathering Bug Info

When a user reports a bug, gather info in this order:
1. **Module/Feature** → First part of title
2. **What's broken** → Second part of title
3. **Where** → Third part of title
4. **Severity** → Show guide, let user pick
5. **Environment** → Production/Staging/Dev, browser, date
6. **Repro steps** → Numbered actions
7. **Expected vs Actual** → What should vs what does happen
8. **Evidence** → Screenshots, logs, API responses
9. **Acceptance criteria** → At least 1 fix condition + regression checkbox

##### Good Example

```
TITLE: Beneficiary Report - Country Column Missing from Export - Admin Panel

SEVERITY: 3 - Medium

REPRO STEPS:
Environment: Production | Chrome 120 | 2026-01-13
Endpoint/Page: Admin Panel > Reports > Beneficiary List

Steps:
1. Login as Admin
2. Navigate to Reports > Beneficiary List
3. Click "Export to Excel"
4. Open the exported file
5. Observe: Country column is not present in the export

Expected: Exported file includes a "Country" column as defined in the
          requirements document (Section 3.2 - Beneficiary Data Fields)
Actual: Export contains all columns except "Country" - the column is
        completely missing from the output

Evidence: [Screenshot of exported file showing missing column]

ACCEPTANCE CRITERIA:
- [ ] Country column appears in the Beneficiary List export
- [ ] Column displays correct country data for all beneficiary records
- [ ] Existing exports are not affected by the fix
```

---

### Enhancement Rules

**Reference**: `rules/business_rules.md` — Rule 1

#### No Role Restriction
Any role (developer, QA, PM, lead) can create Enhancement work items.

#### No Naming Prefix
Enhancement titles are written as plain descriptions — no mandatory prefix.

#### Required Fields

| Field | Description | Required |
|-------|-------------|----------|
| Title | Clear enhancement description | YES |
| Description | What to improve and why | Recommended |
| Parent | User Story / PBI | MANDATORY |

#### Enhancement Template

```markdown
Title: [Clear improvement description]

Description:
## Current Behavior
[How it works now]

## Proposed Improvement
[What should change]

## Expected Benefit
[Why this improvement matters]
```

---

### User Story Rules

**Reference**: `rules/business_rules.md` — Rule 2

#### REQUIRED: How/What/Why Format

Every User Story MUST include these three sections **in this specific order**:

##### 1. HOW? (Implementation Approach) — FIRST
- How will this be implemented?
- What technical approach?
- What components are affected?

##### 2. WHAT? (Requirements) — SECOND
- What needs to be done?
- What is the deliverable?
- What are the acceptance criteria?

##### 3. WHY? (Business Value) — THIRD
- Why is this needed?
- What problem does it solve?
- What value does it deliver?

#### Story Description Template

```markdown
## How (Implementation Approach)
[Technical approach description — HOW this will be built]

### Affected Components
- Component 1
- Component 2

### Technical Notes
- Technical detail 1
- Technical detail 2

## What (Requirements)
[Description of what needs to be done — WHAT the deliverable is]

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Why (Business Value)
[Business justification — WHY this is needed]

### Impact
- User benefit
- Business benefit
```

**Note**: Use "Product Backlog Item" as the work item type — "User Story" may be disabled in some projects.

---

## Step 3: Gather Type-Specific Info

Based on detected type, gather additional information:

| Type | Info to Gather | Source |
|------|---------------|--------|
| Task | Naming prefix, sprint, estimate | Auto-detect + ask if needed |
| Bug | Severity, priority, repro steps | Ask user |
| Enhancement | Current behavior, proposed improvement, benefit | Ask user |
| Story | How/What/Why sections | Ask user in order |

---

## Step 4: Confirmation Gate

**Reference**: `guards/write_operation_guard.md`

Present confirmation summary and wait for explicit approval before proceeding to Step 5.

---

## Step 5: Create Work Item

```javascript
// Create the work item with type-specific fields
const item = await mcp__azure-devops__wit_create_work_item({
  "project": currentProject,
  "workItemType": detectedType,  // "Task", "Bug", or "Product Backlog Item"
  "fields": [
    { "name": "System.Title", "value": formattedTitle },
    { "name": "System.Description", "value": formattedDescription },
    // Task-specific:
    { "name": "System.IterationPath", "value": currentIterationPath },
    { "name": "Microsoft.VSTS.Scheduling.OriginalEstimate", "value": estimate },
    // Bug-specific:
    { "name": "Microsoft.VSTS.Common.Severity", "value": severity },
    { "name": "Microsoft.VSTS.Common.Priority", "value": priority },
  ].filter(f => f.value)  // Remove empty fields
});
```

## Step 6: Link to Parent

```javascript
await mcp__azure-devops__wit_work_items_link({
  "project": currentProject,
  "updates": [{
    "id": item.id,
    "linkToId": selectedParentId,
    "type": "child"
  }]
});
```

## Step 7: Confirm to User

```
Created {Type} #{id}: "{title}"
   Parent: {ParentType} #{parentId} - {parentTitle}

Hierarchy:
Feature #50: Authentication Module
  User Story #100: User Authentication Feature
        Task #150: [DEV] Implement login API   NEW

State: New
Sprint: Sprint 15 (if task)
```

---

## Examples

### Example 1: Create Task (auto-detected)

**User**: `/create "Implement login validation" under #100`

```
Auto-detected type: Task (has parent reference)
Auto-detected prefix: [DEV] (keyword: "implement")
Auto-detected sprint: Sprint 16 (current)

READY TO CREATE: Task
------------------------------
Title:     [DEV] Implement login validation
Project:   Project Alpha
Parent:    #100 - User Authentication Feature
Sprint:    Project Alpha\Sprint 16

Proceed? (yes/no)
```

### Example 2: Create Bug (explicit flag)

**User**: `/create --bug "Login button not working on mobile"`

```
READY TO CREATE: Bug
------------------------------
Title:     [Login] - Login button not working on mobile
Project:   Project Alpha
Severity:  2 - High
Priority:  2 - Should fix

Proceed? (yes/no)
```

### Example 3: Create User Story

**User**: `/create --story "Implement dark mode"`

Claude asks for How/What/Why in order, then:

```
READY TO CREATE: User Story
------------------------------
Title:     Implement dark mode
Project:   Project Alpha
Parent:    Feature #50 - UI Enhancements
Format:    How/What/Why (structured)

Proceed? (yes/no)
```

---

## Error Handling

### Parent Not Found

```
Work item #999 not found.
Please check the ID and try again.
Tip: Use "show user stories in current sprint" to see available parents.
```

### Wrong Parent Type

```
Cannot create Task under Bug #200.
Tasks can only be children of User Stories or PBIs.
Please specify a valid parent type.
```

### No Parents Found

```
No User Stories found matching "AI chatbot integration".

Options:
1. Create a new User Story first (recommended)
2. Select from existing User Stories in current sprint
3. Enter a specific parent ID

What would you like to do?
```

---

## Quick Reference

```
+---------------------------------------------------------------+
|              CREATE WORK ITEM QUICK REFERENCE                  |
+---------------------------------------------------------------+
|                                                                |
|  TASK:                                                        |
|  /create "Title" under #parentID                              |
|  /create --task "Title" under #parentID                       |
|  → Auto-prefix [DEV]/[FRONT]/[QA]/[IMP]                      |
|  → Auto-sprint assignment                                     |
|  → Parent: User Story / PBI                                   |
|                                                                |
|  BUG:                                                         |
|  /create --bug "Title"                                        |
|  → Asks for severity, priority, repro steps                   |
|  → Parent: User Story / PBI                                   |
|                                                                |
|  ENHANCEMENT:                                                 |
|  /create --enhancement "Title"                                |
|  → No prefix required                                         |
|  → Any role can create                                        |
|  → Parent: User Story / PBI                                   |
|                                                                |
|  USER STORY:                                                  |
|  /create --story "Title"                                      |
|  → Asks for How/What/Why in order                             |
|  → Parent: Feature                                            |
|                                                                |
|  AUTO-DETECT:                                                 |
|  /create "Title"                                              |
|  → Detects type from keywords and context                     |
|                                                                |
|  NEVER create orphan work items!                              |
|                                                                |
+---------------------------------------------------------------+
```

## Related Commands

| Command | Description |
|---------|-------------|
| `/workday --tasks` | List assigned work items |
| `/sprint` | View sprint progress |
| `/log-time` | Log hours against work items |

---

*Part of DevOps Plugin v4.0*
*Hierarchy Helper: Enabled*
*Auto-Type Detection: Enabled*
*Previously: /create-task, /create-bug, /create-user-story*
