---
title: 'Create'
read_only: false
type: 'command'
description: 'Create a work item (task, bug, enhancement, or user story). Auto-detects type from context. Enforces hierarchy, naming conventions, and sprint assignment.'
argument-hint: '[--task|--bug|--enhancement|--story] "Title" [under #ID]'
---

# /create - Create Work Item

Parse `$ARGUMENTS` for type flag, title, and optional parent (`under #ID`).

Use the devops skill for:
- Work item type auto-detection from context
- Hierarchy rules (Epic > Feature > Story > Task/Bug)
- Naming conventions and title formatting
- Sprint assignment (current iteration)
- Required fields per type
- State transition validation
- Write operation gate (present -> confirm -> execute)

Execute via MCP `create_work_item` or CLI `az boards work-item create`.
