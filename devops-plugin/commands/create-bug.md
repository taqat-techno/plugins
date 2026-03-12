---
title: 'Create Bug'
read_only: false
type: 'command'
description: 'Create a new bug work item in Azure DevOps'
---

# Create Bug

Create a new bug work item with proper fields.

## WRITE OPERATION GATE

**Reference**: `guards/write_operation_guard.md`

**Before creating the bug**, you MUST present a confirmation summary and wait for explicit user approval. NEVER call `wit_create_work_item` without the user saying "yes".

## Instructions

1. Gather bug information from user:
   - Title (required)
   - Description
   - Repro Steps
   - Expected vs Actual behavior
   - Severity (1-4)
   - Priority (1-4)
2. Ask for project if not specified
3. **MANDATORY: Present confirmation summary and wait for approval**:
   ```
   READY TO CREATE: Bug
   ─────────────────────
   Title:     {title}
   Project:   {project}
   Severity:  {severity}
   Priority:  {priority}
   Parent:    #{parentId} (if specified)

   Proceed? (yes/no)
   ```
   **Only proceed after explicit "yes" from user.**
4. Create the bug work item
5. Optionally link to related items
6. Return bug ID and URL

## Required Fields

| Field | Description | Values |
|-------|-------------|--------|
| Title | Clear bug description | Text |
| Description | Detailed explanation | HTML/Text |
| Repro Steps | How to reproduce | Numbered list |
| Severity | Impact level | 1-Critical, 2-High, 3-Medium, 4-Low |
| Priority | Fix urgency | 1-Must fix, 2-Should fix, 3-Could fix, 4-Won't fix |

## Bug Template

```
Title: [Component] - Brief issue description

Description:
[Detailed explanation of the bug]

Repro Steps:
1. Go to [location]
2. Click on [element]
3. Observe [behavior]

Expected Behavior:
[What should happen]

Actual Behavior:
[What actually happens]

Environment:
- Browser: [Chrome/Firefox/etc]
- OS: [Windows/Mac/etc]
- Version: [App version]

Screenshots/Logs:
[Attach if available]
```

## Example

```
User: Create bug: Login button not working on mobile

Response: Creating bug in [Project]...

Created Bug #1234: [Login] - Login button not working on mobile
- Severity: 2 - High
- Priority: 2 - Should fix
- State: New
- URL: https://dev.azure.com/YOUR-ORG/Project/_workitems/edit/1234

Would you like to:
1. Add more details
2. Link to a user story
3. Assign to someone
```
