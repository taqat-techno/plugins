---
title: 'Time Off'
read_only: false
type: 'command'
description: 'Mark days as time-off (excluded from daily hour requirements)'
---

# Time Off

Mark specific days as time-off so they are excluded from the daily minimum hours requirement. Time-off days show as "TIME-OFF" in timesheets and compliance checks.

## Usage

```
/time-off today "Personal day"
/time-off 2026-03-21 "Eid holiday"
/time-off 2026-03-24 2026-03-28 "Vacation"       # Date range (inclusive)
/time-off --remove 2026-03-21                      # Remove time-off marking
/time-off --list                                    # List all time-off days
```

## Workflow

### Step 1: Parse Input

```
1. Determine action:
   - --list: show all time-off entries
   - --remove DATE: remove a specific entry
   - Single date + reason: mark one day
   - Two dates + reason: mark date range (inclusive)
2. Parse dates:
   - "today" → current date as YYYY-MM-DD
   - "tomorrow" → next day as YYYY-MM-DD
   - YYYY-MM-DD → use as-is
3. Parse reason (quoted string or remaining text)
```

### Step 2: Read Tracker Data

```
1. Read ~/.claude/work-tracker-data.json
2. If NOT found: bootstrap from defaults (same as /workday Step 0)
3. Parse JSON, access timeOff array
```

### Step 3: Execute Action

#### Add Time-Off (Single Day)

```
1. Check if date already exists in timeOff array
   - If YES: "Date {date} is already marked as time-off ({existing reason}). Update reason? (y/n)"
2. Add entry: { "date": "YYYY-MM-DD", "reason": "description" }
3. If timeLog[date] has entries:
   - Mark timeLog[date].isTimeOff = true
   - Mark timeLog[date].timeOffReason = reason
4. Write work-tracker-data.json
5. Regenerate affected sections in work-tracker.md
```

#### Add Time-Off (Date Range)

```
1. Calculate all dates from startDate to endDate (inclusive)
2. Filter to only working days (skip weekends per settings.workingDays)
3. For each working day in range:
   - Add to timeOff array (skip if already exists)
   - Update timeLog if entries exist
4. Write work-tracker-data.json
5. Regenerate work-tracker.md
6. Report: "Marked {N} working days as time-off ({startDate} to {endDate})"
```

#### Remove Time-Off

```
1. Find entry in timeOff array matching the date
2. If NOT found: "No time-off entry for {date}"
3. Remove from timeOff array
4. If timeLog[date] exists:
   - Set isTimeOff = false
   - Remove timeOffReason
5. Write work-tracker-data.json
6. Regenerate work-tracker.md
7. Report: "Removed time-off for {date}. This day now requires {min}h minimum."
```

#### List Time-Off

```
1. Read timeOff array
2. Sort by date
3. Display table
```

### Step 4: Report

#### Add Confirmation

```markdown
## Time-Off Marked

| Date | Day | Reason |
|------|-----|--------|
| 2026-03-21 | Fri | Eid holiday |

This day is now excluded from the {minHoursPerDay}h daily requirement.

### Updated Week Status
| Day | Status | Hours |
|-----|--------|-------|
| Mon | OK | 6.5h |
| Tue | OK | 6.0h |
| Wed | OK | 6.0h |
| Thu | OK | 6.0h |
| Fri | TIME-OFF | Eid holiday |

Week requirement adjusted: {adjustedRequired}h ({workingDays} working days)
```

#### Range Confirmation

```markdown
## Time-Off Period Marked

| # | Date | Day | Reason |
|---|------|-----|--------|
| 1 | 2026-03-24 | Mon | Vacation |
| 2 | 2026-03-25 | Tue | Vacation |
| 3 | 2026-03-26 | Wed | Vacation |
| 4 | 2026-03-27 | Thu | Vacation |
| 5 | 2026-03-28 | Fri | Vacation |

5 working days marked as time-off.
Week 13 requirement adjusted: 0h (0 working days)
```

#### List View

```markdown
## Registered Time-Off Days

| # | Date | Day | Reason |
|---|------|-----|--------|
| 1 | 2026-03-04 | Tue | Personal day |
| 2 | 2026-03-21 | Fri | Eid holiday |
| 3 | 2026-03-24 | Mon | Vacation |
| 4 | 2026-03-25 | Tue | Vacation |
| 5 | 2026-03-26 | Wed | Vacation |
| 6 | 2026-03-27 | Thu | Vacation |
| 7 | 2026-03-28 | Fri | Vacation |

Total: 7 time-off days registered
```

## Error Handling

| Error | Recovery |
|-------|----------|
| Invalid date format | "Invalid date. Use YYYY-MM-DD or 'today'" |
| End date before start date | "End date must be after start date" |
| Date already marked | Ask to update reason |
| Tracker file missing | Bootstrap from defaults |

## Related Commands

- `/timesheet` - View time tracking with time-off reflected
- `/workday` - Daily dashboard shows time-off status
- `/log-time` - Log hours (warns if logging on time-off day)

---

*Part of DevOps Plugin v3.0 - Work Tracking System*
