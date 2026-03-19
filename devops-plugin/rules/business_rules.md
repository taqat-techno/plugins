# YOUR-ORG Business Rules

## Purpose

This document defines mandatory business rules for the DevOps plugin that Claude MUST enforce when creating and updating work items.

---

## Rule 1: Work Item Hierarchy (MANDATORY)

```
                    HIERARCHY STRUCTURE

    Epic (Strategic Initiative)
      |
      +--- Feature (Functional Area)
             |
             +--- User Story / PBI (Requirement)
                    |
                    +--- Task (Technical Work)
                    |
                    +--- Bug (Defect identified by QA)
                    |
                    +--- Enhancement (Improvement to existing functionality)
```

### Enforcement Rules

| Creating | MUST Have Parent | Parent Type |
|----------|------------------|-------------|
| **Task** | YES (MANDATORY) | User Story / PBI |
| **Bug** | YES (MANDATORY) | User Story / PBI |
| **Enhancement** | YES (MANDATORY) | User Story / PBI |
| **User Story / PBI** | YES (MANDATORY) | Feature |
| **Feature** | YES (MANDATORY) | Epic |
| **Epic** | NO | Top-level |

> **Note**: Task, Bug, and Enhancement are **siblings** — all are children of User Story/PBI at the same level.

### Before Creating Work Item

```
STEP 1: Check if parent is specified
  IF parent specified → Validate parent type
  IF parent NOT specified → Search for candidates AND ask user

STEP 2: Validate parent type
  IF wrong parent type → BLOCK creation
  IF correct type → Proceed

STEP 3: Create work item
STEP 4: Link to parent (IMMEDIATELY after creation)
```

### Example: Creating a Bug (QA only — see Rule 8)

```
User (QA role): "Create bug: Login button not working"

Claude MUST:
1. Check user role from profile → QA → ALLOWED
2. Ask: "Which User Story / PBI is this bug related to?"
3. If user doesn't know:
   - Search for related stories: "What feature/area is affected?"
   - Present User Story options
4. Create bug
5. Link bug as child of the User Story
6. Confirm: "Bug #1234 created under User Story #100"
```

### Example: Creating an Enhancement

```
User: "Create enhancement: Improve search performance on product listing"

Claude MUST:
1. Any role → ALLOWED (no restriction)
2. Ask: "Which User Story / PBI is this enhancement for?"
3. Create Enhancement (no prefix required)
4. Link as child of the User Story
5. Confirm: "Enhancement #1235 created under User Story #100"
```

---

## Rule 2: User Story Format (How → What → Why)

### MANDATORY Structure

Every User Story / PBI description MUST follow this sequence:

```markdown
## How (Implementation Approach)
[Technical approach - how will this be implemented?]

### Affected Components
- Component 1
- Component 2

## What (Requirements)
[What needs to be done - the deliverable]

### Acceptance Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Why (Business Value)
[Why is this needed - business justification]

### Impact
- User benefit
- Business benefit
```

### Enforcement

When creating a User Story:

1. **Gather information in this order:**
   - First ask: "HOW should this be implemented? (technical approach)"
   - Then ask: "WHAT needs to be done? (requirements)"
   - Finally ask: "WHY is this needed? (business value)"

2. **Format the description** using the template above

3. **Validate** all three sections are present

### Example

```
User: "Create user story for dark mode"

Claude:
1. "HOW would you like this implemented? (e.g., CSS variables, theme provider)"
2. "WHAT exactly needs to be done? (toggle switch, theme persistence, etc.)"
3. "WHY is this important? (user comfort, accessibility, etc.)"

Then creates PBI with:
## How (Implementation Approach)
Use CSS custom properties for theming with JavaScript toggle control.
Store preference in localStorage.

### Affected Components
- Settings page
- Theme CSS file
- All styled components

## What (Requirements)
Enable users to switch between light and dark themes.

### Acceptance Criteria
- [ ] Toggle visible in settings
- [ ] Theme persists across sessions
- [ ] All UI components styled correctly

## Why (Business Value)
Improves accessibility and user experience in low-light environments.

### Impact
- User benefit: Reduced eye strain
- Business benefit: Modern, competitive feature
```

