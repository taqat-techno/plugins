---
title: 'Error Recovery System'
read_only: false
type: 'helper'
description: 'Transform cryptic API errors into actionable user messages with automatic recovery workflows'
---

# Error Recovery System

Transform cryptic Azure DevOps API errors into **actionable user messages** with guided recovery workflows.

## Core Principle

```
┌─────────────────────────────────────────────────────────────────┐
│           ERROR RECOVERY PHILOSOPHY                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  BEFORE (Frustrating):                                          │
│  "Error: VS403507 - Field cannot be empty"                      │
│                                                                  │
│  AFTER (Actionable):                                            │
│  "To mark Task #1234 as Done, I need:                           │
│   • Original Estimate: ___ hours                                │
│   • Completed Work: ___ hours                                   │
│   Please provide these values."                                 │
│                                                                  │
│  GOAL: Users should NEVER see raw API errors!                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Two-Layer Protection

### Layer 1: Proactive Prevention (PREFERRED)

**Check requirements BEFORE attempting operations** to prevent errors entirely.

```
User: "Mark task #1234 as Done"

STEP 1: Pre-flight check
┌────────────────────────────────────────┐
│ Get current work item state:           │
│ wit_get_work_item({ id: 1234 })        │
│                                        │
│ Check required fields for transition:  │
│ - OriginalEstimate: [empty] ❌         │
│ - CompletedWork: [empty] ❌            │
└────────────────────────────────────────┘

STEP 2: Ask user BEFORE attempting
┌────────────────────────────────────────┐
│ "Task #1234 needs these fields to be   │
│  marked as Done:                       │
│                                        │
│ • Original Estimate (hours): ___       │
│ • Completed Work (hours): ___          │
│                                        │
│ Please provide the values."            │
└────────────────────────────────────────┘

STEP 3: Update with all fields at once
┌────────────────────────────────────────┐
│ wit_update_work_item({                 │
│   id: 1234,                            │
│   updates: [                           │
│     { path: ".../OriginalEstimate",    │
│       value: "8" },                    │
│     { path: ".../CompletedWork",       │
│       value: "6" },                    │
│     { path: ".../State",               │
│       value: "Done" }                  │
│   ]                                    │
│ })                                     │
└────────────────────────────────────────┘

Result: SUCCESS - No error encountered!
```

### Layer 2: Reactive Recovery (FALLBACK)

**When errors occur despite prevention**, transform them into actionable guidance.

```
Error received: "VS403507 - Field 'OriginalEstimate' cannot be empty"

STEP 1: Parse error pattern
┌────────────────────────────────────────┐
│ Pattern: VS403507                      │
│ Category: REQUIRED_FIELD_MISSING       │
│ Field: OriginalEstimate                │
└────────────────────────────────────────┘

STEP 2: Generate friendly message
┌────────────────────────────────────────┐
│ ❌ Cannot mark task as Done            │
│                                        │
│ **Missing Required Field**:            │
│ • Original Estimate (hours)            │
│                                        │
│ **To fix**: Tell me how many hours     │
│ you estimated for this task.           │
└────────────────────────────────────────┘

STEP 3: Collect and retry
┌────────────────────────────────────────┐
│ User: "8 hours"                        │
│ → Retry update with field included     │
│ → SUCCESS                              │
└────────────────────────────────────────┘
```

## Error Pattern Catalog

### Work Item Errors

| Error Code | Pattern | User Message | Recovery Action |
|------------|---------|--------------|-----------------|
| `VS403507` | Field cannot be empty | "Task needs {field} to be marked {state}" | Ask for field value |
| `TF401347` | Invalid state transition | "{Type} must go through {intermediate} before {target}" | Offer two-step transition |
| `TF401019` | Work item does not exist | "Work item #{id} not found. It may have been deleted." | Suggest searching |
| `VS403323` | Update conflict | "Someone else modified this item. Refresh and try again." | Refresh and retry |
| `VS403513` | Invalid field value | "'{value}' is not valid for {field}. Valid options: {options}" | Show valid values |

### Permission Errors

| Error Code | Pattern | User Message | Recovery Action |
|------------|---------|--------------|-----------------|
| `VS403403` | Forbidden | "Permission denied. Your token doesn't have '{scope}' scope." | List required scopes |
| `TF400813` | Resource not available | "Project '{project}' not found or access denied." | List available projects |
| `VS403404` | Not found | "Repository '{repo}' not found in project." | List available repos |

### Repository Errors

| Error Code | Pattern | User Message | Recovery Action |
|------------|---------|--------------|-----------------|
| `TF401398` | Branch not found | "Branch '{branch}' doesn't exist in {repo}." | List available branches |
| `TF401019` | PR not found | "Pull request #{id} not found." | Search for PR |
| `VS403406` | Merge conflict | "PR has merge conflicts. Resolve conflicts first." | Show conflict details |
| `TF401028` | Source/target same | "Source and target branches cannot be the same." | Ask for different branch |

### Pipeline Errors

| Error Code | Pattern | User Message | Recovery Action |
|------------|---------|--------------|-----------------|
| `VS403507` | Pipeline not found | "Pipeline '{name}' not found." | List available pipelines |
| `VS403500` | Build queue failure | "Cannot queue build. Check pipeline configuration." | Show pipeline logs |
| `VS403514` | Invalid parameter | "Template parameter '{param}' is invalid." | Show expected parameters |

## Detailed Recovery Workflows

### Workflow 1: Required Field Missing

```
Error: VS403507 - Microsoft.VSTS.Scheduling.OriginalEstimate cannot be empty

