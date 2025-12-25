# Automation Templates

> **Purpose**: This memory provides reusable automation scripts for common Azure DevOps workflows. Templates are available in PowerShell (Windows), Bash (macOS/Linux), and Python (cross-platform).

## Template Categories

| Category | Templates | Best For |
|----------|-----------|----------|
| Standup & Reports | Daily standup, Sprint report | Regular reporting |
| Work Item Management | Bulk create, Bulk update, Close done items | Batch operations |
| PR Automation | Auto-merge, PR creation, Review reminders | Code review workflow |
| Pipeline Operations | Build monitor, Failure alerts, Deploy scripts | CI/CD |
| Sprint Management | Sprint setup, Capacity planning, Burndown | Agile planning |

---

## 1. Daily Standup Generator

### PowerShell Version

```powershell
# standup.ps1 - Generate daily standup notes
param(
    [string]$Project = "Relief Center",
    [string]$OutputFormat = "markdown"
)

$yesterday = (Get-Date).AddDays(-1).ToString("yyyy-MM-dd")
$today = Get-Date -Format "yyyy-MM-dd"

# Get completed items (yesterday)
$completedWiql = @"
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] = '$Project'
  AND [System.ChangedDate] >= '$yesterday'
  AND [System.State] = 'Done'
"@

$completed = az boards query --wiql $completedWiql --project $Project -o json | ConvertFrom-Json

# Get in-progress items
$activeWiql = @"
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] = '$Project'
  AND [System.State] IN ('Active', 'In Progress')
"@

$active = az boards query --wiql $activeWiql --project $Project -o json | ConvertFrom-Json

# Get blocked items
$blockedWiql = @"
SELECT [System.Id], [System.Title], [System.WorkItemType]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] = '$Project'
  AND [System.Tags] CONTAINS 'Blocked'
"@

$blocked = az boards query --wiql $blockedWiql --project $Project -o json | ConvertFrom-Json

# Output
Write-Host "## Daily Standup - $today`n"

Write-Host "### Yesterday (Completed)"
if ($completed.Count -gt 0) {
    foreach ($item in $completed) {
        $type = $item.fields.'System.WorkItemType'
        $title = $item.fields.'System.Title'
        Write-Host "- [$type #$($item.id)] $title"
    }
} else {
    Write-Host "- No items completed"
}

Write-Host "`n### Today (In Progress)"
if ($active.Count -gt 0) {
    foreach ($item in $active) {
        $type = $item.fields.'System.WorkItemType'
        $title = $item.fields.'System.Title'
        Write-Host "- [$type #$($item.id)] $title"
    }
} else {
    Write-Host "- Planning work items"
}

Write-Host "`n### Blockers"
if ($blocked.Count -gt 0) {
    foreach ($item in $blocked) {
        $title = $item.fields.'System.Title'
        Write-Host "- [#$($item.id)] $title"
    }
} else {
    Write-Host "- None"
}
```

### Bash Version

```bash
#!/bin/bash
# standup.sh - Generate daily standup notes

PROJECT="${1:-Relief Center}"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

echo "## Daily Standup - $TODAY"
echo ""

# Completed yesterday
echo "### Yesterday (Completed)"
COMPLETED=$(az boards query --wiql "
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] = '$PROJECT'
  AND [System.ChangedDate] >= '$YESTERDAY'
  AND [System.State] = 'Done'
" --project "$PROJECT" -o json 2>/dev/null)

if [ "$(echo $COMPLETED | jq length)" -gt 0 ]; then
    echo $COMPLETED | jq -r '.[] | "- [#\(.id)] \(.fields."System.Title")"'
else
    echo "- No items completed"
fi

# In Progress
echo ""
echo "### Today (In Progress)"
ACTIVE=$(az boards query --wiql "
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.AssignedTo] = @Me
  AND [System.TeamProject] = '$PROJECT'
  AND [System.State] IN ('Active', 'In Progress')
" --project "$PROJECT" -o json 2>/dev/null)

if [ "$(echo $ACTIVE | jq length)" -gt 0 ]; then
    echo $ACTIVE | jq -r '.[] | "- [#\(.id)] \(.fields."System.Title")"'
else
    echo "- Planning work items"
fi

