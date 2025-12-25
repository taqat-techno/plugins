<#
.SYNOPSIS
    Configure Azure DevOps CLI defaults for TaqaTechno organization.

.DESCRIPTION
    Sets default organization, project, and other CLI configurations.
    Also validates the configuration by testing connectivity.

.PARAMETER Organization
    The Azure DevOps organization name. Default: TaqaTechno

.PARAMETER Project
    The default project name. Default: None (will prompt)

.PARAMETER PAT
    Personal Access Token. If not provided, will check environment variable.

.EXAMPLE
    .\configure_defaults.ps1 -Project "Relief Center"

.EXAMPLE
    .\configure_defaults.ps1 -Organization "TaqaTechno" -Project "KhairGate"

.NOTES
    Author: TAQAT Techno
    Version: 2.0.0
    Requires: Azure CLI with azure-devops extension
#>

param(
    [string]$Organization = "TaqaTechno",
    [string]$Project = "",
    [string]$PAT = "",
    [switch]$ListProjects,
    [switch]$Validate,
    [switch]$Reset
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

function Test-AzureCLI {
    try {
        $null = az --version 2>&1
        return $true
    } catch {
        return $false
    }
}

function Test-DevOpsExtension {
    $extensions = az extension list --query "[?name=='azure-devops']" -o json 2>$null | ConvertFrom-Json
    return $extensions.Count -gt 0
}

function Get-CurrentDefaults {
    $config = az devops configure --list 2>$null
    $defaults = @{}

    foreach ($line in $config -split "`n") {
        if ($line -match "^(\w+)\s*=\s*(.+)$") {
            $defaults[$matches[1]] = $matches[2].Trim()
        }
    }

    return $defaults
}

# Main execution
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Azure DevOps CLI Configuration Utility" -ForegroundColor Cyan
Write-Host "  Organization: $Organization" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Status "Checking prerequisites..."

if (-not (Test-AzureCLI)) {
    Write-Status "Azure CLI is not installed. Run install_cli.ps1 first." "Error"
    exit 1
}

if (-not (Test-DevOpsExtension)) {
    Write-Status "Azure DevOps extension not found. Installing..." "Warning"
    az extension add --name azure-devops --upgrade
}

Write-Status "Prerequisites OK" "Success"

# Handle reset
if ($Reset) {
    Write-Status "Resetting defaults..." "Warning"
    az devops configure --defaults organization="" project=""
    Write-Status "Defaults cleared" "Success"
    exit 0
}

# Set PAT if provided
if ($PAT) {
    Write-Status "Setting PAT token..."
    [System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', $PAT, 'User')
    $env:AZURE_DEVOPS_EXT_PAT = $PAT
    Write-Status "PAT token configured" "Success"
} elseif (-not $env:AZURE_DEVOPS_EXT_PAT) {
    Write-Status "No PAT token found. Set AZURE_DEVOPS_EXT_PAT environment variable or use -PAT parameter" "Warning"
}

# Set organization default
$orgUrl = "https://dev.azure.com/$Organization"
Write-Status "Setting organization default: $orgUrl"
az devops configure --defaults organization=$orgUrl

# List projects if requested
if ($ListProjects -or (-not $Project)) {
    Write-Status "Available projects in $Organization`:" "Info"
    Write-Host ""

    try {
        $projects = az devops project list --query "value[].name" -o tsv 2>$null
        if ($projects) {
            $i = 1
            foreach ($proj in $projects -split "`n") {
                Write-Host "  $i. $proj"
                $i++
            }
            Write-Host ""

            if (-not $Project) {
                $selection = Read-Host "Enter project number or name (or press Enter to skip)"
                if ($selection -match "^\d+$") {
                    $projectList = $projects -split "`n"
                    $Project = $projectList[[int]$selection - 1]
                } elseif ($selection) {
                    $Project = $selection
                }
            }
        }
    } catch {
        Write-Status "Could not list projects. Check authentication." "Warning"
    }
}

# Set project default
if ($Project) {
    Write-Status "Setting project default: $Project"
    az devops configure --defaults project="$Project"
}

# Show current configuration
Write-Host ""
Write-Status "Current Configuration:" "Info"
Write-Host "----------------------------------------"
az devops configure --list
Write-Host "----------------------------------------"

# Validate if requested
if ($Validate) {
    Write-Host ""
    Write-Status "Validating configuration..." "Info"

    try {
        $projects = az devops project list --top 1 -o json 2>$null | ConvertFrom-Json
        if ($projects.value.Count -gt 0) {
            Write-Status "Connection successful!" "Success"
            Write-Status "Found $($projects.count) projects" "Success"
        }
    } catch {
        Write-Status "Validation failed: $_" "Error"
        exit 1
    }
}

Write-Host ""
Write-Status "Configuration complete!" "Success"
Write-Host ""
Write-Host "Quick test commands:" -ForegroundColor Cyan
Write-Host "  az devops project list --output table"
Write-Host "  az boards work-item show --id 1"
Write-Host ""
