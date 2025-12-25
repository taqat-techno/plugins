<#
.SYNOPSIS
    Bulk update Azure DevOps work items using CLI.

.DESCRIPTION
    Performs batch updates on multiple work items at once.
    Supports state changes, field updates, and assignments.
    Much faster than updating items one by one.

.PARAMETER WorkItemIds
    Array of work item IDs to update. Can be comma-separated or array.

.PARAMETER State
    New state for the work items (e.g., "Active", "Done", "Closed")

.PARAMETER AssignedTo
    Email or name to assign work items to

.PARAMETER IterationPath
    Move items to a different iteration

.PARAMETER AreaPath
    Move items to a different area

.PARAMETER Priority
    Set priority (1-4)

.PARAMETER Tags
    Tags to add (comma-separated)

.PARAMETER Parallel
    Run updates in parallel for faster execution

.PARAMETER Project
    Project name (uses default if not specified)

.EXAMPLE
    .\batch_update.ps1 -WorkItemIds 1,2,3,4,5 -State "Done"

.EXAMPLE
    .\batch_update.ps1 -WorkItemIds 100,101,102 -AssignedTo "ahmed@example.com" -Priority 1

.EXAMPLE
    .\batch_update.ps1 -WorkItemIds (1..10) -State "Active" -Parallel

.NOTES
    Author: TAQAT Techno
    Version: 2.0.0
#>

param(
    [Parameter(Mandatory=$true)]
    [int[]]$WorkItemIds,

    [string]$State = "",
    [string]$AssignedTo = "",
    [string]$IterationPath = "",
    [string]$AreaPath = "",
    [int]$Priority = 0,
    [string]$Tags = "",
    [double]$OriginalEstimate = 0,
    [double]$CompletedWork = 0,
    [double]$RemainingWork = 0,

    [string]$Project = "",
    [switch]$Parallel,
    [switch]$DryRun,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Type = "Info")
    $colors = @{
        "Info" = "Cyan"
        "Success" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
    }
    Write-Host $Message -ForegroundColor $colors[$Type]
}

