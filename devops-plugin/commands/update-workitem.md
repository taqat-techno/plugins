---
title: 'Update Work Item'
read_only: false
type: 'command'
description: 'Update work item state with pre-flight validation and error recovery'
---

# Update Work Item

Update work item fields and state transitions with **mandatory pre-flight validation** and **automatic error recovery**.

## 🛡️ Error Recovery Integration

**References**:
- `validators/state_transition_validator.md`
- `errors/error_recovery.md`
- `data/error_patterns.json`
- `data/required_fields.json`

This command implements a **two-layer protection system**:

1. **Layer 1 - Proactive Prevention**: Check requirements BEFORE attempting updates
2. **Layer 2 - Reactive Recovery**: Transform any errors into actionable guidance

## 🔒 PRE-FLIGHT VALIDATION (MANDATORY)

**Reference**: `validators/state_transition_validator.md`

```
┌─────────────────────────────────────────────────────────────────┐
│              ⚠️ NEVER UPDATE STATE WITHOUT VALIDATION            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE changing state:                                         │
│  1. FETCH work item to check current state and fields           │
│  2. LOOKUP required fields for the transition                   │
│  3. CHECK if required fields are populated                      │
│  4. ASK user for missing values (if any)                        │
│  5. ONLY THEN execute the update                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

```
/update-workitem #1234 state=Done
/update-workitem #1234 state=Active
/update-workitem #1234 title="New Title"
/update-workitem #1234 state=Resolved reason="Fixed"
```

## Pre-Flight Validation Workflow

### Step 1: Fetch Current Work Item

```javascript
mcp__azure-devops__wit_get_work_item({
  "id": 1234,
  "project": "Project Alpha",
  "fields": [
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
    "System.TeamProject",
    "Microsoft.VSTS.Scheduling.OriginalEstimate",
    "Microsoft.VSTS.Scheduling.CompletedWork",
    "Microsoft.VSTS.Scheduling.RemainingWork",
    "Microsoft.VSTS.Common.ResolvedReason"
  ]
})
```

### Step 2: Check Required Fields

Use the lookup table from `data/required_fields.json`:

**Task → Done**:
- Required: `OriginalEstimate`, `CompletedWork`
- Auto-set: `RemainingWork = 0`

**Bug → Resolved**:
- Required: `ResolvedReason`
- Default: "Fixed"

**User Story → Done**:
- **BLOCKED** if current state is "Active"
- Must go through "Ready for QC" first

### Step 3: Handle Missing Fields

#### If Task → Done and Missing Hours

```
⚠️ Cannot mark task #1234 as Done yet.

**Missing Required Fields**:
• Original Estimate (hours): Not set
• Completed Work (hours): Not set

Please provide:
1. How many hours did you estimate for this task?
2. How many hours did you actually spend?

I'll automatically set Remaining Work to 0.
```

#### If User Story → Done from Active

```
⚠️ Cannot mark User Story #1000 as Done directly.

**Reason**: User Stories must pass through "Ready for QC" before Done.

**Current State**: Active
**Required Path**: Active → Ready for QC → Done

Would you like me to:
1. Move to "Ready for QC" now
2. Move through both states (Ready for QC → Done)
```

#### If Bug → Resolved without Reason

```
Resolving Bug #500...

**Resolved Reason**: Fixed (default)

Would you like to use a different reason?
• As Designed
• Cannot Reproduce
• Deferred
• Duplicate
• Not a Bug
• Obsolete
```

### Step 3.5: MANDATORY Confirmation (WRITE OPERATION GATE)

**Reference**: `guards/write_operation_guard.md`

After collecting all required field values (Step 3) and before executing the update, present a confirmation summary and **wait for explicit user approval**. NEVER skip this step.

```
READY TO UPDATE: #{id} {title}
─────────────────────────────────
State:     {currentState} → {newState}
Fields:    {list of fields being set with values}
Hours:     Est: {orig}h / Done: {comp}h (if applicable)

