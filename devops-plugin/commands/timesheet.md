---
title: 'Timesheet'
read_only: false
type: 'command'
description: 'View time tracking status and manage time-off. Flags: --week, --month, --date, --off, --off-list, --off-remove. Local only, no API calls.'
primary_agent: none
---

# /timesheet - Time Tracking Status

Local-only command. Reads/writes to local timesheet files, no API calls.

## Input Format

```
/timesheet [--week|--month|--date YYYY-MM-DD]
/timesheet --off YYYY-MM-DD ["reason"]
/timesheet --off-list
/timesheet --off-remove YYYY-MM-DD
```

| Flag | Action |
|------|--------|
| `--week` | Show current week summary |
| `--month` | Show current month summary |
| `--date YYYY-MM-DD` | Show specific date |
| `--off YYYY-MM-DD [reason]` | Record time off |
| `--off-list` | List recorded time off |
| `--off-remove YYYY-MM-DD` | Remove time off entry |
| *(no flags)* | Show today's status |

## Workflow

1. **Read** local timesheet data (logged via `/log-time`)
2. **Aggregate** hours by day/week/month
3. **Compare** against targets from `data/project_defaults.json` workTracking (6h/day, 5 days/week)
4. **Report** compliance status

## Example

```
User: /timesheet --week

Output:
## Timesheet - Week of 2026-03-24
**Project:** Relief Center

| Day | Logged | Target | Status |
|-----|--------|--------|--------|
| Mon | 6.5h | 6h | ✓ |
| Tue | 7h | 6h | ✓ |
| Wed | 5h | 6h | Behind |
| Thu | -- | 6h | Today |
| Fri | -- | 6h | -- |

**Week Total:** 18.5h / 30h (62%)
```
