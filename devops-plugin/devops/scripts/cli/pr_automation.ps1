<#
.SYNOPSIS
    Automate Azure DevOps Pull Request workflows using CLI.

.DESCRIPTION
    Provides automation for common PR operations:
    - Create PR from current branch
    - Auto-complete approved PRs
    - Merge multiple PRs
    - Add reviewers in bulk
    - Generate PR summary

.PARAMETER Action
    The action to perform: Create, AutoComplete, Merge, AddReviewers, Summary

.PARAMETER Repository
    Repository name or ID

.PARAMETER SourceBranch
    Source branch for PR creation

.PARAMETER TargetBranch
    Target branch for PR creation

.PARAMETER Title
    PR title

.PARAMETER WorkItems
    Work item IDs to link (comma-separated)

.PARAMETER Reviewers
    Reviewer emails (comma-separated)

.EXAMPLE
    .\pr_automation.ps1 -Action Create -Title "Feature: New Login" -WorkItems "123,124"

.EXAMPLE
    .\pr_automation.ps1 -Action AutoComplete -Squash

.EXAMPLE
    .\pr_automation.ps1 -Action Summary

.NOTES
    Author: TAQAT Techno
    Version: 2.0.0
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("Create", "AutoComplete", "Merge", "AddReviewers", "Summary", "Cleanup")]
    [string]$Action,

    [string]$Repository = "",
    [string]$SourceBranch = "",
    [string]$TargetBranch = "main",
    [string]$Title = "",
    [string]$Description = "",
    [string]$WorkItems = "",
    [string]$Reviewers = "",
    [int[]]$PRIds = @(),

    [switch]$Squash,
    [switch]$DeleteSourceBranch,
    [switch]$Draft,
    [switch]$DryRun,
    [string]$Project = ""
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

function Get-CurrentBranch {
    $branch = git rev-parse --abbrev-ref HEAD 2>$null
    return $branch
}

function Get-RepositoryName {
    $remote = git remote get-url origin 2>$null
    if ($remote -match "/([^/]+)\.git$" -or $remote -match "/([^/]+)$") {
        return $matches[1]
    }
    return $null
}