function Build-UpdateCommand {
    param([int]$Id)

    $cmd = "az boards work-item update --id $Id"

    if ($Project) { $cmd += " --project `"$Project`"" }
    if ($State) { $cmd += " --state `"$State`"" }
    if ($AssignedTo) { $cmd += " --assigned-to `"$AssignedTo`"" }
    if ($IterationPath) { $cmd += " --iteration `"$IterationPath`"" }
    if ($AreaPath) { $cmd += " --area `"$AreaPath`"" }

    # Build fields array for numeric/special fields
    $fields = @()
    if ($Priority -gt 0) { $fields += "Microsoft.VSTS.Common.Priority=$Priority" }
    if ($OriginalEstimate -gt 0) { $fields += "Microsoft.VSTS.Scheduling.OriginalEstimate=$OriginalEstimate" }
    if ($CompletedWork -gt 0) { $fields += "Microsoft.VSTS.Scheduling.CompletedWork=$CompletedWork" }
    if ($RemainingWork -ge 0 -and $PSBoundParameters.ContainsKey('RemainingWork')) {
        $fields += "Microsoft.VSTS.Scheduling.RemainingWork=$RemainingWork"
    }
    if ($Tags) { $fields += "System.Tags=$Tags" }

    if ($fields.Count -gt 0) {
        $cmd += " --fields " + ($fields -join " ")
    }

    $cmd += " --output none"

    return $cmd
}

function Update-SingleItem {
    param([int]$Id)

    $cmd = Build-UpdateCommand -Id $Id

    if ($DryRun) {
        Write-Host "[DRY RUN] $cmd" -ForegroundColor Gray
        return @{ Id = $Id; Success = $true; DryRun = $true }
    }

    try {
        if ($Verbose) {
            Write-Host "Executing: $cmd" -ForegroundColor Gray
        }
        Invoke-Expression $cmd
        return @{ Id = $Id; Success = $true; Error = $null }
    } catch {
        return @{ Id = $Id; Success = $false; Error = $_.Exception.Message }
    }
}

# Main execution
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Azure DevOps Batch Work Item Update" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Display update summary
Write-Status "Update Configuration:" "Info"
Write-Host "  Work Items: $($WorkItemIds.Count) items"
Write-Host "  IDs: $($WorkItemIds -join ', ')"
if ($State) { Write-Host "  State: $State" }
if ($AssignedTo) { Write-Host "  Assigned To: $AssignedTo" }
if ($IterationPath) { Write-Host "  Iteration: $IterationPath" }
if ($AreaPath) { Write-Host "  Area: $AreaPath" }
if ($Priority -gt 0) { Write-Host "  Priority: $Priority" }
if ($OriginalEstimate -gt 0) { Write-Host "  Original Estimate: $OriginalEstimate hours" }
if ($CompletedWork -gt 0) { Write-Host "  Completed Work: $CompletedWork hours" }
if ($Tags) { Write-Host "  Tags: $Tags" }
Write-Host "  Mode: $(if ($Parallel) { 'Parallel' } else { 'Sequential' })"
Write-Host ""

if ($DryRun) {
    Write-Status "DRY RUN MODE - No changes will be made" "Warning"
    Write-Host ""
}

# Confirm if many items
if ($WorkItemIds.Count -gt 10 -and -not $DryRun) {
    $confirm = Read-Host "About to update $($WorkItemIds.Count) work items. Continue? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Status "Cancelled by user" "Warning"
        exit 0
    }
}

$startTime = Get-Date
$results = @()

if ($Parallel) {
    Write-Status "Running updates in parallel..." "Info"

    $jobs = @()
    foreach ($id in $WorkItemIds) {
        $cmd = Build-UpdateCommand -Id $id
        if (-not $DryRun) {
            $jobs += Start-Job -ScriptBlock {
                param($command, $workItemId)
                try {
                    Invoke-Expression $command 2>&1
                    @{ Id = $workItemId; Success = $true }
                } catch {
                    @{ Id = $workItemId; Success = $false; Error = $_.Exception.Message }
                }
            } -ArgumentList $cmd, $id
        } else {
            Write-Host "[DRY RUN] $cmd" -ForegroundColor Gray
            $results += @{ Id = $id; Success = $true; DryRun = $true }
        }
    }

    if ($jobs.Count -gt 0) {
        Write-Status "Waiting for $($jobs.Count) jobs to complete..." "Info"
        $completed = $jobs | Wait-Job | Receive-Job
        $jobs | Remove-Job

        foreach ($result in $completed) {
            $results += $result
        }
    }
} else {
    Write-Status "Running updates sequentially..." "Info"

    $i = 0
    foreach ($id in $WorkItemIds) {
        $i++
        Write-Progress -Activity "Updating work items" -Status "Item $i of $($WorkItemIds.Count)" -PercentComplete (($i / $WorkItemIds.Count) * 100)

        $result = Update-SingleItem -Id $id
        $results += $result

        if ($result.Success) {
            Write-Host "  [OK] Work item #$id updated" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Work item #$id - $($result.Error)" -ForegroundColor Red
        }
    }

    Write-Progress -Activity "Updating work items" -Completed
}

$endTime = Get-Date
$duration = $endTime - $startTime

# Summary
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Update Summary" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$successful = ($results | Where-Object { $_.Success }).Count
$failed = ($results | Where-Object { -not $_.Success }).Count

Write-Host ""
Write-Host "  Total Items:  $($WorkItemIds.Count)"
Write-Host "  Successful:   $successful" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "  Failed:       $failed" -ForegroundColor Red
}
Write-Host "  Duration:     $($duration.TotalSeconds.ToString('F2')) seconds"
Write-Host ""

# Show failed items
if ($failed -gt 0) {
    Write-Status "Failed Items:" "Error"
    foreach ($result in ($results | Where-Object { -not $_.Success })) {
        Write-Host "  #$($result.Id): $($result.Error)" -ForegroundColor Red
    }
    Write-Host ""
}

if (-not $DryRun -and $successful -gt 0) {
    Write-Status "Batch update completed!" "Success"
} elseif ($DryRun) {
    Write-Status "Dry run completed. Use without -DryRun to apply changes." "Info"
}

# Return results for pipeline usage
return $results
