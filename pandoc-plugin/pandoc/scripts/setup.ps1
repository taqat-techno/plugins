# Pandoc Plugin - Automated Setup Script
# =======================================
# This script installs and configures Pandoc + LaTeX for PDF generation
# Run as: powershell -ExecutionPolicy Bypass -File setup.ps1

param(
    [switch]$SkipLatex,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-Status($message, $color = "Cyan") {
    if (-not $Quiet) {
        Write-Host $message -ForegroundColor $color
    }
}

function Write-Success($message) {
    Write-Status "[OK] $message" "Green"
}

function Write-Warning($message) {
    Write-Status "[!] $message" "Yellow"
}

function Write-Error($message) {
    Write-Status "[X] $message" "Red"
}

Write-Status "============================================" "White"
Write-Status "   Pandoc Plugin - Automated Setup" "White"
Write-Status "============================================" "White"
Write-Status ""

# ============================================
# STEP 1: Check/Install Pandoc
# ============================================
Write-Status "Step 1: Checking Pandoc installation..."

$pandocPath = $null
$pandocPaths = @(
    "$env:LOCALAPPDATA\Pandoc\pandoc.exe",
    "$env:ProgramFiles\Pandoc\pandoc.exe",
    "C:\Program Files\Pandoc\pandoc.exe"
)

foreach ($path in $pandocPaths) {
    if (Test-Path $path) {
        $pandocPath = $path
        break
    }
}

if (-not $pandocPath) {
    # Try to find in PATH
    $pandocInPath = Get-Command pandoc -ErrorAction SilentlyContinue
    if ($pandocInPath) {
        $pandocPath = $pandocInPath.Source
    }
}

if ($pandocPath) {
    $version = & $pandocPath --version | Select-Object -First 1
    Write-Success "Pandoc found: $version"
    Write-Status "   Path: $pandocPath"
} else {
    Write-Warning "Pandoc not found. Installing via winget..."
    try {
        winget install JohnMacFarlane.Pandoc --accept-package-agreements --accept-source-agreements --silent
        Write-Success "Pandoc installed successfully"
        $pandocPath = "$env:LOCALAPPDATA\Pandoc\pandoc.exe"
    } catch {
        Write-Error "Failed to install Pandoc. Please install manually from https://pandoc.org/installing.html"
        exit 1
    }
}

# ============================================
# STEP 2: Add Pandoc to PATH (session)
# ============================================
Write-Status ""
Write-Status "Step 2: Configuring PATH..."

$pandocDir = Split-Path $pandocPath -Parent
if ($env:PATH -notlike "*$pandocDir*") {
    $env:PATH = "$pandocDir;$env:PATH"
    Write-Success "Added Pandoc to session PATH"
} else {
    Write-Success "Pandoc already in PATH"
}

# ============================================
# STEP 3: Check/Install LaTeX (MiKTeX)
# ============================================
if (-not $SkipLatex) {
    Write-Status ""
    Write-Status "Step 3: Checking LaTeX installation..."

    $miktexPath = $null
    $miktexPaths = @(
        "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe",
        "$env:ProgramFiles\MiKTeX\miktex\bin\x64\pdflatex.exe",
        "C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe"
    )

    foreach ($path in $miktexPaths) {
        if (Test-Path $path) {
            $miktexPath = $path
            break
        }
    }

    if (-not $miktexPath) {
        $pdflatexInPath = Get-Command pdflatex -ErrorAction SilentlyContinue
        if ($pdflatexInPath) {
            $miktexPath = $pdflatexInPath.Source
        }
    }

    if ($miktexPath) {
        Write-Success "LaTeX (MiKTeX) found"
        Write-Status "   Path: $miktexPath"
    } else {
        Write-Warning "LaTeX not found. Installing MiKTeX via winget..."
        Write-Status "   This may take a few minutes (140MB download)..."
        try {
            winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements --silent
            Write-Success "MiKTeX installed successfully"
            $miktexPath = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
        } catch {
            Write-Warning "Failed to install MiKTeX. PDF generation will not be available."
            Write-Warning "Install manually from https://miktex.org/download"
        }
    }

    # ============================================
    # STEP 4: Configure MiKTeX Auto-Install
    # ============================================
    if ($miktexPath) {
        Write-Status ""
        Write-Status "Step 4: Configuring MiKTeX auto-install..."

        $miktexDir = Split-Path (Split-Path (Split-Path (Split-Path $miktexPath -Parent) -Parent) -Parent) -Parent
        $initexmf = Join-Path $miktexDir "miktex\bin\x64\initexmf.exe"
        $miktexCli = Join-Path $miktexDir "miktex\bin\x64\miktex.exe"

        if (Test-Path $initexmf) {
            try {
                & $initexmf --set-config-value="[MPM]AutoInstall=1" 2>$null
                Write-Success "MiKTeX auto-install enabled (no more popups!)"
            } catch {
                Write-Warning "Could not enable auto-install"
            }
        }

        # Add MiKTeX to PATH
        $miktexBinDir = Split-Path $miktexPath -Parent
        if ($env:PATH -notlike "*$miktexBinDir*") {
            $env:PATH = "$miktexBinDir;$env:PATH"
            Write-Success "Added MiKTeX to session PATH"
        }

        # ============================================
        # STEP 5: Pre-install Required LaTeX Packages
        # ============================================
        Write-Status ""
        Write-Status "Step 5: Installing required LaTeX packages..."
        Write-Status "   (This prevents popup dialogs during PDF conversion)"

        if (Test-Path $miktexCli) {
            $packages = @(
                "parskip", "geometry", "fancyvrb", "framed", "booktabs",
                "longtable", "upquote", "microtype", "bookmark", "etoolbox",
                "footnotehyper", "footnote", "hyperref", "ulem", "listings",
                "caption", "float", "setspace", "amsmath", "lm", "xcolor",
                "graphicx", "grffile", "unicode-math", "fontspec", "selnolig",
                "natbib", "biblatex", "csquotes", "soul", "enumitem", "titlesec"
            )

            $installed = 0
            $total = $packages.Count

            foreach ($pkg in $packages) {
                $installed++
                if (-not $Quiet) {
                    Write-Progress -Activity "Installing LaTeX packages" -Status "$pkg ($installed/$total)" -PercentComplete (($installed / $total) * 100)
                }
                try {
                    & $miktexCli packages install $pkg 2>$null | Out-Null
                } catch {
                    # Package might already be installed or not available
                }
            }

            Write-Progress -Activity "Installing LaTeX packages" -Completed
            Write-Success "LaTeX packages installed ($total packages)"
        } else {
            Write-Warning "Could not find MiKTeX CLI. Some packages may need manual installation."
        }
    }
} else {
    Write-Status ""
    Write-Status "Step 3-5: Skipped LaTeX installation (--SkipLatex)"
}

# ============================================
# STEP 6: Verify Installation
# ============================================
Write-Status ""
Write-Status "Step 6: Verifying installation..."

$allGood = $true

# Check Pandoc
$pandocCheck = & $pandocPath --version 2>$null | Select-Object -First 1
if ($pandocCheck) {
    Write-Success "Pandoc: $pandocCheck"
} else {
    Write-Error "Pandoc verification failed"
    $allGood = $false
}

# Check LaTeX
if (-not $SkipLatex -and $miktexPath) {
    $latexCheck = & $miktexPath --version 2>$null | Select-Object -First 1
    if ($latexCheck -like "*pdfTeX*") {
        Write-Success "LaTeX: $latexCheck"
    } else {
        Write-Warning "LaTeX verification: Could not verify"
    }
}

# ============================================
# DONE
# ============================================
Write-Status ""
Write-Status "============================================" "White"
if ($allGood) {
    Write-Status "   Setup Complete!" "Green"
    Write-Status "============================================" "White"
    Write-Status ""
    Write-Status "You can now use:" "White"
    Write-Status "  /pandoc-pdf    - Convert to PDF" "Cyan"
    Write-Status "  /pandoc-docx   - Convert to Word" "Cyan"
    Write-Status "  /pandoc-html   - Convert to HTML" "Cyan"
    Write-Status "  /pandoc-epub   - Create eBooks" "Cyan"
    Write-Status "  /pandoc-slides - Create presentations" "Cyan"
    Write-Status ""
    if (-not $SkipLatex) {
        Write-Status "NOTE: You may need to restart your terminal" "Yellow"
        Write-Status "      for PATH changes to take effect." "Yellow"
    }
} else {
    Write-Status "   Setup completed with warnings" "Yellow"
    Write-Status "============================================" "White"
    Write-Status "Some features may not work correctly." "Yellow"
}

Write-Status ""
