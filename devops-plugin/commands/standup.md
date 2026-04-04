---
title: 'Daily Standup'
read_only: true
type: 'command'
description: 'Generate daily standup notes from Azure DevOps work items'
primary_agent: sprint-planner
---

# /standup - Daily Standup Notes

Generate standup notes from Azure DevOps work items in Yesterday/Today/Blockers format.

## Input Format

```
/standup [--format markdown|text] [--copy]
```

| Flag | Action |
|------|--------|
| `--format` | Output format: `markdown` (default) or `text` |
| `--copy` | Copy output to clipboard (Windows) |
| *(no flags)* | Generate markdown standup for current project |

## Workflow

1. **Load profile** per `rules/profile-loader.md`
2. **Query yesterday's completed items** — items that moved to Done/Closed since yesterday
3. **Query today's active items** — items currently In Progress or Active
4. **Detect blockers** — items tagged "Blocked" or in stalled states
5. **Format** as Yesterday/Today/Blockers

## Example

```
User: /standup

Output:
## Daily Standup - 2026-03-26
**Project:** My Project

### Yesterday
- [#1401] [Dev] Fix geocoding timeout ✅
- [#1399] [Dev] Add error handling to map API ✅

### Today
- [#1398] Map marker offset on zoom 🔄
- [#1395] [Dev] Add disaster category filter 📋

### Blockers
- None

---
*Generated: 09:15*
```
