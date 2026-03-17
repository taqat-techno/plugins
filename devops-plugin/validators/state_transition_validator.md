# State Transition Pre-Flight Validator

## Purpose

This validator **PREVENTS** state transition failures by checking required fields **BEFORE** attempting the update. It transforms cryptic API errors into guided workflows that help users succeed.

**Problem Solved**: Users try to mark a Task as "Done" and get `VS403507 - Field cannot be empty` because OriginalEstimate/CompletedWork are missing.

---

## Step 0: Role-Based Permission Check (MANDATORY)

**BEFORE validating required fields**, check if the user's role allows this transition:

```
1. Load user profile from ~/.claude/devops.md
2. Read statePermissions.{WorkItemType}
3. Check if transition "{currentState} → {targetState}" is in allowed[]

DECISION:
  IF in allowed[]        → PROCEED to field validation (Step 1+)
  IF in blocked[]        → BLOCK with blockedMessage + suggest who can do it
  IF not in either list  → WARN but allow (unknown transition)
  IF no profile loaded   → WARN "No DevOps profile found. Run /init profile for role-based guardrails." and ALLOW
```

**Example: Developer tries to close a Bug**:
```
Profile: Developer
Transition: Resolved → Closed
Check: statePermissions.Bug.blocked[] contains "Resolved → Closed"

→ BLOCK: "Only QA Lead or Project Manager can close resolved bugs.
          Ask @qa-lead to close Bug #500."
```

**Example: No profile loaded**:
```
Profile: [not found]

→ WARN: "No DevOps profile found. Run /init profile for role-based guardrails."
→ ALLOW transition (proceed to field validation)
```

---

## MANDATORY: Before Any State Change

### Validation Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│              PRE-FLIGHT VALIDATION WORKFLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User: "Mark task #1234 as Done"                                │
│                                                                  │
│  STEP 0: ROLE-BASED PERMISSION CHECK                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Load ~/.claude/devops.md                                │    │
│  │ Check statePermissions.Task for "In Progress → Done"    │    │
│  │ IF blocked → STOP and show blockedMessage               │    │
│  │ IF allowed or no profile → CONTINUE                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 1: FETCH CURRENT STATE                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ wit_get_work_item({                                     │    │
│  │   id: 1234,                                             │    │
│  │   project: "Project Alpha",                             │    │
│  │   fields: [                                             │    │
│  │     "System.State",                                     │    │
│  │     "System.WorkItemType",                              │    │
│  │     "Microsoft.VSTS.Scheduling.OriginalEstimate",       │    │
│  │     "Microsoft.VSTS.Scheduling.CompletedWork",          │    │
│  │     "Microsoft.VSTS.Scheduling.RemainingWork",          │    │
│  │     "Microsoft.VSTS.Common.ResolvedReason"              │    │
│  │   ]                                                     │    │
│  │ })                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: CHECK REQUIRED FIELDS                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Type: Task                                              │    │
│  │ Current State: In Progress                              │    │
│  │ Target State: Done                                      │    │
│  │                                                         │    │
│  │ Required Fields for In Progress → Done:                 │    │
│  │   ✗ OriginalEstimate: [MISSING]                         │    │
│  │   ✗ CompletedWork: [MISSING]                            │    │
│  │   ○ RemainingWork: Will auto-set to 0                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 3: ASK USER FOR MISSING VALUES                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ "To mark task #1234 as Done, I need:                    │    │
│  │                                                         │    │
│  │ • Original Estimate (hours): ___                        │    │
│  │ • Completed Work (hours): ___                           │    │
│  │                                                         │    │
│  │ Please provide these values."                           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 4: EXECUTE SINGLE UPDATE (after user provides values)     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ wit_update_work_item({                                  │    │
│  │   id: 1234,                                             │    │
│  │   updates: [                                            │    │
│  │     { path: "/.../OriginalEstimate", value: "8" },      │    │
│  │     { path: "/.../CompletedWork", value: "6" },         │    │
│  │     { path: "/.../RemainingWork", value: "0" },         │    │
│  │     { path: "/fields/System.State", value: "Done" }     │    │
│  │   ]                                                     │    │
│  │ })                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## State Machine Diagrams (TaqaTechno Scrum Process)

