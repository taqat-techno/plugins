<#
.SYNOPSIS
    Generate comprehensive sprint report using Azure DevOps CLI.

.DESCRIPTION
    Queries Azure DevOps for sprint data and generates a formatted report.
    Includes: progress, work items by state/type, velocity, and blockers.

.PARAMETER Project
    The Azure DevOps project name.

.PARAMETER Team
    The team name within the project.

.PARAMETER OutputFormat
    Output format: Console, Markdown, JSON, or HTML

.PARAMETER OutputFile
    File path to save the report (optional)

.EXAMPLE
    .\sprint_report.ps1 -Project "Relief Center" -Team "Relief Center Team"

.EXAMPLE
    .\sprint_report.ps1 -Project "Relief Center" -OutputFormat Markdown -OutputFile "sprint_report.md"

.NOTES
    Author: TAQAT Techno
    Version: 2.0.0
#>

param(
    [string]$Project = "",
    [string]$Team = "",
    [ValidateSet("Console", "Markdown", "JSON", "HTML")]
    [string]$OutputFormat = "Console",
    [string]$OutputFile = "",
    [switch]$IncludeBuilds,
    [switch]$IncludeDetails
)

$ErrorActionPreference = "Stop"

function Get-CurrentIteration {
    param([string]$Project, [string]$Team)

    $iterations = az boards iteration team list `
        --project $Project `
        --team $Team `
        --timeframe current `
        -o json 2>$null | ConvertFrom-Json

    if ($iterations -and $iterations.Count -gt 0) {
        return $iterations[0]
    }
    return $null
}

function Get-SprintWorkItems {
    param([string]$Project, [string]$IterationPath)

    $wiql = @"
SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType],
       [System.AssignedTo], [Microsoft.VSTS.Scheduling.StoryPoints],
       [Microsoft.VSTS.Common.Priority], [Microsoft.VSTS.Common.Severity]
FROM WorkItems
WHERE [System.IterationPath] = '$IterationPath'
  AND [System.TeamProject] = '$Project'
ORDER BY [System.WorkItemType], [System.State]
"@

    $result = az boards query --wiql $wiql --project $Project -o json 2>$null | ConvertFrom-Json
    return $result
}

