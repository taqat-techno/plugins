# Local Timesheet Store

Single owner of where local time entries live and what they look like. `/log-time`,
`/timesheet` and `/workday` read and write this file; do not invent another location.

## Location

`${CLAUDE_PLUGIN_DATA}/timesheet.json`

The plugin data directory survives plugin updates and is deleted when the plugin is
uninstalled. Create the file on the first write. If it is missing, treat it as empty.
Never write time entries into the project, the plugin directory or `~/.claude/`.

## Schema (schemaVersion 1)

```json
{
  "schemaVersion": 1,
  "entries": [
    {
      "id": "2026-10-19T09:30:00Z-1",
      "date": "2026-10-19",
      "hours": 1.5,
      "category": "meeting",
      "workItemId": null,
      "note": "Sprint planning",
      "source": "local"
    },
    {
      "id": "2026-10-19T14:05:00Z-1",
      "date": "2026-10-19",
      "hours": 3,
      "category": "task",
      "workItemId": 1401,
      "note": "Fixed the login timeout",
      "source": "ado"
    }
  ],
  "timeOff": [
    { "date": "2026-10-23", "reason": "Public holiday" }
  ]
}
```

| Field | Rule |
|-------|------|
| `id` | Unique: ISO timestamp of the write plus a counter |
| `date` | `YYYY-MM-DD`, the day the work was done (local date) |
| `hours` | Number > 0 and <= 24 |
| `category` | `task` when `workItemId` is set, else one of `meeting`, `research`, `learning`, `review`, `admin` |
| `workItemId` | Integer, or `null` for category time |
| `note` | Optional short text. Never put secrets or customer data in it |
| `source` | `ado` when the same hours were also written to the work item's Completed Work, else `local` |
| `timeOff[].date` | `YYYY-MM-DD`, at most one entry per date |

## Writing

1. Read the file (or start from `{"schemaVersion": 1, "entries": [], "timeOff": []}`).
2. Append or remove entries; never rewrite unrelated entries.
3. Write the whole file back as UTF-8 JSON with 2-space indentation.
4. A local write needs no Azure DevOps confirmation, but show the user the entry you added.
   A write to a work item still goes through `${CLAUDE_PLUGIN_ROOT}/rules/write-gate.md`
   first; record the `ado` entry only after that update succeeds.

## Targets

The daily target is the plugin option `daily_hours_target` (default 6; the commands
that use it show its current value). Working days come from
`${CLAUDE_PLUGIN_ROOT}/data/project_defaults.json` `workTracking.settings.workingDays`.
Days listed in `timeOff` have a target of 0.

## Retention

Entries are kept until the user deletes them (`/timesheet --off-remove` for time off, or by
editing the file) or uninstalls the plugin. The file stays on this machine.
