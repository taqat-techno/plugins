---
title: 'Task Monitor'
read_only: false
type: 'command'
description: 'Periodic work item monitor - alerts on new Azure DevOps assignments. Use with /loop 15m /task-monitor'
---

# /task-monitor - New Assignment Alerts

Monitor for new work item assignments. Designed for use with `/loop 15m /task-monitor`.

Use the devops skill for:
- Baseline snapshot creation (first run)
- Diff detection (new items since last check)
- Assignment change tracking
- Alert formatting and notification
- State change monitoring

Workflow:
1. Load previous snapshot (or create baseline on first run)
2. Query current assignments via MCP or CLI
3. Diff against snapshot
4. Report new/changed items
5. Save updated snapshot