function Get-RecentBuilds {
    param([string]$Project, [int]$Top = 10)

    $builds = az pipelines runs list `
        --project $Project `
        --top $Top `
        -o json 2>$null | ConvertFrom-Json

    return $builds
}

function Calculate-Metrics {
    param($WorkItems)

    $metrics = @{
        Total = $WorkItems.Count
        ByState = @{}
        ByType = @{}
        StoryPoints = @{
            Planned = 0
            Completed = 0
        }
        ByAssignee = @{}
        Blocked = @()
        HighPriority = @()
    }

    foreach ($item in $WorkItems) {
        $state = $item.fields.'System.State'
        $type = $item.fields.'System.WorkItemType'
        $points = $item.fields.'Microsoft.VSTS.Scheduling.StoryPoints'
        $assignee = $item.fields.'System.AssignedTo'.displayName
        $priority = $item.fields.'Microsoft.VSTS.Common.Priority'

        # By State
        if (-not $metrics.ByState.ContainsKey($state)) {
            $metrics.ByState[$state] = 0
        }
        $metrics.ByState[$state]++

        # By Type
        if (-not $metrics.ByType.ContainsKey($type)) {
            $metrics.ByType[$type] = @{ Total = 0; Done = 0 }
        }
        $metrics.ByType[$type].Total++
        if ($state -eq 'Done' -or $state -eq 'Closed') {
            $metrics.ByType[$type].Done++
        }

        # Story Points
        if ($points) {
            $metrics.StoryPoints.Planned += $points
            if ($state -eq 'Done' -or $state -eq 'Closed') {
                $metrics.StoryPoints.Completed += $points
            }
        }

        # By Assignee
        if ($assignee) {
            if (-not $metrics.ByAssignee.ContainsKey($assignee)) {
                $metrics.ByAssignee[$assignee] = @{ Total = 0; Done = 0; Points = 0 }
            }
            $metrics.ByAssignee[$assignee].Total++
            if ($state -eq 'Done' -or $state -eq 'Closed') {
                $metrics.ByAssignee[$assignee].Done++
                $metrics.ByAssignee[$assignee].Points += $points
            }
        }

        # Blocked items
        if ($state -eq 'Blocked') {
            $metrics.Blocked += @{
                Id = $item.id
                Title = $item.fields.'System.Title'
                Assignee = $assignee
            }
        }

        # High priority
        if ($priority -le 2 -and $state -ne 'Done' -and $state -ne 'Closed') {
            $metrics.HighPriority += @{
                Id = $item.id
                Title = $item.fields.'System.Title'
                Priority = $priority
                State = $state
            }
        }
    }

    return $metrics
}

function Format-ConsoleReport {
    param($Iteration, $Metrics, $BuildMetrics)

    $report = @()
    $report += ""
    $report += "============================================="
    $report += "  Sprint Report: $($Iteration.name)"
    $report += "============================================="
    $report += ""
    $report += "Period: $($Iteration.attributes.startDate) to $($Iteration.attributes.finishDate)"
    $report += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    $report += ""

    # Progress
    $done = ($Metrics.ByState['Done'] ?? 0) + ($Metrics.ByState['Closed'] ?? 0)
    $progress = if ($Metrics.Total -gt 0) { [math]::Round(($done / $Metrics.Total) * 100, 1) } else { 0 }

    $report += "--- Progress ---"
    $report += "Total Items:     $($Metrics.Total)"
    $report += "Completed:       $done ($progress%)"

    # Progress bar
    $barLength = 30
    $filledLength = [math]::Floor($barLength * $progress / 100)
    $bar = ('#' * $filledLength) + ('-' * ($barLength - $filledLength))
    $report += "Progress:        [$bar] $progress%"
    $report += ""

    # By State
    $report += "--- By State ---"
    foreach ($state in $Metrics.ByState.Keys | Sort-Object) {
        $count = $Metrics.ByState[$state]
        $pct = [math]::Round(($count / $Metrics.Total) * 100, 1)
        $report += "  $($state.PadRight(15)) $($count.ToString().PadLeft(3)) ($pct%)"
    }
    $report += ""

    # By Type
    $report += "--- By Type ---"
    foreach ($type in $Metrics.ByType.Keys | Sort-Object) {
        $data = $Metrics.ByType[$type]
        $report += "  $($type.PadRight(15)) $($data.Done)/$($data.Total) done"
    }
    $report += ""

    # Velocity
    $report += "--- Velocity ---"
    $report += "Story Points Planned:    $($Metrics.StoryPoints.Planned)"
    $report += "Story Points Completed:  $($Metrics.StoryPoints.Completed)"
    $velocity = if ($Metrics.StoryPoints.Planned -gt 0) {
        [math]::Round(($Metrics.StoryPoints.Completed / $Metrics.StoryPoints.Planned) * 100, 1)
    } else { 0 }
    $report += "Velocity:                $velocity%"
    $report += ""

    # Team Contribution
    if ($Metrics.ByAssignee.Count -gt 0) {
        $report += "--- Team Contribution ---"
        foreach ($name in $Metrics.ByAssignee.Keys | Sort-Object) {
            $data = $Metrics.ByAssignee[$name]
            $report += "  $($name.PadRight(20)) $($data.Done)/$($data.Total) items, $($data.Points) pts"
        }
        $report += ""
    }

    # Builds
    if ($BuildMetrics) {
        $report += "--- Build Health ---"
        $report += "Last 10 Builds:"
        $succeeded = ($BuildMetrics | Where-Object { $_.result -eq 'succeeded' }).Count
        $failed = ($BuildMetrics | Where-Object { $_.result -eq 'failed' }).Count
        $report += "  Succeeded: $succeeded"
        $report += "  Failed:    $failed"
        $report += "  Success Rate: $([math]::Round(($succeeded / [math]::Max($BuildMetrics.Count, 1)) * 100, 1))%"
        $report += ""
    }

    # Blockers
    if ($Metrics.Blocked.Count -gt 0) {
        $report += "--- BLOCKERS (Requires Attention) ---"
        foreach ($item in $Metrics.Blocked) {
            $report += "  [#$($item.Id)] $($item.Title)"
            if ($item.Assignee) { $report += "           Assigned: $($item.Assignee)" }
        }
        $report += ""
    }

    # High Priority
    if ($Metrics.HighPriority.Count -gt 0) {
        $report += "--- High Priority Items ---"
        foreach ($item in $Metrics.HighPriority) {
            $report += "  P$($item.Priority) [#$($item.Id)] $($item.Title) ($($item.State))"
        }
        $report += ""
    }

    $report += "============================================="

    return $report -join "`n"
}

