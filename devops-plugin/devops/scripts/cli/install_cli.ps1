<#
.SYNOPSIS
    Azure DevOps CLI Installer for Windows
.DESCRIPTION
    Installs Azure CLI, Azure DevOps extension, and configures authentication.
    Part of the DevOps Plugin for Claude Code.
.PARAMETER Organization
    Azure DevOps organization name (e.g., TaqaTechno)
.PARAMETER Project
    Default project name (optional)
.PARAMETER Pat
    Personal Access Token for authentication
.PARAMETER SetDefaults
    Whether to set organization/project defaults (default: true)
.PARAMETER SkipCliInstall
    Skip Azure CLI installation if already installed
.EXAMPLE
    .\install_cli.ps1 -Organization "TaqaTechno" -Project "Relief Center"
.EXAMPLE
    .\install_cli.ps1 -Organization "TaqaTechno" -Pat "your-pat-token"
.NOTES
    Author: TAQAT Techno
    Version: 2.0.0
    Requires: Windows PowerShell 5.1 or PowerShell 7+
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Organization = "TaqaTechno",

    [Parameter(Mandatory=$false)]
    [string]$Project = "",

    [Parameter(Mandatory=$false)]
    [string]$Pat = "",

    [Parameter(Mandatory=$false)]
    [switch]$SetDefaults = $true,

    [Parameter(Mandatory=$false)]
    [switch]$SkipCliInstall = $false
)

