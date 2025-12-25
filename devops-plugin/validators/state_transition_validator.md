# State Transition Pre-Flight Validator

## Purpose

This validator **PREVENTS** state transition failures by checking required fields **BEFORE** attempting the update. It transforms cryptic API errors into guided workflows that help users succeed.

**Problem Solved**: Users try to mark a Task as "Done" and get `VS403507 - Field cannot be empty` because OriginalEstimate/CompletedWork are missing.

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
│  STEP 1: FETCH CURRENT STATE                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ wit_get_work_item({                                     │    │
│  │   id: 1234,                                             │    │
│  │   project: "Relief Center",                             │    │
│  │   fields: [                                             │    │
│  │     "System.State",                                     │    │
│  │     "System.WorkItemType",                              │    │
│  │     "Microsoft.VSTS.Scheduling.OriginalEstimate",       │    │
│  │     "Microsoft.VSTS.Scheduling.CompletedWork",          │    │
│  │     "Microsoft.VSTS.Scheduling.RemainingWork"           │    │
│  │   ]                                                     │    │
│  │ })                                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  STEP 2: CHECK REQUIRED FIELDS                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Type: Task                                              │    │
│  │ Current State: Active                                   │    │
│  │ Target State: Done                                      │    │
│  │                                                         │    │
│  │ Required Fields for Active → Done:                      │    │
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

## Required Fields by Work Item Type and Transition

### Task Transitions

| From State | To State | Required Fields | Auto-Set Fields |
|------------|----------|-----------------|-----------------|
| New | Active | - | - |
| Active | Done | `OriginalEstimate`, `CompletedWork` | `RemainingWork=0` |
| New | Done | `OriginalEstimate`, `CompletedWork` | `RemainingWork=0` |
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
| New | Active | - | - |
| Active | Resolved | `ResolvedReason` | Default: "Fixed" |
| Resolved | Closed | - | - |
| Any | Removed | - | - |

**Field Paths**:
```
Microsoft.VSTS.Common.ResolvedReason
```

**Valid ResolvedReason Values**:
- Fixed (default)
- As Designed
- Cannot Reproduce
- Deferred
- Duplicate
- Not a Bug
- Obsolete

### User Story Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Active | - | - |
| Active | Ready for QC | - | - |
| Ready for QC | Done | - | - |
| Active | Done | **BLOCKED** | Must go through "Ready for QC" |
| New | Done | **BLOCKED** | Must go through "Ready for QC" |

**State Machine Enforcement**:
```
User Story State Flow:
  New → Active → Ready for QC → Done → Closed
                      ↑
                      │ MANDATORY CHECKPOINT
                      │ Cannot skip directly to Done!
```

### Product Backlog Item (PBI) Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Approved | - | - |
| Approved | Committed | - | - |
| Committed | Done | - | - |
| Any | Removed | - | - |

### Feature Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Active | - | - |
| Active | Resolved | - | - |
| Resolved | Closed | - | - |

### Epic Transitions

| From State | To State | Required Fields | Notes |
|------------|----------|-----------------|-------|
| New | Active | - | - |
| Active | Resolved | - | - |
| Resolved | Closed | - | - |

---

## Validation Rules

### Rule 1: Check Required Fields Before State Change

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

5. IF missingFields.length > 0:
   → DO NOT attempt update
   → ASK user for missing values
   → EXPLAIN why each field is needed

6. ONLY after all fields provided:
   → Execute SINGLE update with all fields + state change
```

### Rule 2: Enforce State Machine for User Stories

```
IF workItemType == "User Story"
   AND targetState == "Done"
   AND currentState NOT IN ["Ready for QC"]:

   → BLOCK direct transition
   → WARN: "User Stories must pass through 'Ready for QC' before Done"
   → OFFER: "Would you like me to:
            1. Move to 'Ready for QC' now, then Done?
            2. Just move to 'Ready for QC' for now?"
```

### Rule 3: Auto-Set Companion Fields

```
IF transition has auto_set fields:
   → Include in update automatically
   → INFORM user: "I'll also set RemainingWork to 0"

Example for Task → Done:
{
  "updates": [
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },  // AUTO-SET
    { "path": "/fields/System.State", "value": "Done" }
  ]
}
```

### Rule 4: Provide Defaults When Available

```
IF transition has defaults AND user doesn't specify:
   → OFFER default value
   → ASK for confirmation

Example for Bug → Resolved:
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
  "project": "Relief Center",
  "fields": [
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
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
function validateTransition(workItem, targetState) {
  const type = workItem["System.WorkItemType"];
  const currentState = workItem["System.State"];

  // Check if transition is blocked
  const rules = REQUIRED_FIELDS[type]?.transitions[targetState];
  if (rules?.blocked_from?.includes(currentState)) {
    return {
      valid: false,
      error: rules.message,
      suggestion: rules.requires_intermediate
    };
  }

  // Check required fields
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
✓ State: Done

Task #1234 "Fix login bug" is now Done!
```

### Pattern 2: User Story Blocked from Done

**User**: "Mark user story #1000 as Done"

**Claude** (after pre-flight check):
```
⚠️ Cannot mark User Story #1000 as Done directly.

**Reason**: User Stories must pass through "Ready for QC" before Done.

**Current State**: Active
**Required Path**: Active → Ready for QC → Done

Would you like me to:
1. Move to "Ready for QC" now (I can mark it Done later after QC)
2. Move through both states now (Ready for QC → Done)

Please choose an option.
```

### Pattern 3: Bug with Default ResolvedReason

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
│                 STATE TRANSITION RULES                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TASK → Done                                                    │
│  ├── REQUIRES: OriginalEstimate (hours)                         │
│  ├── REQUIRES: CompletedWork (hours)                            │
│  └── AUTO-SET: RemainingWork = 0                                │
│                                                                  │
│  BUG → Resolved                                                 │
│  └── REQUIRES: ResolvedReason (default: "Fixed")                │
│                                                                  │
│  USER STORY → Done                                              │
│  └── ⚠️ BLOCKED if not in "Ready for QC"                        │
│      Path: Active → Ready for QC → Done                         │
│                                                                  │
│  PBI → Done                                                     │
│  └── Path: New → Approved → Committed → Done                    │
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

---

*State Transition Validator v1.0*
*Part of DevOps Plugin v3.0 Enhancement*
*TaqaTechno - December 2025*
