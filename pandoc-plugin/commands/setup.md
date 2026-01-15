---
title: 'Pandoc Setup'
read_only: false
type: 'command'
description: 'One-click installation of Pandoc and LaTeX with automatic configuration. Fixes all common installation issues.'
---

# /pandoc-setup - Automated Installation & Configuration

One-click setup that installs Pandoc, LaTeX, and configures everything for immediate use.

## Quick Start

Just run:
```
/pandoc-setup
```

This will:
1. Install Pandoc (if not installed)
2. Install MiKTeX/LaTeX (for PDF generation)
3. Enable auto-install for LaTeX packages (no more popups!)
4. Pre-install all required LaTeX packages
5. Configure PATH automatically

---

## What It Fixes

### Problem 1: MiKTeX Popup Dialogs
**Before**: Every PDF conversion shows popups asking to install packages
**After**: Auto-install enabled, packages pre-installed - no interruptions!

### Problem 2: Missing LaTeX Packages
**Before**: `parskip.sty not found` errors
**After**: All 30+ required packages pre-installed

### Problem 3: PATH Issues
**Before**: `pandoc: command not found`
**After**: PATH configured automatically

---

## Platform-Specific Commands

### Windows (PowerShell)
```powershell
# Full setup (Pandoc + LaTeX)
powershell -ExecutionPolicy Bypass -File "C:\odoo\tmp\plugins\pandoc-plugin\pandoc\scripts\setup.ps1"

# Skip LaTeX (Pandoc only)
powershell -ExecutionPolicy Bypass -File "C:\odoo\tmp\plugins\pandoc-plugin\pandoc\scripts\setup.ps1" -SkipLatex

# Quiet mode
powershell -ExecutionPolicy Bypass -File "C:\odoo\tmp\plugins\pandoc-plugin\pandoc\scripts\setup.ps1" -Quiet
```

### Linux/macOS (Bash)
```bash
# Full setup
bash pandoc-plugin/pandoc/scripts/setup.sh

# Skip LaTeX
bash pandoc-plugin/pandoc/scripts/setup.sh --skip-latex
```

---

## Manual Quick Setup

If the script doesn't work, use these commands:

### Windows
```powershell
# 1. Install Pandoc
winget install JohnMacFarlane.Pandoc --accept-package-agreements --accept-source-agreements

# 2. Install MiKTeX (for PDF)
winget install MiKTeX.MiKTeX --accept-package-agreements --accept-source-agreements

# 3. Enable auto-install (RUN THIS - prevents popup dialogs!)
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value="[MPM]AutoInstall=1"

# 4. Install required packages
$packages = @('parskip','geometry','fancyvrb','framed','booktabs','longtable','upquote','microtype','bookmark','etoolbox','hyperref','ulem','listings','caption','float','setspace','amsmath','lm','xcolor')
foreach ($p in $packages) { & "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\miktex.exe" packages install $p }
```

### Linux (Ubuntu/Debian)
```bash
# 1. Install Pandoc
sudo apt install pandoc

# 2. Install LaTeX (for PDF)
sudo apt install texlive texlive-latex-extra texlive-fonts-recommended
```

### macOS
```bash
# 1. Install Pandoc
brew install pandoc

# 2. Install LaTeX (for PDF)
brew install --cask mactex
# Or smaller: brew install basictex
```

---

## Verify Installation

After setup, verify everything works:

```bash
# Check Pandoc
pandoc --version

# Check LaTeX (for PDF)
pdflatex --version

# Test conversion
echo "# Test" | pandoc -o test.pdf
```

---

## Installed LaTeX Packages

The setup pre-installs these packages to prevent popup dialogs:

| Package | Purpose |
|---------|---------|
| parskip | Paragraph spacing |
| geometry | Page margins |
| fancyvrb | Verbatim/code blocks |
| framed | Framed boxes |
| booktabs | Professional tables |
| longtable | Multi-page tables |
| hyperref | PDF links |
| listings | Code listings |
| amsmath | Math formulas |
| xcolor | Colors |
| graphicx | Images |
| ... | +20 more |

---

## Troubleshooting

### "pandoc: command not found"
```powershell
# Windows: Add to PATH manually
$env:PATH = "$env:LOCALAPPDATA\Pandoc;$env:PATH"

# Or restart terminal after installation
```

### "pdflatex: command not found"
```powershell
# Windows: Add MiKTeX to PATH
$env:PATH = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64;$env:PATH"
```

### MiKTeX popup still appearing
```powershell
# Re-enable auto-install
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\initexmf.exe" --set-config-value="[MPM]AutoInstall=1"
```

### Missing package error
```powershell
# Install specific package
& "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64\miktex.exe" packages install <package-name>
```

---

## After Setup

Once setup completes, you can use all Pandoc commands:

| Command | Description |
|---------|-------------|
| `/pandoc-pdf` | Convert to PDF |
| `/pandoc-docx` | Convert to Word |
| `/pandoc-html` | Convert to HTML |
| `/pandoc-epub` | Create eBooks |
| `/pandoc-slides` | Create presentations |
| `/pandoc-convert` | General conversion |

---

*Pandoc Plugin v1.0*
*Automated Setup & Configuration*