# Colors for output
function Write-Step { param($msg) Write-Host "`n[$([char]0x2713)] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "    $msg" -ForegroundColor Cyan }
function Write-Warn { param($msg) Write-Host "    [!] $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "    [X] $msg" -ForegroundColor Red }

# Header
Write-Host "`n" -NoNewline
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  AZURE DEVOPS CLI INSTALLER" -ForegroundColor Cyan
Write-Host "  DevOps Plugin for Claude Code v2.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# PHASE 1: Check Prerequisites
# ============================================
Write-Step "Phase 1: Checking Prerequisites"

# Check if running as admin (recommended but not required)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warn "Not running as Administrator. Some features may require elevation."
}

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
Write-Info "PowerShell Version: $($psVersion.Major).$($psVersion.Minor)"

# ============================================
# PHASE 2: Install Azure CLI
# ============================================
Write-Step "Phase 2: Checking Azure CLI"

$azInstalled = $false
try {
    $azVersion = az --version 2>&1 | Select-String "azure-cli" | ForEach-Object { $_.ToString().Split()[1] }
    if ($azVersion) {
        Write-Info "Azure CLI already installed: $azVersion"
        $azInstalled = $true
    }
} catch {
    Write-Info "Azure CLI not found"
}

if (-not $azInstalled -and -not $SkipCliInstall) {
    Write-Info "Installing Azure CLI..."

    # Try winget first (fastest)
    $wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetAvailable) {
        Write-Info "Using winget to install Azure CLI..."
        try {
            winget install -e --id Microsoft.AzureCLI --silent --accept-package-agreements --accept-source-agreements
            $azInstalled = $true
            Write-Info "Azure CLI installed via winget"
        } catch {
            Write-Warn "Winget installation failed, trying alternative..."
        }
    }

    # Fallback to MSI installer
    if (-not $azInstalled) {
        Write-Info "Downloading Azure CLI MSI installer..."
        $msiPath = "$env:TEMP\AzureCLI.msi"
        try {
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri "https://aka.ms/installazurecliwindows" -OutFile $msiPath

            Write-Info "Running MSI installer (this may take a few minutes)..."
            Start-Process msiexec.exe -Wait -ArgumentList "/I `"$msiPath`" /quiet"

            # Clean up
            Remove-Item $msiPath -ErrorAction SilentlyContinue

            Write-Info "Azure CLI installed via MSI"
            $azInstalled = $true
        } catch {
            Write-Err "Failed to install Azure CLI: $_"
            Write-Err "Please install manually from: https://aka.ms/installazurecliwindows"
            exit 1
        }
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# Verify Azure CLI
try {
    $azVersion = az --version 2>&1 | Select-String "azure-cli" | ForEach-Object { $_.ToString().Split()[1] }
    Write-Info "Azure CLI Version: $azVersion"
} catch {
    Write-Err "Azure CLI verification failed"
    exit 1
}

# ============================================
# PHASE 3: Install DevOps Extension
# ============================================
Write-Step "Phase 3: Installing Azure DevOps Extension"

# Check if extension is already installed
$extInstalled = $false
try {
    $extInfo = az extension show --name azure-devops 2>&1
    if ($extInfo -notlike "*not installed*") {
        $extVersion = ($extInfo | ConvertFrom-Json).version
        Write-Info "DevOps extension already installed: $extVersion"
        $extInstalled = $true

        # Check for updates
        Write-Info "Checking for updates..."
        az extension update --name azure-devops 2>&1 | Out-Null
    }
} catch {
    # Extension not installed
}

if (-not $extInstalled) {
    Write-Info "Installing azure-devops extension..."
    try {
        az extension add --name azure-devops --yes 2>&1 | Out-Null
        Write-Info "Azure DevOps extension installed successfully"
    } catch {
        Write-Err "Failed to install extension: $_"
        exit 1
    }
}

# Verify extension
try {
    $extInfo = az extension show --name azure-devops 2>&1 | ConvertFrom-Json
    Write-Info "Extension Version: $($extInfo.version)"
} catch {
    Write-Err "Extension verification failed"
    exit 1
}

# ============================================
# PHASE 4: Configure Defaults
# ============================================
if ($SetDefaults) {
    Write-Step "Phase 4: Configuring Defaults"

    # Set organization default
    $orgUrl = "https://dev.azure.com/$Organization"
    Write-Info "Setting organization: $orgUrl"
    az devops configure --defaults organization=$orgUrl 2>&1 | Out-Null

    # Set project default (if provided)
    if ($Project) {
        Write-Info "Setting default project: $Project"
        az devops configure --defaults project="$Project" 2>&1 | Out-Null
    }

    # Verify defaults
    $config = az devops configure --list 2>&1
    Write-Info "Current defaults:"
    $config | ForEach-Object { Write-Info "  $_" }
}

# ============================================
# PHASE 5: Configure Authentication
# ============================================
Write-Step "Phase 5: Configuring Authentication"

if ($Pat) {
    # Set PAT as environment variables (persistent)
    Write-Info "Setting PAT as environment variables..."

    # For CLI
    [System.Environment]::SetEnvironmentVariable('AZURE_DEVOPS_EXT_PAT', $Pat, 'User')
    $env:AZURE_DEVOPS_EXT_PAT = $Pat
    Write-Info "Set AZURE_DEVOPS_EXT_PAT (for CLI)"

    # For MCP
    [System.Environment]::SetEnvironmentVariable('ADO_PAT_TOKEN', $Pat, 'User')
    $env:ADO_PAT_TOKEN = $Pat
    Write-Info "Set ADO_PAT_TOKEN (for MCP)"

    # Enable hybrid mode
    [System.Environment]::SetEnvironmentVariable('DEVOPS_HYBRID_MODE', 'true', 'User')
    $env:DEVOPS_HYBRID_MODE = 'true'
    Write-Info "Set DEVOPS_HYBRID_MODE=true"

} else {
    Write-Warn "No PAT provided. You can set it later with:"
    Write-Info '  [System.Environment]::SetEnvironmentVariable("AZURE_DEVOPS_EXT_PAT", "your-pat", "User")'
    Write-Info '  [System.Environment]::SetEnvironmentVariable("ADO_PAT_TOKEN", "your-pat", "User")'
    Write-Info ""
    Write-Info "Or login interactively:"
    Write-Info "  az devops login --organization https://dev.azure.com/$Organization"
}

# ============================================
# PHASE 6: Validation
# ============================================
Write-Step "Phase 6: Validating Installation"

$validationPassed = $true

# Test CLI connection
if ($Pat -or $env:AZURE_DEVOPS_EXT_PAT) {
    Write-Info "Testing CLI connection..."
    try {
        $projects = az devops project list --output json 2>&1 | ConvertFrom-Json
        $projectCount = $projects.value.Count
        Write-Info "Connection successful: $projectCount projects found"

        # List first few projects
        $projects.value | Select-Object -First 3 | ForEach-Object {
            Write-Info "  - $($_.name)"
        }
        if ($projectCount -gt 3) {
            Write-Info "  ... and $($projectCount - 3) more"
        }
    } catch {
        Write-Warn "CLI connection test failed. Please verify your PAT token."
        $validationPassed = $false
    }
} else {
    Write-Warn "Skipping connection test (no PAT configured)"
}

# ============================================
# Summary
# ============================================
Write-Host "`n"
Write-Host "============================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Write-Host "CLI Status:" -ForegroundColor Cyan
Write-Host "  Azure CLI:        Installed ($azVersion)" -ForegroundColor White
Write-Host "  DevOps Extension: Installed ($($extInfo.version))" -ForegroundColor White
Write-Host "  Organization:     $Organization" -ForegroundColor White
if ($Project) {
    Write-Host "  Default Project:  $Project" -ForegroundColor White
}

Write-Host ""
Write-Host "Authentication:" -ForegroundColor Cyan
if ($Pat) {
    Write-Host "  AZURE_DEVOPS_EXT_PAT: Configured" -ForegroundColor White
    Write-Host "  ADO_PAT_TOKEN:        Configured" -ForegroundColor White
    Write-Host "  DEVOPS_HYBRID_MODE:   Enabled" -ForegroundColor White
} else {
    Write-Host "  Status: Not configured (set PAT to enable)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
if (-not $Pat) {
    Write-Host "  1. Set your PAT token (see instructions above)" -ForegroundColor White
}
Write-Host "  2. Configure MCP server in Claude Code settings" -ForegroundColor White
Write-Host "  3. Restart Claude Code" -ForegroundColor White
Write-Host "  4. Test with: az devops project list" -ForegroundColor White
Write-Host ""

# Return status
if ($validationPassed) {
    exit 0
} else {
    exit 1
}
