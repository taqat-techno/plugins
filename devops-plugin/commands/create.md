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
- "fix", "bug", "broken", "error" -> Bug (but check role — developers create `[Dev-Internal-fix]` Tasks instead)
- "test", "qa", "verify" -> Task with `[QC Test Execution]` prefix
- "implement", "add", "create", "build" -> Task with role-based prefix
- "improve", "enhance", "refactor" -> Enhancement

## Workflow

1. **Parse** arguments for type, title, parent reference
2. **Load profile** per `rules/profile-loader.md` (get role, project, task prefix)
3. **Apply naming** — prepend task prefix from profile (e.g., `[Dev] Fix login API`)
4. **Check hierarchy** per `data/hierarchy_rules.json`:
   - Tasks/Bugs/Enhancements MUST have a parent User Story or PBI
   - If no `under #ID`, search for matching parent and ask user to select
5. **Detect sprint** — auto-assign to current iteration
6. **Present confirmation** per `rules/write-gate.md`:
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