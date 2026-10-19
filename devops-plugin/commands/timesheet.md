---
title: 'Timesheet'
read_only: false
type: 'command'
description: 'View logged time and manage time-off from the local timesheet. Flags: --week, --month, --date, --off, --off-list, --off-remove. Local only, no API calls.'
argument-hint: '[--week|--month|--date YYYY-MM-DD|--off YYYY-MM-DD "reason"|--off-list|--off-remove YYYY-MM-DD]'
primary_agent: none
---

# /timesheet - Time Tracking Status

Local-only command: it makes no Azure DevOps calls. It reads and writes
`${CLAUDE_PLUGIN_DATA}/timesheet.json`, whose schema, write rules and retention are owned by
`${CLAUDE_PLUGIN_ROOT}/rules/timesheet-store.md`. Follow that rule; do not use any other file.

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
| `--off YYYY-MM-DD [reason]` | Add a `timeOff` entry (replaces one for the same date) |
| `--off-list` | List `timeOff` entries |
| `--off-remove YYYY-MM-DD` | Remove that date's `timeOff` entry |
| *(no flags)* | Show today's entries and total |

## Workflow

1. **Read** the timesheet file. Missing file = no entries yet; say so and suggest `/log-time`.
2. **Aggregate** `entries[].hours` by day/week/month.
3. **Compare** against the daily target of ${user_config.daily_hours_target} hours on the
   working days from `${CLAUDE_PLUGIN_ROOT}/data/project_defaults.json` `workTracking.settings.workingDays`;
   a `timeOff` date has a target of 0.
4. **Report** per-day logged vs target and the period total.
5. For `--off` / `--off-remove`: change only the `timeOff` list, show the change, and write
   the file back per the rule.

## Example

```
User: /timesheet --week

Output:
## Timesheet - Week of 2026-03-23
Source: local timesheet (6h/day target)

| Day | Logged | Target | Status |
|-----|--------|--------|--------|
| Mon | 6.5h | 6h | OK |
| Tue | 7h | 6h | OK |
| Wed | 5h | 6h | Behind |
| Thu | -- | 6h | Today |
| Fri | -- | 0h | Time off (Public holiday) |

**Week Total:** 18.5h / 24h (77%)
```
