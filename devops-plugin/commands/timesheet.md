---
title: 'Timesheet'
read_only: true
type: 'command'
description: 'View time tracking status - daily, weekly, or monthly (local only, no API calls)'
---

# Timesheet

View your time tracking status with compliance checks. This command reads only from the local `~/.claude/work-tracker-data.json` file -- **zero API calls**.

## Usage

```
/timesheet                      # Today's status + compliance check
/timesheet --week               # Current week summary with per-day breakdown
/timesheet --month              # Monthly rollup with weekly totals
/timesheet --date 2026-03-02    # Specific day's details
```

## Workflow

### Step 1: Read Local Data

```
1. Read ~/.claude/work-tracker-data.json
2. If NOT found: "No work tracker data found. Run /workday or /work-sync first."
3. Parse JSON and extract: settings, timeLog, timeOff
```

### Step 2: Determine View Mode

| Flag | View | Data Range |
|------|------|------------|
| (none) | Today | Current date |
| `--week` | Weekly | Mon-Fri of current week |
| `--month` | Monthly | All weeks in current month |
| `--date YYYY-MM-DD` | Specific day | That date |

### Step 3: Generate Report

#### Default View (Today)

```markdown
## Timesheet - [DayName], [Month] [Day], [Year]

### Time Log
| # | Hours | Type | Work Item | Description |
|---|-------|------|-----------|-------------|
| 1 | 3.0 | task | #1828 | Map duration investigation |
| 2 | 1.0 | meeting | - | Sprint planning |
| 3 | 1.5 | task | #1636 | Checksum debugging |
| | **5.5** | **TOTAL** | | |

### Compliance
| Metric | Value |
|--------|-------|
| Logged | 5.5h |
| Required | 6.0h |
| Remaining | 0.5h |
| Status | !! UNDER by 0.5h |

### Hours by Type
| Type | Hours | % |
|------|-------|---|
| task | 4.5h | 82% |
| meeting | 1.0h | 18% |

[If under minimum]: "!! Log 0.5h more to meet today's target. Use /log-time"
[If met]: "Target met for today!"
[If time-off]: "Today is marked as time-off ({reason})"
[If weekend]: "Today is not a working day"
```

#### Weekly View (--week)

```markdown
## Timesheet - Week [N], [Month] [Year]
[Mon, Date] to [Fri, Date]

### Daily Breakdown
| Day | Date | Status | Hours | Required | Delta |
|-----|------|--------|-------|----------|-------|
| Mon | Mar 2 | OK | 6.5h | 6.0h | +0.5h |
| Tue | Mar 3 | OK | 6.0h | 6.0h | 0.0h |
| Wed | Mar 4 | TIME-OFF | - | - | Personal day |
| Thu | Mar 5 | OK | 6.0h | 6.0h | 0.0h |
| Fri | Mar 6 | UNDER | 4.0h | 6.0h | -2.0h |

### Weekly Summary
| Metric | Value |
|--------|-------|
| Working Days | 4 (1 time-off) |
| Total Hours | 22.5h |
| Required Hours | 24.0h (4 x 6.0h) |
| Average per Day | 5.6h |
| Status | !! UNDER by 1.5h |

### Hours by Type (Week)
| Type | Hours | % |
|------|-------|---|
| task | 17.0h | 76% |
| meeting | 3.0h | 13% |
| research | 1.5h | 7% |
| learning | 1.0h | 4% |

### Alerts
- **Fri, Mar 6**: 4.0h logged, 2.0h remaining

[If all days met]: "All working days meet the minimum. Great week!"
```

#### Monthly View (--month)

```markdown
## Timesheet - [Month] [Year]

### Weekly Rollup
| Week | Dates | Working Days | Hours | Required | Avg/Day | Status |
|------|-------|-------------|-------|----------|---------|--------|
| W9 | Feb 24 - Feb 28 | 5/5 | 32.0h | 30.0h | 6.4h | OK |
| W10 | Mar 3 - Mar 7 | 4/5 | 22.5h | 24.0h | 5.6h | UNDER |
| W11 | Mar 10 - Mar 14 | 5/5 | 31.0h | 30.0h | 6.2h | OK |
| W12 | Mar 17 - Mar 21 | 3/5 | 18.0h | 18.0h | 6.0h | OK |

### Monthly Summary
| Metric | Value |
|--------|-------|
| Total Working Days | 17 (3 time-off, 1 holiday) |
| Total Hours | 103.5h |
| Required Hours | 102.0h (17 x 6.0h) |
| Average per Day | 6.1h |
| Status | OK |

### Hours by Type (Month)
| Type | Hours | % |
|------|-------|---|
| task | 78.0h | 75% |
| meeting | 12.0h | 12% |
| research | 6.5h | 6% |
| learning | 4.0h | 4% |
| review | 2.0h | 2% |
| admin | 1.0h | 1% |

### Under-Logged Days
| Date | Day | Hours | Shortfall |
|------|-----|-------|-----------|
| Mar 6 | Fri | 4.0h | -2.0h |
| Mar 18 | Tue | 5.0h | -1.0h |

[If none]: "No under-logged days this month!"
```

#### Specific Day View (--date)

Same as default view but for the specified date. If no entries exist for that date:

```markdown
## Timesheet - [DayName], [Month] [Day], [Year]

No time entries for this date.

[If working day]: "This day has 0h logged against a 6.0h target. Use /log-time --date YYYY-MM-DD to add entries."
[If time-off]: "This day is marked as time-off ({reason})"
[If weekend]: "This is not a working day"
```

## Compliance Calculation Rules

```
For each day in the period:
1. Skip if NOT in settings.workingDays (weekend)
2. Skip if date is in timeOff array (time-off)
3. Get timeLog[date].total (default 0)
4. Compare with settings.minHoursPerDay
5. Status:
   - total >= min: "OK"
   - total > 0 but < min: "UNDER"
   - total == 0 and date is today: "PENDING"
   - total == 0 and date is past: "MISSING"
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Tracker file not found | "No tracker data found. Run /workday first." |
| No entries for period | Show empty report with guidance |
| Invalid date format | "Invalid date. Use format: YYYY-MM-DD" |

## Related Commands

- `/workday` - Full daily dashboard with sync
- `/log-time` - Add time entries
- `/time-off` - Mark time-off days
- `/work-sync` - Refresh work item cache

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