# Blockers
echo ""
echo "### Blockers"
echo "- None"
```

---

## 2. Sprint Report Generator

### PowerShell Version

```powershell
# sprint_report.ps1 - Generate sprint progress report
param(
    [string]$Project = "Relief Center",
    [string]$Team = "Relief Center Team"
)

# Get current iteration
$iteration = az boards iteration team list `
    --project $Project `
    --team $Team `
    --timeframe current `
    --query "[0]" -o json | ConvertFrom-Json

$iterationPath = $iteration.path

Write-Host "# Sprint Report: $($iteration.name)`n"
Write-Host "**Period**: $($iteration.attributes.startDate.Split('T')[0]) to $($iteration.attributes.finishDate.Split('T')[0])`n"

# Get work items in iteration
$wiql = @"
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [Microsoft.VSTS.Scheduling.StoryPoints]
FROM WorkItems
WHERE [System.IterationPath] = '$iterationPath'
  AND [System.TeamProject] = '$Project'
"@

$items = az boards query --wiql $wiql --project $Project -o json | ConvertFrom-Json

# Calculate stats
$total = $items.Count
$done = ($items | Where-Object { $_.fields.'System.State' -eq 'Done' }).Count
$active = ($items | Where-Object { $_.fields.'System.State' -eq 'Active' }).Count
$new = ($items | Where-Object { $_.fields.'System.State' -eq 'New' }).Count

$progress = if ($total -gt 0) { [math]::Round(($done / $total) * 100, 1) } else { 0 }

# Story points
$totalPoints = ($items | Measure-Object -Property { $_.fields.'Microsoft.VSTS.Scheduling.StoryPoints' } -Sum).Sum
$donePoints = ($items | Where-Object { $_.fields.'System.State' -eq 'Done' } |
    Measure-Object -Property { $_.fields.'Microsoft.VSTS.Scheduling.StoryPoints' } -Sum).Sum

Write-Host "## Progress`n"
Write-Host "**Completion**: $progress% ($done of $total items)`n"
Write-Host "**Story Points**: $donePoints / $totalPoints completed`n"

Write-Host "## Status Breakdown`n"
Write-Host "| State | Count |"
Write-Host "|-------|-------|"
Write-Host "| Done | $done |"
Write-Host "| Active | $active |"
Write-Host "| New | $new |"

# Get bugs
$bugs = $items | Where-Object { $_.fields.'System.WorkItemType' -eq 'Bug' }
$openBugs = $bugs | Where-Object { $_.fields.'System.State' -ne 'Done' }

Write-Host "`n## Bugs`n"
Write-Host "- Total: $($bugs.Count)"
Write-Host "- Open: $($openBugs.Count)"

if ($openBugs.Count -gt 0) {
    Write-Host "`n**Open Bugs:**"
    foreach ($bug in $openBugs) {
        Write-Host "- [#$($bug.id)] $($bug.fields.'System.Title')"
    }
}

# Recent builds
Write-Host "`n## Build Health`n"
$builds = az pipelines runs list --project $Project --top 5 -o json | ConvertFrom-Json
$passed = ($builds | Where-Object { $_.result -eq 'succeeded' }).Count
$failed = ($builds | Where-Object { $_.result -eq 'failed' }).Count

Write-Host "Last 5 builds: $passed passed, $failed failed"
```

---

## 3. Bulk Work Item Creator

### PowerShell Version

```powershell
# bulk_create_tasks.ps1 - Create multiple tasks under a parent
param(
    [Parameter(Mandatory=$true)]
    [int]$ParentId,

    [Parameter(Mandatory=$true)]
    [string[]]$Tasks,

    [string]$Project = "Relief Center",
    [string]$AssignedTo = ""
)

$created = @()