RECOVERY FLOW:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ❌ Cannot mark Task #1234 as Done                             │
│                                                                │
│  **Reason**: Required fields are missing                       │
│                                                                │
│  **Missing Fields**:                                           │
│  • Original Estimate (hours): [not set]                        │
│  • Completed Work (hours): [not set]                           │
│                                                                │
│  **Quick Fix Options**:                                        │
│  1. Tell me the hours: "8 hours estimated, 6 hours actual"     │
│  2. Same hours for both: "8 hours"                             │
│                                                                │
│  I'll update all fields and mark as Done in one step.          │
│                                                                │
└────────────────────────────────────────────────────────────────┘

User: "8 hours estimated, 6 actual"

EXECUTE:
wit_update_work_item({
  id: 1234,
  updates: [
    { path: "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", value: "8" },
    { path: "/fields/Microsoft.VSTS.Scheduling.CompletedWork", value: "6" },
    { path: "/fields/Microsoft.VSTS.Scheduling.RemainingWork", value: "0" },
    { path: "/fields/System.State", value: "Done" }
  ]
})

RESULT:
✅ Task #1234 marked as Done
   • Original Estimate: 8 hours
   • Completed Work: 6 hours
```

### Workflow 2: Invalid State Transition

```
Error: TF401347 - Invalid state transition from 'Active' to 'Done'

RECOVERY FLOW:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ⚠️ Cannot move User Story #1000 directly to Done              │
│                                                                │
│  **Reason**: User Stories must pass through QC                 │
│                                                                │
│  **Required Path**:                                            │
│  Active → Ready for QC → Done                                  │
│         ↑ You are here   ↑ Target                              │
│                                                                │
│  **Options**:                                                  │
│  1. Move to "Ready for QC" first (recommended)                 │
│  2. Move through both states now (requires QC approval)        │
│                                                                │
│  Which would you like to do?                                   │
│                                                                │
└────────────────────────────────────────────────────────────────┘

User: "1" or "Ready for QC"

EXECUTE:
wit_update_work_item({
  id: 1000,
  updates: [
    { path: "/fields/System.State", value: "Ready for QC" }
  ]
})

RESULT:
✅ User Story #1000 moved to "Ready for QC"

Next step: When QC is complete, say "mark #1000 as done" to complete.
```

### Workflow 3: Permission Denied

```
Error: VS403403 - Access denied. User does not have sufficient permissions.

RECOVERY FLOW:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  🔒 Permission Denied                                          │
│                                                                │
│  **Operation**: Update work item #1234                         │
│  **Reason**: Your Personal Access Token (PAT) is missing       │
│              required permissions.                             │
│                                                                │
│  **Required Scopes**:                                          │
│  • vso.work_write (Work Items - Read, write, & manage)         │
│                                                                │
│  **How to Fix**:                                               │
│  1. Go to Azure DevOps → User Settings → Personal Access Tokens│
│  2. Edit your token or create a new one                        │
│  3. Enable "Work Items: Read, write, & manage"                 │
│  4. Save and update your Claude Code settings                  │
│                                                                │
│  Need help? See:                                               │
│  https://docs.microsoft.com/azure/devops/organizations/        │
│  accounts/use-personal-access-tokens-to-authenticate           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Workflow 4: Repository/Branch Not Found

```
Error: TF401398 - The ref 'refs/heads/feature/login' does not exist

RECOVERY FLOW:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ❌ Branch Not Found                                           │
│                                                                │
│  **Looking for**: feature/login                                │
│  **Repository**: relief-center-api                             │
│                                                                │
│  **Similar branches found**:                                   │
│  • feature/login-page                                          │
│  • feature/user-login                                          │
│  • feature/login-api                                           │
│                                                                │
│  **Options**:                                                  │
│  1. Use one of the similar branches above                      │
│  2. Create new branch "feature/login"                          │
│  3. List all branches                                          │
│                                                                │
│  Which would you like?                                         │
│                                                                │
└────────────────────────────────────────────────────────────────┘

User: "1" or "feature/login-page"

→ Retry operation with corrected branch name
```

### Workflow 5: Work Item Not Found