function Format-MarkdownReport {
    param($Iteration, $Metrics, $BuildMetrics)

    $report = @()
    $report += "# Sprint Report: $($Iteration.name)"
    $report += ""
    $report += "**Period:** $($Iteration.attributes.startDate) to $($Iteration.attributes.finishDate)"
    $report += "**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    $report += ""

    # Progress
    $done = ($Metrics.ByState['Done'] ?? 0) + ($Metrics.ByState['Closed'] ?? 0)
    $progress = if ($Metrics.Total -gt 0) { [math]::Round(($done / $Metrics.Total) * 100, 1) } else { 0 }

    $report += "## Progress"
    $report += ""
    $report += "| Metric | Value |"
    $report += "|--------|-------|"
    $report += "| Total Items | $($Metrics.Total) |"
    $report += "| Completed | $done ($progress%) |"
    $report += ""

    # By State
    $report += "## Work Items by State"
    $report += ""
    $report += "| State | Count | % |"
    $report += "|-------|-------|---|"
    foreach ($state in $Metrics.ByState.Keys | Sort-Object) {
        $count = $Metrics.ByState[$state]
        $pct = [math]::Round(($count / $Metrics.Total) * 100, 1)
        $report += "| $state | $count | $pct% |"
    }
    $report += ""

    # By Type
    $report += "## Work Items by Type"
    $report += ""
    $report += "| Type | Done | Total |"
    $report += "|------|------|-------|"
    foreach ($type in $Metrics.ByType.Keys | Sort-Object) {
        $data = $Metrics.ByType[$type]
        $report += "| $type | $($data.Done) | $($data.Total) |"
    }
    $report += ""

    # Velocity
    $report += "## Velocity"
    $report += ""
    $velocity = if ($Metrics.StoryPoints.Planned -gt 0) {
        [math]::Round(($Metrics.StoryPoints.Completed / $Metrics.StoryPoints.Planned) * 100, 1)
    } else { 0 }
    $report += "- **Planned:** $($Metrics.StoryPoints.Planned) story points"
    $report += "- **Completed:** $($Metrics.StoryPoints.Completed) story points"
    $report += "- **Velocity:** $velocity%"
    $report += ""

    # Blockers
    if ($Metrics.Blocked.Count -gt 0) {
        $report += "## Blockers"
        $report += ""
        foreach ($item in $Metrics.Blocked) {
            $report += "- **[#$($item.Id)]** $($item.Title)"
        }
        $report += ""
    }

    $report += "---"
    $report += "*Generated by Azure DevOps CLI Sprint Report Tool*"

    return $report -join "`n"
}

# Main execution
Write-Host ""
Write-Host "Generating Sprint Report..." -ForegroundColor Cyan
Write-Host ""

# Get defaults if not specified
if (-not $Project) {
    $defaults = az devops configure --list 2>$null
    if ($defaults -match "project\s*=\s*(.+)") {
        $Project = $matches[1].Trim()
    }
}

if (-not $Project) {
    Write-Host "Error: Project not specified and no default set." -ForegroundColor Red
    Write-Host "Use: .\sprint_report.ps1 -Project 'ProjectName'"
    exit 1
}

if (-not $Team) {
    $Team = "$Project Team"
}

Write-Host "Project: $Project" -ForegroundColor Gray
Write-Host "Team: $Team" -ForegroundColor Gray
Write-Host ""

# Get current iteration
$iteration = Get-CurrentIteration -Project $Project -Team $Team
if (-not $iteration) {
    Write-Host "Error: Could not get current iteration for $Team" -ForegroundColor Red
    exit 1
}

Write-Host "Sprint: $($iteration.name)" -ForegroundColor Gray

# Get work items
$workItems = Get-SprintWorkItems -Project $Project -IterationPath $iteration.path
Write-Host "Work Items: $($workItems.Count)" -ForegroundColor Gray

# Calculate metrics
$metrics = Calculate-Metrics -WorkItems $workItems

# Get builds if requested
$buildMetrics = $null
if ($IncludeBuilds) {
    $buildMetrics = Get-RecentBuilds -Project $Project
}

# Generate report
$report = switch ($OutputFormat) {
    "Markdown" { Format-MarkdownReport -Iteration $iteration -Metrics $metrics -BuildMetrics $buildMetrics }
    "JSON" { $metrics | ConvertTo-Json -Depth 5 }
    "HTML" { Format-MarkdownReport -Iteration $iteration -Metrics $metrics -BuildMetrics $buildMetrics }  # Placeholder
    default { Format-ConsoleReport -Iteration $iteration -Metrics $metrics -BuildMetrics $buildMetrics }
}

# Output
if ($OutputFile) {
    $report | Out-File -FilePath $OutputFile -Encoding utf8
    Write-Host ""
    Write-Host "Report saved to: $OutputFile" -ForegroundColor Green
} else {
    Write-Host $report
}