---

## Rule 3: State Transitions (Ready for QC Gate)

### User Story State Flow

```
New → Active → Ready for QC → Done → Closed
                    ↑
                    |
            MANDATORY GATE
            Cannot skip!
```

### Enforcement Rules

| Current State | User Wants | Action |
|---------------|------------|--------|
| New | Done | BLOCK → Move to Active → Ready for QC → Done |
| Active | Done | BLOCK → Move to Ready for QC first |
| Ready for QC | Done | ALLOW |
| Done | Done | Already Done |

### Implementation

```
User: "Mark story #1000 as done"

Claude:
1. Get current state via API
2. IF state is "Ready for QC":
   - Proceed to Done
3. IF state is NOT "Ready for QC":
   - Message: "User Stories must pass through 'Ready for QC' for QA review."
   - Ask: "Would you like me to:
           1. Move to 'Ready for QC' now
           2. Move through both states (Ready for QC → Done)?"
4. Execute based on user choice
```

---

## Rule 4: Task Naming Conventions

### MANDATORY Prefixes

All Task titles MUST start with a template prefix from the project's Task Templates.

**Source of truth**: Project Settings → Boards → Templates → Task

These templates are fetched during `/init profile` and cached in `~/.claude/devops.md` under `taskTemplates`. If no profile exists, use the defaults below.

### Default Templates (TaqaTechno Scrum Process)

| Prefix | Role | Description |
|--------|------|-------------|
| `[Dev]` | Backend / Full-Stack Developer | Server-side, database, APIs |
| `[Front]` | Frontend Developer | UI, client-side, JavaScript |
| `[QC Bug Fixing]` | QA — Bug Fixing | Bug fixes, patches, verification |
| `[QC Test Execution]` | QA — Test Execution | Test cases, regression, scenarios |
| `[IMP]` | Implementation | Configuration, deployment, setup |

### Format

```
[PREFIX] Task description
```

### Examples

```
[Dev] Implement user authentication API
[Front] Create login form component
[QC Bug Fixing] Fix and verify login timeout issue
[QC Test Execution] Execute test cases for login flow
[IMP] Configure OAuth2 settings in production
```

### Enforcement

When creating a task:

1. **Check profile for templates**: Read `taskTemplates` from `~/.claude/devops.md`
2. **Detect task type** from context, keywords, or user's role prefix
3. **Add prefix** if not provided:
   - User says: "Create task: Implement login API"
   - Claude adds: "[Dev] Implement login API"
4. **For QC tasks**, distinguish between bug fixing and test execution:
   - Bug-related keywords → `[QC Bug Fixing]`
   - Test-related keywords → `[QC Test Execution]`

### Auto-Detection Rules

| Keywords in Title | Suggested Prefix |
|-------------------|------------------|
| API, endpoint, database, model, backend, server, implement | `[Dev]` |
| UI, component, form, page, style, CSS, frontend, client | `[Front]` |
| fix, bug, patch, hotfix, debug, resolve, reproduce, verify bug | `[QC Bug Fixing]` |
| test, execute, test case, regression, scenario, validate, check | `[QC Test Execution]` |
| deploy, config, setup, install, migration, infrastructure | `[IMP]` |

---

## Rule 5: Task Completion Requirements

### Required Fields for Task → Done

```
┌─────────────────────────────────────────────────────────────────┐
│                    TASK → DONE REQUIREMENTS                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REQUIRED FIELDS (must have values):                            │
│  ✓ Original Estimate (hours)                                    │
│  ✓ Completed Hours (hours)                                      │
│                                                                  │
│  AUTO-SET (by Claude):                                          │
│  → Remaining Work = 0                                           │
│                                                                  │
│  IF MISSING → ASK USER, DO NOT PROCEED!                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Validation Flow

```
User: "Mark task #1234 as done"

Claude:
1. Fetch task details
2. Check Original Estimate:
   - IF empty → Ask: "What was the original estimate (hours)?"
3. Check Completed Hours:
   - IF empty → Ask: "How many hours did you spend?"
