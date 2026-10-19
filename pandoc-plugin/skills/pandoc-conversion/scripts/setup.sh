#!/usr/bin/env bash
# Pandoc Plugin - Linux / macOS setup
# ===================================
# Checks for Pandoc and a LaTeX engine and installs what is missing.
#
#   bash setup.sh [--skip-latex] [--quiet] [--print-only] [--install]
#
# Consent rules:
#   - Package managers run WITHOUT -y / --noconfirm, so the user confirms every
#     install and sees its size.
#   - When stdin is not a terminal (for example when Claude runs this script),
#     sudo and the package managers cannot ask, so the script only checks and
#     PRINTS the commands for the user to run in their own terminal, then exits 0.
#     --install overrides that; --print-only forces it.
#
# Sizes (approximate): pandoc 30-100 MB; TeX Live via apt/dnf with the extras
# below 500 MB - 1 GB; MacTeX about 5 GB (BasicTeX about 100 MB is enough for
# most documents; add packages later with tlmgr).

set -e

SKIP_LATEX=false
QUIET=false
PRINT_ONLY=false
FORCE_INSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-latex) SKIP_LATEX=true; shift ;;
        --quiet) QUIET=true; shift ;;
        --print-only) PRINT_ONLY=true; shift ;;
        --install) FORCE_INSTALL=true; shift ;;
        *) shift ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Each helper returns 0 even under --quiet: a bare `[[ ]] && echo` returns 1 when
# the test is false, which aborted the whole script under `set -e`.
log()     { if [[ "$QUIET" != "true" ]]; then echo -e "${CYAN}$1${NC}"; fi; return 0; }
success() { if [[ "$QUIET" != "true" ]]; then echo -e "${GREEN}[OK] $1${NC}"; fi; return 0; }
warn()    { if [[ "$QUIET" != "true" ]]; then echo -e "${YELLOW}[!] $1${NC}"; fi; return 0; }
error()   { echo -e "${RED}[X] $1${NC}"; return 0; }

MAY_INSTALL=false
if [[ "$PRINT_ONLY" != "true" ]]; then
    if [[ "$FORCE_INSTALL" == "true" || -t 0 ]]; then
        MAY_INSTALL=true
    fi
fi

PENDING=()

OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

log "Pandoc Plugin - Setup (detected OS: $OS)"
if [[ "$MAY_INSTALL" != "true" ]]; then
    warn "Check-only mode: nothing will be installed. Run the printed commands yourself in a terminal."
fi

# The install command for a package on this host, or empty when unknown.
install_cmd() {
    local what=$1
    case $OS in
        linux)
            if command -v apt-get &> /dev/null; then
                if [[ "$what" == "pandoc" ]]; then echo "sudo apt-get install pandoc"
                else echo "sudo apt-get install texlive texlive-latex-extra texlive-fonts-recommended texlive-xetex"; fi
            elif command -v dnf &> /dev/null; then
                if [[ "$what" == "pandoc" ]]; then echo "sudo dnf install pandoc"
                else echo "sudo dnf install texlive texlive-latex texlive-xetex"; fi
            elif command -v pacman &> /dev/null; then
                if [[ "$what" == "pandoc" ]]; then echo "sudo pacman -S pandoc"
                else echo "sudo pacman -S texlive-core texlive-latexextra"; fi
            fi
            ;;
        macos)
            if command -v brew &> /dev/null; then
                if [[ "$what" == "pandoc" ]]; then echo "brew install pandoc"
                else echo "brew install --cask basictex"; fi
            fi
            ;;
        windows)
            if [[ "$what" == "pandoc" ]]; then echo "winget install --id JohnMacFarlane.Pandoc -e"
            else echo "winget install --id MiKTeX.MiKTeX -e"; fi
            ;;
    esac
    return 0
}

# Install (when allowed) or queue the command for the user. Returns 0 always.
ensure() {
    local what=$1 label=$2
    local cmd
    cmd=$(install_cmd "$what")
    if [[ -z "$cmd" ]]; then
        error "No known package manager for $label. See https://pandoc.org/installing.html"
        PENDING+=("install $label manually")
        return 0
    fi
    if [[ "$MAY_INSTALL" == "true" && "$OS" != "windows" ]]; then
        warn "$label not found. Running: $cmd"
        if ! $cmd; then
            error "$label installation failed: $cmd"
        fi
    else
        PENDING+=("$cmd")
    fi
    return 0
}

log "Step 1: Checking Pandoc..."
if command -v pandoc &> /dev/null; then
    success "Pandoc found: $(pandoc --version | head -1)"
else
    ensure pandoc "Pandoc"
fi

if [[ "$SKIP_LATEX" != "true" ]]; then
    log "Step 2: Checking LaTeX (needed only for PDF output)..."
    if command -v pdflatex &> /dev/null || command -v xelatex &> /dev/null; then
        success "LaTeX found"
    else
        ensure latex "LaTeX"
        if [[ "$OS" == "macos" ]]; then
            log "   Full MacTeX instead (about 5 GB): brew install --cask mactex-no-gui"
        fi
    fi
fi

echo ""
if [[ ${#PENDING[@]} -gt 0 ]]; then
    echo -e "${YELLOW}Run these yourself in a terminal to install what is missing:${NC}"
    for cmd in "${PENDING[@]}"; do
        echo "  $cmd"
    done
    echo -e "${YELLOW}Then open a new terminal and run: pandoc --version${NC}"
    exit 0
fi

if command -v pandoc &> /dev/null; then
    success "Pandoc: $(pandoc --version | head -1)"
else
    error "Pandoc not found after installation"
    exit 1
fi
if [[ "$SKIP_LATEX" != "true" ]]; then
    # BasicTeX/MacTeX put the engines in /Library/TeX/texbin, which is on PATH only
    # in a new shell.
    if command -v pdflatex &> /dev/null || command -v xelatex &> /dev/null \
        || [[ -x /Library/TeX/texbin/pdflatex || -x /Library/TeX/texbin/xelatex ]]; then
        success "LaTeX: available"
    else
        # Only reachable after an attempted install (a check-only run exited above).
        error "LaTeX: the install did not complete (PDF output disabled)."
        error "Re-run with --skip-latex if you do not need PDF output."
        exit 1
    fi
fi
log "Setup complete. Open a new terminal if PATH changed."
exit 0