### Task States
```
To Do → In Progress → Done → Closed → Removed

State Categories:
  Proposed:    To Do
  In Progress: In Progress
  Completed:   Done, Closed
  Removed:     Removed
```

### Bug States
```
New → Approved → In Progress → Resolved → Done → Closed → Removed
                      │              │
                      ↑              ↓
                      └── Return ←───┘

State Categories:
  Proposed:    New
  In Progress: Approved, In Progress, Committed, Return
  Resolved:    Resolved
  Completed:   Done, Closed
  Removed:     Removed

Key Transitions:
  Resolved → Return:   QA rejects the fix (COMMENT MANDATORY)
  Return → In Progress: Developer picks up returned bug
  In Progress → Committed: Developer marks as committed
  Committed → Done:    Verified and completed
```

### Product Backlog Item (PBI) States
```
New → Approved → Committed → In Progress → Ready For QC → Done → Removed
                                  │               │
                                  ↑               ↓
                                  └── Return ←────┘

State Categories:
  Proposed:    New
  In Progress: Approved, Committed, In Progress, Return
  QC:          Ready For QC
  Completed:   Done
  Removed:     Removed

Key Transitions:
  Ready For QC → Return:   QA rejects (COMMENT MANDATORY)
  Return → In Progress:    Developer picks up returned PBI
  In Progress → Ready For QC: Developer confirms QC readiness
```

### User Story States
```
New → Committed → Done

State Categories:
  Proposed:    New
  In Progress: Committed
  Completed:   Done
```

### Enhancement States
```
New → Committed → Done → Closed
          │
          ↑
          └── Return

State Categories:
  Proposed:    New
  In Progress: Committed, Return
  Completed:   Done, Closed

Key Transitions:
  Committed → Return:   Sent back for rework (COMMENT MANDATORY)
  Return → Committed:   Developer resubmits after rework (NOT Return → In Progress)
```

### Feature States
```
New → In Progress → Done → Removed

State Categories:
  Proposed:    New
  In Progress: In Progress
  Completed:   Done
  Removed:     Removed
```

### Epic States
```
New → In Progress → Done → Removed

State Categories:
  Proposed:    New
  In Progress: In Progress
  Completed:   Done
  Removed:     Removed
```

---

## Required Fields by Work Item Type and Transition

### Task Transitions

| From State | To State | Required Fields | Auto-Set Fields |
|------------|----------|-----------------|-----------------|
| To Do | In Progress | - | - |
| In Progress | Done | `OriginalEstimate`, `CompletedWork` | `RemainingWork=0` |
| To Do | Done | `OriginalEstimate`, `CompletedWork` | `RemainingWork=0` |
| Done | Closed | - | - |
| Any | Removed | - | - |

**Field Paths**:
```
Microsoft.VSTS.Scheduling.OriginalEstimate  (hours)
Microsoft.VSTS.Scheduling.CompletedWork     (hours)
Microsoft.VSTS.Scheduling.RemainingWork     (hours)
```

### Bug Transitions

| From State | To State | Required Fields | Auto-Set/Defaults |
|------------|----------|-----------------|-------------------|
| New | Approved | - | - |
| Approved | In Progress | - | - |
| In Progress | Resolved | `ResolvedReason` | Default: "Fixed" |
| Resolved | Return | **Comment** (return reason) | - |
| Return | In Progress | - | - |
| In Progress | Committed | - | - |
| Committed | Done | - | - |
| Done | Closed | - | - |
| Any | Removed | - | - |

**Field Paths**:
```
Microsoft.VSTS.Common.ResolvedReason
System.History                          (for mandatory comments)
```

**Valid ResolvedReason Values**:
- Fixed (default)
- As Designed
- Cannot Reproduce
- Deferred
- Duplicate
- Not a Bug
- Obsolete

### Product Backlog Item (PBI) Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Approved | - | - |
| Approved | Committed | - | - |
| Committed | In Progress | - | - |
| In Progress | Ready For QC | - | Developer confirms QC readiness |
| Ready For QC | Return | **Comment** (return reason) | QA rejects the item |
| Ready For QC | Done | - | QA approves |
| Return | In Progress | - | Developer picks up returned PBI |
| Any | Removed | - | - |