4. Only after BOTH provided:
   - Set Original Estimate
   - Set Completed Hours
   - Set Remaining Work = 0
   - Set State = Done
5. Confirm: "Task #1234 marked as Done. Est: 8h, Actual: 6h"
```

---

## Rule 6: Bug Completion Requirements

### Required Fields for Bug → Done/Resolved

```
┌─────────────────────────────────────────────────────────────────┐
│                    BUG → RESOLVED/DONE REQUIREMENTS              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  REQUIRED FIELDS:                                               │
│  ✓ Completed Work (hours spent fixing)                          │
│  ✓ Resolved Reason (default: "Fixed")                          │
│                                                                  │
│  IF Completed Work MISSING → ASK USER, DO NOT PROCEED!          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Valid Resolved Reasons

- Fixed (default)
- As Designed
- Cannot Reproduce
- Deferred
- Duplicate
- Not a Bug
- Obsolete

### Validation Flow

```
User: "Mark bug #500 as resolved"

Claude:
1. Fetch bug details
2. Check Completed Work:
   - IF empty → Ask: "How many hours did you spend fixing this bug?"
3. Check/Set Resolved Reason:
   - Default to "Fixed" unless user specifies otherwise
4. Only after Completed Work provided:
   - Set Completed Work
   - Set Resolved Reason
   - Set State = Resolved
5. Confirm: "Bug #500 resolved. Completed Work: 2h, Reason: Fixed"
```

---

## Rule 7: Auto-Sprint Detection for Tasks

### MANDATORY: Assign to Current Working Sprint

When creating a Task, automatically detect and assign the current sprint based on today's date:

```
┌─────────────────────────────────────────────────────────────────┐
│              AUTO-SPRINT DETECTION RULE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE creating a Task:                                        │
│                                                                  │
│  1. Get current date (today)                                    │
│  2. Fetch team iterations via work_list_team_iterations         │
│  3. Find iteration where: startDate <= today <= finishDate      │
│  4. Set System.IterationPath to that sprint                     │
│                                                                  │
│  IF no current sprint found:                                    │
│  → Ask user to select from available sprints                    │
│  → Present list with dates                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Detection Logic

```javascript
// Step 1: Get team iterations
const iterations = await mcp__azure-devops__work_list_team_iterations({
  "project": projectName,
  "team": teamName
});

// Step 2: Find current sprint by date
const today = new Date();
const currentSprint = iterations.find(iter => {
  const start = new Date(iter.attributes.startDate);
  const finish = new Date(iter.attributes.finishDate);
  return today >= start && today <= finish;
});

// Step 3: Assign or ask
if (currentSprint) {
  // Use this sprint's path
  iterationPath = currentSprint.path;
} else {
  // Present options to user
  askUserToSelectSprint(iterations);
}
```

### Example

```
Today: 2025-12-29

Team Iterations:
| Sprint | Start Date | End Date | Status |
|--------|------------|----------|--------|
| Sprint 14 | 2025-12-01 | 2025-12-14 | Past |
| Sprint 15 | 2025-12-15 | 2025-12-28 | Past |
| Sprint 16 | 2025-12-29 | 2026-01-11 | ← CURRENT |
| Sprint 17 | 2026-01-12 | 2026-01-25 | Future |

