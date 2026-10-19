# Pandoc Plugin - Windows setup
# =============================
# Checks for Pandoc and a LaTeX engine (MiKTeX) and installs what is missing.
#
#   powershell -ExecutionPolicy Bypass -File setup.ps1 [-SkipLatex] [-Quiet]
#       [-PrintOnly] [-Install] [-EnableAutoInstall]
#
# Consent rules:
#   - Nothing is installed without the user's go-ahead. winget runs WITHOUT
#     --accept-package-agreements / --accept-source-agreements, so the user
#     reads and accepts the licence terms themselves.
#   - When stdin is not a terminal (for example when Claude runs this script),
#     the script only checks and PRINTS the install commands for the user to run
#     in their own terminal, then exits 0. -Install overrides that; -PrintOnly
#     forces it.
#   - Enabling MiKTeX on-the-fly package installation changes persistent MiKTeX
#     configuration for this user, so it happens only with -EnableAutoInstall.
#
# Sizes: Pandoc about 35 MB; MiKTeX basic about 140 MB download, more as
# packages are added.

param(
    [switch]$SkipLatex,
    [switch]$Quiet,
    [switch]$PrintOnly,
    [switch]$Install,
    [switch]$EnableAutoInstall
)

$ErrorActionPreference = "Stop"

function Write-Status($message, $color = "Cyan") {
    if (-not $Quiet) {
        Write-Host $message -ForegroundColor $color
    }
}

function Write-Ok($message) { Write-Status "[OK] $message" "Green" }
function Write-Warn($message) { Write-Status "[!] $message" "Yellow" }
# Failures are printed even with -Quiet.
function Write-Fail($message) { Write-Host "[X] $message" -ForegroundColor Red }

# Decide whether installers may run.
$interactive = $false
try { $interactive = -not [Console]::IsInputRedirected } catch { $interactive = $false }
$mayInstall = (-not $PrintOnly) -and ($Install -or $interactive)

function Find-Exe([string[]]$candidates, [string]$name) {
    foreach ($path in $candidates) {
        if ($path -and (Test-Path -LiteralPath $path)) { return $path }
    }
    $found = Get-Command $name -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    return $null
}

function Invoke-Winget([string]$id) {
    # Returns $true only when winget exits 0. A native command's failure does not
    # throw in Windows PowerShell 5.1, so $LASTEXITCODE is the only reliable signal.
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Fail "winget is not available. Install manually (see the URL below)."
        return $false
    }
    # Out-Host keeps winget's text out of this function's return value.
    & $winget.Source install --id $id -e | Out-Host
    return ($LASTEXITCODE -eq 0)
}

$pandocCandidates = @(
    "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
    "$env:ProgramFiles\Pandoc\pandoc.exe"
)
$latexCandidates = @(
    "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe",
    "$env:ProgramFiles\MiKTeX\miktex\bin\x64\pdflatex.exe"
)

Write-Status "============================================" "White"
Write-Status "   Pandoc Plugin - Setup" "White"
Write-Status "============================================" "White"
if (-not $mayInstall) {
    Write-Status "Check-only mode: nothing will be installed. Run the printed commands" "Yellow"
    Write-Status "yourself in a terminal (or re-run this script there) to install." "Yellow"
}
Write-Status ""

$pending = @()

# --------------------------------------------------------------- Step 1: Pandoc
Write-Status "Step 1: Checking Pandoc..."
$pandocPath = Find-Exe $pandocCandidates "pandoc"

if ($pandocPath) {
    $version = & $pandocPath --version | Select-Object -First 1
    Write-Ok "Pandoc found: $version ($pandocPath)"
} elseif ($mayInstall) {
    Write-Warn "Pandoc not found. Installing with winget (you will be asked to accept its terms)..."
    if (Invoke-Winget "JohnMacFarlane.Pandoc") {
        $pandocPath = Find-Exe $pandocCandidates "pandoc"
    }
    if ($pandocPath) {
        Write-Ok "Pandoc installed: $pandocPath"
    } else {
        Write-Fail "Pandoc installation failed or pandoc.exe was not found afterwards."
        Write-Fail "Install manually from https://pandoc.org/installing.html"
        exit 1
    }
} else {
    Write-Warn "Pandoc not found (about 35 MB)."
    $pending += "winget install --id JohnMacFarlane.Pandoc -e"
}

if ($pandocPath) {
    $pandocDir = Split-Path $pandocPath -Parent
    if ($env:PATH -notlike "*$pandocDir*") { $env:PATH = "$pandocDir;$env:PATH" }
}