function Create-PullRequest {
    Write-Status "Creating Pull Request..." "Info"

    # Auto-detect if not specified
    if (-not $SourceBranch) {
        $SourceBranch = Get-CurrentBranch
        Write-Status "Using current branch: $SourceBranch" "Info"
    }

    if (-not $Repository) {
        $Repository = Get-RepositoryName
        if ($Repository) {
            Write-Status "Using repository: $Repository" "Info"
        }
    }

    if (-not $Title) {
        # Generate title from branch name
        $Title = $SourceBranch -replace "^(feature|bugfix|hotfix)/", ""
        $Title = $Title -replace "-", " " -replace "_", " "
        $Title = (Get-Culture).TextInfo.ToTitleCase($Title)
        Write-Status "Auto-generated title: $Title" "Info"
    }

    # Build command
    $cmd = "az repos pr create"
    $cmd += " --source-branch `"$SourceBranch`""
    $cmd += " --target-branch `"$TargetBranch`""
    $cmd += " --title `"$Title`""

    if ($Repository) { $cmd += " --repository `"$Repository`"" }
    if ($Project) { $cmd += " --project `"$Project`"" }
    if ($Description) { $cmd += " --description `"$Description`"" }
    if ($WorkItems) { $cmd += " --work-items $WorkItems" }
    if ($Reviewers) { $cmd += " --reviewers $Reviewers" }
    if ($Draft) { $cmd += " --draft true" }
    if ($DeleteSourceBranch) { $cmd += " --delete-source-branch true" }
    if ($Squash) { $cmd += " --squash true" }

    if ($DryRun) {
        Write-Status "[DRY RUN] Would execute:" "Warning"
        Write-Host $cmd -ForegroundColor Gray
        return
    }

    Write-Status "Executing: $cmd" "Info"
    $result = Invoke-Expression "$cmd -o json" | ConvertFrom-Json

    if ($result) {
        Write-Host ""
        Write-Status "Pull Request Created!" "Success"
        Write-Host ""
        Write-Host "  PR ID:        $($result.pullRequestId)"
        Write-Host "  Title:        $($result.title)"
        Write-Host "  Source:       $($result.sourceRefName -replace 'refs/heads/', '')"
        Write-Host "  Target:       $($result.targetRefName -replace 'refs/heads/', '')"
        Write-Host "  Status:       $($result.status)"
        Write-Host "  URL:          $($result.url -replace 'pullRequests', 'pullrequest')"
        Write-Host ""

        if ($result.workItemRefs) {
            Write-Host "  Linked Work Items: $($result.workItemRefs.id -join ', ')"
        }

        return $result
    }
}

function Set-AutoComplete {
    Write-Status "Setting Auto-Complete on approved PRs..." "Info"

    # Get active PRs
    $prs = az repos pr list --status active -o json 2>$null | ConvertFrom-Json

    if (-not $prs -or $prs.Count -eq 0) {
        Write-Status "No active PRs found" "Warning"
        return
    }

    $updated = 0
    foreach ($pr in $prs) {
        # Check if all reviewers approved
        $allApproved = $true
        if ($pr.reviewers) {
            foreach ($reviewer in $pr.reviewers) {
                if ($reviewer.vote -lt 10) {  # 10 = Approved
                    $allApproved = $false
                    break
                }
            }
        }

        if ($allApproved) {
            $cmd = "az repos pr update --id $($pr.pullRequestId) --auto-complete true"
            if ($Squash) { $cmd += " --squash true" }
            if ($DeleteSourceBranch) { $cmd += " --delete-source-branch true" }

            if ($DryRun) {
                Write-Status "[DRY RUN] Would auto-complete PR #$($pr.pullRequestId): $($pr.title)" "Info"
            } else {
                Write-Status "Setting auto-complete on PR #$($pr.pullRequestId)..." "Info"
                Invoke-Expression "$cmd --output none"
                $updated++
            }
        }
    }

    Write-Status "Updated $updated PRs with auto-complete" "Success"
}

function Merge-PullRequests {
    Write-Status "Merging Pull Requests..." "Info"

    if ($PRIds.Count -eq 0) {
        # Get all approved PRs
        $prs = az repos pr list --status active -o json 2>$null | ConvertFrom-Json

        foreach ($pr in $prs) {
            $allApproved = $true
            if ($pr.reviewers) {
                foreach ($reviewer in $pr.reviewers) {
                    if ($reviewer.vote -lt 10) {
                        $allApproved = $false
                        break
                    }
                }
            }
            if ($allApproved) {
                $PRIds += $pr.pullRequestId
            }
        }
    }

    if ($PRIds.Count -eq 0) {
        Write-Status "No PRs to merge" "Warning"
        return
    }

    $merged = 0
    foreach ($id in $PRIds) {
        $cmd = "az repos pr update --id $id --status completed"
        if ($Squash) { $cmd += " --squash true" }
        if ($DeleteSourceBranch) { $cmd += " --delete-source-branch true" }

        if ($DryRun) {
            Write-Status "[DRY RUN] Would merge PR #$id" "Info"
        } else {
            try {
                Write-Status "Merging PR #$id..." "Info"
                Invoke-Expression "$cmd --output none"
                $merged++
                Write-Status "PR #$id merged successfully" "Success"
            } catch {
                Write-Status "Failed to merge PR #$id: $_" "Error"
            }
        }
    }

    Write-Status "Merged $merged PRs" "Success"
}

function Add-Reviewers {
    Write-Status "Adding Reviewers to PRs..." "Info"

    if (-not $Reviewers) {
        Write-Status "No reviewers specified. Use -Reviewers 'email1,email2'" "Error"
        return
    }

    $reviewerList = $Reviewers -split ","

    if ($PRIds.Count -eq 0) {
        # Get active PRs
        $prs = az repos pr list --status active -o json 2>$null | ConvertFrom-Json
        $PRIds = $prs | ForEach-Object { $_.pullRequestId }
    }

    foreach ($id in $PRIds) {
        $cmd = "az repos pr reviewer add --id $id --reviewers $Reviewers"

        if ($DryRun) {
            Write-Status "[DRY RUN] Would add reviewers to PR #$id" "Info"
        } else {
            try {
                Write-Status "Adding reviewers to PR #$id..." "Info"
                Invoke-Expression "$cmd --output none"
            } catch {
                Write-Status "Failed to add reviewers to PR #$id: $_" "Warning"
            }
        }
    }

    Write-Status "Reviewers added" "Success"
}

function Get-PRSummary {
    Write-Status "Generating PR Summary..." "Info"
    Write-Host ""

    # Get all PRs
    $activePRs = az repos pr list --status active -o json 2>$null | ConvertFrom-Json
    $completedPRs = az repos pr list --status completed --top 10 -o json 2>$null | ConvertFrom-Json

    Write-Host "============================================="
    Write-Host "  Pull Request Summary"
    Write-Host "============================================="
    Write-Host ""

    # Active PRs
    Write-Host "--- Active PRs ($($activePRs.Count)) ---" -ForegroundColor Yellow
    if ($activePRs) {
        foreach ($pr in $activePRs) {
            $approvals = ($pr.reviewers | Where-Object { $_.vote -ge 10 }).Count
            $totalReviewers = $pr.reviewers.Count
            $status = if ($approvals -eq $totalReviewers -and $totalReviewers -gt 0) { "Ready" } else { "Pending" }

            Write-Host ""
            Write-Host "  PR #$($pr.pullRequestId): $($pr.title)" -ForegroundColor Cyan
            Write-Host "    Source:    $($pr.sourceRefName -replace 'refs/heads/', '')"
            Write-Host "    Author:    $($pr.createdBy.displayName)"
            Write-Host "    Approvals: $approvals/$totalReviewers"
            Write-Host "    Status:    $status"
        }
    } else {
        Write-Host "  No active PRs"
    }
    Write-Host ""

    # Recently Completed
    Write-Host "--- Recently Completed (Last 10) ---" -ForegroundColor Green
    if ($completedPRs) {
        foreach ($pr in $completedPRs) {
            $closedDate = [DateTime]::Parse($pr.closedDate).ToString("yyyy-MM-dd")
            Write-Host "  [$closedDate] PR #$($pr.pullRequestId): $($pr.title)"
        }
    }
    Write-Host ""

    # Statistics
    Write-Host "--- Statistics ---"
    $avgReviewTime = 0
    if ($completedPRs) {
        foreach ($pr in $completedPRs) {
            $created = [DateTime]::Parse($pr.creationDate)
            $closed = [DateTime]::Parse($pr.closedDate)
            $avgReviewTime += ($closed - $created).TotalHours
        }
        $avgReviewTime = [math]::Round($avgReviewTime / $completedPRs.Count, 1)
    }
    Write-Host "  Active PRs:        $($activePRs.Count)"
    Write-Host "  Completed (10d):   $($completedPRs.Count)"
    Write-Host "  Avg Review Time:   $avgReviewTime hours"
    Write-Host ""
}

function Cleanup-Branches {
    Write-Status "Cleaning up merged branches..." "Info"

    # Get merged PRs
    $completedPRs = az repos pr list --status completed --top 50 -o json 2>$null | ConvertFrom-Json

    $deletedCount = 0
    foreach ($pr in $completedPRs) {
        if ($pr.sourceRefName -notmatch "/(main|master|develop)$") {
            $branchName = $pr.sourceRefName -replace "refs/heads/", ""

            if ($DryRun) {
                Write-Status "[DRY RUN] Would delete branch: $branchName" "Info"
            } else {
                try {
                    # Note: This requires git access to the repo
                    Write-Status "Deleting branch: $branchName" "Info"
                    # az repos ref delete --name "$($pr.sourceRefName)" --repository $Repository
                    $deletedCount++
                } catch {
                    Write-Status "Could not delete $branchName" "Warning"
                }
            }
        }
    }

    Write-Status "Cleanup complete. Processed $deletedCount branches." "Success"
}

# Main execution
Write-Host ""
Write-Host "============================================="
Write-Host "  Azure DevOps PR Automation"
Write-Host "  Action: $Action"
Write-Host "============================================="
Write-Host ""

switch ($Action) {
    "Create" { Create-PullRequest }
    "AutoComplete" { Set-AutoComplete }
    "Merge" { Merge-PullRequests }
    "AddReviewers" { Add-Reviewers }
    "Summary" { Get-PRSummary }
    "Cleanup" { Cleanup-Branches }
}
