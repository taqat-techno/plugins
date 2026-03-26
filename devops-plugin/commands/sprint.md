---
title: 'Sprint Summary'
read_only: true
type: 'command'
description: 'Generate sprint progress summary. Use --full for comprehensive hybrid report with builds, tests, PRs, security.'
primary_agent: sprint-planner
---

# /sprint - Sprint Progress Summary

Parse `$ARGUMENTS` for flags.

## Input Format

```
/sprint [--full] [--sprint "Sprint Name"]
```

| Flag | Action |
|------|--------|
| `--full` | Comprehensive report: adds builds, test results, PRs, security alerts |
| `--sprint "Name"` | Specific sprint (default: current iteration) |
| *(no flags)* | Standard report: work items by state, velocity, blockers |

## Workflow

1. **Load profile** per `rules/profile-loader.md`
2. **Get iteration** via `work_get_team_iterations` (current or named)
3. **Fetch work items** via `wit_get_work_items_for_iteration`
4. **Aggregate** by state, type, assignee
5. **Calculate** velocity, completion percentage, at-risk items
6. If `--full`: also query builds, test results, open PRs, security alerts

## Example (Standard)

```
User: /sprint

Output:
## Sprint Report - Sprint 15
**Period**: 2026-03-18 to 2026-03-29 | **Project**: Relief Center

### Progress Overview
| Metric | Value |
|--------|-------|
| Total Items | 18 |
| Completed | 11 (61%) |
| In Progress | 4 |
| Not Started | 3 |
| Story Points (Done) | 21/34 (62%) |

### At Risk Items
| ID | Type | Title | Priority |
|----|------|-------|----------|
| #1395 | Task | Add disaster category filter | P2 |
```

## Example (Full)

```
User: /sprint --full

Output:
[Standard report above, plus:]

### Build Status
- CI-Main: 12 succeeded, 1 failed (last failure: 2026-03-25)

### Open PRs
- PR #67: Fix map rendering (2 approvals, ready to merge)

### Test Results
- Last run: 142 passed, 0 failed, 3 skipped
```
