---
title: 'Create'
read_only: false
type: 'command'
description: 'Create a work item (task, bug, enhancement, or user story). Auto-detects type from context. Enforces hierarchy, naming conventions, and sprint assignment.'
argument-hint: '[--task|--bug|--enhancement|--story] "Title" [under #ID]'
primary_agent: work-item-ops
---

# /create - Create Work Item

Parse `$ARGUMENTS` for type flag, title, and optional parent (`under #ID`).

With no arguments, ask for the title (and parent, if the type needs one) before doing
anything else; never create an item with a placeholder title.

## Input Format

```
/create [--task|--bug|--enhancement|--story] "Title text" [under #PARENT_ID]
```

| Argument | Required | Description |
|----------|----------|-------------|
| Type flag | Optional | `--task`, `--bug`, `--enhancement`, `--story`. If omitted, auto-detect from keywords. |
| Title | Required | Work item title in quotes or as remaining text |
| `under #ID` | Optional | Parent work item ID for hierarchy linking |

## Auto-Detection Rules

If no type flag is given, detect from title keywords:
- "fix", "bug", "broken", "error" -> Bug (if the active preset's `roleRules.createRestrictions.Bug` denies the user's role, offer its `redirect` instead, e.g. a `[Dev-Internal-fix]` Task under `custom-scrum-qc`)
- "test", "qa", "verify" -> Task (with the matching `taskNaming` prefix when the preset defines one)
- "implement", "add", "create", "build" -> Task (role-based prefix when the preset defines `taskNaming`)
- "improve", "enhance", "refactor" -> Enhancement if the preset has that type, else the preset's `requirementType` or a Task
- Use only work item types that exist in the active preset (`processPresets[process].workItemTypes`)

## Workflow

1. **Parse** arguments for type, title, parent reference
2. **Load profile** per `${CLAUDE_PLUGIN_ROOT}/rules/profile-loader.md` (get role, project, process preset, task prefix)
3. **Apply naming** — prepend `preferences.taskPrefix` if set; a prefix is **required** only when the preset/profile defines `taskNaming` (e.g., `[Dev] Fix login API` under `custom-scrum-qc`)
4. **Check hierarchy** per `${CLAUDE_PLUGIN_ROOT}/data/hierarchy_rules.json`:
   - Tasks/Bugs/Enhancements MUST have a parent at the preset's requirement level (User Story, PBI, Requirement or Issue)
   - If no `under #ID`, search for matching parent and ask user to select
5. **Detect sprint** — auto-assign to current iteration
6. **Present confirmation** per `${CLAUDE_PLUGIN_ROOT}/rules/write-gate.md`:
   ```
   READY TO CREATE: Task
   ----------------------------------
   Title:     [Dev] Fix login API timeout
   Project:   My Project
   Parent:    #1234 - User Authentication Story
   Sprint:    Sprint 15
   Assigned:  the current user
   Priority:  2

   Proceed? (yes/no)
   ```
7. **Execute** via `wit_create_work_item` + `wit_work_items_link` for parent
8. **Report** created item with ID and hierarchy tree

## Example

```
User: /create --task "Fix login API timeout" under #1234