foreach ($taskTitle in $Tasks) {
    Write-Host "Creating: $taskTitle..." -NoNewline

    $args = @(
        "--title", "`"$taskTitle`"",
        "--type", "Task",
        "--project", $Project
    )

    if ($AssignedTo) {
        $args += "--assigned-to", $AssignedTo
    }

    # Create task
    $task = az boards work-item create @args -o json | ConvertFrom-Json

    # Link to parent
    az boards work-item relation add `
        --id $task.id `
        --relation-type "Parent" `
        --target-id $ParentId `
        --output none

    Write-Host " Done (#$($task.id))"
    $created += $task
}

Write-Host "`nCreated $($created.Count) tasks under parent #$ParentId"

# Usage example:
# .\bulk_create_tasks.ps1 -ParentId 1234 -Tasks "Design UI", "Implement API", "Write Tests", "Documentation"
```

### Bash Version

```bash
#!/bin/bash
# bulk_create_tasks.sh - Create multiple tasks under a parent

PARENT_ID=$1
PROJECT="${2:-Relief Center}"
shift 2
TASKS=("$@")

if [ -z "$PARENT_ID" ] || [ ${#TASKS[@]} -eq 0 ]; then
    echo "Usage: $0 <parent_id> [project] <task1> <task2> ..."
    exit 1
fi

echo "Creating ${#TASKS[@]} tasks under parent #$PARENT_ID"

for TASK in "${TASKS[@]}"; do
    echo -n "Creating: $TASK... "

    # Create task
    TASK_ID=$(az boards work-item create \
        --title "$TASK" \
        --type Task \
        --project "$PROJECT" \
        --query "id" -o tsv)

    # Link to parent
    az boards work-item relation add \
        --id $TASK_ID \
        --relation-type "Parent" \
        --target-id $PARENT_ID \
        --output none

    echo "Done (#$TASK_ID)"
done

# Usage:
# ./bulk_create_tasks.sh 1234 "Relief Center" "Design UI" "Implement API" "Write Tests"
```

---

## 4. Close All Done Items

### PowerShell Version

```powershell
# close_done_items.ps1 - Close all items in Done state
param(
    [string]$Project = "Relief Center",
    [switch]$WhatIf = $false
)

$wiql = @"
SELECT [System.Id], [System.Title]
FROM WorkItems
WHERE [System.TeamProject] = '$Project'
  AND [System.State] = 'Done'
  AND [System.WorkItemType] IN ('Task', 'Bug', 'User Story')
"@

$items = az boards query --wiql $wiql --project $Project -o json | ConvertFrom-Json

Write-Host "Found $($items.Count) items in 'Done' state"

if ($WhatIf) {
    Write-Host "`n[WhatIf] Would close:"
    foreach ($item in $items) {
        Write-Host "  - #$($item.id): $($item.fields.'System.Title')"
    }
    return
}

$closed = 0
foreach ($item in $items) {
    Write-Host "Closing #$($item.id)..." -NoNewline
    try {
        az boards work-item update --id $item.id --state Closed --output none
        Write-Host " Done"
        $closed++
    } catch {
        Write-Host " Failed"
    }
}

Write-Host "`nClosed $closed of $($items.Count) items"
```

---

## 5. PR Auto-Merger

### Bash Version

```bash
#!/bin/bash
# auto_merge_approved.sh - Merge all approved PRs

REPO="${1:-my-repo}"
PROJECT="${2:-Relief Center}"

echo "Checking approved PRs in $REPO..."

# Get active PRs that are approved
PRS=$(az repos pr list \
    --repository "$REPO" \
    --project "$PROJECT" \
    --status active \
    --query "[?mergeStatus=='succeeded'].pullRequestId" \
    -o tsv)

if [ -z "$PRS" ]; then
    echo "No approved PRs ready to merge"
    exit 0
fi

for PR_ID in $PRS; do
    echo "Processing PR #$PR_ID..."

    # Check all policies passed
    POLICIES=$(az repos pr policy list --id $PR_ID -o json)
    ALL_PASSED=$(echo $POLICIES | jq 'all(.status == "approved" or .status == "notApplicable")')

    if [ "$ALL_PASSED" == "true" ]; then
        echo "  Completing PR #$PR_ID..."
        az repos pr update \
            --id $PR_ID \
            --status completed \
            --squash true \
            --delete-source-branch true \
            --output none
        echo "  Merged!"
    else
        echo "  Policies not satisfied, skipping"
    fi
done
```

---

## 6. Build Monitor with Alerts

### Python Version

```python
#!/usr/bin/env python3
"""
build_monitor.py - Monitor builds and alert on failures
"""

import subprocess
import json
import sys
import time
from datetime import datetime

def run_cli(command):
    """Execute CLI command and return JSON result"""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return json.loads(result.stdout) if result.stdout else None

def get_recent_builds(project, pipeline_id=None, top=5):
    """Get recent builds"""
    cmd = f'az pipelines runs list --project "{project}" --top {top}'
    if pipeline_id:
        cmd += f' --pipeline-ids {pipeline_id}'
    cmd += ' -o json'
    return run_cli(cmd) or []

def check_build_status(project, build_id):
    """Get build status"""
    cmd = f'az pipelines runs show --project "{project}" --id {build_id} -o json'
    return run_cli(cmd)

def create_bug_for_failure(project, build):
    """Create bug for failed build"""
    build_id = build['id']
    pipeline_name = build.get('definition', {}).get('name', 'Unknown')

    title = f"Build Failure: {pipeline_name} #{build_id}"
    description = f"""
<h3>Build Failure Details</h3>
<ul>
<li><b>Build ID:</b> {build_id}</li>
<li><b>Pipeline:</b> {pipeline_name}</li>
<li><b>Branch:</b> {build.get('sourceBranch', 'Unknown')}</li>
<li><b>Time:</b> {build.get('finishTime', 'Unknown')}</li>
<li><b>Reason:</b> {build.get('result', 'Unknown')}</li>
</ul>
<p>Please investigate and fix the build failure.</p>
"""

    cmd = f'''az boards work-item create \
        --title "{title}" \
        --type Bug \
        --project "{project}" \
        --description "{description}" \
        --fields "Microsoft.VSTS.Common.Priority=1" \
        -o json'''

    return run_cli(cmd)

def monitor_builds(project, pipeline_id=None, interval=60, create_bugs=False):
    """Continuously monitor builds"""
    print(f"Monitoring builds for {project}...")
    print(f"Check interval: {interval} seconds")
    print("-" * 50)

    seen_failures = set()

    while True:
        builds = get_recent_builds(project, pipeline_id, top=10)

        for build in builds:
            build_id = build['id']
            result = build.get('result', '')

            if result == 'failed' and build_id not in seen_failures:
                seen_failures.add(build_id)
                pipeline = build.get('definition', {}).get('name', 'Unknown')

                print(f"\n[ALERT] Build #{build_id} FAILED!")
                print(f"  Pipeline: {pipeline}")
                print(f"  Branch: {build.get('sourceBranch', 'Unknown')}")
                print(f"  Time: {build.get('finishTime', 'Unknown')}")

                if create_bugs:
                    bug = create_bug_for_failure(project, build)
                    if bug:
                        print(f"  Created Bug: #{bug['id']}")

        time.sleep(interval)

if __name__ == '__main__':
    project = sys.argv[1] if len(sys.argv) > 1 else 'Relief Center'
    pipeline_id = sys.argv[2] if len(sys.argv) > 2 else None

    monitor_builds(project, pipeline_id, interval=60, create_bugs=True)
```

---

## 7. Sprint Setup Script

### PowerShell Version

```powershell
# sprint_setup.ps1 - Set up a new sprint
param(
    [Parameter(Mandatory=$true)]
    [string]$SprintName,

    [Parameter(Mandatory=$true)]
    [datetime]$StartDate,

    [int]$DurationDays = 14,

    [string]$Project = "Relief Center",
    [string]$Team = "Relief Center Team"
)

$endDate = $StartDate.AddDays($DurationDays - 1)

Write-Host "Setting up: $SprintName"
Write-Host "  Start: $($StartDate.ToString('yyyy-MM-dd'))"
Write-Host "  End: $($endDate.ToString('yyyy-MM-dd'))"
Write-Host ""

# Create iteration
Write-Host "Creating iteration..." -NoNewline
az boards iteration project create `
    --name $SprintName `
    --path "\\$Project\\Iteration" `
    --start-date $StartDate.ToString("yyyy-MM-dd") `
    --finish-date $endDate.ToString("yyyy-MM-dd") `
    --project $Project `
    --output none

Write-Host " Done"

# Get iteration ID
$iterations = az boards iteration project list --project $Project --depth 2 -o json | ConvertFrom-Json
$newIteration = $iterations.children | Where-Object { $_.name -eq $SprintName }

if ($newIteration) {
    # Assign to team
    Write-Host "Assigning to team..." -NoNewline
    az boards iteration team add `
        --id $newIteration.identifier `
        --project $Project `
        --team $Team `
        --output none
    Write-Host " Done"
}

Write-Host "`nSprint '$SprintName' is ready!"
Write-Host "Next steps:"
Write-Host "  1. Set team capacity using MCP: work_get_team_capacity, work_update_team_capacity"
Write-Host "  2. Add work items to sprint"
Write-Host "  3. Start sprint planning"

# Usage:
# .\sprint_setup.ps1 -SprintName "Sprint 16" -StartDate "2025-01-01"
```

---

## 8. Release Notes Generator

### Python Version

```python
#!/usr/bin/env python3
"""
release_notes.py - Generate release notes from work items and commits
"""

import subprocess
import json
import sys
from datetime import datetime

def run_cli(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return json.loads(result.stdout) if result.stdout else None

def get_work_items_in_iteration(project, iteration_path):
    """Get all work items in an iteration"""
    wiql = f'''
    SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State]
    FROM WorkItems
    WHERE [System.IterationPath] = '{iteration_path}'
      AND [System.State] = 'Done'
    ORDER BY [System.WorkItemType]
    '''

    cmd = f'az boards query --wiql "{wiql}" --project "{project}" -o json'
    return run_cli(cmd) or []

def categorize_items(items):
    """Categorize items by type"""
    categories = {
        'Features': [],
        'Bugs': [],
        'Tasks': [],
        'Other': []
    }

    for item in items:
        item_type = item['fields']['System.WorkItemType']
        title = item['fields']['System.Title']
        item_id = item['id']

        entry = f"- [#{item_id}] {title}"

        if item_type == 'User Story' or item_type == 'Feature':
            categories['Features'].append(entry)
        elif item_type == 'Bug':
            categories['Bugs'].append(entry)
        elif item_type == 'Task':
            categories['Tasks'].append(entry)
        else:
            categories['Other'].append(entry)

    return categories

def generate_release_notes(project, iteration_path, version):
    """Generate release notes markdown"""
    items = get_work_items_in_iteration(project, iteration_path)
    categories = categorize_items(items)

    today = datetime.now().strftime("%Y-%m-%d")

    notes = f"""# Release Notes - {version}

**Release Date**: {today}
**Project**: {project}

---

"""

    # Features
    if categories['Features']:
        notes += "## New Features\n\n"
        notes += "\n".join(categories['Features'])
        notes += "\n\n"

    # Bug Fixes
    if categories['Bugs']:
        notes += "## Bug Fixes\n\n"
        notes += "\n".join(categories['Bugs'])
        notes += "\n\n"

    # Improvements
    if categories['Tasks']:
        notes += "## Improvements\n\n"
        notes += "\n".join(categories['Tasks'])
        notes += "\n\n"

    # Summary
    total = sum(len(cat) for cat in categories.values())
    notes += f"""---

**Summary**: {total} items completed
- {len(categories['Features'])} features
- {len(categories['Bugs'])} bug fixes
- {len(categories['Tasks'])} improvements
"""

    return notes

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python release_notes.py <project> <iteration_path> [version]")
        print("Example: python release_notes.py 'Relief Center' 'Relief Center\\Sprint 15' 'v1.2.0'")
        sys.exit(1)

    project = sys.argv[1]
    iteration = sys.argv[2]
    version = sys.argv[3] if len(sys.argv) > 3 else "v1.0.0"

    notes = generate_release_notes(project, iteration, version)
    print(notes)
```

---

## Usage Tips

### Running Templates

**PowerShell**:
```powershell
.\script_name.ps1 -Parameter Value
```

**Bash**:
```bash
chmod +x script_name.sh
./script_name.sh arg1 arg2
```

**Python**:
```bash
python script_name.py arg1 arg2
```

### Customization

1. Copy template to your project
2. Modify project/team names
3. Adjust WIQL queries for your workflow
4. Add custom fields as needed

---

## Related Memories

- `cli_best_practices.md` - CLI patterns used in templates
- `wiql_queries.md` - WIQL query patterns
- `hybrid_routing.md` - When to use CLI vs MCP
