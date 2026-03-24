---
title: 'Timesheet'
read_only: false
type: 'command'
description: 'View time tracking status and manage time-off. Flags: --week, --month, --date, --off, --off-list, --off-remove. Local only, no API calls.'
---

# /timesheet - Time Tracking Status

Parse `$ARGUMENTS` for flags:

| Flag | Action |
|------|--------|
| `--week` | Show current week summary |
| `--month` | Show current month summary |
| `--date YYYY-MM-DD` | Show specific date |
| `--off YYYY-MM-DD [reason]` | Record time off |
| `--off-list` | List recorded time off |
| `--off-remove YYYY-MM-DD` | Remove time off entry |
| *(no flags)* | Show today's status |

Use the devops skill for:
- Time tracking data format and storage
- Weekly/monthly aggregation logic
- Time-off management patterns
- Compliance tracking (hours per day/week)
- Report formatting

Local only - reads/writes to local timesheet files, no API calls.