### User Story Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Committed | - | - |
| Committed | Done | - | - |

### Enhancement Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Committed | - | - |
| Committed | Return | **Comment** (return reason) | Sent back for rework |
| Return | Committed | - | Developer resubmits |
| Committed | Done | - | - |
| Done | Closed | - | - |

### Feature Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | In Progress | - | - |
| In Progress | Done | - | - |
| Any | Removed | - | - |

### Epic Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | In Progress | - | - |
| In Progress | Done | - | - |
| Any | Removed | - | - |

---

## Return Loop Handling

### When QA Returns a Work Item

The **Return** state is a QA rejection mechanism used in Bug, PBI, and Enhancement workflows. A comment explaining the return reason is **ALWAYS MANDATORY**.

```
RULE: Any transition INTO "Return" state REQUIRES a comment.

IF targetState == "Return":
  1. REQUIRE comment from user explaining the return reason
  2. IF no comment provided:
     → DO NOT execute transition
     → ASK: "A return reason is required. Please describe why this item
             is being returned (e.g., 'Fix does not address edge case X',
             'Unit tests failing on scenario Y')."
  3. Include comment in update:
     { path: "/fields/System.History", value: "<return reason>" }
  4. Execute state change with comment in SINGLE update
```

### Return → Resume Paths

Each work item type has a specific path out of the Return state:

| Work Item Type | Return → Next State | Notes |
|----------------|---------------------|-------|
| Bug | Return → In Progress | Developer picks up and reworks the fix |
| PBI | Return → In Progress | Developer addresses QA feedback |
| Enhancement | Return → Committed | Developer resubmits (no "In Progress" state for Enhancement) |

### Return Interaction Pattern

**QA**: "Return PBI #2000"

**Claude** (after permission + pre-flight check):
```
To return PBI #2000 "Implement search filters", I need:

**Required:**
• Return reason: Please describe why this is being returned to the developer.

This will move the PBI from "Ready For QC" back to "Return" and notify
the assigned developer.
```

**QA**: "Search by date range not working, returns all results regardless of dates"

**Claude**:
```
Returning PBI #2000...

✓ State: Ready For QC → Return
✓ Comment: "Search by date range not working, returns all results regardless of dates"

PBI #2000 has been returned. The developer will see it in their Return queue.
```

---

## Validation Rules

### Rule 1: Check Role Permissions Before Anything

```
BEFORE any field validation or state change:

1. LOAD user profile from ~/.claude/devops.md
2. READ statePermissions.{WorkItemType}
3. CHECK if "{currentState} → {targetState}" is in allowed[]

IF in blocked[]:
  → BLOCK with blockedMessage
  → SUGGEST who can perform this transition
  → DO NOT proceed to field validation

IF in allowed[] or not in either list or no profile:
  → PROCEED to field validation (Rule 2+)
```

### Rule 2: Check Required Fields Before State Change

```
BEFORE executing wit_update_work_item with State change:

1. GET current work item:
   wit_get_work_item({ id, project, expand: "fields" })

2. IDENTIFY work item type and current state

3. LOOKUP required fields from data/required_fields.json:
   requiredFields = REQUIRED_FIELDS[workItemType].transitions[targetState]

4. CHECK each required field:
   FOR each field in requiredFields.required:
     IF field value is null/empty/0:
       missingFields.push(field)

5. IF targetState == "Return":
   → REQUIRE comment (System.History) — no exceptions

6. IF missingFields.length > 0:
   → DO NOT attempt update
   → ASK user for missing values
   → EXPLAIN why each field is needed

7. ONLY after all fields provided:
   → Execute SINGLE update with all fields + state change
```

### Rule 3: Enforce Return Comment Requirement

```
IF targetState == "Return"
   AND (workItemType IN ["Bug", "Product Backlog Item", "Enhancement"]):

   → REQUIRE comment explaining return reason
   → IF no comment provided:
     → BLOCK transition
     → ASK: "Please provide a reason for returning this item."
   → Include comment as System.History in update payload
```

### Rule 4: Auto-Set Companion Fields

```
IF transition has auto_set fields:
   → Include in update automatically
   → INFORM user: "I'll also set RemainingWork to 0"

Example for Task In Progress → Done:
{
  "updates": [
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },  // AUTO-SET
    { "path": "/fields/System.State", "value": "Done" }
  ]
}
```