Auto-detected: Sprint 16
Task will be created with: System.IterationPath = "Project\Sprint 16"
```

### Fallback Behavior

If no sprint matches today's date:
1. Show available sprints to user
2. Let user choose
3. If user doesn't specify, use the **next upcoming sprint**

---

## Rule 8: Bug Creation Authority & Developer Internal Fix SOP

### Policy Statement

**Bugs are reserved exclusively for defects identified by QA/QC.**

When a developer identifies and fixes an issue in their own code, the effort MUST be logged as a **Task**, not a Bug. This ensures accurate bug metrics and clear separation of Dev/QA responsibilities.

### Role-Based Bug Creation Gate

```
+---------------------------------------------------------------+
|           BUG CREATION AUTHORITY (MANDATORY)                   |
+---------------------------------------------------------------+
|                                                                |
|  CHECK user's role from ~/.claude/devops.md profile:          |
|                                                                |
|  role = "tester" / "qa" / "qc-bugfix" / "qc-test"           |
|    → ALLOWED to create Bugs                                   |
|    → Standard bug creation flow applies                       |
|                                                                |
|  role = "developer" / "frontend" / "fullstack" / "devops"    |
|  role = "pm" / "lead" / ANY non-QA role                      |
|    → BLOCKED from creating Bugs                               |
|    → REDIRECT to Task creation with [Dev-Internal-fix]        |
|    → Show: "As a {role}, you should create a Task instead.   |
|       Bugs are reserved for QA/QC-identified defects.         |
|       I'll create a [Dev-Internal-fix] Task for you."        |
|                                                                |
|  role = not set / profile missing                             |
|    → ASK: "Are you QA/QC? Only QA can create Bugs.           |
|       If you're a developer, I'll create a Task instead."    |
|                                                                |
+---------------------------------------------------------------+
```

### Developer Internal Fix — Process Scenarios

#### Scenario A: Issue Found During an Active PBI (PBI still In Progress)

```
Developer: "I found a bug in the login code, need to fix it"

Claude checks profile → role: developer → CANNOT create Bug

Claude response:
  "Since the PBI is still in progress, log the fix on the existing Task.

   I'll add a comment to your current Task describing:
   - The issue found
   - The fix applied

   No new work item needed. Log your fix time on the existing Task."

Actions:
1. Find the developer's active Task under the PBI
2. Add a comment with issue description using the Bug Report Template format (data/bug_report_template.md)
3. Log time on the existing Task
4. ALWAYS mention QC member as FYI (see Auto-Mention rule below)
```

#### Scenario B: Issue Found After the PBI Is Done

```
Developer: "I found an issue in the login module but the PBI is already done"

Claude checks profile → role: developer → CANNOT create Bug

Claude response:
  "Since the PBI is already Done, I'll create a [Dev-Internal-fix] Task
   under the original PBI and move the PBI back to In Progress."

Actions:
1. Create a new Task under the original User Story / PBI (as Child)
2. Title format: [Dev-Internal-fix] [Module/Feature] - [What is broken] - [Where]
3. Use Bug Report Template for description body (data/bug_report_template.md)
4. Move parent PBI back to In Progress
5. ALWAYS mention QC member as FYI (see Auto-Mention rule below)
6. Developer applies fix, logs time, closes Task
```

**Task creation for Scenario B**:
```javascript
// Step 1: Create [Dev-Internal-fix] Task
const task = await mcp__azure-devops__wit_create_work_item({
  "project": currentProject,
  "workItemType": "Task",
  "fields": [
    { "name": "System.Title", "value": "[Dev-Internal-fix] " + description },
    { "name": "System.Description", "value": issueAndFixDescription },
    { "name": "System.IterationPath", "value": currentSprintPath }
  ]
});

// Step 2: Link to parent PBI
await mcp__azure-devops__wit_work_items_link({
  "project": currentProject,
  "updates": [{ "id": task.id, "linkToId": pbiId, "type": "child" }]
});

// Step 3: Move parent PBI back to In Progress
await mcp__azure-devops__wit_update_work_item({
  "id": pbiId,
  "updates": [
    { "path": "/fields/System.State", "value": "In Progress" }
  ]
});