Proceed? (yes/no)
```

**Only proceed to Step 4 after the user explicitly says "yes".**

If in Plan Mode: STOP HERE. Only describe what would be updated. Do not call any write tools.

### Step 4: Execute Update with All Fields

After user provides missing values AND explicitly approves:

```javascript
mcp__azure-devops__wit_update_work_item({
  "id": 1234,
  "updates": [
    // Required fields from user
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    // Auto-set fields
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },
    // State change (LAST)
    { "path": "/fields/System.State", "value": "Done" }
  ]
})
```

## Required Fields Reference

### Task → Done

| Field | Path | Required | Notes |
|-------|------|----------|-------|
| Original Estimate | `Microsoft.VSTS.Scheduling.OriginalEstimate` | **YES** | Hours planned |
| Completed Work | `Microsoft.VSTS.Scheduling.CompletedWork` | **YES** | Hours spent |
| Remaining Work | `Microsoft.VSTS.Scheduling.RemainingWork` | Auto-set | Set to 0 |

### Bug → Resolved

| Field | Path | Required | Notes |
|-------|------|----------|-------|
| Resolved Reason | `Microsoft.VSTS.Common.ResolvedReason` | **YES** | Default: "Fixed" |

**Valid Resolved Reasons**:
- Fixed
- As Designed
- Cannot Reproduce
- Deferred
- Duplicate
- Not a Bug
- Obsolete

### User Story → Done

| Transition | Allowed | Notes |
|------------|---------|-------|
| Active → Done | **NO** | Must go through Ready for QC |
| Ready for QC → Done | **YES** | Direct transition allowed |

## State Machine Diagrams

### Task States

```
New ──────► Active ──────► Done
  │                         ▲
  │                         │
  └─────────────────────────┘
            (all fields required)
```

### Bug States

```
New ──► Active ──► Resolved ──► Closed
                      │
                      │ (requires ResolvedReason)
```

### User Story States

```
New ──► Active ──► Ready for QC ──► Done ──► Closed
                        ▲
                        │
                   MANDATORY
                   CHECKPOINT
                        │
              (Cannot skip to Done!)
```

## Examples

### Example 1: Mark Task as Done

**User**: "Mark task #1234 as done, I spent 6 hours on it, estimate was 8"

**Claude**:
```javascript
// Step 1: Verify task exists and get current state
mcp__azure-devops__wit_get_work_item({
  "id": 1234,
  "project": "Project Alpha",
  "fields": ["System.State", "System.WorkItemType", "System.Title"]
})