### Rule 5: Provide Defaults When Available

```
IF transition has defaults AND user doesn't specify:
   → OFFER default value
   → ASK for confirmation

Example for Bug In Progress → Resolved:
"Setting ResolvedReason to 'Fixed' (default).
 Would you like to use a different reason?
 Options: As Designed, Cannot Reproduce, Deferred, Duplicate, Not a Bug, Obsolete"
```

---

## Pre-Flight Check Implementation

### Step 1: Fetch Work Item with Required Fields

```javascript
// Get current state and all potentially required fields
mcp__azure-devops__wit_get_work_item({
  "id": 1234,
  "project": "Project Alpha",
  "fields": [
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
    "System.History",
    "Microsoft.VSTS.Scheduling.OriginalEstimate",
    "Microsoft.VSTS.Scheduling.CompletedWork",
    "Microsoft.VSTS.Scheduling.RemainingWork",
    "Microsoft.VSTS.Common.ResolvedReason"
  ]
})
```

### Step 2: Validate Transition

```javascript
// Pseudo-code for validation logic
function validateTransition(workItem, targetState, userProfile) {
  const type = workItem["System.WorkItemType"];
  const currentState = workItem["System.State"];
  const transition = `${currentState} → ${targetState}`;

  // Step 0: Role-based permission check
  if (userProfile?.statePermissions?.[type]) {
    const perms = userProfile.statePermissions[type];
    if (perms.blocked?.some(b => b.transition === transition)) {
      const rule = perms.blocked.find(b => b.transition === transition);
      return {
        valid: false,
        error: rule.blockedMessage,
        roleBlocked: true
      };
    }
  }

  // Check if transition requires mandatory comment (Return states)
  if (targetState === "Return") {
    return {
      valid: false,
      requiresComment: true,
      message: "Return transitions require a comment explaining the reason."
    };
  }

  // Check required fields
  const rules = REQUIRED_FIELDS[type]?.transitions[targetState];
  const missing = [];
  for (const field of rules?.required || []) {
    if (!workItem[field] || workItem[field] === 0) {
      missing.push(field);
    }
  }

  if (missing.length > 0) {
    return {
      valid: false,
      missingFields: missing,
      autoSet: rules?.auto_set || {}
    };
  }

  return { valid: true };
}
```

### Step 3: Execute Update with All Fields

```javascript
// After user provides missing values
mcp__azure-devops__wit_update_work_item({
  "id": 1234,
  "updates": [
    // User-provided fields
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    // Auto-set fields
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },
    // State change (LAST)
    { "path": "/fields/System.State", "value": "Done" }
  ]
})

// For Return transitions — include comment
mcp__azure-devops__wit_update_work_item({
  "id": 2000,
  "updates": [
    { "path": "/fields/System.History", "value": "Search by date range not working" },
    { "path": "/fields/System.State", "value": "Return" }
  ]
})
```

---

## User Interaction Patterns

### Pattern 1: Missing Hours for Task → Done

**User**: "Mark task #1234 as Done"

**Claude** (after pre-flight check):
```
To mark task #1234 "Fix login bug" as Done, I need the following:

**Required Fields:**
• Original Estimate (hours): How many hours did you estimate for this task?
• Completed Work (hours): How many hours did you actually spend?

I'll automatically set Remaining Work to 0.

Please provide these values.
```

**User**: "8 hours estimated, took 6 hours"

**Claude**:
```
Updating task #1234...

✓ Original Estimate: 8 hours
✓ Completed Work: 6 hours
✓ Remaining Work: 0 hours (auto-set)
✓ State: In Progress → Done

Task #1234 "Fix login bug" is now Done!
```

### Pattern 2: Bug with Default ResolvedReason

**User**: "Resolve bug #500"

**Claude** (after pre-flight check):
```
Resolving bug #500 "UI alignment issue"...

**Resolved Reason**: Fixed (default)

Would you like to use a different reason?
• As Designed
• Cannot Reproduce
• Deferred
• Duplicate
• Not a Bug
• Obsolete

Or press Enter to use "Fixed".
```

### Pattern 3: QA Returns a Bug