```
Error: TF401019 - Work item 99999 does not exist

RECOVERY FLOW:
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ❌ Work Item Not Found                                        │
│                                                                │
│  **Looking for**: #99999                                       │
│                                                                │
│  **Possible reasons**:                                         │
│  1. Work item was deleted                                      │
│  2. Typo in the work item number                               │
│  3. Work item is in a different project                        │
│                                                                │
│  **Actions**:                                                  │
│  • Search for similar items: "search for [keywords]"           │
│  • Check your recent items: "show my recent activity"          │
│  • Search in all projects: "find #99999 in all projects"       │
│                                                                │
│  What would you like to do?                                    │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Pre-Flight Validation Checklist

Before executing operations, validate to prevent errors:

### State Transitions

```javascript
// Before changing state
async function validateStateTransition(workItemId, targetState) {
  // Step 1: Get current work item
  const item = await wit_get_work_item({ id: workItemId });

  // Step 2: Check transition validity
  const currentState = item.fields["System.State"];
  const type = item.fields["System.WorkItemType"];

  // Step 3: Load transition rules
  const rules = getTransitionRules(type, currentState, targetState);

  // Step 4: Check required fields
  const missingFields = [];
  for (const field of rules.requiredFields) {
    if (!item.fields[field]) {
      missingFields.push(field);
    }
  }

  // Step 5: Check intermediate states
  if (rules.requiresIntermediate) {
    return {
      valid: false,
      reason: "intermediate_required",
      intermediate: rules.intermediateState,
      message: `${type} must go through "${rules.intermediateState}" before "${targetState}"`
    };
  }

  // Step 6: Return validation result
  if (missingFields.length > 0) {
    return {
      valid: false,
      reason: "missing_fields",
      fields: missingFields,
      message: `Missing required fields: ${missingFields.join(", ")}`
    };
  }

  return { valid: true };
}
```

### PR Operations

```javascript
// Before creating PR
async function validatePRCreation(repoId, source, target) {
  // Check source branch exists
  const sourceBranch = await repo_get_branch_by_name({
    repositoryId: repoId,
    branchName: source
  });

  if (!sourceBranch) {
    return {
      valid: false,
      reason: "source_not_found",
      message: `Source branch "${source}" not found`
    };
  }

  // Check target branch exists
  const targetBranch = await repo_get_branch_by_name({
    repositoryId: repoId,
    branchName: target
  });

  if (!targetBranch) {
    return {
      valid: false,
      reason: "target_not_found",
      message: `Target branch "${target}" not found`
    };
  }

  // Check not same branch
  if (source === target) {
    return {
      valid: false,
      reason: "same_branch",
      message: "Source and target branches must be different"
    };
  }

  return { valid: true };
}
```

## Error Message Templates

### Standard Error Format

```
{emoji} {Short Summary}

**Reason**: {Why the error occurred}

**Details**:
{Specific information about the error}

**To fix**:
{Numbered steps or options to resolve}

**Need help?** {Optional resource link}
```

### Emoji Guide

| Emoji | Meaning | Use Case |
|-------|---------|----------|
| ❌ | Error/Blocked | Operation failed |
| ⚠️ | Warning | Partial success or caution needed |
| 🔒 | Permission | Access denied |
| 🔍 | Not Found | Resource missing |
| ⏳ | Timeout | Operation took too long |
| 🔄 | Conflict | Update conflict |
| ✅ | Success | Recovery successful |

## Integration with Other Helpers

### With State Transition Validator

```
Reference: validators/state_transition_validator.md

When error occurs during state change:
1. Parse error for transition details
2. Lookup valid transitions
3. Suggest correct path
4. Offer to execute correct transition
```

### With Pre-Flight Validator

```
Reference: validators/pre_flight_validator.md

Error prevention priority:
1. Pre-flight catches 90% of errors
2. Error recovery handles remaining 10%
3. Always prefer prevention over recovery
```

### With Hierarchy Helper

```
Reference: helpers/hierarchy_helper.md

When error indicates parent issue:
1. Parse error for work item type
2. Look up valid parent types
3. Search for candidate parents
4. Offer to link to parent
```

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│              ERROR RECOVERY QUICK REFERENCE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  COMMON ERRORS & QUICK FIXES:                                   │
│                                                                  │
│  "Field cannot be empty" (VS403507)                             │
│  → Ask user for the required field value                        │
│  → Update all fields in single call                             │
│                                                                  │
│  "Invalid state transition" (TF401347)                          │
│  → Show required intermediate states                            │
│  → Offer to do multi-step transition                            │
│                                                                  │
│  "Not found" (TF401019)                                         │
│  → Check for typos                                              │
│  → Search for similar items                                     │
│  → Check project scope                                          │
│                                                                  │
│  "Permission denied" (VS403403)                                 │
│  → List required PAT scopes                                     │
│  → Provide setup instructions                                   │
│                                                                  │
│  PREVENTION IS BETTER THAN RECOVERY:                            │
│  • Always pre-fetch work item before updating                   │
│  • Check required fields before state change                    │
│  • Validate branches before PR creation                         │
│  • Resolve repository names before API calls                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Related Files

| File | Purpose |
|------|---------|
| `data/error_patterns.json` | Error code to message mappings |
| `data/required_fields.json` | Field requirements by transition |
| `validators/state_transition_validator.md` | State machine rules |
| `validators/pre_flight_validator.md` | Pre-execution validation |

---

*Part of DevOps Plugin v3.0*
*Error Recovery System: Enabled*
*Never show raw API errors to users!*
