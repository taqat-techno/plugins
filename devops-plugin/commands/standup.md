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
| `--copy` | Copy output to the clipboard: `clip` on Windows, `pbcopy` on macOS, `wl-copy` or `xclip -selection clipboard` on Linux; skip with a note if none exists |
| *(no flags)* | Generate markdown standup for current project |

## Workflow

1. **Load profile** per `${CLAUDE_PLUGIN_ROOT}/rules/profile-loader.md`
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
- [#1401] Fix login timeout (done)
- [#1399] Add error handling to the export API (done)

### Today
- [#1398] Report export drops last row (in progress)
- [#1395] Add status filter to search (to do)

### Blockers
- None

---
*Generated: 09:15*
```