// Step 4: Add comment mentioning QA Lead
// Use profile teamMembers to find QA lead, resolve GUID, format HTML mention
```

### Auto-Mention QC Rule (MANDATORY — Every [Dev-Internal-fix])

**EVERY** `[Dev-Internal-fix]` Task must notify QC — this is NOT conditional.

```
+---------------------------------------------------------------+
|           AUTO-MENTION QC RULE (MANDATORY)                     |
+---------------------------------------------------------------+
|                                                                |
|  AFTER creating any [Dev-Internal-fix] Task:                  |
|                                                                |
|  1. Find QC/QA member from profile teamMembers               |
|     (where role = "tester" or "qa")                           |
|  2. Resolve GUID from profile cache                           |
|  3. Post FYI comment with HTML mention:                       |
|                                                                |
|     "@{QC_Member} FYI: Developer-identified fix created.      |
|     [Dev-Internal-fix] {title}                                |
|     Parent PBI: #{pbiId} - {pbiTitle}                         |
|     Please monitor for any QC implications."                  |
|                                                                |
+---------------------------------------------------------------+
```

### Raise Flag Rule (Escalation — User-Facing Changes)

**In addition** to the mandatory FYI mention, if the fix changes user-facing behavior:

```
+---------------------------------------------------------------+
|           RAISE FLAG ESCALATION                                |
+---------------------------------------------------------------+
|                                                                |
|  BEFORE closing the [Dev-Internal-fix] Task, ASK:            |
|                                                                |
|  "Does this fix change any user-facing behavior?"             |
|                                                                |
|  If YES → ESCALATE (in addition to the FYI):                 |
|  1. Post ATTENTION comment to QA Lead:                        |
|     "@{QA_Lead} ATTENTION: This [Dev-Internal-fix] changes   |
|     user-facing behavior: {description}.                      |
|     Please assess if regression testing is needed."           |
|  2. QA Lead decides — involvement is decision-based          |
|                                                                |
|  If NO → FYI mention was already posted, no escalation       |
|                                                                |
+---------------------------------------------------------------+
```

### Enforcement in `/create` Command

When a user requests bug creation:

```
1. Load user profile (role from ~/.claude/devops.md)
2. IF role is QA/QC:
   → Proceed with standard Bug creation
3. IF role is NOT QA/QC:
   → BLOCK Bug creation
   → Ask: "Is the parent PBI still In Progress or already Done?"
     - In Progress → Scenario A (log on existing Task)
     - Done → Scenario B (create [Dev-Internal-fix] Task)
   → Ask: "Does this fix change user-facing behavior?" (Raise Flag)
4. IF no profile:
   → Ask: "Are you QA/QC? Only QA can create Bugs."
```

### Roles & Responsibilities

| Role | Responsibility |
|------|---------------|
| **Developer** | Create/use Task with `[Dev-Internal-fix]`, fix code, log time, close Task |
| **QA/QC** | Create Bugs for defects they identify. No action on dev fixes unless flagged. |
| **Project Manager** | Monitor `[Dev-Internal-fix]` volume and trends in sprint reports |
| **QA Lead** | Assess flagged fixes for regression testing need (decision-based) |

### Definitions

| Term | Definition |
|------|-----------|
| **Bug** | A defect identified and logged by QA/QC, owned by Quality |
| **Task** | A development work item, including internal fixes by developers |
| **[Dev-Internal-fix]** | Special Task prefix for developer self-identified fixes |
| **PBI** | Product Backlog Item — a business requirement being delivered |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│              TAQATECHNO BUSINESS RULES QUICK REF                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HIERARCHY:                                                      │
│  Epic → Feature → User Story → Task / Bug / Enhancement         │
│  (Task, Bug, Enhancement are siblings under User Story)         │
│                                                                  │
│  USER STORY FORMAT:                                             │
│  How? (approach) → What? (requirements) → Why? (value)          │
│                                                                  │
│  STORY STATE FLOW:                                              │
│  Must go through "Ready for QC" before "Done"                   │
│                                                                  │
│  TASK PREFIXES:                                                 │
│  [Dev] backend | [Front] frontend | [QC Bug Fixing] fix | [QC Test Execution] test | [IMP] deploy │
│                                                                  │
│  AUTO-SPRINT:                                                   │
│  Tasks auto-assigned to current sprint by date                  │
│                                                                  │
│  TASK → DONE:                                                   │
│  Requires: Original Estimate + Completed Hours                  │
│                                                                  │
│  BUG → RESOLVED/DONE:                                           │
│  Requires: Completed Work                                       │
│                                                                  │
│  BUG CREATION AUTHORITY:                                        │
│  QA/QC role → CAN create Bugs                                  │
│  Developer role → BLOCKED → use [Dev-Internal-fix] Task         │
│  User-facing fix → Flag QA Lead for regression assessment       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

*YOUR-ORG Business Rules v1.1*
*December 2025*