**User**: "Return bug #500 to developer"

**Claude** (after pre-flight check):
```
To return bug #500 "UI alignment issue", I need:

**Required:**
• Return reason: Please describe why this fix is being rejected.

This will move the bug from "Resolved" to "Return".
```

**User**: "Fix only works on Chrome, still broken on Firefox and Safari"

**Claude**:
```
Returning bug #500...

✓ State: Resolved → Return
✓ Comment: "Fix only works on Chrome, still broken on Firefox and Safari"

Bug #500 has been returned to the developer.
```

### Pattern 4: Role-Blocked Transition

**User**: "Close bug #500"

**Claude** (after role check):
```
⚠️ Permission Denied

Your role (Developer) does not allow closing bugs.
Transition "Done → Closed" is restricted.

**Who can do this**: QA Lead, Project Manager
**Suggestion**: Ask your QA Lead to close Bug #500.
```

### Pattern 5: PBI Ready For QC

**User**: "Move PBI #2000 to Ready For QC"

**Claude** (after pre-flight check):
```
Moving PBI #2000 "Implement search filters" to Ready For QC...

This confirms the item is ready for QA review.

✓ State: In Progress → Ready For QC

PBI #2000 is now in the QC queue.
```

---

## Error Recovery

### If Update Still Fails After Pre-Flight

```
If wit_update_work_item returns error despite pre-flight check:

1. PARSE error message
2. IDENTIFY missing field from error
3. ADD to required fields cache (learning)
4. ASK user for the additional field
5. RETRY update

Example:
Error: VS403507 - Field 'Custom.ReviewedBy' cannot be empty

Response:
"It looks like this project requires an additional field:
 • Reviewed By: Who reviewed this task?

Please provide this value."
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│             STATE TRANSITION RULES (TaqaTechno Scrum)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TASK (To Do → In Progress → Done → Closed → Removed)          │
│  ├── In Progress → Done                                         │
│  │   ├── REQUIRES: OriginalEstimate (hours)                     │
│  │   ├── REQUIRES: CompletedWork (hours)                        │
│  │   └── AUTO-SET: RemainingWork = 0                            │
│  └── To Do → Done (same requirements as above)                  │
│                                                                  │
│  BUG (New → Approved → In Progress → Resolved → Done → Closed) │
│  ├── In Progress → Resolved                                     │
│  │   └── REQUIRES: ResolvedReason (default: "Fixed")            │
│  ├── Resolved → Return                                          │
│  │   └── REQUIRES: Comment (return reason) ⚠️ MANDATORY         │
│  └── Return → In Progress (developer reworks)                   │
│                                                                  │
│  PBI (New → Approved → Committed → In Progress → Ready For QC  │
│       → Done → Removed)                                         │
│  ├── In Progress → Ready For QC (developer confirms QC ready)   │
│  ├── Ready For QC → Return                                      │
│  │   └── REQUIRES: Comment (return reason) ⚠️ MANDATORY         │
│  └── Return → In Progress (developer reworks)                   │
│                                                                  │
│  USER STORY (New → Committed → Done)                            │
│  └── Simple two-step flow, no special requirements              │
│                                                                  │
│  ENHANCEMENT (New → Committed → Done → Closed)                  │
│  ├── Committed → Return                                         │
│  │   └── REQUIRES: Comment (return reason) ⚠️ MANDATORY         │
│  └── Return → Committed (developer resubmits)                   │
│                                                                  │
│  FEATURE (New → In Progress → Done → Removed)                   │
│  └── No special field requirements                              │
│                                                                  │
│  EPIC (New → In Progress → Done → Removed)                      │
│  └── No special field requirements                              │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│  ROLE CHECK: Always runs BEFORE field validation.               │
│  RETURN RULE: ALL Return transitions require a comment.         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

This validator integrates with:

1. **SKILL.md** - Main skill file references this validator
2. **data/required_fields.json** - Lookup table for field requirements
3. **errors/error_recovery.md** - Error handling for failed transitions
4. **commands/update-task.md** - Uses validator before updates
5. **~/.claude/devops.md** - User profile for role-based permission checks

---

*State Transition Validator v2.0*
*Part of DevOps Plugin v3.0 Enhancement*
*TaqaTechno - March 2026*
