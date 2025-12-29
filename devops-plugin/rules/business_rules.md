# TaqaTechno Business Rules

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
                           +--- Bug (Defect found during task)
```

### Enforcement Rules

| Creating | MUST Have Parent | Parent Type |
|----------|------------------|-------------|
| **Bug** | YES (MANDATORY) | Task |
| **Task** | YES (MANDATORY) | User Story / PBI |
| **User Story / PBI** | YES (MANDATORY) | Feature |
| **Feature** | YES (MANDATORY) | Epic |
| **Epic** | NO | Top-level |

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

### Example: Creating a Bug

```
User: "Create bug: Login button not working"

Claude MUST:
1. Ask: "Which Task is this bug related to?"
2. If user doesn't know:
   - Search for related tasks: "What feature/area were you working on?"
   - Present task options
3. Create bug
4. Link bug as child of the task
5. Confirm: "Bug #1234 created under Task #100"
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

All Task titles MUST start with a type prefix:

| Prefix | Role | Description |
|--------|------|-------------|
| `[DEV]` | Backend Developer | Server-side, database, APIs |
| `[FRONT]` | Frontend Developer | UI, client-side, JavaScript |
| `[QA]` | Tester/QA | Testing, test cases, bug verification |
| `[IMP]` | Implementation | Configuration, deployment, setup |

### Format

```
[PREFIX] Task description
```

### Examples

```
[DEV] Implement user authentication API
[FRONT] Create login form component
[QA] Write test cases for login flow
[IMP] Configure OAuth2 settings in production
```

### Enforcement

When creating a task:

1. **Detect task type** from context or ask user:
   - "Is this a backend [DEV], frontend [FRONT], testing [QA], or implementation [IMP] task?"

2. **Add prefix** if not provided:
   - User says: "Create task: Implement login API"
   - Claude adds: "[DEV] Implement login API"

3. **Validate prefix** on existing tasks:
   - If task has no prefix, suggest adding one

### Auto-Detection Rules

| Keywords in Title | Suggested Prefix |
|-------------------|------------------|
| API, endpoint, database, model, backend, server | `[DEV]` |
| UI, component, form, page, style, CSS, frontend, client | `[FRONT]` |
| test, QA, verify, validate, check, bug fix verification | `[QA]` |
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

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│              TAQATECHNO BUSINESS RULES QUICK REF                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  HIERARCHY:                                                      │
│  Epic → Feature → User Story → Task → Bug                       │
│  (Every item MUST have parent except Epic)                      │
│                                                                  │
│  USER STORY FORMAT:                                             │
│  How? (approach) → What? (requirements) → Why? (value)          │
│                                                                  │
│  STORY STATE FLOW:                                              │
│  Must go through "Ready for QC" before "Done"                   │
│                                                                  │
│  TASK PREFIXES:                                                 │
│  [DEV] backend | [FRONT] frontend | [QA] test | [IMP] deploy    │
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
└─────────────────────────────────────────────────────────────────┘
```

---

*TaqaTechno Business Rules v1.1*
*December 2025*