// Step 2: All info provided, execute update
mcp__azure-devops__wit_update_work_item({
  "id": 1234,
  "updates": [
    { "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": "8" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": "6" },
    { "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": "0" },
    { "path": "/fields/System.State", "value": "Done" }
  ]
})
```

**Result**:
```
✓ Task #1234 "Fix login bug" marked as Done

• Original Estimate: 8 hours
• Completed Work: 6 hours
• Remaining Work: 0 hours
• State: Done
```

### Example 2: Resolve Bug

**User**: "Resolve bug #500"

**Claude**:
```
Resolving Bug #500 "UI alignment issue"...

Using default Resolved Reason: "Fixed"

✓ Bug #500 resolved!
```

### Example 3: User Story Blocked

**User**: "Mark story #1000 as done"

**Claude**:
```
⚠️ Cannot mark User Story #1000 as Done directly.

**Current State**: Active
**Required Path**: Active → Ready for QC → Done

Would you like me to move it to "Ready for QC" first?
```

## Error Recovery (Layer 2 - Fallback)

**Reference**: `errors/error_recovery.md`

When errors occur despite pre-flight validation, transform them into actionable guidance:

### Error Pattern Matching

| Error Code | User Message | Recovery Action |
|------------|--------------|-----------------|
| `VS403507` | "Task needs {field} to be marked {state}" | Ask for field value, retry |
| `TF401347` | "{Type} must go through {intermediate}" | Offer two-step transition |
| `TF401019` | "Work item #{id} not found" | Suggest searching |
| `VS403403` | "Permission denied" | Show required PAT scopes |
| `VS403323` | "Update conflict" | Refresh and retry |

### If Update Fails Despite Pre-Flight

If `wit_update_work_item` returns an error after pre-flight validation:

1. Parse error code and message
2. Match to error pattern catalog
3. Generate user-friendly message
4. Provide recovery action
5. Retry with corrected data

**Example - Missing Field:**
```
Error: VS403507 - Field 'Custom.ReviewedBy' cannot be empty

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ ❌ Cannot mark Task #1234 as Done                               │
│                                                                │
│ **Reason**: Project requires additional field                  │
│                                                                │
│ **Missing Field**:                                             │
│ • Reviewed By: [not set]                                       │
│                                                                │
│ **To fix**: Who reviewed this task?                            │
│                                                                │
│ I'll retry the update after you provide this value.            │
└────────────────────────────────────────────────────────────────┘
```

**Example - Permission Denied:**
```
Error: VS403403 - Access denied

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ 🔒 Permission Denied                                            │
│                                                                │
│ **Operation**: Update work item #1234                          │
│ **Reason**: PAT missing required permissions                   │
│                                                                │
│ **Required Scopes**:                                           │
│ • vso.work_write (Work Items - Read, write, & manage)          │
│                                                                │
│ **How to Fix**:                                                │
│ 1. Go to Azure DevOps → User Settings → Personal Access Tokens │
│ 2. Edit your token and enable required scope                   │
│ 3. Update your Claude Code settings                            │
└────────────────────────────────────────────────────────────────┘
```

**Example - Update Conflict:**
```
Error: VS403323 - Optimistic concurrency conflict

Claude Response:
┌────────────────────────────────────────────────────────────────┐
│ 🔄 Update Conflict                                              │
│                                                                │
│ **Reason**: Someone else modified this work item               │
│                                                                │
│ **Options**:                                                   │
│ 1. Refresh and retry (recommended)                             │
│ 2. Force update (override their changes)                       │
│ 3. Cancel operation                                            │
│                                                                │
│ Which would you like?                                          │
└────────────────────────────────────────────────────────────────┘
```

## Pre-Flight Checklist

Before any state change, verify:

- [ ] Work item fetched with current state and fields
- [ ] Work item type identified (Task, Bug, User Story, etc.)
- [ ] Target state validated against state machine
- [ ] Required fields checked against lookup table
- [ ] Missing fields prompted to user
- [ ] All required values collected
- [ ] Single update executed with all fields + state

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              UPDATE WORK ITEM QUICK REFERENCE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TWO-LAYER PROTECTION:                                          │
│  Layer 1: Pre-flight validation (PREVENT errors)                │
│  Layer 2: Error recovery (TRANSFORM errors if they occur)       │
│                                                                  │
│  PRE-FLIGHT STEPS:                                              │
│  1. Fetch current work item                                     │
│  2. Check required fields for transition                        │
│  3. Ask user for missing values                                 │
│  4. Execute single update with all fields                       │
│                                                                  │
│  COMMON TRANSITIONS:                                            │
│  • Task → Done: Need OriginalEstimate + CompletedWork           │
│  • Bug → Resolved: Need ResolvedReason (default: Fixed)         │
│  • User Story → Done: Must go through Ready for QC first        │
│                                                                  │
│  NEVER show raw API errors to users!                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Step 5: Auto-Prompt Time Logging (Work Tracker Integration)

When a work item state changes to **Done**, **Closed**, or **Resolved**, automatically offer to log the hours in the persistent work tracker:

```
1. Check if state was changed to Done/Closed/Resolved
2. If YES:
   a. Note the CompletedWork hours from the update (already collected in Step 3)
   b. Ask the user:
      "Would you like me to log {CompletedWork}h for #{id} in your work tracker?"
   c. If user agrees (or doesn't object):
      - Read ~/.claude/work-tracker-data.json
      - Add entry to timeLog[today]:
        {
          "hours": <CompletedWork>,
          "type": "task",
          "workItemId": <id>,
          "description": "Completed: <title>"
        }
      - Recalculate today's total
      - Write updated work-tracker-data.json
      - Regenerate work-tracker.md day section
      - Run compliance check:
        If total < minHoursPerDay:
          "Today: {total}h / {min}h logged. {remaining}h remaining."
        Else:
          "Today: {total}h / {min}h logged. Target met!"
      - Report: "Logged {hours}h in work tracker for #{id}"
3. If state NOT changed to completion state: skip this step
4. If work-tracker-data.json doesn't exist: skip (user hasn't set up work tracking)
```

**Example output after marking task Done**:
```
Task #1234 "Fix login bug" marked as Done

- Original Estimate: 8 hours
- Completed Work: 6 hours
- Remaining Work: 0 hours

Logged 6.0h in work tracker for #1234
Today: 7.5h / 6.0h logged. Target met!
```

## Related Commands

| Command | Description |
|---------|-------------|
| `/create-task` | Create task with hierarchy |
| `/create-bug` | Create bug with parent task |
| `/my-tasks` | List assigned work items (cache-first) |
| `/workday` | Daily dashboard with time tracking |
| `/log-time` | Manually log hours |
| `/timesheet` | View time tracking status |

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
*Pre-Flight Validation: Enabled*
*Error Recovery System: Enabled*
*Auto Time Logging: Enabled*
