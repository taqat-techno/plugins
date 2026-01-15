#!/bin/bash
# Pandoc Plugin - Automated Setup Script
# =======================================
# This script installs and configures Pandoc + LaTeX for PDF generation
# Run as: bash setup.sh

set -e

SKIP_LATEX=false
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-latex) SKIP_LATEX=true; shift ;;
        --quiet) QUIET=true; shift ;;
        *) shift ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

log() { [[ "$QUIET" != "true" ]] && echo -e "${CYAN}$1${NC}"; }
success() { [[ "$QUIET" != "true" ]] && echo -e "${GREEN}[OK] $1${NC}"; }
warn() { [[ "$QUIET" != "true" ]] && echo -e "${YELLOW}[!] $1${NC}"; }
error() { echo -e "${RED}[X] $1${NC}"; }

echo -e "${WHITE}============================================${NC}"
echo -e "${WHITE}   Pandoc Plugin - Automated Setup${NC}"
echo -e "${WHITE}============================================${NC}"
echo ""

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

log "Detected OS: $OS"
echo ""

# ============================================
# STEP 1: Check/Install Pandoc
# ============================================
log "Step 1: Checking Pandoc installation..."

if command -v pandoc &> /dev/null; then
    PANDOC_VERSION=$(pandoc --version | head -1)
    success "Pandoc found: $PANDOC_VERSION"
else
    warn "Pandoc not found. Installing..."

    case $OS in
        linux)
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install -y pandoc
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y pandoc
            elif command -v pacman &> /dev/null; then
                sudo pacman -S --noconfirm pandoc
            else
                error "Could not detect package manager. Install Pandoc manually."
                exit 1
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install pandoc
            else
                error "Homebrew not found. Install from https://pandoc.org/installing.html"
                exit 1
            fi
            ;;
        windows)
            warn "On Windows, run: winget install JohnMacFarlane.Pandoc"
            exit 1
            ;;
        *)
            error "Unsupported OS. Install Pandoc manually from https://pandoc.org/installing.html"
            exit 1
            ;;
    esac

    success "Pandoc installed"
fi

# ============================================
# STEP 2: Check/Install LaTeX
# ============================================
if [[ "$SKIP_LATEX" != "true" ]]; then
    echo ""
    log "Step 2: Checking LaTeX installation..."

    if command -v pdflatex &> /dev/null; then
        LATEX_VERSION=$(pdflatex --version | head -1)
        success "LaTeX found: $LATEX_VERSION"
    else
        warn "LaTeX not found. Installing..."

        case $OS in
            linux)
                if command -v apt &> /dev/null; then
                    sudo apt install -y texlive texlive-latex-extra texlive-fonts-recommended texlive-xetex
                elif command -v dnf &> /dev/null; then
                    sudo dnf install -y texlive texlive-latex texlive-xetex
                elif command -v pacman &> /dev/null; then
                    sudo pacman -S --noconfirm texlive-core texlive-latexextra
                fi
                ;;
            macos)
                if command -v brew &> /dev/null; then
                    brew install --cask mactex-no-gui
                    # Or smaller: brew install basictex
                fi
                ;;
            windows)
                warn "On Windows, run: winget install MiKTeX.MiKTeX"
                ;;
        esac

        if command -v pdflatex &> /dev/null; then
            success "LaTeX installed"
        else
            warn "LaTeX installation may require restart or PATH update"
        fi
    fi
else
    echo ""
    log "Step 2: Skipped LaTeX installation (--skip-latex)"
fi

# ============================================
# STEP 3: Verify Installation
# ============================================
echo ""
log "Step 3: Verifying installation..."

ALL_GOOD=true

if command -v pandoc &> /dev/null; then
    success "Pandoc: $(pandoc --version | head -1)"
else
    error "Pandoc not found"
    ALL_GOOD=false
fi

if [[ "$SKIP_LATEX" != "true" ]]; then
    if command -v pdflatex &> /dev/null; then
        success "LaTeX: Available"
    else
        warn "LaTeX: Not available (PDF generation disabled)"
    fi
fi

# ============================================
# DONE
# ============================================
echo ""
echo -e "${WHITE}============================================${NC}"
if [[ "$ALL_GOOD" == "true" ]]; then
    echo -e "${GREEN}   Setup Complete!${NC}"
    echo -e "${WHITE}============================================${NC}"
    echo ""
    echo -e "${WHITE}You can now use:${NC}"
    echo -e "${CYAN}  /pandoc-pdf    - Convert to PDF${NC}"
    echo -e "${CYAN}  /pandoc-docx   - Convert to Word${NC}"
    echo -e "${CYAN}  /pandoc-html   - Convert to HTML${NC}"
    echo -e "${CYAN}  /pandoc-epub   - Create eBooks${NC}"
    echo -e "${CYAN}  /pandoc-slides - Create presentations${NC}"
else
    echo -e "${YELLOW}   Setup completed with warnings${NC}"
    echo -e "${WHITE}============================================${NC}"
fi
echo ""