# --------------------------------------------------------------- Step 2: LaTeX
$latexPath = $null
if (-not $SkipLatex) {
    Write-Status ""
    Write-Status "Step 2: Checking LaTeX (needed only for PDF output)..."
    $latexPath = Find-Exe $latexCandidates "pdflatex"

    if ($latexPath) {
        Write-Ok "LaTeX found: $latexPath"
    } elseif ($mayInstall) {
        Write-Warn "LaTeX not found. Installing MiKTeX with winget (about 140 MB)..."
        if (Invoke-Winget "MiKTeX.MiKTeX") {
            $latexPath = Find-Exe $latexCandidates "pdflatex"
        }
        if ($latexPath) {
            Write-Ok "MiKTeX installed: $latexPath"
        } else {
            Write-Warn "MiKTeX installation failed or pdflatex.exe was not found afterwards."
            Write-Warn "PDF output will not work. Install manually from https://miktex.org/download"
        }
    } else {
        Write-Warn "LaTeX not found (MiKTeX basic, about 140 MB)."
        $pending += "winget install --id MiKTeX.MiKTeX -e"
    }
}

# ------------------------------------------------- Step 3: MiKTeX configuration
if ($latexPath) {
    $binDir = Split-Path $latexPath -Parent
    if ($env:PATH -notlike "*$binDir*") { $env:PATH = "$binDir;$env:PATH" }
    $initexmf = Join-Path $binDir "initexmf.exe"
    $miktexCli = Join-Path $binDir "miktex.exe"

    Write-Status ""
    if ($EnableAutoInstall -and $mayInstall) {
        Write-Status "Step 3: Enabling MiKTeX on-the-fly package installation (user consented)..."
        if (Test-Path -LiteralPath $initexmf) {
            & $initexmf --set-config-value="[MPM]AutoInstall=1"
            if ($LASTEXITCODE -eq 0) { Write-Ok "MiKTeX AutoInstall enabled" }
            else { Write-Warn "Could not enable AutoInstall (initexmf exit $LASTEXITCODE)" }
        } else {
            Write-Warn "initexmf.exe not found next to pdflatex; AutoInstall unchanged."
        }

        Write-Status "Pre-installing common LaTeX packages (downloads from the MiKTeX repository)..."
        if (Test-Path -LiteralPath $miktexCli) {
            $packages = @(
                "parskip", "geometry", "fancyvrb", "framed", "booktabs",
                "longtable", "upquote", "microtype", "bookmark", "etoolbox",
                "footnotehyper", "footnote", "hyperref", "ulem", "listings",
                "caption", "float", "setspace", "amsmath", "lm", "xcolor",
                "graphicx", "grffile", "unicode-math", "fontspec", "selnolig",
                "natbib", "biblatex", "csquotes", "soul", "enumitem", "titlesec"
            )
            $failed = @()
            foreach ($pkg in $packages) {
                # In PowerShell 5.1 a native command's stderr becomes a terminating
                # error under ErrorActionPreference=Stop, hence the try.
                try {
                    & $miktexCli packages install $pkg 2>$null | Out-Null
                    if ($LASTEXITCODE -ne 0) { $failed += $pkg }
                } catch { $failed += $pkg }
            }
            if ($failed.Count -eq 0) { Write-Ok "LaTeX packages ready ($($packages.Count))" }
            else { Write-Warn "Not installed (may already exist or be unavailable): $($failed -join ', ')" }
        } else {
            Write-Warn "miktex.exe not found; skipped package pre-install."
        }
    } else {
        Write-Status "Step 3: MiKTeX configuration left unchanged."
        Write-Status "   Optional: let MiKTeX download missing LaTeX packages on demand instead of"
        Write-Status "   showing a dialog for each one. This changes persistent MiKTeX settings for"
        Write-Status "   your user account; re-run with -EnableAutoInstall, or run:"
        Write-Status "     initexmf --set-config-value=[MPM]AutoInstall=1"
    }
}

# --------------------------------------------------------------- Step 4: verify
Write-Status ""
Write-Status "Step 4: Summary"

if ($pending.Count -gt 0) {
    Write-Status "Run these yourself in a terminal to install what is missing:" "Yellow"
    foreach ($cmd in $pending) { Write-Status "  $cmd" "White" }
    Write-Status "Then open a new terminal and run: pandoc --version" "Yellow"
    exit 0
}

$pandocCheck = $null
if ($pandocPath) { $pandocCheck = & $pandocPath --version 2>$null | Select-Object -First 1 }
if ($pandocCheck) {
    Write-Ok "Pandoc: $pandocCheck"
} else {
    Write-Fail "Pandoc verification failed"
    exit 1
}

if (-not $SkipLatex) {
    if ($latexPath) { Write-Ok "LaTeX: $latexPath" }
    else { Write-Warn "LaTeX: not available (PDF output disabled)" }
}

Write-Status ""
Write-Status "Setup complete. Open a new terminal if PATH changed." "Green"
exit 0
